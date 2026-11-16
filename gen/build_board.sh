#!/bin/sh
# Rebuilds the board from the netlist. Run from gen/ in Git Bash, KiCad closed. Freerouting's window opens for 2 to 4 minutes.
set -e
PY="/c/Users/grigo/AppData/Local/Programs/KiCad/10.0/bin/python.exe"
"$PY" led_board.py place | tail -1
"$PY" led_board.py hand | tail -1
"$PY" led_board.py drc all | grep -v "\[GND\]" | head -6
cp ../led_heart.kicad_pcb ../led_heart_hand.kicad_pcb
"$PY" led_board.py auto 1.5 | grep -v "^20" | tail -3
"$PY" led_board.py merge | tail -2
for i in 1 2 3 4; do
  "$PY" led_board.py drc > /dev/null
  "$PY" led_board.py clean | tail -1
done
"$PY" led_board.py drc all | grep -v "\[GND\].*\[GND\]\|via_dangling  " | cut -c1-240 | head -20
cp ../led_heart.kicad_pcb ../led_heart_routed.kicad_pcb
"$PY" led_board.py ground | tail -20
"$PY" led_board.py silk | tail -2
"$PY" led_board.py drc all | cut -c1-250 | head -40
