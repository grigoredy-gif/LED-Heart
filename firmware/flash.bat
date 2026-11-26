@echo off
rem Flashes a hex file into the board over the ST-Link (WinUSB driver from Zadig).
rem Usage: flash.bat [file.hex]
rem   default: personal\led_heart.hex if that folder exists, else heart\led_heart.hex
rem   the bring-up test is test\led_test.hex
cd /d "%~dp0"
set "HEX=%~1"
if "%HEX%"=="" if exist personal\led_heart.hex set "HEX=personal\led_heart.hex"
if "%HEX%"=="" set "HEX=heart\led_heart.hex"
echo Flashing %HEX%
tools\stm8flash.exe -c stlinkv2 -p stm8s003f3 -w "%HEX%"
