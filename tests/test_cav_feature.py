from __future__ import annotations

from pathlib import Path
from tkinter import messagebox, ttk

import fitz
import pytest

from core.part_master import (
    InspectionCSVError,
    PartMasterRegistry,
    PartMasterValidationError,
    find_inspection_csv_file,
    format_cav_list,
    load_cav_from_inspection_source,
    parse_inspection_csv,
    parse_manual_cav_input,
)
from core.po_registry import PORegistry
from core.slip_printer_engine import (
    create_record,
    generate_pdf_from_records,
    generate_preview_image,
    get_default_layout_config,
)
from ui.app_controller import AppController
from ui.app_state import AppState
from ui.components.data_tab import DataTabPanel

REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PDF = REPO_ROOT / "template.pdf"
FIXTURE_INSPECTION_ROOT = REPO_ROOT / "tests" / "fixtures" / "inspection_data"
DOWNLOAD_DIR = Path(r"d:\SETUP\tvn183660\download")


def _sample_csv_path(filename: str) -> Path:
    """Return sample CSV from user download path if present, else fixture copy."""
    candidate = DOWNLOAD_DIR / filename
    if candidate.is_file():
        return candidate
    part_code = filename.split("_")[0]
    return FIXTURE_INSPECTION_ROOT / part_code[:5] / part_code / filename


class _HarnessView:
    """Lightweight view wrapper around DataTabPanel for controller & preview integration testing."""

    def __init__(self, state: AppState, controller: AppController, data_tab: DataTabPanel) -> None:
        self.app_state = state
        self.controller = controller
        self.data_tab = data_tab
        self.logs: list[str] = []

    def append_log(self, msg: str) -> None:
        self.logs.append(msg)

    def set_records(self, records, select_index=None, source=None) -> None:
        self.app_state.records = list(records)
        if select_index is not None and self.app_state.records:
            self.app_state.selected_record_index = min(select_index, len(self.app_state.records) - 1)
        self.data_tab.set_records(select_index=select_index)

    def auto_commit_form(self) -> bool:
        return self.data_tab.auto_commit_form()

    def refresh_preview_image(self) -> None:
        if self.app_state.split_cav_var.get() and not self.app_state.selected_cavs:
            self.app_state.preview_source_image = None
            self.data_tab.reset_preview_display()
            self.data_tab.preview_image_label.configure(
                text="⚠️ Đang bật 'Tách CAV' nhưng chưa chọn CAV nào.\nVui lòng chọn ít nhất một CAV hợp lệ để xem trước tem."
            )
            self.data_tab.set_qr_payload_text("")
            return


