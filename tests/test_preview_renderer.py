"""Tests for the async preview rendering pipeline (AsyncPreviewRenderer)."""
from __future__ import annotations

import threading
import time

from PIL import Image

from core.slip_printer_engine import EDI_TEMPLATE_CROP, create_record, generate_preview_image, get_default_layout_config
from ui.preview_renderer import AsyncPreviewRenderer


def _make_record(item_code: str = "3W2ND25350"):
    return create_record(
        row_number=1,
        item_code=item_code,
        item_name=f"Item {item_code}",
        carton_qty="20",
        total_qty="60",
        po="1126021101",
        po_detail="00010",
        po_sub="+001",
        box="001/003",
        rev="01",
        lot="",
    )


def _make_image(color: str) -> Image.Image:
    return Image.new("RGB", (8, 8), color=color)


def _pump(root, seconds: float) -> None:
    """Pump the Tk event loop so after-callbacks and poll timers run."""
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        root.update()
        time.sleep(0.02)


def test_cached_request_applies_instantly_without_rerender(tk_root):
    calls: list[str] = []
    applied: list[str] = []

    def render_fn(record, template_path, layout_config, *, zoom=1.0):
        calls.append(record.item_code)
        return _make_image("red")

    renderer = AsyncPreviewRenderer(tk_root, render_fn, debounce_ms=10, zoom=1.0)
    record = _make_record()

    renderer.request(record, "dummy.pdf", {}, on_ready=lambda img: applied.append(img.getpixel((0, 0))))
    _pump(tk_root, 1.0)
    assert applied == [(255, 0, 0)]
    assert len(calls) == 1

    # Second request for the same key must be served from cache (no re-render)
    served_from_cache = renderer.request(
        record, "dummy.pdf", {}, on_ready=lambda img: applied.append(img.getpixel((0, 0)))
    )
    assert served_from_cache is True
    assert applied == [(255, 0, 0), (255, 0, 0)]
    assert len(calls) == 1


def test_debounce_coalesces_burst_into_single_render(tk_root):
    calls: list[str] = []
    applied: list[str] = []

    def render_fn(record, template_path, layout_config, *, zoom=1.0):
        calls.append(record.item_code)
        return _make_image("blue")

    renderer = AsyncPreviewRenderer(tk_root, render_fn, debounce_ms=10, zoom=1.0)

    renderer.request(_make_record("AAA"), "dummy.pdf", {}, on_ready=lambda img: applied.append("A"))
    renderer.request(_make_record("BBB"), "dummy.pdf", {}, on_ready=lambda img: applied.append("B"))
    _pump(tk_root, 1.5)

    # Only the last request of the burst is rendered and applied
    assert calls == ["BBB"]
    assert applied == ["B"]


def test_stale_result_is_discarded_but_cached(tk_root):
    release_a = threading.Event()
    lock = threading.Lock()
    applied: list[str] = []

    def render_fn(record, template_path, layout_config, *, zoom=1.0):
        if record.item_code == "AAA":
            release_a.wait(timeout=3.0)
            return _make_image("green")
        return _make_image("yellow")

    def on_ready(img):
        with lock:
            applied.append(img.getpixel((0, 0)))

    renderer = AsyncPreviewRenderer(tk_root, render_fn, debounce_ms=10, zoom=1.0)

    renderer.request(_make_record("AAA"), "dummy.pdf", {}, on_ready=on_ready)
    _pump(tk_root, 0.4)  # let worker A start and block

    renderer.request(_make_record("BBB"), "dummy.pdf", {}, on_ready=on_ready)
    _pump(tk_root, 1.0)
    with lock:
        assert applied == [(255, 255, 0)]  # only B applied

    release_a.set()
    _pump(tk_root, 0.8)
    with lock:
        # A finished but its result is stale -> must NOT be applied
        assert applied == [(255, 255, 0)]
    # ...but it is still cached for future re-selection
    assert renderer.cache_size == 2


def test_render_error_routes_to_on_error(tk_root):
    applied: list[str] = []
    errors: list[str] = []

    def render_fn(record, template_path, layout_config, *, zoom=1.0):
        raise RuntimeError("boom")

    renderer = AsyncPreviewRenderer(
        tk_root, render_fn, debounce_ms=10, zoom=1.0, on_error=errors.append
    )
    renderer.request(_make_record(), "dummy.pdf", {}, on_ready=lambda img: applied.append("x"))
    _pump(tk_root, 1.0)

    assert applied == []
    assert any("boom" in message for message in errors)


def test_invalidates_and_re_renders(tk_root):
    calls: list[str] = []
    applied: list[str] = []

    def render_fn(record, template_path, layout_config, *, zoom=1.0):
        calls.append(record.item_code)
        return _make_image("red")

    renderer = AsyncPreviewRenderer(tk_root, render_fn, debounce_ms=10, zoom=1.0)
    record = _make_record()

    renderer.request(record, "dummy.pdf", {}, on_ready=lambda img: applied.append("1"))
    _pump(tk_root, 1.0)
    assert len(calls) == 1

    renderer.invalidate()
    assert renderer.cache_size == 0

    served_from_cache = renderer.request(record, "dummy.pdf", {}, on_ready=lambda img: applied.append("2"))
    assert served_from_cache is False
    _pump(tk_root, 1.0)
    assert len(calls) == 2
    assert applied == ["1", "2"]


def test_layout_change_produces_new_cache_entry(tk_root):
    calls: list[dict] = []
    applied: list[str] = []

    def render_fn(record, template_path, layout_config, *, zoom=1.0):
        calls.append(dict(layout_config))
        return _make_image("red")

    renderer = AsyncPreviewRenderer(tk_root, render_fn, debounce_ms=10, zoom=1.0)
    record = _make_record()

    renderer.request(record, "dummy.pdf", {"qr_122": {"x": 1}}, on_ready=lambda img: applied.append("a"))
    _pump(tk_root, 1.0)

    renderer.request(record, "dummy.pdf", {"qr_122": {"x": 2}}, on_ready=lambda img: applied.append("b"))
    _pump(tk_root, 1.0)

    assert applied == ["a", "b"]
    assert len(calls) == 2
    assert calls[0] != calls[1]


def test_cancel_stops_pending_work(tk_root):
    calls: list[str] = []
    applied: list[str] = []

    def render_fn(record, template_path, layout_config, *, zoom=1.0):
        calls.append(record.item_code)
        return _make_image("red")

    renderer = AsyncPreviewRenderer(tk_root, render_fn, debounce_ms=200, zoom=1.0)
    renderer.request(_make_record(), "dummy.pdf", {}, on_ready=lambda img: applied.append("x"))
    renderer.cancel()
    _pump(tk_root, 0.6)

    assert calls == []
    assert applied == []


def test_generate_preview_image_renders_the_edi_label_region():
    """The preview must crop the EDI label from the landscape template, not tiled A4."""
    record = _make_record()

    image = generate_preview_image(record, "template.pdf", get_default_layout_config(), zoom=1.45)

    expected_width = int(EDI_TEMPLATE_CROP.width * 1.45)
    expected_height = int(EDI_TEMPLATE_CROP.height * 1.45)
    assert abs(image.width - expected_width) <= 2
    assert abs(image.height - expected_height) <= 2
    assert any(low < 250 for low, _high in image.getextrema())
