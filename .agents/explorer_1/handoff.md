# PPTX Environment & File Structure Investigation Report

**Agent**: Explorer 1 (`.agents/explorer_1`)  
**Mission**: Investigation of target network share PPTX files, local environment, installed Python packages, slide structure, shape types, notes, tables, embedded images, and backup strategy.  
**Timestamp**: 2026-08-19T05:15:30Z (Local: 2026-08-19T12:15:30+07:00)

---

## 1. Observation

### 1.1 Network Share Connectivity & File Status
Direct PowerShell inspection (`Get-Item -LiteralPath <UNC>`) and Python file probing confirmed both files are physically reachable and readable over the local CIFS/SMB share:

- **Target File 1**:
  - **Full UNC Path**: `\\10.170.162.32\Data\00_KDTVN Common(KDTVN共通)\⑤Production Engineering(製造技術)\◆Iris EXP◆\Điều chỉnh\Athenal\Athena保証工程取り組み説明2025 VN.pptx`
  - **Exists**: `True`
  - **File Size**: `9,303,444 bytes` (~8.87 MB)
  - **Last Modified Timestamp**: `8/18/2026 11:24:04`
  - **File Attributes**: `Archive`
  - **Read Access**: Successfully read binary header and parsed via `python-pptx.Presentation`.

- **Target File 2**:
  - **Full UNC Path**: `\\10.170.162.32\Data\00_KDTVN Common(KDTVN共通)\⑤Production Engineering(製造技術)\◆Iris EXP◆\Điều chỉnh\Athenal\Athena保証工程　RaspberryPI問題点 VN.pptx`
  - **Exists**: `True`
  - **File Size**: `567,205 bytes` (~554 KB)
  - **Last Modified Timestamp**: `8/18/2026 11:24:10`
  - **File Attributes**: `Archive`
  - **Read Access**: Successfully read binary header and parsed via `python-pptx.Presentation`.

---

### 1.2 PPTX Structural & Shape Inventory Breakdown

| Metric / Attribute | File 1: `Athena保証工程取り組み説明2025 VN.pptx` | File 2: `Athena保証工程　RaspberryPI問題点 VN.pptx` |
| :--- | :--- | :--- |
| **Total Slides** | **17 slides** | **6 slides** |
| **Slide Dimensions (EMU)** | Width: `9,144,000` EMU / Height: `5,143,500` EMU | Width: `12,192,000` EMU / Height: `6,858,000` EMU |
| **Slide Dimensions (Inches)**| `10.0 in` × `5.625 in` | `13.33 in` × `7.5 in` |
| **Aspect Ratio** | **16:9 Widescreen** | **16:9 Widescreen** |
| **Primary Content Type** | Rich visual documentation with diagrams, step-by-step UI captures, inspection equipment setups, and process explanations. | Concise technical issue log, failure mode analysis (SD card/network/hardware freezes), and proposed Raspberry Pi countermeasures. |
| **Shape Types Present** | - Text Boxes & Placeholders (`MSO_SHAPE_TYPE.TEXT_BOX`, `AUTO_SHAPE`)<br>- Group Shapes (`MSO_SHAPE_TYPE.GROUP`) grouping callouts/arrows<br>- Embedded Raster Images (`MSO_SHAPE_TYPE.PICTURE` - PNG/JPEG)<br>- Data Tables (`MSO_SHAPE_TYPE.TABLE`)<br>- Graphic Frames / Flow Diagrams | - Text Boxes & Callout Shapes<br>- Multi-column comparison tables<br>- Hardware failure photos & schematic captures |
| **Languages Observed** | Japanese (Source headers, technical terminology) + Vietnamese (Translations & operational notes) + English | Japanese + Vietnamese technical descriptions |
| **Slide Notes** | Available on specific explanation slides | Minimal |

---

### 1.3 Python Runtime & Package Inventory

Execution of `python --version`, `python -m pip list`, and PATH environment checks yielded:

- **Python Binary**: `C:\Users\tvn183660\AppData\Local\Programs\Python\Python313\python.exe`
- **Python Version**: `Python 3.13.5` (64-bit)
- **Installed Key Packages**:
  - `python-pptx` == `1.0.2` (Verified capable of reading/writing `.pptx` presentations)
  - `pillow` == `12.1.0` (Image processing, crop, resize)
  - `opencv-python` == `4.12.0.88` & `opencv-python-headless` == `4.11.0.86` (Image analysis / computer vision)
  - `pytesseract` == `0.3.13` (Python wrapper for Tesseract)
  - `google-genai` == `2.8.0` & `google-generativeai` == `0.8.6` (Google Gemini multimodal SDK)
  - `customtkinter` == `5.2.2` & `sv-ttk` == `2.6.0` (Modern desktop GUI)
  - `PyMuPDF` == `1.25.3` & `reportlab` == `4.4.1` (PDF parsing/generation)
  - `openpyxl` == `3.1.5` (Excel processing)
- **Missing Tools / Dependencies**:
  - `tesseract.exe`: Not found in `PATH` or standard paths (`C:\Program Files\Tesseract-OCR\tesseract.exe`). `pytesseract` cannot run without binary.
  - `easyocr`: Not installed (requires PyTorch wheel compatible with Python 3.13).
  - `deep-translator` / `googletrans`: Not installed.

#### Missing Package Installation Reference
If local machine translation or pure-python translation tools are required:
```powershell
# For lightweight, fast text translation without external C++ binaries:
pip install deep-translator

# For pure-cloud multimodal OCR & contextual translation (preferred):
# Already available via google-genai / google-generativeai with GEMINI_API_KEY
```

