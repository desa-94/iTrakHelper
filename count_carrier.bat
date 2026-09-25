@echo off
REM Startet iTrakHelper und zaehlt die Pieces pro Carrier fuer heute.
REM Wechselt in den Ordner dieser .bat, nutzt das venv und ruft main.py -cc auf.

cd /d "%~dp0"

call venv\Scripts\activate.bat

py main.py -cc

echo.
pause
