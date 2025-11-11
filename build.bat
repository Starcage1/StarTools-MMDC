@echo off
echo Building StarTools: MMDC...
pyinstaller --noconfirm --windowed --onefile ^
 --name "StarTools-MMDC" ^
 --icon=icon.ico ^
 mc_dupes_gui_full.py

echo Build complete!
pause
