# Bring-up test firmware

Over and over: the 72 LEDs one at a time (0.2 s each, row by row from the top
left), then all LEDs for 2 s, then the heart for 3 s. While MODE, SPEED, BRIGHT
or ON/OFF is held, column 1, 2, 4 or 5 lights instead. DIM is not tested: its pin
is also the programming pin, and this test leaves programming working.

What a fault looks like:

| You see | Look at |
|---|---|
| one dot dark | that LED (the right way round?) or its joints |
| a whole row dark | its S8050, its 1 k base resistor, or the 74HC595 |
| a whole column dark | its 270 ohm resistor or the STM8 pin |
| two dots lit at once | a solder bridge |
| nothing at all | power, the STM8, or the flashing |

## Build

1. Install SDCC 4.x (https://sdcc.sourceforge.net, the Windows x64 installer; let it add itself to PATH).
2. Double-click `build.bat`. It writes `led_test.hex`.

## Flash

Used on the first board (2026-11-24): stm8flash with the WinUSB driver (installed
with Zadig on "STM32 STLink"). Double-click `firmware\flash.bat`, or run
`tools\stm8flash.exe -c stlinkv2 -p stm8s003f3 -w test\led_test.hex` in `firmware`.
A read or verify (`-r`, `-v`) leaves the chip paused: run `-R` afterwards, or
unplug the ST-Link's USB.

The other way, with ST's own driver and tool, is below.

No batteries needed: the ST-Link powers the board.

1. Solder a 4-pin 2.54 mm header into J1.
2. Wire the ST-Link to J1 by the names printed on both: 3.3V to VDD, SWIM to SWIM,
   GND to GND, RST to RST. Never the 5 V pin. No batteries in the board.
3. Install ST Visual Programmer (STVP-STM8, free from st.com; it also installs the
   ST-Link driver). Plug in the ST-Link.
4. In STVP: Configure → ST-LINK, port USB, protocol SWIM, device STM8S003F3.
5. File → Open → `led_test.hex`, then Program → Current tab (on the PROGRAM MEMORY tab).
6. The test starts at once, still powered by the ST-Link.

If STVP asks to update the ST-Link's firmware, say no.
