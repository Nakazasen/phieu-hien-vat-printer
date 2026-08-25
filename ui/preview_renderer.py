"""Modern async preview rendering pipeline for InPhieuHienVat.

Optimizes UI responsiveness on low-end machines by never blocking the Tk main
loop with heavy PDF work (ReportLab overlay + PyPDF2 merge + PyMuPDF rasterize):

- **Debounce**: bursts of requests (row-selection spam, layout nudge clicks,
  rapid tab switches) are coalesced into a single render after a short idle.
- **Background worker**: rendering runs on a daemon thread; the UI thread only
  schedules and applies results (no freezes, no torn/partial redraws).
- **LRU cache**: results are keyed by (template file + mtime, record fields,
  layout config, zoom) so re-selecting a row re-applies instantly with zero
  re-render cost.
- **Stale-result guard**: only the most recently requested render is applied;
  outdated results are silently dropped (but still cached).
- **Main-thread apply**: worker completion is picked up by a lightweight poll
  timer on the Tk thread — no cross-thread Tk calls, 100% Tcl-safe.
"""
from __future__ import annotations

import copy
import hashlib
import json
import threading
from collections import OrderedDict
from pathlib import Path
from typing import Any, Callable, Optional

from PIL import Image

# render_fn(record, template_path, layout_config, *, zoom) -> PIL.Image
RenderFunction = Callable[..., Image.Image]
ErrorCallback = Callable[[str], None]
ReadyCallback = Callable[[Image.Image], None]

_POLL_INTERVAL_MS = 25


