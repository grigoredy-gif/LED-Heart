# Beating heart firmware

A beating heart, with the buttons working:

| Button | Does |
|---|---|
| MODE | free: the place to add your own animations (see `run()` in `main.c`) |
| SPEED | slow, normal, fast, faster (then slow again) |
| DIM / BRIGHT | 6 brightness steps |
| ON/OFF | off (the chip sleeps, about 10 uA); hold it for half a second to switch on |

It switches itself off 30 minutes after the last button press. Speed and
brightness are remembered, also with the cells out (saved 3 s after a change,
and when it switches off).

`main.c` also has everything a new animation needs: a frame buffer `fb[8]` (one
9-bit word per row, bit 0 = left column), `pause(ms)` that keeps the buttons
working and returns 1 when the animation must stop, and the row scan in the timer
interrupt (125 frames per second, brightness by on-time).

Build: double-click `build.bat` (SDCC 4.x). Flash: `..\flash.bat`.

DIM shares its pin with the programming pin SWIM, so the firmware turns SWIM off.
Flashing still works because the ST-Link resets the chip through RST before it
connects. If a first try ends with "SWIM error", run it again.
