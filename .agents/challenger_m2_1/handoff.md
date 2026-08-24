# Milestone 2 Verification & Challenge Report: Tutorial Script & Business Workflows

**Author:** `challenger_m2_1` (teamwork_preview_challenger)  
**Task:** Milestone 2 Empirical Verification — Tutorial Script, Terminology, Widget Accessors, and Test Coverage  
**Date:** 2026-08-19  
**Verdict:** **APPROVE**

---

## 1. Observation

Direct structural, textual, and behavioral inspection of the codebase yields the following factual observations:

### A. Tutorial Script Structure & Count (`ui/components/tutorial_script.py`)
1. `build_tutorial_steps(app: Optional[Any] = None) -> list[TutorialStep]` constructs and returns a list containing exactly **4 steps**:
   - Step 1: `step_id="step_excel_import"`, `target_tab_index=0`, `tooltip_position="right"`, `padding=8`
   - Step 2: `step_id="step_qr_scanner"`, `target_tab_index=0`, `tooltip_position="right"`, `padding=8`
   - Step 3: `step_id="step_auto_po"`, `target_tab_index=0`, `tooltip_position="right"`, `padding=8`
   - Step 4: `step_id="step_pdf_generation"`, `target_tab_index=0`, `tooltip_position="right"`, `padding=8`
2. Re-export verified: `ui/components/tutorial_overlay.py:861-875` re-exports `build_tutorial_steps` and includes it in `__all__`.

### B. Vietnamese Business Terminology & Content Verification
1. **Step 1 — Excel Data Import (`ORIGINAL_REQUEST.md §R2.1`)**:
   - `title`: `"1. Nạp dữ liệu từ Excel"`
   - `description`: Contains required Vietnamese terminology:
     - `Excel (.xlsx)`, `Import từ Excel`
     - Mandatory columns: `Mã hàng`, `Tên hàng`, `SL thùng`, `Số box`, `Rev (01–99)`
     - Blank lot rule: `Cột Ngày/Lot: Nếu để trống sẽ tự động điền 10 dấu cách trong mã QR.`
     - Duplicate detection: `Dữ liệu trùng lặp (trùng mã hàng, PO, box) sẽ được tự động phát hiện và tô nền đỏ cảnh báo.`
2. **Step 2 — Smart QR Scanner 3 Modes (`ORIGINAL_REQUEST.md §R2.2`)**:
   - `title`: `"2. Quét mã QR thông minh"`
   - `description`: Contains required 3-mode terminology and definitions:
     - Button trigger: `⚡ Quét QR`
     - Mode 1: `Phân tách (分割): Chia nhỏ thùng lớn, giữ nguyên PO gốc và tự động tăng PO chi tiết (00010, 00020,...).`
     - Mode 2: `Hoàn kho (戻入): Nhập hàng hoàn trả, tự động sinh PO chi tiết đuôi 900+ (00900, 00910,...).`
     - Mode 3: `Bóc tách / Nhập tem: Giải mã chuỗi QR 129 ký tự để nạp thẳng vào danh sách hoặc form chính.`
3. **Step 3 — Auto PO Generation & Manual Record Addition (`ORIGINAL_REQUEST.md §R2.3`)**:
   - `title`: `"3. Tạo mã Auto PO & Thêm phiếu"`
   - `description`: Contains required Auto PO format and registry terms:
     - Location: `Tab Dữ liệu`
     - PO format: `Mã Auto PO: Tự động cấp phát mã PO chuẩn định dạng '11YYMMDDNN' (11 + Năm/Tháng/Ngày + STT 01–99 trong ngày).`
     - Uniqueness: `Không lo trùng lặp: Cơ sở dữ liệu PO Registry đảm bảo mỗi tem có số PO duy nhất.`
     - Actions: `➕ Thêm mới` (thêm tem vào bảng in) and `📋 Điền mẫu` (thử nghiệm).
4. **Step 4 — PDF Generation & Printing (`ORIGINAL_REQUEST.md §R2.4`)**:
   - `title`: `"4. Tạo & In phiếu hiện vật PDF"`
   - `description`: Contains required preview and layout terms:
     - Preview: `Xem trước trực quan: Kiểm tra hình ảnh tem và chuỗi QR 129 ký tự tại khung xem trước bên phải.`
     - Imposition: `Tiết kiệm giấy in: Hệ thống tự động ghép chuẩn xác 4 phiếu / trang A4 theo đúng layout cấu hình.`
     - Export & Print: `Xuất & In: Bấm 'Tạo PDF' để xuất file, sau đó bấm 'Mở PDF vừa tạo' để in trực tiếp.`

### C. Defensive Target Widget Resolution & Resilience
1. `_resolve_app(app)` resolves whether `app` is a `SlipPrinterApp` view instance or an `AppController` wrapping `view`.
2. Each step's `target_widget_getter` (`_get_excel_target`, `_get_qr_target`, `_get_form_target`, `_get_pdf_target`) wraps property lookups inside `try ... except Exception: return None`.
3. If `app` is `None` (headless testing), uninitialized, or raises an unexpected exception during widget access, the getter safely returns `None`, allowing `InteractiveTutorialOverlay` to center the modal card gracefully without unhandled crashes.

### D. Panel Widget Accessors & Properties
1. **`ui/components/sidebar.py`**:
   - Retains persistent references to: `excel_frame`, `excel_entry`, `excel_import_button`, `qr_scan_button`, `generate_button`, `open_pdf_button`.
   - Exposes accessors: `get_excel_import_widget()`, `get_excel_path_widget()`, `get_excel_frame_widget()`, `get_qr_scan_widget()`, `get_generate_pdf_widget()`, `get_open_pdf_widget()`.
   - Exposes aliases: `excel_import_btn`, `btn_import_excel`, `qr_scan_btn`, `btn_qr_scan`, `btn_generate_pdf`, `open_pdf_btn`, `btn_open_pdf`.
