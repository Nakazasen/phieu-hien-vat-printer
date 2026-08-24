## 2026-08-19T05:07:50Z
Mission:
Analyze the pipeline for detecting, erasing Japanese text inside embedded images in PPTX, and overlaying Vietnamese translated text.

Investigate:
1. Identifying and extracting image shapes from PPTX slides (including pictures inside group shapes).
2. OCR engine selection and configuration for Japanese text detection and bounding box extraction (e.g. EasyOCR with `ja`, `en`, or Tesseract with `jpn` or RapidOCR/PaddleOCR). Check what is installed/available on Windows.
3. Image inpainting / text removal: how to erase/blur/inpaint Japanese text areas on the image (e.g., using OpenCV inpainting `cv2.inpaint` with TELEA/Navier-Stokes or solid/gradient background fill matching local pixel background) and replace the image blob in the slide.
4. Text box overlay on slide vs direct text rendering on image: evaluate coordinate transformation from image pixel space (DPI, aspect ratio, image crop) to PowerPoint slide EMUs / points, font sizing, and background transparency for overlay text boxes.
5. Fallback mechanisms if OCR fails or finds low-confidence text.

Record all findings, architecture diagrams, and recommended implementation patterns in `.agents/explorer_3/handoff.md`.
When finished, send a completion message with summary to your parent via `send_message`.
