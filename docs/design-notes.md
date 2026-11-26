# LED heart board: design notes

Working notes kept while the board was designed: state, decisions, circuit, checks, bring-up and firmware notes. Paths are relative to the repository root; the short overview is the [README](../README.md).

State on 2026-11-15, afternoon: **schematic, board and JLC files are done and were checked four times. One fault was found (the on/off button) and fixed on the silkscreen. Board widened to 85 x 50 mm with four M3 mounting holes (Edy, 2026-11-15). Ordered by Edy with a black solder mask instead of green (he said so on 2026-11-16). Boards arrived; first board flashed with the test firmware on 2026-11-24 and every LED and button tested passed (bring-up step 4). Main firmware (`firmware/heart`: 10 modes, buttons, sleep, EEPROM settings) flashed the same day.**
- Mounting holes (Edy's request, 2026-11-15): M3 (3.2 mm, not plated) in all four corners, 2.75 mm in from both edges. They did not fit in the right-hand corners of the 80 x 50 mm board (the MODE button and JP1 sit there), so Edy chose to widen the board on the right to 85 x 50 mm. No part moved and nothing was re-routed: `led_board.py widen` redrew the outline and added the holes, then `ground` filled the new strip on both sides (7 new stitching vias; the 2 vias that would have sat under a screw head were removed). A 6 mm screw head clears every pad, part and via; the nearest track (COL1, under solder mask) is 0.12 mm outside the head of the top-left hole. DRC 0 / 0 / 0. Order files remade: BOM and placement file byte-identical to the 11:50 set; the Gerbers changed in copper, mask and outline; the drill file is now split into `led_heart-PTH.drl` (222 plated holes) and `led_heart-NPTH.drl` (the 4 mounting holes). The left and bottom edges did not move, so every part keeps its place relative to the board's corner: the placement preview checked below still applies. The fourth check's Gerber-to-circuit script, re-run on the new files: 280 pins, 0 differences, 54 of 54 nets, 0 shorts, 0 opens, 72 of 72 LEDs the right way round, ground one piece, mask and paste on every placed pad.
- JLCPCB's placement preview checked on 2026-11-15 from Edy's screenshot of the 11:50 files, by script: all 156 magenta marks found where expected. 72 of 72 LEDs with "+" (anode) at the top and "-" at the bottom; the base dot of Q1 to Q8 at pad 1 (0.8 mm, at the lead tip; the next pad 1.95 mm or more away); the pin-1 dots of U1 and U2 at pin 1 (0.7 mm); D1 "+" on the left and "-" on the right, its stripe on the right. Step 7 of "Next steps" is done; the boards can be ordered.
- Fourth check on 2026-11-15, in four parts (the circuit rebuilt from the order files alone; LTspice simulation; programming and firmware against the STM8 data sheet; a pre-mortem): no fault. Applied with Edy's go: the back labels moved (+ and - now under their own battery pads, J1's pin names above its holes; the + and - used to sit right under J1's GND and VDD holes), the order-settings text and this README corrected, the cost estimate now includes JLC's extra parts for loss (about EUR 15.1 to 15.3 for 2 boards, a little over the EUR 15 limit). DRC 0 / 0 / 0. Order files remade at 11:50: BOM and placement file byte-identical to before; of the Gerbers only the back silkscreen changed. See "Fourth check".
- Third check on 2026-11-15 (the final files after all changes; the routing itself): no fault, nothing changed on the board or in the order files after it. See "Third check".
- Second check on 2026-11-15 (data sheets; power-up, flashing, assembly): one fault. On/off was on SW1 = PA1, and PA1 cannot wake the chip from halt (ST data sheet, table 6, note 2). Fixed with Edy's go by printing the buttons, from the top, MODE, SPEED, DIM, BRIGHT, ON/OFF: on/off is now SW5 = PB5, which can wake it. No copper changed; the netlist is the same; ERC 0 / 0, netlist check 0 differences, DRC 0 / 0 / 0; order files remade at 00:24 (BOM and placement file byte-identical to before, only the top silkscreen Gerber differs).
- First check on 2026-11-14, on Edy's request: no fault in the circuit, the board or the order files; see "First check". Two silkscreen points from it were fixed with Edy's go (the voltage print on the back, the mark near the board edge), then DRC was run again (0 / 0 / 0) and the order files were remade on 2026-11-15 at 00:07.
- Schematic: `led_heart.kicad_sch` (one A1 sheet, also `led_heart.pdf`), written by `gen/led_sch.py`. ERC: 0 errors, 0 warnings. `gen/led_check.py` compares the exported netlist with the circuit below: 0 differences (115 symbols; 55 nets, not counting the 6 pins that are left unconnected on purpose).
- Board: `led_heart.kicad_pcb`, built by `gen/led_board.py`. DRC with schematic parity: 0 violations, 0 unconnected, 0 parity differences. Pictures in `preview/`: 3D renders in the colours of the order (black mask), made by `gen/led_render.py`.
- JLC files: `fabrication/` (Gerber zip, BOM with 9 lines, placement file with 111 parts) and `fabrication/READ_ME_FIRST.txt` with the order settings and the expected cart total. 111 parts and 272 solder joints per board.
- JLC's database on 2026-11-14, 23:30, and again on 2026-11-15: all 9 part numbers in stock, 8 Basic and the STM8 Preferred, all allowed in Economic assembly, none marked "Assembly Difficulty: High".
- Next, all Edy's: see "Next steps". Then the firmware, in a later session; it needs the two tables in `gen/pins.py`.

Design agreed with Edy on 2026-11-14. This file is the hand-off: read it first. The sections "Circuit" to "Second check" are the spec; "As built" says what the board looks like and where it differs from the spec.

## As built (2026-11-14; silkscreen changed and board widened on 2026-11-15)
Places, in mm from the top left corner:
- Board 85 x 50 mm (80 x 50 until 2026-11-15; the strip x 80 to 85 is empty, ground on both sides). Mounting holes H1 to H4, M3, 3.2 mm, not plated, at (2.75, 2.75), (82.25, 2.75), (2.75, 47.25), (82.25, 47.25); they are on the board only (not in the schematic, BOM or placement file).
- LEDs: centres at x = 6 + 5c, y = 7.5 + 5r (c = 0 to 8, r = 0 to 7), all upright: anode pad to the north, cathode pad to the south. LED n = 9 x row + column + 1.
- Row r: one 0.4 mm top track through the 9 cathode pads, on to the collector of Q(r+1) at x = 51. Base resistors R10 to R17 at x = 54.6.
- Column c: a via 1.9 mm north of each LED centre, one bottom track through the 8 vias, then along the north edge (bottom layer) to its 270 ohm resistor.
- U1 at (63.5, 10.5), turned so that pins 11 to 20 face north. R1 to R7 in a row north of it (y = 3.2), R8 and R9 south of it. C1 and C2 south of U1.
- U2 at (62.5, 29.9), outputs QB to QH (pins 1 to 7) to the west; QA (pin 15) is on the east side and its track runs under the chip. C3 beside its pin 16.
- SW1 to SW5 at x = 74.5, y = 6.5, 14.9, 23.3, 31.7, 40.1, the name printed above each: MODE, SPEED, DIM, BRIGHT, ON/OFF (changed on 2026-11-15, see the button table under "Circuit"). Pull-ups R18 (27.0) and R19 (35.2) at x = 69.
- J1 (programming pads) under U2 at y = 38, x = 58.8 to 66.4, from the left: VDD, SWIM, GND, RST (printed).
- Battery pads on the back: plus at (64, 44.5), minus at (58.5, 44.5), 4 x 6 mm. On the back: + and - under their own pads by the bottom edge, "4.5 V, max 5 V" beside the +, and J1's pin names (VDD, SWIM, GND, RST) above its holes. Until 2026-11-15 the + and - sat between J1 and the battery pads, right under J1's GND and VDD holes.
- D1 at (69.5, 46), cathode to the right; C4 above it; JP1 at (75, 46), printed "JP1". "Dedeghe" (1.2 mm) with a TM (1.0 mm, tops level) at the bottom right, under D1; the tail of the "g" is 0.33 mm from the board edge. Edy chose this over a larger mark under the matrix (2026-11-15).

Pin tables (`gen/pins.py`, the firmware needs them):
| Column | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|
| U1 pin | 20 | 19 | 17 | 16 | 15 | 14 | 13 | 10 | 1 |
| Port | PD3 | PD2 | PC7 | PC6 | PC5 | PC4 | PC3 | PA3 | PD4 |

Rows 1 to 8 are the 74HC595 outputs QA to QH in order. QA holds the bit that was shifted in last.

Differences from the spec and the sketch:
- The chip side was routed by Freerouting, not by rule: planning it by hand ran into too many crossings. The matrix, the column bundle, the row transistors, the SR1 track and the ground vias beside pads are laid by rule in `led_board.py` and locked.
- J1 is under U2, not along the top edge: the top edge holds the column resistors. U1 is above U2 (the sketch had them the other way round). The column resistors are at the top edge and beside U1, not near y = 30.
- Buttons: pad 1 is the signal, pads 3 and 4 are ground, pad 2 is left free (the spec said pad 1 and pad 4 only).
- Added to the silkscreen: "JP1"; on the back "4.5 V, max 5 V" (first printed as "max 5.5 V", the chip's own limit; changed after the check because of the supply-pin current, see below) and J1's pin names.
- Ground pour: 8 slivers between tracks could not be tied to ground and stay bare, 3.0 mm2 together, the largest 1.2 mm2 (left of U2). 213 vias in all, 120 of them ground.
- Board size: 85 x 50 mm, not 80 x 50, since 2026-11-15, to make room for the mounting holes in the right-hand corners.
- Rebuilding the board (`gen/build_board.sh`) runs Freerouting again and gives a different, equally valid routing of the chip side. The fab files belong to the board file as it is now: after a rebuild run `led_fab.py` again. (`place` now draws the 85 mm outline and the holes itself; `widen` was the one-time step that changed the routed board.)

## What it is
- 85 x 50 mm (80 x 50 until the mounting holes were added on 2026-11-15), 2 layers, all parts on top, made and assembled by JLCPCB (Economic assembly, top side). M3 mounting holes in the corners.
- Left: a 9 x 8 grid of 72 red LEDs, 5 mm apart. It shows a heart, animations and scrolling 5 x 7 text.
- Right: STM8S003 microcontroller, 74HC595, 8 row transistors, 5 push buttons.
- Back: two solder pads for the battery wires.
- Limit set by Edy: under EUR 15 at JLC for 5 boards with 2 assembled.

## Decisions (Edy, 2026-11-14)
| Topic | Decision | Why |
|---|---|---|
| Microcontroller | STM8S003F3P6TR, not a PIC | every PIC at JLC is Extended: + EUR 5.3 on 2 boards |
| Programmer | ST-Link V2 mini clone (AliExpress about 1 to 3 dollars, Amazon.nl e.g. AZDelivery about EUR 5 to 10); not a "V2-1" (may lack SWIM) and not an STLINK-V3MINI/MINIE (STM32 only); software: ST Visual Programmer or stm8flash; skip firmware updates of the clone | the STM8 is flashed over its SWIM interface |
| Main switch | on/off push button, chip sleeps | JLC has no fee-free slide switch (+ EUR 2.9) |
| LED layout | full 9 x 8 rectangle, 72 LEDs | text can scroll; the heart is drawn as a pattern |
| LED type | red 0603, C2286 | cheapest; 145 to 300 mcd at 20 mA per its data sheet |
| Battery | 3 x AAA or 3 x AA (4.5 V) | chip runs from 2.95 to 5.5 V, no regulator; 5 V USB also works if the supply gives no more than 5.0 V; one Li-ion cell only with its own protection (the board stops near 3.3 V); 4 cells, 9 V or 12 V destroy it |

## First check (2026-11-14) and what the firmware must know
Two independent checks, each working from the produced files and not from the generator scripts.
- Circuit and parts: the exported netlist against the spec, connection for connection (0 differences); pin numbers and polarities against JLCPCB's own library parts read that evening (U1, U2, S8050, LED, SS14, switch: all agree; the LED's pad 1 is the anode there); `gen/jlc_pads.json` equal to JLCPCB's data; counts 111 parts, 272 joints.
- Board and order files: all 280 pads on the right net, every net one piece of copper, JP1 bridged in copper, all 72 LEDs with the anode to the north, no via in or on a pad; smallest track 0.25 mm, gap 0.20 mm, via hole 0.3 mm with 0.15 mm ring; Gerbers identical to a fresh export (80 x 50 mm, 217 holes, 272 paste openings); BOM 9 lines; all 111 placement rows land on their pads with the right rotation.
- Not covered: the data-sheet PDFs were not read again (the figures of this README were used), and JLCPCB's live placement preview.

Findings, and what was done:
- Supply current: with a full row lit, U1's VDD pin carries about 61 to 70 mA at 4.5 V on the battery pads, about 79 mA at 5 V and about 93 to 103 mA at 5.5 V (absolute maximum 100 mA; ST gives its output figures with 80 mA in total). The back print was changed from "max 5.5 V" to "max 5 V". (The fourth check simulated it: 59 to 73 mA at 4.5 V, up to 86 mA on fresh cells, 73 to 93 mA at 5.0 V, up to 101 mA at 5.25 V in the strongest corner. So USB only from a supply of no more than 5.0 V; batteries are the normal supply.)
- The mark: the tail of the "g" was 0.08 mm from the board edge. Now 0.33 mm, with a 1.2 mm name.
- Reset pin: NRST has only its internal pull-up, no capacitor. Left as it is. If a board ever resets by itself, or (fourth check) does not start when the cells go in, solder a 100 nF capacitor across the RST and GND pads of J1 on the back (an 0603 or 0805 across the two pads, which leaves the holes free for the programming header).

For the firmware:
- The 595's two clocks are tied together: the outputs show what the shift register held one clock earlier. Give one clock more than the bits sent.
- Power-up: the 595 outputs come up at random, so some row transistors may be on, but U1's pins are inputs and no LED current flows. Clear the 595 first, then make the column pins outputs.
- SW3 is on PD1, the SWIM pin: set the SWD bit in CFG_GCR to read it as a normal input. After that the ST-Link needs "connect under reset" through the RST pad. Do not hold SW3 while flashing.
- Turn on the internal pull-ups of PA1, PA2 and PD1 (CR1). PB4 and PB5 have R18 and R19; a press draws about 4.5 mA while held.
- Lowest battery voltage: about 3.25 V with LEDs on (1.08 V per cell), about 3.05 V in sleep. (Fourth check, simulated: with a full row lit, VDD falls to 2.95 V at 1.08 to 1.11 V per cell, and the chip resets at about 1.0 to 1.05 V per cell, then restarts with the LEDs off and dips again. 1.10 V per cell is the safer end point: change the cells when the display flickers or restarts.)
- At 5 V a full row is close to ST's 80 mA figure. A lower duty cycle dims the LEDs but does not lower this peak current.

Second check (2026-11-15):
- Data sheets, read in LCSC's viewer: the STM8 pin table and every figure of the two data-sheet sections below agree with ST's sheet (DocID018576 Rev 9); the 74HC595 and S8050 pin tables and limits, the LED's polarity drawing (terminal 1 = anode, green mark at the cathode), the diode's cathode band, the switch's inner connections and its pad pattern (sheet: pad centres at 3.0 and 1.875 mm; footprint: 3.0 and 1.85 mm) agree. Not read: the package drawings of the two chips and the capacitor's sheet.
- The fault found there: PA1 cannot wake the chip from halt; see the button table under "Circuit" for the fix.
- Power-up, flashing, assembly: no fault. The remade Gerbers are byte-identical to a fresh export; BOM and placement file cover the same 111 parts; every statement of `fabrication/READ_ME_FIRST.txt` is true on the board.
- One reviewer wrote from memory that PA1 can wake the chip. The data sheet says it cannot; the data sheet was followed.

For Edy's hand work:
- Flashing: take the batteries out and power the board from the ST-Link's 3.3 V pin through the VDD pad of J1. With batteries in, 4.3 to 4.7 V (fresh cells) would be pushed into the programmer's 3.3 V pin, and its 3.3 V SWIM level is marginal for a chip running at 4.5 V (the chip wants 0.7 x VDD, tables 38 and 42). Never use the clone's 5 V pin. (The clone's circuit comes from a reviewer's general knowledge, not from a document.)
- A blank chip: until firmware runs, the 595 outputs are random and up to about 30 mA of base current flows; no LED lights.
- Battery pads: plus and minus are 1.5 mm apart and bare, and D1 does not protect against a short between them. Solder the wires pointing apart, then cover the back with tape or glue. There is no hole to tie the wires down.
- J1 takes a standard 2.54 mm header (1.0 mm holes); pins only held in by hand sit loose.

More for the firmware:
- Changing the row: columns low, shift, wait a few microseconds for the row transistors to switch off (they are driven hard through 1 k and have no base pull-down), then set the columns. The wait is a reviewer's estimate; the S8050 sheet gives no storage time. Without it the old row may glow faintly. (Fourth check, simulated: even with no wait the glow is at most 0.15 % of a lit dot; 2 us is enough, 5 us if dimming uses on-times shorter than 1/16 of the row time.)
- ST asks that pins carrying high current together be spread around the package (table 6, note 1). Seven of the nine column pins are neighbours (pins 13 to 20). The total stays inside the limits; it is a reason not to raise the LED current.
- The S8050 from C2146 is the 200 to 350 gain rank (JLC's part name says so); the sheet's whole range is 120 to 400. The design needs a gain of about 20.

Third check (2026-11-15), on the files as they are after all changes:
- Final files: the netlist has the same parts, pins and connections as before the button change; all 280 pads on the right net; DRC with parity 0 / 0 / 0; the Gerbers and the drill file in the zip equal a fresh export line for line (217 holes, 272 paste openings); BOM and placement file: 111 parts, positions and rotations right; the five buttons agree end to end (position, net, U1 pin, printed label, `gen/pins.py`, this README, the schematic note); `gen/pins.py` agrees with the netlist. No fault.
- Routing (the autorouted chip side, from the copper data): no fault. Smallest gaps: track to track 0.202 mm, track to via 0.202 mm, via to via 0.278 mm, track to pad 0.2 mm or more (0.238 mm between the VDD track and the round SWIM pad of J1); JLCPCB's limit is 0.127 mm. Supply: VBAT 0.5 mm, VIN and VDD 0.4 mm wide, VDD without a via; drop at 80 mA about 4 mV to U2 and 6 mV to U1. Decoupling: C1, C2 and C3 are about 2 mm of track from their pins, each with a ground via 1.2 mm away. Longest detours: SW2 1.5 times the shortest connection, SER 1.28 (2 vias), SWIM 1.10 (40 mm, 2 vias). Eleven signal vias in all.
- Neatness: the reviewer would leave the routing as it is. Its list of places a person may find untidy: VDD threading between the pads of R8 and making a zig-zag to U2 pin 10; SER's jogs on the bottom layer; SR1's four right-angle corners (laid by rule); a few pad entries 0.1 to 0.25 mm off centre; three segments shorter than 0.1 mm. None affects function.
- Left as it is, Edy's decision of 2026-11-15: each button label is 0.7 mm above its own button and 1.1 mm below the button above it. Moving the labels 0.4 mm down would tie each more clearly to its button (silkscreen only); not done.

Fourth check (2026-11-15, four parts in one run), each from an angle the earlier checks had not used:
- Order files to circuit, without KiCad: the circuit rebuilt from the Gerbers, the drill file and the placement file with JLCPCB's own footprints is the netlist: 54 of 54 nets, 280 pins, 0 shorts, 0 opens, no copper without a pad; 72 of 72 LEDs with the anode on their column and the cathode on their row; JP1 joined in copper; mask and paste openings on every placed pad. What it cannot rule out is a mix-up of JLCPCB's rotation rule (clockwise instead of counter-clockwise would turn every LED round): that is why the placement preview stays step 7.
- LTspice: every current inside the part limits on batteries: U1's VDD pin up to 86 mA on fresh cells, an LED or a column pin at most 9.5 mA, the transistors saturated (forced gain 9 to 23), a 595 output at most 4.2 mA. An off LED sees at most 1.9 V in reverse while a row is lit. Halt current 6 uA. Brightness about 7 to 15 mcd per dot on fresh cells: clearly visible indoors, weak in direct sun. The heart pattern draws about 53 mA from fresh cells.
- Programming and firmware, against ST's data sheet: the chip can be flashed over J1 as wired; a new chip's option bytes are open; every pin can do its job; PB5 wakes the chip from halt (table 11); the planned firmware needs about 11 % of the CPU and about 5 KB of the 8 KB flash.
- Pre-mortem: all 9 parts in stock and fee-free; no single dead part or likely wiring mistake damages the board, apart from the trap below, now fixed.

Found, and what was done:
- Back labels: the + and - sat right under J1's GND and VDD holes. Battery wires soldered into J1 by them would put a reversed supply straight on VDD, past D1. Fixed on the silkscreen, see "As built".
- Cost: the estimate left out JLC's extra parts for loss; corrected under "Cost estimate". About EUR 0.15 to 0.30 over the EUR 15 limit for 2 boards; no part swap gets it reliably under (an MMBT3904 in place of the S8050 saves $0.08).
- Power-up: putting the cells in raises VDD faster than ST allows (table 20, page 50: at least 2 us per volt; simulated 0.5 to 1.4 us per volt), and NRST has no capacitor. ST does not say what happens; the chip will most likely start anyway. Left as it is: test it on the first board (step 8 of "Next steps"); if it ever fails to start, fit 100 nF across J1's RST and GND pads on the back.
- The program flash is guaranteed for only 100 write cycles (table 37, page 65; the data EEPROM for 100 000). Develop the firmware on a separate cheap STM8S103F3 board, or on one of the boards, and flash the gift board only with the finished firmware.
- Run time: the heart draws about 45 to 53 mA, so about 20 hours on AAA cells and about 50 on AA (estimate). An auto-off in the firmware is worth having.
- A wrong supply kills the chips: 4 cells (6 V) or a 9 V battery. D1 only protects against swapped wires. Use a 3-cell holder.
- To have ready for bring-up: the ST-Link V2, a 3 x AAA holder with wires, a 4-pin 2.54 mm header for J1 (optional), a 100 nF capacitor for the reset fallback.

More for the firmware (fourth check):
- PD1 is the only programming pin and SW3 shorts it to ground: never make PD1 an output. Order: pull-up on (PD_CR1 bit 1), then CFG_GCR.SWD = 1. Debug builds keep SWD = 0 (DIM then does not work).
- PD5 and PD6 start as slow outputs: set PD_CR2 bits 5 and 6, or hold each clock level for 2 cycles. Change SER and raise SCK in separate writes. One clock per row change; SER = 1 only on the clock that brings up row 8; 9 clocks with SER = 0 blank all rows.
- Keep the columns low whenever no row is on (while clearing the 595, or in a blank slot): otherwise the off LEDs see up to VDD in reverse (4.0 to 4.5 V, under their 5 V limit but without margin).
- Before halt: clear the 595; columns, PD5 and PD6 low; the port B interrupt on PB5 only (PB_CR2 bit 5 = 1, bit 4 = 0, because PB4 shares port B), falling edge (EXTI_CR1 PBIS = 10, set while interrupts are masked); CR2 = 0 on PA2 and PD1; wait until SW5 is released plus about 50 ms; keep FLASH_CR1.HALT = 0 so that the flash powers down; no independent watchdog (it cannot be stopped once started). After waking, ask for a press of about 0.5 s before turning on. Expected halt current 6 to 10 uA.
- EEPROM: a write stops the CPU for 6.0 to 6.6 ms, so turn the columns off first. Save mode, speed, brightness and a check byte as one 4-byte word, only after a change (for example 3 s after the last press), and check it when loading.
- Timing: CLK_CKDIVR = 0 for 16 MHz; TIM4 with prescaler 64 and ARR 249 gives a 1 ms row tick, 125 frames per second; a TIM2 compare can end the on-time for the brightness steps (leave TIM2's outputs off so that PD4, PD3 and PA3 stay normal pins).
- Optional low-battery check: light row 1 and read column 1's pin (PD3 = AIN4) as an input with its pull-up: the LED's voltage is a reference within 3 % over VDD 2.8 to 4.6 V (simulated); calibrate once at the ST-Link's 3.3 V.
- Several register names above come from the reviewers' knowledge of ST's reference manual RM0016, which could not be read without a download: check them there when writing the firmware.

## Circuit
Power
- BAT+ pad (back) -> D1 (SS14) -> JP1 -> VDD. BAT- pad (back) -> GND.
- JP1 is a two-pad jumper bridged by a thin trace. To add a hard switch later: cut the trace and wire the switch across the pads.
- C1 1 uF at U1 VDD, C2 1 uF on U1 VCAP, C3 1 uF at U2 VCC, C4 1 uF at D1.

LED matrix
- LED at column c (1 to 9), row r (1 to 8): anode to net COLc, cathode to net ROWr.
- COLc: U1 pin -> 270 ohm (R1 to R9) -> COLc. About 6.5 mA peak per LED at 4.5 V, about 0.8 mA average (one of 8 rows is on at a time).
- ROWr: collector of Qr (S8050). Emitter to GND. Base <- 1 k (R10 to R17) <- U2 output r.
- U2 74HC595: SER <- U1 PD5; SRCLK and RCLK tied together <- U1 PD6; OE to GND; SRCLR to VDD; QH' not connected.

Buttons (the other side of each button goes to GND)
| Button | Function | U1 pin | Pull-up |
|---|---|---|---|
| SW1 (top) | mode | PA1 | internal |
| SW2 | speed | PA2 | internal |
| SW3 | dimmer | PD1 (shared with SWIM) | internal |
| SW4 | brighter | PB4 | R18 1 k to VDD (open-drain pin) |
| SW5 (bottom) | on/off (wakes the chip) | PB5 | R19 1 k to VDD (open-drain pin) |

The wiring is as first agreed; the functions were moved on 2026-11-15. On/off was first on SW1, but ST's data sheet (table 6, note 2) says: "When the MCU is in halt/active-halt mode, PA1 is automatically configured in input weak pull-up and cannot be used for waking up the device." PA2, PD1, PB4 and PB5 have an external interrupt and can wake it; Edy chose the bottom button. The same table is in `gen/pins.py` (BUTTONS).

Programming pads J1 (1 x 4, 2.54 mm, not fitted): VDD, SWIM (PD1), GND, NRST.

U1 pin plan (TSSOP-20; pin numbers confirmed on 2026-11-14 from JLC's library part)
| Pin | Name | Use | Pin | Name | Use |
|---|---|---|---|---|---|
| 1 | PD4 | column | 11 | PB5 | SW5 |
| 2 | PD5 | 595 SER | 12 | PB4 | SW4 |
| 3 | PD6 | 595 clock | 13 | PC3 | column |
| 4 | NRST | J1 | 14 | PC4 | column |
| 5 | PA1 | SW1 | 15 | PC5 | column |
| 6 | PA2 | SW2 | 16 | PC6 | column |
| 7 | VSS | GND | 17 | PC7 | column |
| 8 | VCAP | C2 | 18 | PD1 | SWIM, SW3 |
| 9 | VDD | VDD | 19 | PD2 | column |
| 10 | PA3 | column | 20 | PD3 | column |

Which column goes to which pin is free: pick it for the easiest routing. All 16 I/O pins are used.

## Parts
See `parts.csv`: 9 kinds, 111 parts and 272 solder joints per board, none with a JLC fee.

## Cost estimate
JLC prices read on 2026-11-14 and again on 2026-11-15, cart price before shipping and VAT, $1.068 per euro.
| Item | 2 assembled (USD) | 5 assembled (USD) |
|---|---|---|
| 5 boards ($2 offer in JLC's desktop app, up to 100 x 100 mm, so also at 85 x 50; $4 on the website) | 2.00 | 2.00 |
| Assembly setup + stencil | 9.71 | 9.71 |
| Parts, with JLC's extra parts for loss | 3.59 to 3.73 | 8.00 |
| Soldering ($0.0016 per joint) | 0.87 | 2.18 |
| Total | 16.17 to 16.31 = EUR 15.1 to 15.3 | 21.89 = EUR 20.5 |

Corrected on 2026-11-15 (fourth check): the first estimate ($15.69 = EUR 14.7 and $21.26 = EUR 19.9) left out the extra parts JLC bills on every line for loss in placement (lossNumber in its parts data: 10 LEDs, 5 transistors, 10 of each resistor and capacitor, 8 switches, 10 diodes, none for the two chips). The range for 2 boards depends on whether JLC adds them on top of a line's minimum quantity. So the 2-board order is about EUR 0.15 to 0.30 over Edy's EUR 15 limit; no part swap gets it reliably under (an MMBT3904 in place of the S8050 saves $0.08). Not counted: "Confirm parts placement" ($0.45), a possible fee for "Remove Mark", lead-free HASL. The real total is the one in JLC's cart.

## Layout plan: the first sketch, replaced by "As built" (mm, origin top left, x to the right, y down)
- LED (c, r), counted from 0: x = 6 + 5c, y = 7.5 + 5r.
- Row nets run left to right on the top layer; column nets run top to bottom on the bottom layer, one via per LED.
- Q1 to Q8 at x = 51, each at the y of its row; base resistors at x = 54.
- U2 near (59, 12), U1 near (59, 24), column resistors in a line near y = 30.
- SW1 to SW5 down the right edge at x = 74.5, y = 6.5, 14.9, 23.3, 31.7, 40.1.
- J1 along the top near (60, 3). Battery pads on the back near (58.5, 44.5) and (64, 44.5), 4 x 6 mm, marked + and -. D1 near (69, 45).
- Silkscreen: button names, + and -, "Dedeghe" with a small raised TM at the bottom right.

This is the sketch from the chat preview, not a checked placement.

## Firmware plan
- C, built with SDCC, flashed over SWIM with the ST-Link.
- A timer tick scans the 8 rows at 100 frames per second or more; brightness in steps.
- Modes on the mode button: beating heart, chase, fill, sparkle, steady, scrolling text. Room for more (8 KB flash, 1 KB RAM).
- Heart pattern, top row first: `.##...##.` `####.####` `#########` `#########` `.#######.` `..#####..` `...###...` `....#....`
- Text uses the usual 5 x 7 font. The message is fixed in the firmware at first; an editor with the buttons, saved in the 128 bytes of EEPROM, is a possible extra.
- Last mode, speed and brightness are saved in EEPROM.
- Off: clear the 595 (the clocks are tied, so 9 clocks with the data line low), columns low, PD5 and PD6 low, chip in halt; SW5 (PB5, port B interrupt, falling edge) wakes it. A row left on in halt would draw about 3.8 mA and empty the cells in about 10 days.
- Before writing it, read the firmware notes under the four checks above ("For the firmware", "More for the firmware").

## Data-sheet check (2026-11-14)
Read from the LCSC copies of the data sheets (text only, no drawings) and from the EasyEDA library parts that JLC places.

STM8S003F3P6 (ST data sheet, 104 pages)
| Item | Value | Where |
|---|---|---|
| Supply | 2.95 to 5.5 V | table 19 |
| Total current out of the pins, through VDD | 100 mA absolute maximum | table 17 |
| Total current into the pins, through VSS | 80 mA absolute maximum | table 17 |
| One pin | 20 mA absolute maximum, in or out | table 17 |
| High-sink pin, output high | at least 4.0 V at 10 mA with 8 pins loaded (5 V supply); at least 2.1 V at 10 mA with 4 pins (3.3 V supply) | table 41 |
| High-sink pin, output low | at most 0.8 V at 10 mA with 8 pins loaded (5 V supply) | table 41 |
| Internal pull-up | 30 / 55 / 80 k (min / typ / max) | table 38 |
| Input levels | low below 0.3 x VDD, high above 0.7 x VDD | table 38 |
| VCAP capacitor | 470 nF to 3.3 uF, ESR up to 0.3 ohm at 1 MHz | table 19 |
| Halt current at 3.3 V | 4.5 uA typical, 17 uA maximum at 85 C (flash powered down) | page 56 |
| Pins | as in the pin plan above; PB4 and PB5 are true open drain, PA1 and PA2 are standard pins, all other I/O are high-sink | EasyEDA part |

What follows for the design
- The 9 column pins together must stay well under 100 mA. ST's own output figures are given with 80 mA in total. By my estimate with typical voltage drops, 270 ohm gives about 70 mA in the worst case (a full row on, fresh batteries or 5 V USB) and 220 ohm close to 90 mA. So the column resistors are 270 ohm. (Simulated in the fourth check: up to 86 mA on fresh cells and 73 to 93 mA at 5.0 V; see the first check.)
- The 1 uF capacitor on VCAP is inside the allowed range.
- The sleep estimate given to Edy (about 6 uA in total) fits: the chip is 4.5 uA typical at 3.3 V.

Red LED KT-0603R, C2286 (Hubei Kento, 11 pages)
- Brightness 145 to 300 mcd at 20 mA. The 300 in JLC's listing is the top of the range.
- Forward voltage 1.8 to 2.4 V at 20 mA. Continuous current up to 25 mA, pulses up to 60 mA (1/10 duty, 0.1 ms).
- Reverse voltage up to 5 V. By my estimate an LED that is off sees about 2.5 V in reverse at most in this matrix. (Simulated in the fourth check: at most 1.9 V while a row is lit, but up to VDD if the columns are on while no row is on, so the firmware keeps them low then.)
- In JLC's footprint pad 1 is the anode and pad 2 the cathode. KiCad's LED footprint numbers them the other way round (pad 1 = cathode), so the placement angle must be checked in JLC's preview.

S8050, C2146 (Changjing, marking J3Y)
- SOT-23: pin 1 base, pin 2 emitter, pin 3 collector.
- 25 V, 500 mA, gain 200 to 350 at 50 mA. Saturation at most 0.6 V at 500 mA; off-state leakage at most 0.1 uA.
- With a 1 k base resistor the base gets about 3 mA, enough for the 70 mA of a full row.

74HC595D, C5947 (Nexperia)
- Pins: 14 DS (data), 11 SHCP (shift clock), 12 STCP (latch clock), 13 OE (low = outputs on), 10 MR (low = clear), 15 Q0, 1 to 7 Q1 to Q7, 9 Q7S, 8 GND, 16 VCC.
- Outputs: at least 3.84 V at 6 mA with a 4.5 V supply; limit 35 mA per output, 70 mA in total.
- Inputs: high above 3.15 V at a 4.5 V supply, which the STM8 outputs reach.

Tact switch TS-1187A, C318884
- Pads (mm from the centre): 1 (-3, -1.85), 2 (3, -1.85), 3 (-3, 1.85), 4 (3, 1.85).
- Inside, pads 1 + 2 are joined and pads 3 + 4 are joined (see the second check). Wire each button between pad 1 and pad 4.

SS14, C2480: pad 1 cathode, pad 2 anode.

## Second check (2026-11-14, same day)
- STM8 halt current at 5 V: 6.0 uA typical, 20 uA maximum at 85 C, flash powered down (table 27).
- 74HC595 quiescent current: at most 80 uA from -40 to 85 C at 6 V. This revision of the data sheet gives no typical or 25 C figure.
- Sleep current of the whole board: a few uA expected at room temperature (chip 6 uA plus the 595). The guaranteed worst case at 85 C is 20 + 80 = 100 uA, which would empty 3 AAA cells in about 15 months. Measure it on the first board.
- LED polarity, from the drawing: terminal 1 is the anode (+), terminal 2 the cathode. A green mark on the top face sits at the cathode end. This agrees with JLC's footprint (pad 1 = anode).
- Tact switch, from the drawing: A and B are joined, C and D are joined, and the button connects the two pairs. In JLC's footprint that is pads 1 + 2 against pads 3 + 4. Rated 50 mA at 12 V.
- 270 ohm resistor: C22966 (0603WAF2700T5E), Basic, $0.0017, minimum 20.

Nothing in the data sheets is left open.

## Tools to reuse (they exist and work)
In `C:\Users\grigo\OneDrive\Desktop\QFH.Claudiu\pcb_v2\gen` (the receiver board's generator scripts; copy what is needed into `LED Heart\gen`, do not change the originals):
- `kisch.py`: small KiCad 10 schematic writer. `Project`, `Sheet.auto(ref, lib_id, value, conns, footprint, props)`; every pin gets a stub with a net label, so connections are made by name; power symbols GND, VCC, +5V, +3V3; `pwr_flag`; `intended_nets()` for checking.
- `rx2_sch.py`: how the project file is written and the kicad-cli calls (ERC, netlist, PDF). `rx2_check.py`: compares the exported netlist with the intent.
- `rx2_board.py`: builds the board with pcbnew from the netlist (`read_netlist`, `setup_rules`, `load_fp`, `dress`, DRC with schematic parity). `rx2_route.py`: tracks, vias, pours, pocket fix. `rx2_fab.py` with `jlc_pads.json`: Gerbers, parts list, placement file with JLC's angles.
- KiCad 10: `C:\Users\grigo\AppData\Local\Programs\KiCad\10.0` (`bin\python.exe` with pcbnew, `bin\kicad-cli.exe`). No other Python on this PC.

## Scripts of this project (`gen/`, run with KiCad's Python, KiCad closed)
- `led_sch.py`: schematic, ERC, netlist, PDF. `led_check.py`: netlist against the circuit. `pins.py`: the two pin tables.
- `led_board.py <step>`: place, hand, auto, merge, clean, ground, silk, drc. `build_board.sh` runs them in order (Freerouting opens its window for 2 to 4 minutes).
- `led_fab.py`: Gerber zip, BOM, placement file; `jlc_pads.json`: the pads of JLCPCB's footprints for the 9 part numbers.
- `led_render.py`: the 3D pictures in `preview/` (top, bottom, angle, close-up), rendered from a temporary copy of the board with a black stackup, KiCad's TL3342 model as a look-alike for the buttons and no header on J1; the board file is not changed.
- `kisch.py`, `frhelp.py`: copies from the receiver project, unchanged.

## Next steps
1. Data-sheet check: done. 2. Schematic: done. 3. Board: done. 4. JLC files: done (2026-11-14; made again on 2026-11-15 at 00:24 and at 11:50 after silkscreen changes).
5. Edy: open `led_heart.kicad_pcb` in KiCad and look it over.
6. Edy: order in JLCPCB's desktop app (5 boards for $2 there) with the three files in `fabrication/`; the settings are in `fabrication/READ_ME_FIRST.txt`: Economic assembly, top side, HASL with lead, green, 1.6 mm, 5 boards, 2 or 5 assembled, "Confirm Parts Placement" off. Expect about EUR 15.1 to 15.3 for 2 assembled. Done: Edy ordered (said on 2026-11-16), with a black solder mask instead of green.
7. Done on 2026-11-15 (all right, see the state at the top). After uploading the 85 mm Gerber zip, JLCPCB draws the preview again: the placement file is unchanged, so it should look the same, with the board 5 mm wider and four holes. Edy, before paying: in JLCPCB's placement preview every LED must show its "+" at the top (towards the board's top edge). JLCPCB numbers the LED's pads the other way round than KiCad; the placement file allows for it, and this preview is the one check at JLCPCB itself. Also look at the 8 transistors, U1, U2 and D1 (the list is in READ_ME_FIRST.txt). A screenshot of the preview can be checked by script.
8. Edy, when the boards arrive (bring-up, from the fourth check; the currents come from its simulations):
   1. Look with a loupe: each LED's green mark at its south (bottom) end, D1's stripe on the right.
   2. No cells yet: resistance between J1's VDD and GND above 1 kohm (below 10 ohm is a short).
   3. Cells in, meter in series: 1 to 30 mA and no LED lit (blank chip, random 595 outputs); VDD at J1 4.3 to 4.7 V; VCAP (C2) about 1.8 V. Swapped wires: 0 V, no harm.
   4. Done on the first board on 2026-11-24 (no cells; ST-Link clone, stm8flash, `firmware/test`): option bytes at factory values, all 72 LEDs, all-on, heart and the buttons MODE, SPEED, BRIGHT, ON/OFF passed. DIM (PD1) not tested yet. Steps 2, 3 and 5 to 8 still open.
      Cells out, ST-Link on J1: 3.3V to VDD, SWIM, GND, RST (as printed on both sides). Read the option bytes (factory values), then flash a test that lights one LED at a time: a dark dot = that LED or its joint, a dark row = its transistor, base resistor or the 595, a dark column = its 270 ohm resistor or U1's pin, two lit = a solder bridge.
   5. Cells in again with the real firmware: whole matrix about 74 to 81 mA, heart about 48 to 53 mA, no glow in the neighbouring row; each button reads about VDD released and 0 V pressed.
   6. Off: 6 to 10 uA (switch the meter to mA before pressing ON again). 3.5 to 3.8 mA = a row left on; 4.3 to 4.6 mA = a button held or PB4 / PB5 driven low; about 60 uA = the flash is not powered down in halt.
   7. Put the cells in 20 times: it must start every time. If it ever does not, solder 100 nF across J1's RST and GND pads on the back.
   8. Glue the battery wires and the holder to the back (bare pads, no strain relief).
9. Firmware: done (2026-11-24 to 26). `firmware/test` (bring-up test) and `firmware/heart` (beating heart, speed, brightness, sleep, auto-off); the display, button and sleep code has run on the board.
