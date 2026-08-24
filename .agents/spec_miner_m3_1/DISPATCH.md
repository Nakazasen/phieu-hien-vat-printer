## 2026-08-19T11:17:50Z
You are spec_miner_m3_1. Your working directory is d:\Sandbox\PM_in_lai_phieuhienvat\.agents\spec_miner_m3_1.
Create your working directory and progress.md immediately.
Read:
- d:\Sandbox\PM_in_lai_phieuhienvat\ORIGINAL_REQUEST.md
- d:\Sandbox\PM_in_lai_phieuhienvat\PROJECT.md
- d:\Sandbox\PM_in_lai_phieuhienvat\ui\main_window.py
- d:\Sandbox\PM_in_lai_phieuhienvat\ui\components\tutorial_overlay.py
- d:\Sandbox\PM_in_lai_phieuhienvat\ui\components\tutorial_script.py

Mission:
Extract precise behavioral and UX requirements for the First-Launch Tutorial Prompt from ORIGINAL_REQUEST.md §R3 and modern desktop UX standards.
Design the first-launch trigger flow:
1. When the application starts for the first time (`has_seen_tutorial == False` and `auto_suggest_tutorial == True`): how and when should the user be prompted (e.g., using a clean CustomTkinter modal dialog or banner scheduled via `after(600, ...)` after UI renders)?
2. Dialog options: "Bắt đầu hướng dẫn (Khuyên dùng)" vs "Để sau / Không nhắc lại".
3. How to ensure headless/test safety so tests don't get stuck on blocking dialogs.
4. How the prompt interacts with `start_tutorial()` and updating `has_seen_tutorial`.
Write a detailed specification report in `d:\Sandbox\PM_in_lai_phieuhienvat\.agents\spec_miner_m3_1\analysis.md` and handoff in `handoff.md`.
Send a message when done.
