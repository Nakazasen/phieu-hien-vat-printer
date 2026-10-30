"""Persistent Part Master (Master Linh Kiện) registry backed by SQLite & Inspection CSV parser.

Responsibilities
----------------
1. Store and manage master parts: item_code (Mã linh kiện), item_name (Tên linh kiện),
   rev (Revision), and cav_list (Danh sách CAV hợp lệ, ví dụ: "1, 2").
2. Parse real Kyocera Inspection CSV files from the network directory structure:
   \\\\10.170.178.1\\data\\5000PJ\\Inspection_data\\[nhóm mã]\\[mã linh kiện]\\[mã linh kiện]_[revision]_[version].csv
3. Validate inputs:
   - item_code must not be empty (auto-trimmed, uppercase).
   - item_name must not be empty (prevents missing data).
   - rev must be exactly two digits between "01" and "99".
   - cav_list (optional manual fallback): only integers 1..16, deduplicated, sorted ascending.
4. Provide fast lookup by item_code to auto-fill item_name, rev, and CAV No. on the main form.
5. Support listing, searching, upserting, and deleting part master records.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
import os
from pathlib import Path
import re
import sqlite3
import threading

DEFAULT_INSPECTION_DATA_DIR = r"\\10.170.178.1\data\5000PJ\Inspection_data"
ENV_INSPECTION_DATA_DIR = "INPHIEUHIENVAT_INSPECTION_DIR"
MAX_CAV_DEFAULT = 16

_MAX_CAV_HEADER_RE = re.compile(r"^maxCavN\s*:\s*(\d+)$", re.IGNORECASE)


@dataclass(slots=True)
class PartMaster:
    """Represents a master part entry."""

    item_code: str
    item_name: str
    rev: str
    updated_at: str = ""
    cav_list: str = ""
    carton_qty: str = ""

    @property
    def valid_cavs(self) -> list[int]:
        """Return parsed list of valid integer CAV numbers (e.g. [1, 2])."""
        try:
            return parse_manual_cav_input(self.cav_list)
        except PartMasterValidationError:
            return []


class PartMasterValidationError(ValueError):
    """Raised when part master data fails validation."""


class InspectionCSVError(ValueError):
    """Raised when an inspection CSV file cannot be located or fails structural validation."""


@dataclass(slots=True)
class InspectionCSVData:
    """Parsed metadata, valid CAV list, and pcs/box from a Kyocera Inspection_data CSV file."""

    file_path: Path
    max_cav_n: int
    item_code: str
    rev: str
    version: str
    item_name: str
    material: str
    cav_booleans: tuple[bool, ...]
    valid_cavs: list[int]
    pcs_per_box: int | None = None
    is_from_old_archive: bool = False
    active_csv_files: tuple[str, ...] = ()
    active_revisions: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    @property
    def cav_text(self) -> str:
        """Formatted CAV No. string joined by comma and space (e.g., '1, 2')."""
        return format_cav_list(self.valid_cavs)

    @property
    def revision(self) -> str:
        """Alias for rev."""
        return self.rev


def format_cav_list(cavs: Iterable[int]) -> str:
    """Format an iterable of CAV numbers as ascending comma-separated string (e.g. '1, 2')."""
    unique_sorted = sorted({int(c) for c in cavs if int(c) >= 1})
    return ", ".join(str(c) for c in unique_sorted)


def parse_manual_cav_input(raw_cav: object, *, max_cav: int = MAX_CAV_DEFAULT) -> list[int]:
    """Validate and normalize manual CAV input.

    Rules:
    - Empty / None -> []
    - Accepts only integers between 1 and max_cav (default 16).
    - Deduplicates and sorts ascending.
    - Rejects non-integers, 0, negative numbers, or numbers > max_cav.
    """
    if raw_cav is None:
        return []
    if isinstance(raw_cav, (list, tuple, set)):
        tokens = [str(item).strip() for item in raw_cav if str(item).strip()]
    else:
        text = str(raw_cav).strip()
        if not text:
            return []
        tokens = [tok.strip() for tok in re.split(r"[\s,;]+", text) if tok.strip()]

    if not tokens:
        return []

    parsed: set[int] = set()
    for tok in tokens:
        if not re.fullmatch(r"\d+", tok):
            raise PartMasterValidationError(
                f"Giá trị CAV '{tok}' không hợp lệ. Chỉ nhận số nguyên từ 1 đến {max_cav}!"
            )
        val = int(tok)
        if not (1 <= val <= max_cav):
            raise PartMasterValidationError(
                f"Số CAV '{val}' không hợp lệ. Chỉ nhận số nguyên từ 1 đến {max_cav}!"
            )
        parsed.add(val)

    return sorted(parsed)


def get_inspection_data_root(custom_root: str | Path | None = None) -> Path:
    """Resolve the root directory for Inspection_data CSV files."""
    if custom_root is not None:
        cleaned = str(custom_root).strip().strip('"').strip("'").strip()
        if cleaned:
            return Path(cleaned)
    env_root = os.environ.get(ENV_INSPECTION_DATA_DIR, "").strip().strip('"').strip("'").strip()
    if env_root:
        return Path(env_root)
    return Path(DEFAULT_INSPECTION_DATA_DIR)


def _read_csv_text_with_fallback(path: Path) -> str:
    """Read CSV file text safely supporting UTF-8-SIG, UTF-8, CP932 (Shift-JIS), and Latin-1."""
    try:
        raw_bytes = path.read_bytes()
    except FileNotFoundError as exc:
        raise InspectionCSVError(f"Không tìm thấy tệp CSV master: {path}") from exc
    except PermissionError as exc:
        raise InspectionCSVError(f"Không có quyền truy cập tệp CSV master: {path}") from exc
    except IsADirectoryError as exc:
        raise InspectionCSVError(f"Đường dẫn CSV master là thư mục, không phải tệp: {path}") from exc
    except OSError as exc:
        raise InspectionCSVError(f"Không thể đọc tệp CSV master ({path}): {exc}") from exc

    if not raw_bytes or not raw_bytes.strip():
        raise InspectionCSVError(f"Tệp CSV master rỗng: {path}")

    for encoding in ("utf-8-sig", "utf-8", "cp932", "cp1258", "latin-1"):
        try:
            return raw_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise InspectionCSVError(f"Không thể giải mã bảng mã (encoding) của tệp CSV: {path}")


def _trim_trailing_empty_cells(cells: list[str]) -> list[str]:
    """Strip whitespace/quotes from CSV cells and remove trailing empty cells added by Excel."""
    cleaned = [c.strip().strip('"').strip("'").strip() for c in cells]
    while cleaned and cleaned[-1] == "":
        cleaned.pop()
    return cleaned


def _extract_single_metadata_cell(line: str, field_label: str) -> str:
    """Extract a single metadata cell from a header line and guard against missing metadata rows."""
    cells = _trim_trailing_empty_cells(line.split(","))
    non_empty_cells = [c for c in cells if c != ""]
    if not non_empty_cells:
        raise InspectionCSVError(f"Thiếu thông tin metadata '{field_label}' trong tệp CSV.")

    # Guard: If a metadata line looks like the CAV boolean array or an inspection item row (True,1,...),
    # then a preceding metadata line was omitted.
    first_lower = cells[0].lower()
    if len(cells) >= 2 and first_lower in ("true", "false"):
        second_cell = cells[1].strip().lower()
        if second_cell in ("true", "false") or second_cell.isdigit():
            raise InspectionCSVError(
                f"Tệp CSV thiếu dòng metadata ('{field_label}') trước danh sách Boolean CAV."
            )

    return non_empty_cells[0]


def parse_inspection_csv(csv_path: str | Path) -> InspectionCSVData:
    """Parse a Kyocera Inspection_data CSV file to extract metadata, valid CAV numbers, and pcs/box.

    Expected Header Structure (non-empty lines at top of file):
    - Line 0: maxCavN:<N> (e.g., maxCavN:16)
    - Line 1: Part code (e.g., 302YJ03340)
    - Line 2: Revision (e.g., 02)
    - Line 3: Version (e.g., 01)
    - Line 4: Part name (e.g., BOTTLE WASTE)
    - Line 5: Material (e.g., HD-PE; may be blank in some Excel-saved CSVs)
    - Line 6: Boolean CAV list of length maxCavN (e.g., True,True,False,...,False)
              Position 1 -> CAV 1, Position 2 -> CAV 2, ..., only True is valid.
              (Trailing empty commas added by Microsoft Excel are automatically stripped.)
    - Line 7: Extra header flag (e.g., False)
    - Line 8: Extra header parameter (e.g., 2)
    - Line 9 (1-based Line 10): Quantity pcs/box (SL/thùng, e.g., 60, 18, 30)
    - Subsequent lines (inspection parameters starting with True,1 / True,2...) are ignored.
    """
    path = Path(csv_path)
    text = _read_csv_text_with_fallback(path)

    # Extract fallback item_code, rev, version from filename (<item_code>_<rev>_<ver>.csv)
    stem_match = re.match(
        r"^\s*([A-Za-z0-9\-]+?)(?:[\s_]+(\d+))?(?:[\s_]+(\d+))?(?:[\s_].*)?$",
        path.stem,
    )
    file_item_code = stem_match.group(1).strip().upper() if stem_match else ""
    file_rev: str | None = None
    file_ver: str | None = None
    if stem_match and stem_match.group(2) and stem_match.group(2).isdigit():
        r_int = int(stem_match.group(2))
        if 1 <= r_int <= 99:
            file_rev = f"{r_int:02d}"
    if stem_match and stem_match.group(3) and stem_match.group(3).isdigit():
        file_ver = f"{int(stem_match.group(3)):02d}"

    # Filter out blank lines or lines containing only commas/whitespace
    non_empty_lines: list[str] = []
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if not stripped or not stripped.strip(",").strip():
            continue
        non_empty_lines.append(stripped)
        if len(non_empty_lines) >= 35:
            break

    if len(non_empty_lines) < 5:
        raise InspectionCSVError(
            f"Tệp CSV '{path.name}' không đủ cấu trúc header (cần tối thiểu các dòng metadata và danh sách Boolean CAV)."
        )

    # 1. Detect whether Line 0 has 'maxCavN:<N>' (newer 16-CAV format) or starts directly with Part Code (legacy 8-CAV format)
    header_cells = _trim_trailing_empty_cells(non_empty_lines[0].split(","))
    header_first_cell = header_cells[0] if header_cells else ""
    match = _MAX_CAV_HEADER_RE.match(header_first_cell)
    has_max_cav_header = False
    max_cav_n = MAX_CAV_DEFAULT
    meta_offset = 0

    if match:
        has_max_cav_header = True
        max_cav_n = int(match.group(1))
        if max_cav_n <= 0 or max_cav_n > 64:
            raise InspectionCSVError(f"Giá trị maxCavN={max_cav_n} trong '{path.name}' không hợp lệ.")
        meta_offset = 1
    elif header_first_cell.lower().startswith("maxcavn"):
        raise InspectionCSVError(
            f"Tệp CSV '{path.name}' có khai báo 'maxCavN:' không hợp lệ ở dòng đầu tiên (nhận được: '{header_first_cell}')."
        )

    # 2. Locate Boolean CAV data:
    #    - Format A (Horizontal): a single row with >=2 tokens where all non-empty tokens are True/False
    #    - Format B (Vertical, e.g. 302NR25651_01_01.csv): consecutive single-cell True/False lines
    cav_start_idx: int | None = None
    cav_end_idx: int | None = None
    raw_tokens: list[str] = []

    search_limit = min(len(non_empty_lines), meta_offset + 9)
    for idx in range(meta_offset + 1, search_limit):
        cand_tokens = _trim_trailing_empty_cells(non_empty_lines[idx].split(","))
        if len(cand_tokens) >= 2 and all(t.lower() in ("true", "false") for t in cand_tokens):
            cav_start_idx = idx
            cav_end_idx = idx
            raw_tokens = cand_tokens
            if not has_max_cav_header:
                max_cav_n = len(raw_tokens)
            break

    if cav_start_idx is None:
        # Check for vertical single-cell True/False lines starting after metadata (3 to 6 metadata lines)
        for idx in range(meta_offset + 3, min(len(non_empty_lines), meta_offset + 7)):
            cand_tokens = _trim_trailing_empty_cells(non_empty_lines[idx].split(","))
            if len(cand_tokens) == 1 and cand_tokens[0].lower() in ("true", "false"):
                run_tokens: list[str] = []
                k = idx
                while k < len(non_empty_lines):
                    k_tokens = _trim_trailing_empty_cells(non_empty_lines[k].split(","))
                    if len(k_tokens) == 1 and k_tokens[0].lower() in ("true", "false"):
                        run_tokens.append(k_tokens[0])
                        k += 1
                    else:
                        break
                run_len = len(run_tokens)
                if run_len >= 4:
                    cav_start_idx = idx
                    if has_max_cav_header and run_len >= max_cav_n:
                        raw_tokens = run_tokens[:max_cav_n]
                        cav_end_idx = idx + max_cav_n - 1
                    elif run_len in (9, 17):
                        # 8 (or 16) vertical CAV lines + 1 post-CAV boolean flag line
                        max_cav_n = run_len - 1
                        raw_tokens = run_tokens[:max_cav_n]
                        cav_end_idx = idx + max_cav_n - 1
                    elif (
                        idx + run_len + 2 < len(non_empty_lines)
                        and _trim_trailing_empty_cells(non_empty_lines[idx + run_len + 2].split(","))[:1]
                        and _trim_trailing_empty_cells(non_empty_lines[idx + run_len + 2].split(","))[0].lower() == "mix"
                    ):
                        max_cav_n = run_len - 1
                        raw_tokens = run_tokens[:max_cav_n]
                        cav_end_idx = idx + max_cav_n - 1
                    else:
                        max_cav_n = run_len
                        raw_tokens = run_tokens
                        cav_end_idx = idx + run_len - 1
                break

    if cav_start_idx is None or cav_end_idx is None:
        if not has_max_cav_header or len(non_empty_lines) < meta_offset + 6:
            raise InspectionCSVError(
                f"Tệp CSV '{path.name}' không đủ cấu trúc header (thiếu dòng metadata hoặc dòng Boolean CAV)."
            )
        cav_start_idx = meta_offset + 5
        cav_end_idx = cav_start_idx
        raw_tokens = _trim_trailing_empty_cells(non_empty_lines[cav_start_idx].split(","))

    meta_lines = non_empty_lines[meta_offset:cav_start_idx]
    if len(meta_lines) < 3:
        raise InspectionCSVError(
            f"Tệp CSV '{path.name}' thiếu dòng metadata trước danh sách Boolean CAV."
        )

    # 3. Parse Metadata block before cav_start_idx (item_code, rev, version, item_name, material)
    if len(meta_lines) >= 5:
        item_code = _extract_single_metadata_cell(meta_lines[0], "Mã linh kiện").upper()
        raw_rev = _extract_single_metadata_cell(meta_lines[1], "Revision")
        raw_ver = _extract_single_metadata_cell(meta_lines[2], "Version")
        item_name = _extract_single_metadata_cell(meta_lines[3], "Tên linh kiện")
        material = _extract_single_metadata_cell(meta_lines[4], "Vật liệu")
    elif len(meta_lines) == 4:
        # Material (or Version) row was left blank in Excel
        item_code = _extract_single_metadata_cell(meta_lines[0], "Mã linh kiện").upper()
        raw_rev = _extract_single_metadata_cell(meta_lines[1], "Revision")
        m3 = _extract_single_metadata_cell(meta_lines[2], "Version/Tên linh kiện")
        m4 = _extract_single_metadata_cell(meta_lines[3], "Tên linh kiện/Vật liệu")
        if re.fullmatch(r"\d+(?:\.0+)?", m3):
            raw_ver = m3
            item_name = m4
            material = ""
        else:
            raw_ver = file_ver or "01"
            item_name = m3
            material = m4
    else:
        # len(meta_lines) == 3: Both Version and Material rows were left blank in Excel
        item_code = _extract_single_metadata_cell(meta_lines[0], "Mã linh kiện").upper()
        raw_rev = _extract_single_metadata_cell(meta_lines[1], "Revision")
        raw_ver = file_ver or "01"
        item_name = _extract_single_metadata_cell(meta_lines[2], "Tên linh kiện")
        material = ""

    if not item_code and file_item_code:
        item_code = file_item_code

    warnings_list: list[str] = []
    content_rev: str | None = None
    if re.fullmatch(r"\d+(?:\.0+)?", raw_rev) and (1 <= int(float(raw_rev)) <= 99):
        content_rev = f"{int(float(raw_rev)):02d}"

    if content_rev is not None and file_rev is not None:
        if content_rev != file_rev:
            rev = f"{max(int(file_rev), int(content_rev)):02d}"
            warnings_list.append(
                f"Tên tệp '{path.name}' ghi Rev {file_rev} nhưng dòng Revision bên trong tệp đang ghi Rev {content_rev} "
                f"(QC có thể quên cập nhật nội dung khi copy file). Đã ưu tiên lấy Rev {rev}."
            )
        else:
            rev = content_rev
    elif content_rev is not None:
        rev = content_rev
    elif file_rev is not None:
        rev = file_rev
    else:
        raise InspectionCSVError(
            f"Revision '{raw_rev}' trong tệp CSV '{path.name}' không hợp lệ (phải là số từ 01 đến 99)."
        )

    content_ver: str | None = None
    if re.fullmatch(r"\d+(?:\.0+)?", raw_ver) and int(float(raw_ver)) >= 0:
        content_ver = f"{int(float(raw_ver)):02d}"

    if content_ver is not None and file_ver is not None:
        if content_ver != file_ver:
            version = f"{max(int(file_ver), int(content_ver)):02d}"
            warnings_list.append(
                f"Tên tệp '{path.name}' ghi Ver {file_ver} nhưng dòng Version bên trong tệp đang ghi Ver {content_ver}. "
                f"Đã ưu tiên lấy Ver {version}."
            )
        else:
            version = content_ver
    elif content_ver is not None:
        version = content_ver
    elif file_ver is not None:
        version = file_ver
    else:
        raise InspectionCSVError(
            f"Version '{raw_ver}' trong tệp CSV '{path.name}' không hợp lệ."
        )

    # 4. Validate Boolean CAV tokens
    for idx, tok in enumerate(raw_tokens, start=1):
        if tok.lower() not in ("true", "false"):
            raise InspectionCSVError(
                f"Phần tử thứ {idx} ('{tok}') trong dòng Boolean CAV của '{path.name}' không phải là True/False."
            )

    if len(raw_tokens) != max_cav_n:
        raise InspectionCSVError(
            f"Số phần tử Boolean CAV ({len(raw_tokens)}) không khớp với maxCavN ({max_cav_n}) trong tệp '{path.name}'."
        )

    cav_booleans = tuple(tok.lower() == "true" for tok in raw_tokens)
    valid_cavs = [idx for idx, is_true in enumerate(cav_booleans, start=1) if is_true]

    # 5. Quantity pcs/box (SL/thùng): normally 3rd non-empty row after Boolean CAV block,
    # or the row immediately preceding 'mix'.
    pcs_per_box: int | None = None
    after_cav = non_empty_lines[cav_end_idx + 1 :]

    def _try_parse_pcs_row(row_str: str) -> int | None:
        cells = [c for c in _trim_trailing_empty_cells(row_str.split(",")) if c != ""]
        if len(cells) == 1 and re.fullmatch(r"\d+(?:\.0+)?", cells[0]):
            val = int(float(cells[0]))
            if val > 0:
                return val
        return None

    if len(after_cav) >= 3:
        pcs_per_box = _try_parse_pcs_row(after_cav[2])

    if pcs_per_box is None:
        for idx_after, r_str in enumerate(after_cav[:6]):
            r_cells = [c.lower() for c in _trim_trailing_empty_cells(r_str.split(",")) if c != ""]
            if r_cells and r_cells[0] == "mix" and idx_after >= 1:
                pcs_per_box = _try_parse_pcs_row(after_cav[idx_after - 1])
                if pcs_per_box is not None:
                    break

    is_from_old = path.parent.name.strip().lower() == "old"
    return InspectionCSVData(
        file_path=path,
        max_cav_n=max_cav_n,
        item_code=item_code,
        rev=rev,
        version=version,
        item_name=item_name,
        material=material,
        cav_booleans=cav_booleans,
        valid_cavs=valid_cavs,
        pcs_per_box=pcs_per_box,
        is_from_old_archive=is_from_old,
        warnings=tuple(warnings_list),
    )


def _find_inspection_csv_with_context(
    item_code: str,
    *,
    preferred_rev: str | None = None,
    inspection_root: str | Path | None = None,
    root_dir: str | Path | None = None,
) -> tuple[Path, tuple[str, ...], tuple[str, ...], bool]:
    """Locate the target CSV file along with active-directory file & revision context.

    Returns:
        (selected_csv_path, active_csv_files, active_revisions, is_from_old_archive)
    """
    clean_code = str(item_code or "").strip().upper()
    if not clean_code:
        raise InspectionCSVError("Chưa nhập Mã linh kiện để tìm tệp CSV.")

    effective_root = inspection_root if inspection_root is not None else root_dir
    root = get_inspection_data_root(effective_root)

    try:
        if not root.is_dir():
            raise InspectionCSVError(
                f"Không tìm thấy tệp CSV master cho mã '{clean_code}' trong '{root}'."
            )
    except (PermissionError, OSError) as exc:
        raise InspectionCSVError(
            f"Không thể truy cập thư mục dữ liệu mạng ({root}): {exc}"
        ) from exc

    matched_files: list[tuple[int, int, Path]] = []
    located_part_dir: Path | None = None
    access_error: OSError | None = None

    strict_pattern = re.compile(
        rf"^\s*{re.escape(clean_code)}[\s_]*(\d+)[\s_]+(\d+)(?:[\s_].*)?\.csv\s*$",
        re.IGNORECASE,
    )
    single_rev_pattern = re.compile(
        rf"^\s*{re.escape(clean_code)}(?:[\s_]+(\d+))?\.csv\s*$",
        re.IGNORECASE,
    )
    any_csv_in_part_dir_pattern = re.compile(
        r"^\s*[A-Za-z0-9\-]+?[\s_]+(\d+)(?:[\s_]+(\d+))?(?:[\s_].*)?\.csv\s*$",
        re.IGNORECASE,
    )

    def _classify_csv_entries(
        directory: Path, *, is_exact_part_dir: bool = False
    ) -> list[tuple[int, int, Path]]:
        nonlocal access_error
        found_in_dir: list[tuple[int, int, Path]] = []
        try:
            if not directory.is_dir():
                return found_in_dir
            entries = [e for e in directory.iterdir() if e.is_file() and e.suffix.lower() == ".csv"]
            for entry in entries:
                fname = entry.name.strip()
                m = strict_pattern.match(fname)
                if m:
                    found_in_dir.append((int(m.group(1)), int(m.group(2)), entry))
                    continue
                m1 = single_rev_pattern.match(fname)
                if m1:
                    rev_num = int(m1.group(1)) if m1.group(1) else 1
                    found_in_dir.append((rev_num, 1, entry))
                    continue
                if is_exact_part_dir:
                    m_any = any_csv_in_part_dir_pattern.match(fname)
                    if m_any:
                        rev_num = int(m_any.group(1))
                        ver_num = int(m_any.group(2)) if m_any.group(2) else 1
                        found_in_dir.append((rev_num, ver_num, entry))
                    else:
                        found_in_dir.append((1, 1, entry))
        except (PermissionError, OSError) as exc:
            if access_error is None:
                access_error = exc
        return found_in_dir

    p5 = clean_code[:5] if len(clean_code) >= 5 else clean_code
    p4 = clean_code[:4] if len(clean_code) >= 4 else clean_code
    alt_group_prefix = ""
    if len(clean_code) >= 5:
        if clean_code.startswith("3V"):
            alt_group_prefix = "30" + clean_code[2:5]
        elif clean_code.startswith("30"):
            alt_group_prefix = "3V" + clean_code[2:5]

    group_variants: list[str] = []
    for g in (
        p5,
        p4,
        f" {p5}",
        f" {p4}",
        alt_group_prefix,
        alt_group_prefix[:4] if alt_group_prefix else "",
        f" {alt_group_prefix}" if alt_group_prefix else "",
    ):
        if g and g not in group_variants:
            group_variants.append(g)

    part_variants = [clean_code, f" {clean_code}"]
    candidate_dirs: list[tuple[Path, bool]] = []
    for grp in group_variants:
        for prt in part_variants:
            candidate_dirs.append((root / grp / prt, True))
    for prt in part_variants:
        candidate_dirs.append((root / prt, True))
    candidate_dirs.append((root, False))

    for cand_dir, is_exact_part in candidate_dirs:
        if is_exact_part and located_part_dir is None:
            try:
                if cand_dir.is_dir():
                    located_part_dir = cand_dir
            except OSError:
                pass
        found = _classify_csv_entries(cand_dir, is_exact_part_dir=is_exact_part)
        if found:
            matched_files = found
            if is_exact_part:
                located_part_dir = cand_dir
            break

    # Fallback: scan 1st-level group folders for the exact clean_code subfolder
    if not matched_files:
        try:
            if root.is_dir():
                model_key = clean_code[2:5] if len(clean_code) >= 5 else clean_code[:3]
                all_group_dirs = [d for d in root.iterdir() if d.is_dir()]
                prioritized_groups = sorted(
                    all_group_dirs,
                    key=lambda d: (
                        0
                        if (
                            model_key in d.name.strip().upper()
                            or clean_code.startswith(d.name.strip().upper())
                        )
                        else 1,
                        d.name.upper(),
                    ),
                )
                for group_dir in prioritized_groups:
                    for prt in part_variants:
                        sub_cand = group_dir / prt
                        if located_part_dir is None:
                            try:
                                if sub_cand.is_dir():
                                    located_part_dir = sub_cand
                            except OSError:
                                pass
                        found = _classify_csv_entries(sub_cand, is_exact_part_dir=True)
                        if found:
                            matched_files = found
                            located_part_dir = sub_cand
                            break
                    if matched_files:
                        break
                    grp_clean = group_dir.name.strip().upper()
                    if grp_clean and (
                        model_key in grp_clean
                        or clean_code.startswith(grp_clean)
                        or grp_clean.startswith(clean_code[:3])
                    ):
                        try:
                            for sub_dir in group_dir.iterdir():
                                if sub_dir.is_dir() and sub_dir.name.strip().upper() == clean_code:
                                    if located_part_dir is None:
                                        located_part_dir = sub_dir
                                    found = _classify_csv_entries(sub_dir, is_exact_part_dir=True)
                                    if found:
                                        matched_files = found
                                        located_part_dir = sub_dir
                                        break
                        except (PermissionError, OSError):
                            pass
                    if matched_files:
                        break
        except (PermissionError, OSError) as exc:
            if access_error is None:
                access_error = exc

    sorted_active = sorted(matched_files, key=lambda item: (item[0], item[1], item[2].name.upper()))
    active_csv_files = tuple(item[2].name.strip() for item in sorted_active)
    active_revisions = tuple(sorted({f"{item[0]:02d}" for item in sorted_active}))

    is_from_old = False
    selected_candidates = list(matched_files)

    # Filter by preferred_rev if specified; if not in active root folder, check 'old/' archive subfolder
    if preferred_rev is not None and str(preferred_rev).strip().isdigit():
        target_rev = int(str(preferred_rev).strip())
        rev_filtered = [item for item in matched_files if item[0] == target_rev]
        if rev_filtered:
            selected_candidates = rev_filtered
        elif located_part_dir is not None:
            try:
                old_dirs = [
                    sub
                    for sub in located_part_dir.iterdir()
                    if sub.is_dir() and sub.name.strip().lower() == "old"
                ]
            except (PermissionError, OSError):
                old_dirs = []
            for old_dir in old_dirs:
                old_entries = _classify_csv_entries(old_dir, is_exact_part_dir=True)
                old_rev_filtered = [item for item in old_entries if item[0] == target_rev]
                if old_rev_filtered:
                    selected_candidates = old_rev_filtered
                    is_from_old = True
                    break

    if not selected_candidates:
        if access_error is not None:
            raise InspectionCSVError(
                f"Không thể truy cập thư mục dữ liệu mạng ({root}): {access_error}"
            ) from access_error
        raise InspectionCSVError(
            f"Không tìm thấy tệp CSV master cho mã '{clean_code}' trong '{root}'."
        )

    selected_candidates.sort(key=lambda item: (item[0], item[1], item[2].name.upper()))
    selected_path = selected_candidates[-1][2]
    return selected_path, active_csv_files, active_revisions, is_from_old


def find_inspection_csv_file(
    item_code: str,
    *,
    preferred_rev: str | None = None,
    inspection_root: str | Path | None = None,
    root_dir: str | Path | None = None,
) -> Path:
    """Locate the target CSV file for `item_code` inside the Inspection_data folder hierarchy.

    Folder hierarchy:
        \\\\10.170.178.1\\data\\5000PJ\\Inspection_data\\[nhóm mã]\\[mã linh kiện]\\[mã linh kiện]_[revision]_[version].csv
    Looks up ONLY the exact `item_code` entered (no code guessing/substitution), while supporting
    real folder naming variations on the network server (5-char or 4-char group prefix, folders/files
    with leading spaces such as `\\ 302Y\\ 302YJJ1320\\ 302YJJ1320_01_01.csv`, or CSV files inside
    the exact `[mã linh kiện]` folder).

    Selection rule when multiple files exist for the same part code:
    - If `preferred_rev` is specified and matching files exist for that revision in the active root folder
      (or in the `old/` archive subfolder when running-change old stock is requested), select the file
      with the highest version among that revision.
    - Otherwise, select the file with the highest (revision, version) overall in the active root folder.
    """
    selected_path, _, _, _ = _find_inspection_csv_with_context(
        item_code,
        preferred_rev=preferred_rev,
        inspection_root=inspection_root,
        root_dir=root_dir,
    )
    return selected_path


def collect_inspection_diagnostics(
    item_code: str,
    *,
    inspection_root: str | Path | None = None,
    csv_file: Path | None = None,
) -> dict[str, object]:
    """Collect detailed folder/file diagnostics for `item_code` to write to error_log."""
    clean_code = str(item_code or "").strip().upper()
    root = get_inspection_data_root(inspection_root)
    diag: dict[str, object] = {
        "entered_code": clean_code,
        "inspection_root": str(root),
        "root_exists": False,
        "matching_group_folders": [],
        "candidate_part_folders": [],
    }
    try:
        root_exists = root.is_dir()
        diag["root_exists"] = root_exists
        if root_exists and clean_code:
            model_key = clean_code[2:5] if len(clean_code) >= 5 else clean_code[:3]
            code_prefix6 = clean_code[:6] if len(clean_code) >= 6 else clean_code
            matching_groups: list[dict[str, object]] = []
            for g_dir in root.iterdir():
                if not g_dir.is_dir():
                    continue
                g_name = g_dir.name.strip().upper()
                if (
                    model_key in g_name
                    or clean_code.startswith(g_name)
                    or g_name.startswith(clean_code[:4])
                ):
                    similar_subs: list[str] = []
                    exact_sub_files: list[str] = []
                    try:
                        for sub in g_dir.iterdir():
                            s_clean = sub.name.strip().upper()
                            if s_clean == clean_code and sub.is_dir():
                                try:
                                    exact_sub_files = [x.name for x in sub.iterdir()]
                                except OSError as e_sub:
                                    exact_sub_files = [f"<error: {e_sub}>"]
                            if s_clean.startswith(code_prefix6) or model_key in s_clean:
                                similar_subs.append(sub.name)
                    except OSError as e_grp:
                        similar_subs.append(f"<error: {e_grp}>")
                    matching_groups.append(
                        {
                            "group_dir": str(g_dir),
                            "exact_part_dir_contents": exact_sub_files,
                            "similar_subfolders_sample": similar_subs[:30],
                        }
                    )
            diag["matching_group_folders"] = matching_groups
    except OSError as exc:
        diag["root_access_error"] = str(exc)

    if csv_file is not None:
        diag["csv_file"] = str(csv_file)
        try:
            raw_text = _read_csv_text_with_fallback(csv_file)
            diag["csv_first_15_lines"] = raw_text.splitlines()[:15]
        except Exception as exc:  # noqa: BLE001
            diag["csv_read_error"] = str(exc)

    return diag


def load_cav_from_inspection_source(
    item_code: str,
    *,
    preferred_rev: str | None = None,
    inspection_root: str | Path | None = None,
    root_dir: str | Path | None = None,
) -> InspectionCSVData:
    """Find and parse the Inspection CSV file for the exact `item_code`."""
    clean_code = str(item_code or "").strip().upper()
    effective_root = inspection_root if inspection_root is not None else root_dir
    csv_file, active_files, active_revs, is_from_old = _find_inspection_csv_with_context(
        clean_code,
        preferred_rev=preferred_rev,
        inspection_root=effective_root,
    )
    parsed = parse_inspection_csv(csv_file)
    if parsed.item_code.strip().upper() != clean_code:
        parsed.item_code = clean_code
    parsed.active_csv_files = active_files
    parsed.active_revisions = active_revs
    parsed.is_from_old_archive = bool(is_from_old or parsed.is_from_old_archive)

    combined_warnings = list(parsed.warnings)
    if len(active_revs) > 1:
        revs_str = ", ".join(f"Rev {r}" for r in active_revs)
        files_str = ", ".join(active_files)
        combined_warnings.append(
            f"Thư mục gốc của mã '{clean_code}' đang tồn tại đồng thời nhiều Revision ({revs_str}: {files_str}) "
            f"do QC chưa chuyển file cũ vào thư mục 'old'. Đang sử dụng file '{csv_file.name}' (Rev {parsed.rev}, Ver {parsed.version})."
        )
    parsed.warnings = tuple(combined_warnings)
    return parsed


def validate_part_master(item_code: object, item_name: object, rev: object) -> tuple[str, str, str]:
    """Validate and normalize part master fields.

    Rules:
    - item_code: Non-empty, uppercase, trimmed.
    - item_name: Non-empty, trimmed.
    - rev: Exactly 2 digits, "01" to "99".

    Returns:
        (clean_item_code, clean_item_name, clean_rev)
    Raises:
        PartMasterValidationError if any rule is violated.
    """
    code_str = str(item_code or "").strip().upper()
    if not code_str:
        raise PartMasterValidationError("Vui lòng nhập Mã linh kiện!")

    name_str = str(item_name or "").strip()
    if not name_str:
        raise PartMasterValidationError("Vui lòng nhập Tên linh kiện!")

    rev_str = str(rev or "").strip()
    if not rev_str:
        raise PartMasterValidationError("Vui lòng nhập Rev linh kiện!")

    if not (len(rev_str) == 2 and rev_str.isdigit() and 1 <= int(rev_str) <= 99):
        raise PartMasterValidationError(
            f"Rev linh kiện '{rev_str}' không hợp lệ. Rev bắt buộc phải là đúng 2 chữ số (từ 01 đến 99)!"
        )

    return code_str, name_str, rev_str


class PartMasterRegistry:
    """SQLite-backed persistent Part Master registry."""

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = str(db_path)
        self._lock = threading.Lock()
        self._init_connection()

    def _init_connection(self) -> None:
        if self._db_path != ":memory:":
            Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False, timeout=30.0)
        self._conn.row_factory = sqlite3.Row
        self._setup_pragmas()
        self._create_schema()

    def _setup_pragmas(self) -> None:
        self._conn.execute("PRAGMA busy_timeout=30000")
        is_network = self._db_path.startswith(r"\\") or self._db_path.startswith("//")
        if is_network:
            self._conn.execute("PRAGMA journal_mode=DELETE")
        elif self._db_path != ":memory:":
            try:
                self._conn.execute("PRAGMA journal_mode=WAL")
            except sqlite3.OperationalError:
                pass

    def _create_schema(self) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS part_master (
                    item_code TEXT PRIMARY KEY,
                    item_name TEXT NOT NULL,
                    rev TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    cav_list TEXT NOT NULL DEFAULT '',
                    carton_qty TEXT NOT NULL DEFAULT ''
                );
                """
            )
            # Migrate existing databases that were created before cav_list / carton_qty columns existed
            cols = {
                row["name"]
                for row in self._conn.execute("PRAGMA table_info(part_master)").fetchall()
            }
            if "cav_list" not in cols:
                self._conn.execute(
                    "ALTER TABLE part_master ADD COLUMN cav_list TEXT NOT NULL DEFAULT ''"
                )
            if "carton_qty" not in cols:
                self._conn.execute(
                    "ALTER TABLE part_master ADD COLUMN carton_qty TEXT NOT NULL DEFAULT ''"
                )
            self._conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_part_master_item_name
                ON part_master(item_name);
                """
            )

    def close(self) -> None:
        with self._lock:
            if hasattr(self, "_conn") and self._conn:
                try:
                    self._conn.close()
                except Exception:
                    pass

    def get(self, item_code: str) -> PartMaster | None:
        """Look up a part master entry by item_code (case-insensitive, trimmed)."""
        clean_code = str(item_code or "").strip().upper()
        if not clean_code:
            return None

        with self._lock:
            cur = self._conn.execute(
                "SELECT item_code, item_name, rev, updated_at, cav_list, carton_qty FROM part_master WHERE item_code = ?",
                (clean_code,),
            )
            row = cur.fetchone()
            if row:
                return PartMaster(
                    item_code=row["item_code"],
                    item_name=row["item_name"],
                    rev=row["rev"],
                    updated_at=row["updated_at"],
                    cav_list=row["cav_list"] or "",
                    carton_qty=row["carton_qty"] or "",
                )
            return None

    def upsert(
        self,
        item_code: object,
        item_name: object,
        rev: object,
        cav_list: object | None = None,
        carton_qty: object | None = None,
    ) -> PartMaster:
        """Validate and insert or update a part master record.

        If `cav_list` or `carton_qty` is None (not specified by caller), any existing value stored
        for `item_code` is preserved.
        """
        code_clean, name_clean, rev_clean = validate_part_master(item_code, item_name, rev)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        existing = self.get(code_clean) if (cav_list is None or carton_qty is None) else None

        if cav_list is not None:
            parsed_cavs = parse_manual_cav_input(cav_list)
            cav_clean = format_cav_list(parsed_cavs)
        else:
            cav_clean = existing.cav_list if existing is not None else ""

        if carton_qty is not None:
            raw_qty = str(carton_qty).strip()
            qty_clean = str(int(raw_qty)) if (raw_qty.isdigit() and int(raw_qty) > 0) else ""
        else:
            qty_clean = existing.carton_qty if existing is not None else ""

        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO part_master (item_code, item_name, rev, updated_at, cav_list, carton_qty)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(item_code) DO UPDATE SET
                    item_name = excluded.item_name,
                    rev = excluded.rev,
                    updated_at = excluded.updated_at,
                    cav_list = excluded.cav_list,
                    carton_qty = excluded.carton_qty;
                """,
                (code_clean, name_clean, rev_clean, now_str, cav_clean, qty_clean),
            )

        return PartMaster(
            item_code=code_clean,
            item_name=name_clean,
            rev=rev_clean,
            updated_at=now_str,
            cav_list=cav_clean,
            carton_qty=qty_clean,
        )

    def delete(self, item_code: str) -> bool:
        """Delete a part master entry by item_code. Returns True if deleted."""
        clean_code = str(item_code or "").strip().upper()
        if not clean_code:
            return False

        with self._lock, self._conn:
            cur = self._conn.execute(
                "DELETE FROM part_master WHERE item_code = ?",
                (clean_code,),
            )
            return cur.rowcount > 0

    def list_all(self, search_query: str = "") -> list[PartMaster]:
        """List part master entries, optionally filtered by search_query."""
        query = str(search_query or "").strip().upper()
        with self._lock:
            if query:
                pattern = f"%{query}%"
                cur = self._conn.execute(
                    """
                    SELECT item_code, item_name, rev, updated_at, cav_list, carton_qty
                    FROM part_master
                    WHERE item_code LIKE ? OR UPPER(item_name) LIKE ?
                    ORDER BY item_code ASC;
                    """,
                    (pattern, pattern),
                )
            else:
                cur = self._conn.execute(
                    """
                    SELECT item_code, item_name, rev, updated_at, cav_list, carton_qty
                    FROM part_master
                    ORDER BY item_code ASC;
                    """
                )

            return [
                PartMaster(
                    item_code=row["item_code"],
                    item_name=row["item_name"],
                    rev=row["rev"],
                    updated_at=row["updated_at"],
                    cav_list=row["cav_list"] or "",
                    carton_qty=row["carton_qty"] or "",
                )
                for row in cur.fetchall()
            ]

    def count(self) -> int:
        """Return total number of registered parts in master."""
        with self._lock:
            cur = self._conn.execute("SELECT COUNT(*) FROM part_master")
            return int(cur.fetchone()[0])
