"""
led_check.py - compares the netlist exported by KiCad (../led_heart.net) with the circuit of ../README.md.

The expected circuit is written out here a second time, from the README and not from led_sch.py, so that a
slip in the schematic script shows up. Only the two free pin tables are shared (pins.py).
Also checked: value, footprint and LCSC number of every part, and the part counts of ../parts.csv.
Run: <KiCad 10>/bin/python.exe led_check.py
"""
import csv
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from netlist import read_netlist, short  # noqa: E402
from pins import COLPIN, ROWOUT  # noqa: E402

OUT = os.path.dirname(HERE)
NET = os.path.join(OUT, "led_heart.net")
PARTS = os.path.join(OUT, "parts.csv")

exp = {}                 # net -> {(ref, pin)}
kind = {}                # ref -> (value, footprint name, LCSC number or "")


def con(ref, pin, net):
    exp.setdefault(net, set()).add((ref, str(pin)))


def part(ref, value, fp, lcsc, pins):
    kind[ref] = (value, fp, lcsc)
    for pin, net in pins.items():
        if net:
            con(ref, pin, net)


# ---- power
part("TP1", "BAT+", "BatPad_4x6", "", {1: "VBAT"})
part("TP2", "BAT-", "BatPad_4x6", "", {1: "GND"})
part("D1", "SS14", "D_SMA", "C2480", {2: "VBAT", 1: "VIN"})                  # SS14: pad 1 cathode, pad 2 anode
part("JP1", "bridged", "SolderJumper-2_P1.3mm_Bridged_Pad1.0x1.5mm", "", {1: "VIN", 2: "VDD"})
part("C1", "1u", "C_0603_1608Metric", "C15849", {1: "VDD", 2: "GND"})
part("C2", "1u", "C_0603_1608Metric", "C15849", {1: "VCAP", 2: "GND"})
part("C3", "1u", "C_0603_1608Metric", "C15849", {1: "VDD", 2: "GND"})
part("C4", "1u", "C_0603_1608Metric", "C15849", {1: "VIN", 2: "GND"})
# ---- U1 STM8S003F3P6: pin plan of the README
u1 = {2: "SER", 3: "SCK", 4: "NRST", 5: "SW1", 6: "SW2", 7: "GND", 8: "VCAP", 9: "VDD", 11: "SW5", 12: "SW4",
      18: "SWIM"}
if sorted(COLPIN.values()) != [1, 10, 13, 14, 15, 16, 17, 19, 20] or sorted(COLPIN) != list(range(1, 10)):
    raise SystemExit("pins.py: the columns must use exactly the pins 1, 10, 13 to 17, 19, 20")
if sorted(ROWOUT.values()) != [1, 2, 3, 4, 5, 6, 7, 15] or sorted(ROWOUT) != list(range(1, 9)):
    raise SystemExit("pins.py: the rows must use exactly the 595 outputs 15, 1 to 7")
for c in range(1, 10):
    u1[COLPIN[c]] = "DRV%d" % c
    part("R%d" % c, "270", "R_0603_1608Metric", "C22966", {1: "DRV%d" % c, 2: "COL%d" % c})
part("U1", "STM8S003F3P6TR", "TSSOP-20_4.4x6.5mm_P0.65mm", "C52717", u1)
# ---- U2 74HC595D: 14 data, 11 shift clock, 12 latch clock, 13 OE (low = on), 10 clear (low), 9 serial out
u2 = {14: "SER", 11: "SCK", 12: "SCK", 13: "GND", 10: "VDD", 16: "VDD", 8: "GND", 9: None}
for r in range(1, 9):
    u2[ROWOUT[r]] = "SR%d" % r
    part("R%d" % (9 + r), "1k", "R_0603_1608Metric", "C21190", {1: "SR%d" % r, 2: "B%d" % r})
    part("Q%d" % r, "S8050", "SOT-23", "C2146", {1: "B%d" % r, 2: "GND", 3: "ROW%d" % r})   # 1 B, 2 E, 3 C