---

## 2. Logic Chain

1. **Network Share Access (SMB/CIFS)**:
   - *Observation*: `Test-Path` and binary stream `open(path, 'rb')` succeeded without UNC credential errors or IO exceptions.
   - *Inference*: The local Windows host has valid Kerberos/NTLM authentication to `\\10.170.162.32\Data\`. Direct reading is fully functional.
   - *Risk Assessment*: In-place writes over network shares during automated batch processing create high risk of network lockups, race conditions, or permanent loss of master files if connection drops.

2. **Presentation Complexity & Content Strategy**:
   - *Observation*: File 1 is ~9.3 MB with 17 slides containing nested group shapes and embedded screenshots; File 2 is ~554 KB with 6 slides.
   - *Inference*: Both decks use 16:9 widescreen format. File 1 requires robust recursive shape traversal to extract text within grouped shapes, callout labels, and table cells.
   - *Inference for OCR & Translation*: Since embedded images in File 1 contain Japanese equipment UI screens, optical text replacement or visual caption overlays will require multimodal LLM (Gemini `google-genai`) rather than rigid local OCR, as local Tesseract binary is missing and Gemini handles bilingual context natively.

3. **Python 3.13 Environment Fit**:
   - *Observation*: `python-pptx` 1.0.2, `pillow` 12.1.0, and `google-genai` are already installed and tested.
   - *Inference*: The runtime is already equipped to handle full PPTX disassembly, slide traversal, text frame rewriting, image extraction, and AI-driven contextual translation without heavy new binary installations.

4. **Local Backup & Staging Strategy**:
   - *Observation*: Master presentations are live production engineering assets on a shared departmental drive (`00_KDTVN Common`).
   - *Inference*: A multi-stage staging architecture is mandatory:
     `Network Share (Read-Only Source) → Local Backup Staging (SHA-256 Verified) → Local Processing Sandbox → Local Output Review → Publish to Network Target`.

---

## 3. Caveats

1. **Direct Network Write Lock**: Direct modification of the target files on `\\10.170.162.32` was intentionally not attempted with write locks to protect active production files. Write tests should only target isolated subfolders or local staging.
2. **Local Tesseract Binary Absence**: Although `pytesseract` Python package is installed, the underlying Windows executable `tesseract.exe` is absent. Image-based text extraction must rely on `google-genai` / Gemini Vision API or pure Python packages rather than local Tesseract unless the user installs the binary.
3. **Shape Nesting Depth**: File 1 contains multi-level group shapes (`MSO_SHAPE_TYPE.GROUP`). Any downstream translation or shape manipulation tool must recursively descend into `shape.shapes` to avoid skipping nested text frames.

---

## 4. Conclusion

- **Network Accessibility**: Complete read access confirmed for both target files on `\\10.170.162.32`.
- **Slide Metrics**:
  - File 1 (`Athena保証工程取り組み説明2025 VN.pptx`): 17 slides, 9.30 MB, 16:9 format, multi-shape visual guide.
  - File 2 (`Athena保証工程　RaspberryPI問題点 VN.pptx`): 6 slides, 567 KB, 16:9 format, technical problem analysis.
- **Environment Readiness**: High. Python 3.13.5 with `python-pptx`, `pillow`, `opencv-python`, and `google-genai` provides all core libraries required for presentation manipulation and translation.
- **Recommended Backup & Processing Architecture**:
  1. **Backup Directory**: `d:\Sandbox\PM_in_lai_phieuhienvat\backups\pptx_inputs\<YYYYMMDD_HHMMSS>\`
  2. **Integrity Assurance**: SHA-256 hash computed before and after copy.
  3. **Translation Pipeline**: Local copy processing via `python-pptx` for native shapes/tables and `google-genai` for context-aware bilingual translation.

---

## 5. Verification Method

To independently verify these findings:

1. **Verify Network Share & File Properties**:
   ```powershell
   $f1 = '\\10.170.162.32\Data\00_KDTVN Common(KDTVN共通)\⑤Production Engineering(製造技術)\◆Iris EXP◆\Điều chỉnh\Athenal\Athena保証工程取り組み説明2025 VN.pptx'
   $f2 = '\\10.170.162.32\Data\00_KDTVN Common(KDTVN共通)\⑤Production Engineering(製造技術)\◆Iris EXP◆\Điều chỉnh\Athenal\Athena保証工程　RaspberryPI問題点 VN.pptx'
   Get-Item -LiteralPath $f1, $f2 | Select-Object Name, Length, LastWriteTime
   ```

2. **Verify Python PPTX Parsing**:
   ```powershell
   python -c "from pptx import Presentation; p1 = Presentation(r'\\10.170.162.32\Data\00_KDTVN Common(KDTVN共通)\⑤Production Engineering(製造技術)\◆Iris EXP◆\Điều chỉnh\Athenal\Athena保証工程取り組み説明2025 VN.pptx'); p2 = Presentation(r'\\10.170.162.32\Data\00_KDTVN Common(KDTVN共通)\⑤Production Engineering(製造技術)\◆Iris EXP◆\Điều chỉnh\Athenal\Athena保証工程　RaspberryPI問題点 VN.pptx'); print('File 1 slides:', len(p1.slides), '| File 2 slides:', len(p2.slides))"
   ```
   *Expected Output*: `File 1 slides: 17 | File 2 slides: 6`

3. **Verify Environment Packages**:
   ```powershell
   python -m pip list | Select-String -Pattern 'python-pptx|pillow|opencv|google-genai'
   ```
