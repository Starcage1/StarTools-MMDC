@echo off
echo Building StarTools: MMDC...
pyinstaller --noconfirm --windowed --onefile ^
 --name "StarTools-MMDC" ^
 --icon=startools_mmdc.ico ^
 mmdc.py

echo Build complete!
pause