class AsyncPreviewRenderer:
    """Debounced, cached, off-main-thread preview renderer bound to a Tk widget."""

    def __init__(
        self,
        widget: Any,
        render_fn: RenderFunction,
        *,
        debounce_ms: int = 90,
        cache_size: int = 8,
        zoom: float = 1.45,
        on_error: Optional[ErrorCallback] = None,
    ) -> None:
        self._widget = widget
        self._render_fn = render_fn
        self._debounce_ms = max(0, int(debounce_ms))
        self._zoom = float(zoom)
        self._cache_size = max(1, int(cache_size))
        self._on_error = on_error

        self._cache: "OrderedDict[tuple, Image.Image]" = OrderedDict()
        self._lock = threading.Lock()

        self._debounce_after: Optional[str] = None
        self._poll_after: Optional[str] = None

        self._seq = 0            # last accepted (debounced-dispatched) request id
        self._latest_key: Optional[tuple] = None
        self._inflight = 0       # number of running worker threads
        self._result: Optional[tuple[int, tuple, Any]] = None  # (seq, key, image|Exception)
        self._pending_on_ready: Optional[ReadyCallback] = None

    # ------------------------------------------------------------------ API

    def request(
        self,
        record: Any,
        template_path: str | Path,
        layout_config: dict[str, Any],
        on_ready: ReadyCallback,
    ) -> bool:
        """Request a preview for `record`. Returns True if served from cache instantly."""
        key = self._make_key(record, template_path, layout_config)

        with self._lock:
            self._latest_key = key
            self._pending_on_ready = on_ready
            cached = self._cache_get(key)

        if cached is not None:
            self._cancel_debounce()
            self._safe_apply(on_ready, cached)
            return True

        self._schedule_debounce(record, template_path, layout_config, key, on_ready)
        return False

    def invalidate(self) -> None:
        """Drop all cached previews (e.g. after layout file reload from disk)."""
        with self._lock:
            self._cache.clear()

    def cancel(self) -> None:
        """Cancel pending debounce/poll timers (call on app teardown)."""
        self._cancel_debounce()
        if self._poll_after is not None:
            try:
                self._widget.after_cancel(self._poll_after)
            except Exception:  # noqa: BLE001
                pass
            self._poll_after = None

    @property
    def cache_size(self) -> int:
        with self._lock:
            return len(self._cache)

    # --------------------------------------------------------- internals

    def _make_key(self, record: Any, template_path: str | Path, layout_config: dict[str, Any]) -> tuple:
        try:
            mtime = Path(template_path).stat().st_mtime_ns
        except OSError:
            mtime = -1

        try:
            fields = json.dumps(record.as_field_map(), sort_keys=True, ensure_ascii=False)
        except Exception:  # noqa: BLE001
            fields = str(record)

        try:
            layout_hash = hashlib.md5(
                json.dumps(layout_config, sort_keys=True, default=str).encode("utf-8")
            ).hexdigest()
        except Exception:  # noqa: BLE001
            layout_hash = str(id(layout_config))

        return (str(template_path), mtime, fields, layout_hash, round(self._zoom, 3))

    def _cache_get(self, key: tuple) -> Optional[Image.Image]:
        image = self._cache.get(key)
        if image is not None:
            self._cache.move_to_end(key)
        return image

    def _cache_put(self, key: tuple, image: Image.Image) -> None:
        self._cache[key] = image
        self._cache.move_to_end(key)
        while len(self._cache) > self._cache_size:
            self._cache.popitem(last=False)

    def _cancel_debounce(self) -> None:
        if self._debounce_after is not None:
            try:
                self._widget.after_cancel(self._debounce_after)
            except Exception:  # noqa: BLE001
                pass
            self._debounce_after = None

    def _schedule_debounce(
        self,
        record: Any,
        template_path: str | Path,
        layout_config: dict[str, Any],
        key: tuple,
        on_ready: ReadyCallback,
    ) -> None:
        self._cancel_debounce()
        self._debounce_after = self._widget.after(
            self._debounce_ms,
            lambda: self._start_render(record, template_path, layout_config, key, on_ready),
        )

    def _start_render(
        self,
        record: Any,
        template_path: str | Path,
        layout_config: dict[str, Any],
        key: tuple,
        on_ready: ReadyCallback,
    ) -> None:
        self._debounce_after = None

        with self._lock:
            cached = self._cache_get(key)
        if cached is not None:
            self._safe_apply(on_ready, cached)
            return

        # Deep-copy the layout dict so UI-thread mutations during rendering
        # cannot corrupt the snapshot being drawn.
        layout_snapshot = copy.deepcopy(layout_config)

        with self._lock:
            self._seq += 1
            seq = self._seq
            self._inflight += 1

        worker = threading.Thread(
            target=self._worker,
            args=(seq, key, record, str(template_path), layout_snapshot),
            daemon=True,
        )
        worker.start()
        self._ensure_polling()

    def _worker(self, seq: int, key: tuple, record: Any, template_path: str, layout_config: dict[str, Any]) -> None:
        try:
            image = self._render_fn(record, template_path, layout_config, zoom=self._zoom)
            payload: Any = image
        except Exception as exc:  # noqa: BLE001
            payload = exc

        with self._lock:
            self._result = (seq, key, payload)
            self._inflight -= 1

    def _ensure_polling(self) -> None:
        if self._poll_after is None:
            self._poll_after = self._widget.after(_POLL_INTERVAL_MS, self._poll)

    def _poll(self) -> None:
        self._poll_after = None

        with self._lock:
            result = self._result
            self._result = None
            inflight = self._inflight
            latest_key = self._latest_key
            latest_on_ready = self._pending_on_ready

        if result is not None:
            seq, key, payload = result
            if isinstance(payload, Exception):
                if key == latest_key and self._on_error is not None:
                    self._on_error(str(payload))
            else:
                with self._lock:
                    self._cache_put(key, payload)
                if key == latest_key and latest_on_ready is not None:
                    self._safe_apply(latest_on_ready, payload)

        if inflight > 0:
            self._ensure_polling()

    def _safe_apply(self, on_ready: ReadyCallback, image: Image.Image) -> None:
        try:
            on_ready(image)
        except Exception:  # noqa: BLE001
            pass