part("U2", "74HC595D", "SOIC-16_3.9x9.9mm_P1.27mm", "C5947", u2)
# ---- buttons: pads 1 + 2 one side, pads 3 + 4 the other side
for k, net in ((1, "SW1"), (2, "SW2"), (3, "SWIM"), (4, "SW4"), (5, "SW5")):
    part("SW%d" % k, "TS-1187A", "SW_TS-1187A", "C318884", {1: net, 3: "GND", 4: "GND"})
part("R18", "1k", "R_0603_1608Metric", "C21190", {1: "VDD", 2: "SW4"})
part("R19", "1k", "R_0603_1608Metric", "C21190", {1: "VDD", 2: "SW5"})
part("J1", "SWIM", "PinHeader_1x04_P2.54mm_Vertical", "", {1: "VDD", 2: "SWIM", 3: "GND", 4: "NRST"})
# ---- matrix: KiCad's LED has pin 1 = cathode, pin 2 = anode
for r in range(1, 9):
    for c in range(1, 10):
        part("LED%d" % (9 * (r - 1) + c), "red", "LED_0603_1608Metric", "C2286", {2: "COL%d" % c, 1: "ROW%d" % r})

comps, nets = read_netlist(NET)
diffs = []
got = {}
unconnected = []
for name, nodes in nets.items():
    if name.startswith("unconnected-"):
        unconnected += nodes
    else:
        got[short(name)] = set(nodes)
for net in sorted(set(exp) | set(got)):
    a, b = exp.get(net, set()), got.get(net, set())
    if a != b:
        diffs.append("net %s: only expected %s, only in the netlist %s" % (net, sorted(a - b), sorted(b - a)))
free = sorted([("U2", "9")] + [("SW%d" % k, "2") for k in range(1, 6)])      # 595 serial output; second pad of each button
if sorted(unconnected) != free:
    diffs.append("unconnected pins: %s (expected %s)" % (sorted(unconnected), free))
for ref in sorted(set(kind) | set(comps)):
    if ref not in kind or ref not in comps:
        diffs.append("part %s: %s" % (ref, "not expected" if ref in comps else "missing in the netlist"))
        continue
    c = comps[ref]
    have = (c["value"], c["footprint"].split(":")[-1], c["fields"].get("LCSC", ""))
    if have != kind[ref]:
        diffs.append("part %s: netlist %s, expected %s" % (ref, have, kind[ref]))
    fitted = c["fields"].get("Assembly") == "JLCPCB"
    if fitted != bool(kind[ref][2]):
        diffs.append("part %s: field Assembly does not fit its LCSC number" % ref)
    if not fitted and re.match(r"J\d", ref) and "dnp" not in c["props"]:
        diffs.append("part %s: not marked do-not-populate" % ref)

# ---- part counts against parts.csv
count = {}
for ref, (_v, _f, num) in kind.items():
    if num:
        count[num] = count.get(num, 0) + 1
with open(PARTS, encoding="utf-8", newline="") as f:
    for row in csv.DictReader(f):
        if row["LCSC"] and count.get(row["LCSC"]) != int(row["Qty per board"]):
            diffs.append("parts.csv: %s x %s, circuit has %s" % (row["LCSC"], row["Qty per board"], count.get(row["LCSC"])))
        if row["LCSC"]:
            count.pop(row["LCSC"], None)
if count:
    diffs.append("LCSC numbers that are not in parts.csv: %s" % sorted(count))

fitted = [r for r in comps if comps[r]["fields"].get("Assembly") == "JLCPCB"]
joints = sum(1 for nodes in nets.values() for ref, _pin in nodes if ref in fitted)
for d in diffs:
    print("DIFF " + d)
print("checked: %d parts, %d nets, %d pins; fitted by JLCPCB: %d parts of %d kinds, %d solder joints"
      % (len(comps), len(got), sum(len(v) for v in got.values()) + len(unconnected), len(fitted),
         len({comps[r]["fields"]["LCSC"] for r in fitted}), joints))
print("differences: %d" % len(diffs))
sys.exit(1 if diffs else 0)