class TestRealCSVParserAndFolderLookup:
    """Kiểm thử parser với 3 file CSV gốc do người dùng cung cấp và cấu trúc thư mục thực tế."""

    @pytest.mark.parametrize(
        ("filename", "expected_code", "expected_rev", "expected_ver", "expected_name", "expected_material", "expected_pcs"),
        [
            ("302YJ03340_02_01.csv", "302YJ03340", "02", "01", "BOTTLE WASTE", "HD-PE", 60),
            ("302YJ12010_08_02.csv", "302YJ12010", "08", "02", "FRAME DRUM", "ABS-300", 18),
            ("302YJ14030_03_01.csv", "302YJ14030", "03", "01", "CASE DLP", "ABS P2H-AT", 30),
        ],
    )
    def test_parse_three_original_csv_files(
        self,
        filename: str,
        expected_code: str,
        expected_rev: str,
        expected_ver: str,
        expected_name: str,
        expected_material: str,
        expected_pcs: int,
    ) -> None:
        csv_path = _sample_csv_path(filename)
        assert csv_path.is_file(), f"Missing sample CSV: {csv_path}"

        parsed = parse_inspection_csv(csv_path)
        assert parsed.max_cav_n == 16
        assert parsed.item_code == expected_code
        assert parsed.rev == expected_rev
        assert parsed.revision == expected_rev
        assert parsed.version == expected_ver
        assert parsed.item_name == expected_name
        assert parsed.material == expected_material
        assert parsed.valid_cavs == [1, 2]
        assert parsed.cav_text == "1, 2"
        assert parsed.pcs_per_box == expected_pcs

    def test_find_csv_in_real_network_folder_structure(self) -> None:
        for code, expected_file in [
            ("302YJ03340", "302YJ03340_02_01.csv"),
            ("302YJ12010", "302YJ12010_08_02.csv"),
            ("302YJ14030", "302YJ14030_03_01.csv"),
        ]:
            found = find_inspection_csv_file(code, root_dir=FIXTURE_INSPECTION_ROOT)
            assert found.name == expected_file

            data = load_cav_from_inspection_source(code, root_dir=FIXTURE_INSPECTION_ROOT)
            assert data.valid_cavs == [1, 2]
            assert data.cav_text == "1, 2"

    def test_multiple_revision_and_version_selection_rule(self, tmp_path: Path) -> None:
        part_dir = tmp_path / "302YJ" / "302YJ03340"
        part_dir.mkdir(parents=True)

        csv_template = (
            "maxCavN:16\n"
            "302YJ03340\n"
            "{rev}\n"
            "{ver}\n"
            "BOTTLE WASTE\n"
            "HD-PE\n"
            "{bools}\n"
            "True,1,,2.95,0.08,-0.08,2.85,2.92\n"
        )
        bools_1_2 = ",".join(["True", "True"] + ["False"] * 14)
        bools_1_2_3 = ",".join(["True", "True", "True"] + ["False"] * 13)
        bools_3_4 = ",".join(["False", "False", "True", "True"] + ["False"] * 12)

        (part_dir / "302YJ03340_01_02.csv").write_text(
            csv_template.format(rev="01", ver="02", bools=bools_1_2), encoding="utf-8"
        )
        (part_dir / "302YJ03340_02_01.csv").write_text(
            csv_template.format(rev="02", ver="01", bools=bools_1_2_3), encoding="utf-8"
        )
        (part_dir / "302YJ03340_02_03.csv").write_text(
            csv_template.format(rev="02", ver="03", bools=bools_3_4), encoding="utf-8"
        )

        # Không chỉ định preferred_rev -> lấy revision cao nhất (02), version cao nhất (03)
        best = load_cav_from_inspection_source("302YJ03340", root_dir=tmp_path)
        assert best.file_path.name == "302YJ03340_02_03.csv"
        assert best.valid_cavs == [3, 4]

        # Chỉ định preferred_rev="01" -> lấy đúng Rev 01
        rev01 = load_cav_from_inspection_source("302YJ03340", preferred_rev="01", root_dir=tmp_path)
        assert rev01.file_path.name == "302YJ03340_01_02.csv"
        assert rev01.valid_cavs == [1, 2]

    def test_folder_and_filename_with_leading_spaces_and_4char_group_and_no_code_guessing(
        self, tmp_path: Path
    ) -> None:
        """Kiểm thử thực tế đường dẫn có dấu cách đầu tên folder/file và KHÔNG tự đoán mã (3V <-> 30)."""
        bools_1_2 = ",".join(["True", "True"] + ["False"] * 14)
        bools_5_6_7_8 = ",".join(["False"] * 4 + ["True"] * 4 + ["False"] * 8)

        # Trường hợp 1: "\\10.170.178.1\data\5000PJ\Inspection_data\ 302Y\ 302YJJ1320\ 302YJJ1320_01_01.csv"
        spaced_dir = tmp_path / " 302Y" / " 302YJJ1320"
        spaced_dir.mkdir(parents=True)
        (spaced_dir / " 302YJJ1320_01_01.csv").write_text(
            f"maxCavN:16\n 302YJJ1320\n01\n01\nHOLDER ROLLER\nPOM\n{bools_1_2}\nFalse\n2\n45\n",
            encoding="utf-8",
        )

        # Trường hợp 2: "\\10.170.178.1\data\5000PJ\Inspection_data\302RV\302RVJ1530\302RVJ1530_01_07.csv"
        rv_dir = tmp_path / "302RV" / "302RVJ1530"
        rv_dir.mkdir(parents=True)
        (rv_dir / "302RVJ1530_01_07.csv").write_text(
            f"maxCavN:16\n302RVJ1530\n01\n07\nCASE CONTAINER E 3\nHIPS\n{bools_5_6_7_8}\nFalse\n2\n20\n",
            encoding="utf-8",
        )

        # Trường hợp 3: "\\10.170.178.1\data\5000PJ\Inspection_data\3V2L1\3V2L1J1011\3V2L1J1011_01_03.csv"
        v_dir = tmp_path / "3V2L1" / "3V2L1J1011"
        v_dir.mkdir(parents=True)
        (v_dir / "3V2L1J1011_01_03.csv").write_text(
            f"maxCavN:16\n3V2L1J1011\n01\n03\nPULLEY COVER\nABS\n{bools_1_2}\nFalse\n2\n50\n",
            encoding="utf-8",
        )

        data_spaced = load_cav_from_inspection_source("302YJJ1320", root_dir=f'"{tmp_path}"')
        assert data_spaced.item_name == "HOLDER ROLLER"
        assert data_spaced.rev == "01"
        assert data_spaced.valid_cavs == [1, 2]
        assert data_spaced.pcs_per_box == 45

        data_rv = load_cav_from_inspection_source("302RVJ1530", root_dir=tmp_path)
        assert data_rv.item_name == "CASE CONTAINER E 3"
        assert data_rv.rev == "01"
        assert data_rv.valid_cavs == [5, 6, 7, 8]
        assert data_rv.pcs_per_box == 20

        data_3v = load_cav_from_inspection_source("3V2L1J1011", root_dir=tmp_path)
        assert data_3v.item_name == "PULLEY COVER"
        assert data_3v.rev == "01"
        assert data_3v.valid_cavs == [1, 2]
        assert data_3v.pcs_per_box == 50

        # Mã 3V2RVJ1530 KHÔNG tồn tại trên server (chỉ có 302RVJ1530) -> bắt buộc báo lỗi không tìm thấy, tuyệt đối không đoán mã
        with pytest.raises(InspectionCSVError, match="Không tìm thấy tệp CSV master"):
            load_cav_from_inspection_source("3V2RVJ1530", root_dir=tmp_path)

    def test_excel_saved_csv_trailing_commas_and_internal_code_mismatch_3v2xc25160_and_302nr25651(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Kiểm thử thực tế lỗi của 3V2XC25160 và 302NR25651:
        - File CSV lưu bằng Excel có dư dấu phẩy ',,,' cuối dòng Boolean CAV (19 cột thay vì 16 cột).
        - Ô A2 bên trong CSV ghi mã bản vẽ cũ (302XC25160 / 302NR25650) hoặc dòng Material để trống.
        - Ghi log chẩn đoán vào thư mục error_log khi tra cứu mã không tồn tại (302NR25650).
        """
        from core.error_logger import ENV_ERROR_LOG_DIR, log_error_event
        from core.part_master import collect_inspection_diagnostics

        log_dir = tmp_path / "error_log"
        monkeypatch.setenv(ENV_ERROR_LOG_DIR, str(log_dir))

        bools_1_2 = ",".join(["TRUE", "TRUE"] + ["FALSE"] * 14)
        bools_1_to_4 = ",".join(["TRUE"] * 4 + ["FALSE"] * 12)

        # 1. 3V2XC\3V2XC25160\3V2XC25160_01_02.csv (Lưu bằng Excel có thêm ',,,' ở cuối dòng CAV, A2 ghi 2XC25160)
        xc_dir = tmp_path / "3V2XC" / "3V2XC25160"
        (xc_dir / "OLD").mkdir(parents=True)
        (xc_dir / "3V2XC25160_01_02.csv").write_text(
            f"maxCavN:16,,,,,,,,,,,,,,,,,,\n"
            f"2XC25160,,,,,,,,,,,,,,,,,,\n"
            f"1,,,,,,,,,,,,,,,,,,\n"
            f"2,,,,,,,,,,,,,,,,,,\n"
            f"HOLDER FEED,,,,,,,,,,,,,,,,,,\n"
            f",,,,,,,,,,,,,,,,,,\n"  # Dòng Material để trống trong Excel
            f"{bools_1_2},,,\n"     # Dòng CAV có thêm 3 dấu phẩy cuối dòng do Excel tự thêm theo cột thứ 19
            f"FALSE,,,,,,,,,,,,,,,,,,\n"
            f"2,,,,,,,,,,,,,,,,,,\n"
            f"80,,,,,,,,,,,,,,,,,,\n"
            f"mix,,,,,,,,,,,,,,,,,,\n"
            f"TRUE,1,,6.03,0.02,-0.02,mm,PG,,,to,,FALSE,FALSE,FALSE,TRUE,TRUE,TRUE,\n",
            encoding="utf-8",
        )

        parsed_xc = load_cav_from_inspection_source("3V2XC25160", root_dir=tmp_path)
        assert parsed_xc.item_code == "3V2XC25160"
        assert parsed_xc.item_name == "HOLDER FEED"
        assert parsed_xc.rev == "01"
        assert parsed_xc.version == "02"
        assert parsed_xc.valid_cavs == [1, 2]
        assert parsed_xc.pcs_per_box == 80

        # 2. 302NR\302NR25651\302NR25651_01_01.csv (Định dạng CSV cũ từ error_log thực tế:
        #    KHÔNG có dòng maxCavN:16 ở đầu, 8 dòng Boolean CAV xếp dọc + 1 dòng cờ False + " 4 " + SL/thùng + "mix")
        nr_dir = tmp_path / "302NR" / "302NR25651"
        nr_dir.mkdir(parents=True)
        (nr_dir / "302NR25651_01_01.csv").write_text(
            "302NR25651\n"
            "01\n"
            "01\n"
            "PULLEY RELEASE\n"
            "PPS C6008G\n"
            "True\n"
            "True\n"
            "True\n"
            "True\n"
            "False\n"
            "False\n"
            "False\n"
            "False\n"
            "False\n"
            " 4 \n"
            "500\n"
            "mix\n"
            "True,1,,2.95,0.05,-0.05,mm,N,,,,,False,False,False,True,True,True,\n",
            encoding="utf-8",
        )

        parsed_nr = load_cav_from_inspection_source("302NR25651", root_dir=tmp_path)
        assert parsed_nr.max_cav_n == 8
        assert parsed_nr.item_code == "302NR25651"
        assert parsed_nr.item_name == "PULLEY RELEASE"
        assert parsed_nr.rev == "01"
        assert parsed_nr.version == "01"
        assert parsed_nr.material == "PPS C6008G"
        assert parsed_nr.valid_cavs == [1, 2, 3, 4]
        assert parsed_nr.cav_text == "1, 2, 3, 4"
        assert parsed_nr.pcs_per_box == 500

        # 2b. 302NR\302NR14051\302NR14051_01_01.csv (Định dạng CSV cũ từ error_log thực tế: CAV 1, 2)
        nr2_dir = tmp_path / "302NR" / "302NR14051"
        nr2_dir.mkdir(parents=True)
        (nr2_dir / "302NR14051_01_01.csv").write_text(
            "302NR14051\n"
            "01\n"
            "01\n"
            "CASE DLP\n"
            "ABS P2H-AT\n"
            "True\n"
            "True\n"
            "False\n"
            "False\n"
            "False\n"
            "False\n"
            "False\n"
            "False\n"
            "False\n"
            " 2 \n"
            "30\n"
            "mix\n"
            "True,1,,1.46,0.03,-0.03,mm,M,,,to,,False,False,False,True,True,True,\n",
            encoding="utf-8",
        )

        parsed_nr2 = load_cav_from_inspection_source("302NR14051", root_dir=tmp_path)
        assert parsed_nr2.max_cav_n == 8
        assert parsed_nr2.item_code == "302NR14051"
        assert parsed_nr2.item_name == "CASE DLP"
        assert parsed_nr2.rev == "01"
        assert parsed_nr2.version == "01"
        assert parsed_nr2.material == "ABS P2H-AT"
        assert parsed_nr2.valid_cavs == [1, 2]
        assert parsed_nr2.cav_text == "1, 2"
        assert parsed_nr2.pcs_per_box == 30

        # 3. Nhập 302NR25650 (mã đuôi 0 không tồn tại folder) -> báo không tìm thấy và ghi log chẩn đoán
        with pytest.raises(InspectionCSVError, match="Không tìm thấy"):
            load_cav_from_inspection_source("302NR25650", root_dir=tmp_path)

        diag = collect_inspection_diagnostics("302NR25650", inspection_root=tmp_path)
        log_error_event(
            "ITEM_CODE_NOT_FOUND",
            "Không tìm thấy 302NR25650",
            item_code="302NR25650",
            diagnostics=diag,
            app_version="0.1.13",
            async_write=False,
        )
        readable_log = log_dir / "error_log_readable.log"
        assert readable_log.is_file()
        log_text = readable_log.read_text(encoding="utf-8")
        assert "302NR25650" in log_text
        assert "302NR25651" in log_text  # Ghi nhận luôn các folder tương tự đang có trong nhóm 302NR!


class TestCSVParserEdgeCases:
    """Kiểm thử toàn diện các trường hợp lỗi và biên của CSV Parser (Mục 5 & Mục 10)."""

    def test_does_not_confuse_lower_inspection_rows_with_cav_booleans(self, tmp_path: Path) -> None:
        # Toàn bộ 16 CAV là False, nhưng bên dưới có nhiều dòng hạng mục kiểm tra bắt đầu bằng True,1 / True,2
        csv_file = tmp_path / "302YJ99999_01_01.csv"
        csv_file.write_text(
            "maxCavN:16\n"
            "302YJ99999\n"
            "01\n"
            "01\n"
            "TEST PART\n"
            "POM\n"
            + ",".join(["False"] * 16)
            + "\n"
            "True,1,,2.95,0.08,-0.08,2.85,2.92\n"
            "True,2,,4.40,0.05,-0.05,4.41,4.41\n"
            "True,3,,10.0,0.10,-0.10,10.0,10.0\n",
            encoding="utf-8",
        )
        parsed = parse_inspection_csv(csv_file)
        assert parsed.valid_cavs == []
        assert parsed.cav_text == ""

    def test_case_insensitive_booleans_and_blank_lines_and_shift_jis_encoding(self, tmp_path: Path) -> None:
        csv_file = tmp_path / "302YJ88888_01_01.csv"
        bools = ["false", " false ", "TRUE", "True", "true", "FALSE"] + ["False"] * 10
        content = (
            "\n"
            "maxCavN:16,,,,\n"
            "\n"
            "302YJ88888,,,,\n"
            "01,,,,\n"
            "01,,,,\n"
            "PULLEY FEED (日本語テスト),,,,\n"
            "POM (ポリアセタール),,,,\n"
            + ",".join(bools)
            + "\n"
        )
        csv_file.write_bytes(content.encode("cp932"))
        parsed = parse_inspection_csv(csv_file)
        assert parsed.valid_cavs == [3, 4, 5]
        assert parsed.cav_text == "3, 4, 5"

    def test_boolean_count_mismatch_raises_error(self, tmp_path: Path) -> None:
        csv_file = tmp_path / "bad_count.csv"
        csv_file.write_text(
            "maxCavN:16\n"
            "302YJ03340\n"
            "02\n"
            "01\n"
            "BOTTLE WASTE\n"
            "HD-PE\n"
            "True,True,False\n",
            encoding="utf-8",
        )
        with pytest.raises(InspectionCSVError, match="Số phần tử Boolean CAV"):
            parse_inspection_csv(csv_file)

    def test_missing_metadata_or_invalid_header_raises_error(self, tmp_path: Path) -> None:
        f1 = tmp_path / "no_header.csv"
        f1.write_text("302YJ03340\n02\n01\n", encoding="utf-8")
        with pytest.raises(InspectionCSVError, match="maxCavN|không đủ cấu trúc header"):
            parse_inspection_csv(f1)

        f2 = tmp_path / "truncated.csv"
        f2.write_text("maxCavN:16\n302YJ03340\n02\n", encoding="utf-8")
        with pytest.raises(InspectionCSVError, match="không đủ cấu trúc header|thiếu dòng metadata"):
            parse_inspection_csv(f2)

    def test_nonexistent_file_or_permission_denied_handled_gracefully(self, tmp_path: Path) -> None:
        with pytest.raises(InspectionCSVError, match="Không tìm thấy"):
            parse_inspection_csv(tmp_path / "missing.csv")

        with pytest.raises(InspectionCSVError, match="Không tìm thấy"):
            load_cav_from_inspection_source("302YJ03340", root_dir=tmp_path / "nonexistent_root")


class TestManualPartMasterFallback:
    """Kiểm thử cơ chế nhập/đăng ký master thủ công khi không đọc được nguồn CSV (Mục 8)."""

    def test_parse_manual_cav_input_validation(self) -> None:
        assert parse_manual_cav_input("") == []
        assert parse_manual_cav_input("16, 2, 1, 2, 5") == [1, 2, 5, 16]
        assert format_cav_list(parse_manual_cav_input("3; 4; 5; 6")) == "3, 4, 5, 6"

        with pytest.raises(PartMasterValidationError, match="1 đến 16"):
            parse_manual_cav_input("0, 1, 2")
        with pytest.raises(PartMasterValidationError, match="1 đến 16"):
            parse_manual_cav_input("1, 17")
        with pytest.raises(PartMasterValidationError, match="không hợp lệ"):
            parse_manual_cav_input("1, hai, 3")

    def test_part_master_registry_persists_cav_list_and_migrates_schema(self, tmp_path: Path) -> None:
        db_path = tmp_path / "part_master.db"
        reg = PartMasterRegistry(db_path)
        try:
            saved = reg.upsert("302YJ90000", "COVER TEST", "01", cav_list="4, 2, 4, 1")
            assert saved.cav_list == "1, 2, 4"
            assert saved.valid_cavs == [1, 2, 4]

            # Update name/rev without passing cav_list preserves existing cav_list
            updated = reg.upsert("302YJ90000", "COVER TEST NEW", "02")
            assert updated.cav_list == "1, 2, 4"
        finally:
            reg.close()


class TestSplitCAVWorkflowAndController:
    """Kiểm thử luồng Tách CAV, chọn CAV, chặn in khi chưa chọn (Mục 6, 7, 11)."""

    def test_cav_workflow_with_three_sample_csvs_and_split_cav(
        self, tk_root, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        state = AppState(tk_root)
        controller = AppController(state)
        notebook = ttk.Notebook(tk_root)
        data_tab = DataTabPanel(notebook, controller)
        view = _HarnessView(state, controller, data_tab)
        controller.set_view(view)
        try:
            state.inspection_root_var.set(str(FIXTURE_INSPECTION_ROOT))
            state.records.clear()
            data_tab.clear_form()

            # 1. Chọn mã 302YJ03340 -> đọc CSV -> CAV 1, 2
            state.item_code_var.set("302YJ03340")
            controller.on_item_code_input_changed()
            assert state.valid_cavs == [1, 2]
            assert state.split_cav_var.get() is False
            assert state.cav_var.get() == "1, 2"

            # Tắt Tách CAV -> thêm dòng -> in "1, 2"
            state.carton_qty_var.set("20")
            state.box_var.set("001/001")
            controller.add_record()
            assert len(state.records) == 1
            assert state.records[-1].cav_no == "1, 2"

            # 2. Bật Tách CAV nhưng chưa chọn CAV -> chặn preview, thêm dòng và tạo PDF
            state.split_cav_var.set(True)
            controller.on_split_cav_toggled()
            assert state.selected_cavs == []
            assert state.cav_var.get() == ""

            # Kiểm tra chặn Preview
            view.refresh_preview_image()
            assert state.preview_source_image is None
            assert "Tách CAV" in str(data_tab.preview_image_label.cget("text"))

            # Kiểm tra chặn Thêm dòng
            errors: list[str] = []
            monkeypatch.setattr(messagebox, "showerror", lambda title, msg, **kw: errors.append(msg))
            state.box_var.set("002/002")
            controller.add_record()
            assert len(state.records) == 1  # Không thêm được dòng mới
            assert errors and "Tách CAV" in errors[-1]

            # Kiểm tra chặn Tạo PDF
            errors.clear()
            controller.start_generation()
            assert errors and "Tách CAV" in errors[-1]

            # 3. Bật Tách CAV: chọn 1 -> in "1"
            controller.set_selected_cavs([1])
            assert state.cav_var.get() == "1"
            state.box_var.set("002/004")
            controller.add_record()
            assert state.records[-1].cav_no == "1"

            # 4. Bật Tách CAV: chọn 2 -> in "2"
            controller.set_selected_cavs([2])
            assert state.cav_var.get() == "2"
            state.box_var.set("003/004")
            controller.add_record()
            assert state.records[-1].cav_no == "2"

            # 5. Bật Tách CAV: chọn 1 và 2 -> in "1, 2"
            controller.set_selected_cavs([2, 1])
            assert state.cav_var.get() == "1, 2"
            state.box_var.set("004/004")
            controller.add_record()
            assert state.records[-1].cav_no == "1, 2"

            # 6. Không cho phép chọn CAV không có trong CSV (ví dụ CAV 3)
            with pytest.raises(ValueError, match="không nằm trong danh sách CAV hợp lệ"):
                controller.set_cav_selection(3, True)
            with pytest.raises(ValueError, match="không nằm trong danh sách CAV hợp lệ"):
                controller.set_selected_cavs([1, 5])
        finally:
            state.po_registry.close()
            state.part_master.close()
            data_tab.destroy()
            notebook.destroy()

    def test_printing_rule_cav_3_4_5_6_split_batches(
        self, tk_root, tmp_path: Path
    ) -> None:
        """Kiểm thử đúng kịch bản Mục 7: CSV cho CAV 3, 4, 5, 6 -> tắt in '3, 4, 5, 6'; bật chọn 3, 4 -> '3, 4'; chọn 5, 6 -> '5, 6'."""
        part_dir = tmp_path / "302YJ" / "302YJ55555"
        part_dir.mkdir(parents=True)
        bools = ["False", "False", "True", "True", "True", "True"] + ["False"] * 10
        (part_dir / "302YJ55555_01_01.csv").write_text(
            "maxCavN:16\n302YJ55555\n01\n01\nGEAR IDLE\nPOM\n" + ",".join(bools) + "\n",
            encoding="utf-8",
        )

        state = AppState(tk_root)
        controller = AppController(state)
        notebook = ttk.Notebook(tk_root)
        data_tab = DataTabPanel(notebook, controller)
        view = _HarnessView(state, controller, data_tab)
        controller.set_view(view)
        try:
            state.inspection_root_var.set(str(tmp_path))
            state.records.clear()
            data_tab.clear_form()

            state.item_code_var.set("302YJ55555")
            controller.on_item_code_input_changed()
            assert state.valid_cavs == [3, 4, 5, 6]
            assert state.cav_var.get() == "3, 4, 5, 6"

            # Lần 1: Tắt Tách CAV => "3, 4, 5, 6"
            state.carton_qty_var.set("50")
            state.box_var.set("001/003")
            controller.add_record()
            assert state.records[-1].cav_no == "3, 4, 5, 6"

            # Lần 2: Bật Tách CAV, chọn 3 và 4 => "3, 4"
            state.split_cav_var.set(True)
            controller.on_split_cav_toggled()
            controller.set_selected_cavs([3, 4])
            assert state.cav_var.get() == "3, 4"
            state.box_var.set("002/003")
            controller.add_record()
            assert state.records[-1].cav_no == "3, 4"

            # Lần 3: Chọn 5 và 6 => "5, 6"
            controller.set_selected_cavs([5, 6])
            assert state.cav_var.get() == "5, 6"
            state.box_var.set("003/003")
            controller.add_record()
            assert state.records[-1].cav_no == "5, 6"
        finally:
            state.po_registry.close()
            state.part_master.close()
            data_tab.destroy()
            notebook.destroy()

    def test_consecutive_item_code_lookups_exact_match_and_missing_code_reported(
        self, tk_root, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Kiểm thử nạp liên tiếp nhiều mã hàng: chỉ mã thực tế tồn tại mới lấy thông tin (kèm SL/thùng); mã không có phải báo rõ và xóa trắng."""
        warnings: list[str] = []
        monkeypatch.setattr(messagebox, "showwarning", lambda title, msg, **kw: warnings.append(msg))

        state = AppState(tk_root)
        controller = AppController(state)
        notebook = ttk.Notebook(tk_root)
        data_tab = DataTabPanel(notebook, controller)
        view = _HarnessView(state, controller, data_tab)
        controller.set_view(view)
        try:
            state.inspection_root_var.set(str(FIXTURE_INSPECTION_ROOT))
            state.records.clear()
            data_tab.clear_form()

            # Lần 1: Nhập 302YJ03340 -> BOTTLE WASTE, Rev 02, SL/thùng 60, CAV 1, 2
            data_tab.item_code_entry.delete(0, "end")
            data_tab.item_code_entry.insert(0, "302YJ03340")
            data_tab._on_item_code_return(None)
            assert state.item_code_var.get() == "302YJ03340"
            assert state.item_name_var.get() == "BOTTLE WASTE"
            assert state.rev_var.get() == "02"
            assert state.carton_qty_var.get() == "60"
            assert state.cav_var.get() == "1, 2"
            assert not warnings

            # Lần 2 (KHÔNG bấm Xóa biểu mẫu): Nhập 302YJ12010 -> FRAME DRUM, Rev 08, SL/thùng 18, CAV 1, 2
            data_tab.item_code_entry.delete(0, "end")
            data_tab.item_code_entry.insert(0, "302YJ12010")
            data_tab._on_item_code_return(None)
            assert state.item_code_var.get() == "302YJ12010"
            assert state.item_name_var.get() == "FRAME DRUM"
            assert state.rev_var.get() == "08"
            assert state.carton_qty_var.get() == "18"
            assert state.cav_var.get() == "1, 2"
            assert not warnings

            # Giả lập trường hợp part_master.db từng lưu nhầm mã 3V2YJ14030 từ bản cũ
            state.part_master.upsert("3V2YJ14030", "CASE DLP", "03", cav_list="1, 2", carton_qty=30)

            # Lần 3: Nhập mã KHÔNG tồn tại trong Inspection_data (3V2YJ14030) -> phải báo không tồn tại và xóa trắng các trường
            data_tab.item_code_entry.delete(0, "end")
            data_tab.item_code_entry.insert(0, "3V2YJ14030")
            data_tab._on_item_code_return(None)
            assert state.item_code_var.get() == "3V2YJ14030"
            assert state.item_name_var.get() == ""
            assert state.rev_var.get() == ""
            assert state.carton_qty_var.get() == ""
            assert state.cav_var.get() == ""
            assert state.valid_cavs == []
            assert warnings and "3V2YJ14030" in warnings[-1] and "không tồn tại" in warnings[-1]
            assert "không tồn tại" in state.status_var.get()
            # Bản ghi nhầm trong part_master cũng được dọn sạch
            assert state.part_master.get("3V2YJ14030") is None

            # Lần 4: Nhập mã đúng tồn tại thực tế 302YJ14030 -> CASE DLP, Rev 03, SL/thùng 30, CAV 1, 2
            warnings.clear()
            data_tab.item_code_entry.delete(0, "end")
            data_tab.item_code_entry.insert(0, "302YJ14030")
            data_tab._on_item_code_return(None)
            assert state.item_code_var.get() == "302YJ14030"
            assert state.item_name_var.get() == "CASE DLP"
            assert state.rev_var.get() == "03"
            assert state.carton_qty_var.get() == "30"
            assert state.cav_var.get() == "1, 2"
            assert not warnings
        finally:
            state.po_registry.close()
            state.part_master.close()
            data_tab.destroy()
            notebook.destroy()


class TestSlipPDFAndPreviewRendering:
    """Kiểm thử hiển thị CAV No. trên Preview, PDF A4/Letter, không làm hỏng QR/Barcode và bố cục tem (Mục 9, 10, 11)."""

    def test_pdf_and_preview_render_cav_no_and_preserve_qr_and_layout(self, tmp_path: Path) -> None:
        layout_cfg = get_default_layout_config()
        rec_short = create_record(
            row_number=4,
            item_code="302YJ03340",
            item_name="BOTTLE WASTE",
            carton_qty=20,
            total_qty=20,
            po="00232098",
            po_detail="0001",
            po_sub="00",
            box="001/003",
            rev="02",
            lot="",
            cav_no="1, 2",
        )
        # QR payload vẫn đúng 129 ký tự chuẩn EDI
        assert len(rec_short.qr_payload) == 129

        # Preview image tạo thành công và khác với bản không có CAV
        rec_empty_cav = create_record(
            row_number=6,
            item_code="302YJ03340",
            item_name="BOTTLE WASTE",
            carton_qty=20,
            total_qty=20,
            po="00232098",
            po_detail="0001",
            po_sub="00",
            box="003/003",
            rev="02",
            lot="",
            cav_no="",
        )
        img_with_cav = generate_preview_image(rec_short, TEMPLATE_PDF, layout_cfg)
        img_no_cav = generate_preview_image(rec_empty_cav, TEMPLATE_PDF, layout_cfg)
        assert img_with_cav.size == img_no_cav.size
        assert img_with_cav.tobytes() != img_no_cav.tobytes()

        # Kiểm tra xuất PDF với cả chuỗi CAV ngắn ("1, 2") và chuỗi CAV rất dài (1..16)
        all_16_cavs = format_cav_list(range(1, 17))
        rec_long = create_record(
            row_number=5,
            item_code="302YJ12010",
            item_name="FRAME DRUM",
            carton_qty=50,
            total_qty=50,
            po="00232098",
            po_detail="0001",
            po_sub="00",
            box="002/003",
            rev="08",
            lot="",
            cav_no=all_16_cavs,
        )

        out_a4 = tmp_path / "out_a4.pdf"
        reg = PORegistry(tmp_path / "po_reg.db")
        try:
            generate_pdf_from_records(
                [rec_short, rec_long, rec_empty_cav],
                TEMPLATE_PDF,
                out_a4,
                layout_config=layout_cfg,
                registry=reg,
                paper_size="A4",
            )
        finally:
            reg.close()

        assert out_a4.is_file()
        doc = fitz.open(str(out_a4))
        try:
            assert len(doc) == 1
            page_text = doc[0].get_text("text")
            assert "1, 2" in page_text
            assert "302YJ03340" in page_text
            assert "302YJ12010" in page_text
        finally:
            doc.close()

        # Kiểm tra khổ Letter (4 tem/trang)
        out_letter = tmp_path / "out_letter.pdf"
        generate_pdf_from_records(
            [rec_short],
            TEMPLATE_PDF,
            out_letter,
            layout_config=layout_cfg,
            paper_size="Letter",
        )
        assert out_letter.is_file()

    def test_error_logger_pytest_isolation_and_deduplication(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from core.error_logger import ENV_ERROR_LOG_DIR, _RECENT_EVENTS, log_error_event

        _RECENT_EVENTS.clear()
        log_dir = tmp_path / "isolated_log"
        monkeypatch.setenv(ENV_ERROR_LOG_DIR, str(log_dir))

        # Two rapid identical calls within 2s -> only 1 entry written
        log_error_event("CSV_PARSE_ERROR", "Duplicate test error", item_code="302Y812170", async_write=False)
        log_error_event("CSV_PARSE_ERROR", "Duplicate test error", item_code="302Y812170", async_write=False)

        readable = log_dir / "error_log_readable.log"
        assert readable.is_file()
        assert readable.read_text(encoding="utf-8").count("Duplicate test error") == 1

    def test_cav_resolution_cache_and_dark_mode_tags(self, tk_root) -> None:
        state = AppState(tk_root)
        controller = AppController(state)
        notebook = ttk.Notebook(tk_root)
        data_tab = DataTabPanel(notebook, controller)
        try:
            state.inspection_root_var.set(str(FIXTURE_INSPECTION_ROOT))
            cavs1, data1, src1 = controller.resolve_cav_for_item("302YJ03340")
            assert cavs1 == [1, 2]
            assert src1 == "csv"
            assert len(controller._cav_cache) == 1

            # Second call hits cache
            cavs2, data2, src2 = controller.resolve_cav_for_item("302YJ03340")
            assert cavs2 == [1, 2]
            assert data2 is data1
            assert src2 == "csv"

            controller.clear_cav_cache()
            assert len(controller._cav_cache) == 0

            # Verify apply_theme_tags runs without error
            data_tab.apply_theme_tags()
            bg = data_tab.preview_tree.tag_configure("duplicate", "background")
            assert str(bg).upper() in ("#FEE2E2", "#450A0A")
        finally:
            state.po_registry.close()
            state.part_master.close()
            data_tab.destroy()
            notebook.destroy()


class TestCSVRevisionVersionAndArchiveGuardrails:
    """Kiểm thử 5 chốt chặn an toàn (Fail-Closed Guardrails) cho Revision, Version và thư mục lưu trữ 'old'."""

    def test_guardrail1_mixed_naming_and_multiple_active_revs_warning(
        self, tmp_path: Path
    ) -> None:
        """Guardrail 1: Quét đồng nhất mọi mẫu đặt tên CSV (_rev_ver.csv và _rev.csv) và cảnh báo khi QC quên cất Rev cũ vào 'old'."""
        part_dir = tmp_path / "302YJ" / "302YJ03340"
        part_dir.mkdir(parents=True)
        bools_1_2 = ",".join(["True", "True"] + ["False"] * 14)
        bools_1_to_4 = ",".join(["True"] * 4 + ["False"] * 12)

        # File cũ đặt tên kiểu _01_02.csv, file mới QC tạo kiểu _02.csv (thiếu hậu tố _ver)
        (part_dir / "302YJ03340_01_02.csv").write_text(
            f"maxCavN:16\n302YJ03340\n01\n02\nBOTTLE WASTE\nHD-PE\n{bools_1_2}\nFalse\n2\n60\n",
            encoding="utf-8",
        )
        (part_dir / "302YJ03340_02.csv").write_text(
            f"maxCavN:16\n302YJ03340\n02\n01\nBOTTLE WASTE\nHD-PE\n{bools_1_to_4}\nFalse\n2\n60\n",
            encoding="utf-8",
        )

        data = load_cav_from_inspection_source("302YJ03340", root_dir=tmp_path)
        assert data.file_path.name == "302YJ03340_02.csv"
        assert data.rev == "02"
        assert data.valid_cavs == [1, 2, 3, 4]
        assert data.active_revisions == ("01", "02")
        assert len(data.warnings) >= 1
        assert any("nhiều Revision" in w and "old" in w for w in data.warnings)

    def test_guardrail2_filename_vs_internal_content_rev_mismatch(
        self, tmp_path: Path
    ) -> None:
        """Guardrail 2: Phát hiện lệch Revision/Version giữa tên file (_02_03.csv) và nội dung bên trong (ghi 01 / 01)."""
        csv_file = tmp_path / "302YJ03340_02_03.csv"
        bools_1_2 = ",".join(["True", "True"] + ["False"] * 14)
        csv_file.write_text(
            f"maxCavN:16\n302YJ03340\n01\n01\nBOTTLE WASTE\nHD-PE\n{bools_1_2}\nFalse\n2\n60\n",
            encoding="utf-8",
        )

        parsed = parse_inspection_csv(csv_file)
        assert parsed.rev == "02"
        assert parsed.version == "03"
        assert len(parsed.warnings) == 2
        assert any("ghi Rev 02" in w and "ghi Rev 01" in w for w in parsed.warnings)
        assert any("ghi Ver 03" in w and "ghi Ver 01" in w for w in parsed.warnings)

    def test_guardrail3_old_archive_subfolder_lookup_and_manual_rev_switch(
        self, tk_root, tmp_path: Path
    ) -> None:
        """Guardrail 3: Khi QC đã cất Rev 01 vào 'old/' và để Rev 02 ở ngoài, mặc định lấy Rev 02 nhưng khi chọn Rev 01 sẽ tìm trong 'old/'."""
        part_dir = tmp_path / "302YJ" / "302YJ03340"
        old_dir = part_dir / "old"
        old_dir.mkdir(parents=True)

        bools_1_2 = ",".join(["True", "True"] + ["False"] * 14)
        bools_3_4 = ",".join(["False", "False", "True", "True"] + ["False"] * 12)

        # Rev 01 nằm trong thư mục old/ (CAV 1, 2; SL/thùng 50)
        (old_dir / "302YJ03340_01_02.csv").write_text(
            f"maxCavN:16\n302YJ03340\n01\n02\nBOTTLE WASTE\nHD-PE\n{bools_1_2}\nFalse\n2\n50\n",
            encoding="utf-8",
        )
        # Rev 02 nằm ở thư mục gốc (CAV 3, 4; SL/thùng 60)
        (part_dir / "302YJ03340_02_01.csv").write_text(
            f"maxCavN:16\n302YJ03340\n02\n01\nBOTTLE WASTE\nHD-PE\n{bools_3_4}\nFalse\n2\n60\n",
            encoding="utf-8",
        )

        # 1. Tra cứu mặc định -> lấy Rev 02 ở thư mục gốc, không có cảnh báo trùng Rev
        active_data = load_cav_from_inspection_source("302YJ03340", root_dir=tmp_path)
        assert active_data.rev == "02"
        assert active_data.is_from_old_archive is False
        assert active_data.valid_cavs == [3, 4]
        assert active_data.warnings == ()

        # 2. Tra cứu chỉ định preferred_rev="01" -> lấy từ thư mục 'old/'
        old_data = load_cav_from_inspection_source("302YJ03340", preferred_rev="01", root_dir=tmp_path)
        assert old_data.rev == "01"
        assert old_data.version == "02"
        assert old_data.is_from_old_archive is True
        assert old_data.valid_cavs == [1, 2]
        assert old_data.pcs_per_box == 50

        # 3. Kiểm thử trên UI Controller: nhập mã -> nạp Rev 02; đổi ô Rev sang "01" -> tự động nạp CAV [1, 2] từ 'old/'
        state = AppState(tk_root)
        controller = AppController(state)
        notebook = ttk.Notebook(tk_root)
        data_tab = DataTabPanel(notebook, controller)
        view = _HarnessView(state, controller, data_tab)
        controller.set_view(view)
        try:
            state.inspection_root_var.set(str(tmp_path))
            state.item_code_var.set("302YJ03340")
            controller.on_item_code_input_changed()
            assert state.rev_var.get() == "02"
            assert state.valid_cavs == [3, 4]
            assert state.carton_qty_var.get() == "60"
            assert "302YJ03340_02_01.csv" in state.status_var.get()

            # Người vận hành sửa Rev về 01 để in hàng tồn kho cũ
            state.rev_var.set("01")
            controller.on_rev_input_changed()
            assert state.valid_cavs == [1, 2]
            assert state.cav_var.get() == "1, 2"
            assert state.carton_qty_var.get() == "50"
            assert "old" in state.status_var.get()
        finally:
            state.po_registry.close()
            state.part_master.close()
            data_tab.destroy()
            notebook.destroy()

    def test_guardrail4_and_5_excel_import_rev_mismatch_and_offline_cache_warning(
        self, tk_root, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Guardrail 4 & 5: Cảnh báo khi file Excel dùng Rev cũ so với Server QC và cảnh báo khi dùng dữ liệu lưu tạm Offline."""
        import openpyxl
        from core.slip_printer_engine import START_ROW

        part_dir = tmp_path / "302YJ" / "302YJ03340"
        old_dir = part_dir / "old"
        old_dir.mkdir(parents=True)
        bools_1_2 = ",".join(["True", "True"] + ["False"] * 14)
        bools_3_4 = ",".join(["False", "False", "True", "True"] + ["False"] * 12)

        (old_dir / "302YJ03340_01_01.csv").write_text(
            f"maxCavN:16\n302YJ03340\n01\n01\nBOTTLE WASTE\nHD-PE\n{bools_1_2}\nFalse\n2\n50\n",
            encoding="utf-8",
        )
        (part_dir / "302YJ03340_02_01.csv").write_text(
            f"maxCavN:16\n302YJ03340\n02\n01\nBOTTLE WASTE\nHD-PE\n{bools_3_4}\nFalse\n2\n60\n",
            encoding="utf-8",
        )

        # Tạo file Excel ghi Rev 01 (cũ) trong khi Server QC đang ở Rev 02
        excel_path = tmp_path / "stale_rev.xlsx"
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.cell(row=START_ROW, column=1, value="302YJ03340")
        ws.cell(row=START_ROW, column=2, value="BOTTLE WASTE")
        ws.cell(row=START_ROW, column=3, value="50")
        ws.cell(row=START_ROW, column=4, value="50")
        ws.cell(row=START_ROW, column=5, value="00998877")
        ws.cell(row=START_ROW, column=6, value="0001")
        ws.cell(row=START_ROW, column=7, value="00")
        ws.cell(row=START_ROW, column=8, value="001/001")
        ws.cell(row=START_ROW, column=9, value="01")
        ws.cell(row=START_ROW, column=10, value="")
        wb.save(excel_path)
        wb.close()

        warnings: list[str] = []
        monkeypatch.setattr(messagebox, "showwarning", lambda title, msg, **kw: warnings.append(msg))

        state = AppState(tk_root)
        controller = AppController(state)
        notebook = ttk.Notebook(tk_root)
        data_tab = DataTabPanel(notebook, controller)
        view = _HarnessView(state, controller, data_tab)
        controller.set_view(view)
        try:
            state.inspection_root_var.set(str(tmp_path))
            state.excel_var.set(str(excel_path))
            controller.import_from_excel()

            # 1. Phải phát cảnh báo lệch Revision giữa Excel (Rev 01) và Server QC (Rev 02)
            assert len(warnings) == 1
            assert "Excel ghi Rev 01" in warnings[0]
            assert "Server QC hiện tại là Rev 02" in warnings[0]
            assert "old/302YJ03340_01_01.csv" in warnings[0]

            # 2. Bản ghi Excel Rev 01 được điền đúng CAV [1, 2] của Rev 01 từ thư mục 'old/'
            assert len(state.records) == 1
            assert state.records[0].cav_no == "1, 2"

            # 3. part_master.db KHÔNG bị ghi đè thành Rev 01 cũ mà giữ đúng Rev 02 mới nhất của Server
            master_entry = state.part_master.get("302YJ03340")
            assert master_entry is not None
            assert master_entry.rev == "02"

            # 4. Khi mất kết nối tới Inspection_data (Offline), phải hiển thị cảnh báo dùng dữ liệu lưu tạm
            state.inspection_root_var.set(str(tmp_path / "offline_missing_root"))
            controller.clear_cav_cache()
            state.item_code_var.set("302YJ03340")
            controller.on_item_code_input_changed(force_reload=True)
            assert state.rev_var.get() == "02"
            assert "Mất kết nối Server CSV QC" in state.status_var.get()
        finally:
            state.po_registry.close()
            state.part_master.close()
            data_tab.destroy()
            notebook.destroy()


class TestDailyLogQuotaAndPrintQueueHygiene:
    """Kiểm thử ghi log theo ngày, tự động dọn dẹp theo ngưỡng dung lượng (500 MB) và làm sạch danh sách in sau khi xuất PDF."""

    def test_daily_log_files_and_quota_cleanup_with_date_range(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from datetime import datetime
        from core.error_logger import (
            DEFAULT_MAX_LOG_DIR_BYTES,
            ENV_ERROR_LOG_DIR,
            _RECENT_EVENTS,
            enforce_log_dir_quota,
            log_error_event,
        )

        assert DEFAULT_MAX_LOG_DIR_BYTES == 500 * 1024 * 1024
        _RECENT_EVENTS.clear()
        log_dir = tmp_path / "daily_logs"
        log_dir.mkdir(parents=True)
        monkeypatch.setenv(ENV_ERROR_LOG_DIR, str(log_dir))

        # 1. Tạo các file log của những ngày cũ vượt ngưỡng thử nghiệm (10 KB)
        (log_dir / "error_log_2026-10-01.jsonl").write_text("A" * 4500, encoding="utf-8")
        (log_dir / "error_log_readable_2026-10-01.log").write_text("B" * 4500, encoding="utf-8")
        (log_dir / "error_log_2026-10-05.jsonl").write_text("C" * 4500, encoding="utf-8")

        # 2. Ghi sự kiện hôm nay
        today_tag = datetime.now().strftime("%Y-%m-%d")
        log_error_event(
            "ADD_RECORD",
            "Test daily log creation",
            item_code="302RVJ1530",
            async_write=False,
        )
        assert (log_dir / f"error_log_{today_tag}.jsonl").is_file()
        assert (log_dir / f"error_log_readable_{today_tag}.log").is_file()
        assert (log_dir / "error_log_readable.log").is_file()

        # 3. Thực thi dọn dẹp theo ngưỡng 8000 bytes -> xóa các ngày cũ nhất (2026-10-01 đến 2026-10-05)
        summary = enforce_log_dir_quota(log_dir, max_bytes=8000)
        assert summary is not None
        assert summary["deleted_count"] >= 2
        assert summary["start_date"] == "2026-10-01"
        assert summary["end_date"] in ("2026-10-01", "2026-10-05")
        assert not (log_dir / "error_log_2026-10-01.jsonl").exists()

        readable_txt = (log_dir / "error_log_readable.log").read_text(encoding="utf-8")
        assert "LOG_QUOTA_CLEANUP" in readable_txt
        assert "từ ngày 2026-10-01 đến ngày" in readable_txt

    def test_clear_all_button_and_post_pdf_export_queue_cleanup(
        self, tk_root, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from core.error_logger import ENV_ERROR_LOG_DIR, _RECENT_EVENTS

        _RECENT_EVENTS.clear()
        log_dir = tmp_path / "op_logs"
        monkeypatch.setenv(ENV_ERROR_LOG_DIR, str(log_dir))
        monkeypatch.setattr(messagebox, "askyesno", lambda *a, **kw: True)

        state = AppState(tk_root)
        controller = AppController(state)
        notebook = ttk.Notebook(tk_root)
        data_tab = DataTabPanel(notebook, controller)
        view = _HarnessView(state, controller, data_tab)
        controller.set_view(view)
        try:
            # 1. Nút '🗑️ Xóa tất cả' phải tồn tại trên thanh tiêu đề bảng và gọi đúng clear_all_records
            clear_all_btn = data_tab.get_clear_all_button_widget()
            assert clear_all_btn is not None
            assert "Xóa tất cả" in clear_all_btn.cget("text")

            # 2. Thêm lô 1 (6 thùng) -> Xuất PDF -> Danh sách chờ in tự động được làm sạch
            state.inspection_root_var.set(str(FIXTURE_INSPECTION_ROOT))
            state.item_code_var.set("302YJ03340")
            controller.on_item_code_input_changed()
            state.box_var.set("6")
            controller.add_record()
            assert len(state.records) == 6
            batch1_po = state.records[0].po

            # Giả lập đăng ký vào po_registry như generate_pdf_from_records và gọi on_pdf_export_completed
            exported_batch1 = list(state.records)
            for r in exported_batch1:
                state.po_registry.register_combo(r.po, r.po_detail, r.po_sub, r.box)
            controller.on_pdf_export_completed(
                exported_records=exported_batch1,
                output_path=tmp_path / "batch1.pdf",
                record_count=len(exported_batch1),
                page_count=1,
                paper_size="A4",
            )
            assert len(state.records) == 0
            assert state.po_var.get() == ""

            # 3. Thêm lô 2 tiếp theo (cùng hoặc khác mã hàng) -> Tự sinh PO mới và không còn dòng cũ gây cảnh báo trùng
            state.item_code_var.set("302YJ03340")
            controller.on_item_code_input_changed()
            state.box_var.set("6")
            controller.add_record()
            assert len(state.records) == 6
            batch2_po = state.records[0].po
            assert batch2_po != batch1_po

            # 4. Bấm nút '🗑️ Xóa tất cả' -> bảng về 0 dòng và ghi nhận CLEAR_ALL_RECORDS vào log
            clear_all_btn.invoke()
            assert len(state.records) == 0
        finally:
            state.po_registry.close()
            state.part_master.close()
            data_tab.destroy()
            notebook.destroy()



