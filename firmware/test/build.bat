@echo off
rem Builds main.c into led_test.hex with SDCC (https://sdcc.sourceforge.net).
rem Needs SDCC 4.x installed; the installer can add it to PATH.
cd /d "%~dp0"
set "PATH=%ProgramFiles%\SDCC\bin;%PATH%"
if not exist build mkdir build
sdcc -mstm8 --std-c99 --opt-code-size -o build\ main.c || exit /b 1
copy /y build\main.ihx led_test.hex >nul
echo Built led_test.hex
