Files for JLCPCB, LED heart board. Made by gen/led_fab.py from the board file.

Upload:
- led_heart_gerbers_jlc.zip   as the Gerber file
- led_heart_jlc_bom.csv       as the BOM
- led_heart_jlc_cpl.csv       as the placement (CPL) file

Order in JLCPCB's desktop app: there 5 boards cost $2 (on the website $4).

Board settings:
- Base Material FR-4, Layers 2, PCB Qty 5, Single PCB, PCB Thickness 1.6 mm, PCB Color Green.
  The size (85 x 50 mm) comes from the Gerber file. The four corner holes (M3, 3.2 mm) are not plated:
  they are in their own drill file, led_heart-NPTH.drl; the plated holes are in led_heart-PTH.drl.
- Surface Finish: HASL with lead (the lead-free kind may cost extra). NOT OSP, which the page lists first:
  with OSP the order becomes Standard assembly and costs several times more.
- Outer Copper Weight 1 oz, Via Covering Tented, Min via hole size 0.3 mm.
- Mark on PCB: Remove Mark if the page adds no fee for it; otherwise leave the default.
- Leave every other option as the page sets it.

PCB Assembly:
- PCBA Type Economic, Assembly Side Top Side, PCBA Qty 2 (or 5).
- Confirm Parts Placement: No (it costs $0.45). Check the preview yourself instead, see below.
- After the upload JLCPCB must find all 9 BOM lines (111 parts per board), all Basic or Preferred:
  no "Extended" fee on any line.

Expected cart total, before shipping and VAT (JLCPCB prices of 2026-11-15, $1.068 per euro):
- 2 assembled: about $16.2 to $16.3 = EUR 15.1 to 15.3; 5 assembled: about $21.9 = EUR 20.5.
- JLCPCB bills a few extra parts per line for loss in placement (attrition): parts about $3.6 for 2 boards.
- If the cart shows much more, look at the surface finish (OSP) and the PCBA type (Standard) first.

Before paying, in JLCPCB's placement preview:
- The LEDs. Every LED stands upright. Its "+" (anode) must be at the top, towards the board's top edge, and
  its "-" (cathode) at the bottom, on the horizontal track of its row. If the 72 LEDs show "+" at the
  bottom, do not order: the LEDs' angle in the placement file is then 180 degrees off.
- The 8 transistors (SOT-23): three legs on three pads, the single leg towards the LEDs.
- U1 and U2: the dot of pin 1 at the pad marked by the small triangle on the board.
- D1: its "-" (cathode, the stripe) on the right, towards the jumper JP1.
The angles in the placement file are already turned to JLCPCB's footprints (180 degrees for C2146; 270 degrees for C5947, C52717)
and checked by script against JLCPCB's footprint data.

Not in the BOM and the placement file, on purpose: J1 (4 programming pads), JP1 (jumper made of copper),
the two battery pads on the back.