2. **`ui/components/data_tab.py`**:
   - Retains persistent references to: `btn_qr_scan`, `btn_add_record`, `btn_update_record`, `btn_delete_record`, `btn_refresh_preview`, `form_frame`, `preview_frame`, `preview_tree`, `preview_image_label`, `qr_payload_box`.
   - Exposes accessors: `get_form_frame()`, `get_auto_po_widget()`, `get_po_detail_widget()`, `get_po_sub_widget()`, `get_add_button_widget()`, `get_update_button_widget()`, `get_delete_button_widget()`, `get_qr_button_widget()`, `get_treeview_widget()`, `get_table_frame()`, `get_preview_frame()`, `get_preview_image_label()`, `get_qr_payload_box()`, `get_refresh_preview_button()`.
   - Exposes aliases: `qr_scan_btn`, `add_btn`, `update_btn`, `delete_btn`.

### E. Test Coverage Verification
1. **`tests/test_tutorial_script.py`**:
   - `TestTutorialScriptStructure`: Verifies 4 steps, step IDs, Vietnamese content (Excel, QR 3 modes, Auto PO 11YYMMDDNN, PDF 4 slips/A4), tooltip positions, and padding.
   - `TestWidgetGettersWithNoneAndMocks`: Verifies getters return `None` when headless, work with mock accessors, fallback to attribute names, handle `AppController` wrapper, and catch exceptions gracefully.
   - `TestSidebarAndDataTabAccessors`: Verifies live widget accessors and aliases on `SidebarPanel` and `DataTabPanel`.
   - `TestReExportAndControllerIntegration`: Verifies `build_tutorial_steps` re-export, controller hooks, `SlipPrinterApp.get_tutorial_steps()`, and real widget object matching.
2. **`tests/test_tutorial_overlay_e2e.py`**:
   - `test_t1_f6_01_script_contains_four_core_steps`: Verifies >= 4 steps registered.
   - `test_t1_f6_02_step1_excel_import_content`: Verifies Excel import assertions.
   - `test_t1_f6_03_step2_qr_scanner_modes_content`: Verifies QR scanner 3 modes assertions.
   - `test_t1_f6_04_step3_auto_po_increment_content`: Verifies Auto PO increment assertions.
   - `test_t1_f6_05_step4_pdf_generation_content`: Verifies PDF generation assertions.
   - `test_t2_f6_01` to `test_t2_f6_05`: Boundary tests for `None` targets, exceptions, destroyed widgets, tab mismatch, non-widget returns.
   - `test_t3_01` to `test_t3_08`: Cross-feature combinations (tab switching, theme mode switch, uncommitted form data, sequential tutorial sessions).

---

## 2. Logic Chain

1. **Requirement Traceability**:
   - `ORIGINAL_REQUEST.md §R2` explicitly details 4 business walkthrough requirements.
   - The implementation in `ui/components/tutorial_script.py` provides exact 1:1 mapping with accurate domain knowledge of the Slip Printer software (129-char QR format, 4 slips/A4 layout, `11YYMMDDNN` PO format, Phân tách/Hoàn kho/Bóc tách modes, blank lot 10 spaces padding).
2. **Robustness & Defensive Design**:
   - The script does not assume UI widgets will always be mapped or present. The combination of multi-tiered attribute lookups (`get_*_widget` -> attribute names -> frame/parent) with `try-except` blocks guarantees that the tutorial engine never crashes if a UI element is absent or throws an exception.
3. **Tab Index Synchronization**:
   - Every step explicitly defines `target_tab_index=0`. When `InteractiveTutorialOverlay` transitions to a step, it switches the notebook tab to Tab 0 (`Tab Dữ liệu`), updates idletasks, and calculates accurate bounding boxes for the target widgets.
4. **Separation of Concerns**:
   - Panel components (`SidebarPanel`, `DataTabPanel`) maintain control over their internal widgets while exposing clean public accessors.
   - The tutorial script is isolated in its own module (`ui/components/tutorial_script.py`), cleanly decoupling presentation from application logic.

---

## 3. Caveats

- **Milestone 3 Features**: The permanent `💡 Hướng dẫn` header button and first-launch preference prompt (`has_seen_tutorial` in `user_settings.json`) belong to Milestone 3 as specified in `PROJECT.md` and are not required for Milestone 2 approval.
- **No Production Defects**: No blocking bugs or regressions were discovered in the Milestone 2 codebase.

---

## 4. Conclusion

All Milestone 2 requirements are completely and rigorously met:
1. `build_tutorial_steps()` returns exactly 4 well-structured steps.
2. All 4 steps contain comprehensive, accurate Vietnamese terminology matching the application's actual business rules.
3. Target widget getters are resilient and handle all edge cases (`None`, destroyed widgets, mock controllers, thrown exceptions).
4. Panel widget accessors and aliases are cleanly exposed and verified against live Tk components.
5. Unit tests (`tests/test_tutorial_script.py`) and E2E Feature 6 tests (`tests/test_tutorial_overlay_e2e.py`) provide comprehensive coverage across normal and boundary conditions.

**Final Explicit Verdict:** **APPROVE**

---

## 5. Verification Method

To independently verify all findings and test suites:

```powershell
# 1. Run tutorial script unit and integration tests
pytest tests/test_tutorial_script.py -v

# 2. Run E2E Feature 6 and boundary/combination tests
pytest tests/test_tutorial_overlay_e2e.py -k "test_t1_f6 or test_t2_f6 or test_t3" -v

# 3. Run full tutorial overlay test suite
pytest tests/test_tutorial_overlay.py -v
```
