"""
led_fab.py - the files for JLCPCB in ../fabrication/: Gerber zip, BOM and placement file.

JLCPCB places every part by its own footprint, and some of those are drawn turned against KiCad's.
jlc_pads.json holds the pad positions of JLCPCB's footprint for every LCSC number on the board. For each part
this script finds the angle at which JLCPCB's footprint lands on the board's pads, pad for pad, writes that
angle, and stops if a part does not land.
The LED is special: JLCPCB's footprint numbers its pads the other way round (pad 1 = anode, KiCad pad 1 =
cathode). jlc_pads.json says so ("same_as"), and the pads are compared by function, anode on anode.

Not in the BOM and the placement file: J1 (programming pads, not fitted), JP1 (jumper made of copper), the
battery pads.
Run: <KiCad 10>/bin/python.exe led_fab.py
"""
import csv
import json
import math
import os
import re
import shutil
import subprocess
import sys
import zipfile

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from netlist import read_netlist  # noqa: E402
from led_board import NETLIST, PCB, CLI, OUT, NAME  # noqa: E402

FAB = os.path.join(OUT, "fabrication")
TMP = os.path.join(FAB, "_gerbers")
PADS = os.path.join(HERE, "jlc_pads.json")
FIT = 0.45          # mm: JLCPCB's pad centre may be this far from the board's (other land size, same package)
CLEAR = 0.9         # mm: every other angle must miss by at least this much

README = """Files for JLCPCB, LED heart board. Made by gen/led_fab.py from the board file.

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
- After the upload JLCPCB must find all %(lines)d BOM lines (%(parts)d parts per board), all Basic or Preferred:
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
The angles in the placement file are already turned to JLCPCB's footprints (%(turned)s)
and checked by script against JLCPCB's footprint data.

Not in the BOM and the placement file, on purpose: J1 (4 programming pads), JP1 (jumper made of copper),
the two battery pads on the back.
"""


def run(*a):
    r = subprocess.run([CLI] + list(a), capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout[-500:], r.stderr[-500:])
        raise SystemExit("kicad-cli failed: " + " ".join(a[:3]))


def order(ref):
    m = re.match(r"([A-Z]+)(\d+)", ref)
    return (m.group(1), int(m.group(2)))


def turn(x, y, deg):
    """Turn a point counter-clockwise as seen on the board (y points down)."""
    a = math.radians(deg)
    return x * math.cos(a) + y * math.sin(a), -x * math.sin(a) + y * math.cos(a)


def angle_for(fp, jlc):
    """Angle to add to KiCad's rotation so that JLCPCB's footprint lands on this footprint's pads.
    jlc: {KiCad pad number: (x, y) of JLCPCB's pad with the same function}."""
    o = fp.GetPosition()
    k = fp.GetOrientationDegrees()
    mine = {}
    for p in fp.Pads():
        if p.GetNumber():                    # pad positions in the footprint's own frame (rotation taken out)
            dx, dy = pcbnew.ToMM(p.GetPosition().x - o.x), pcbnew.ToMM(p.GetPosition().y - o.y)
            mine[p.GetNumber()] = turn(dx, dy, -k)
    if set(mine) != set(jlc):
        raise SystemExit("%s: pad numbers differ, board %s, JLCPCB %s" % (fp.GetReference(), sorted(mine), sorted(jlc)))
    miss = {}
    for add in (0, 90, 180, 270):
        miss[add] = max(math.hypot(turn(*jlc[n], add)[0] - mine[n][0], turn(*jlc[n], add)[1] - mine[n][1]) for n in mine)
    best = min(miss, key=miss.get)
    others = min(v for a, v in miss.items() if a != best)
    if miss[best] > FIT or others < CLEAR:
        raise SystemExit("%s: no clear angle, misses %s" % (fp.GetReference(), {a: round(v, 2) for a, v in miss.items()}))
    return best, miss[best]


def main():
    if os.path.isdir(FAB):
        shutil.rmtree(FAB)
    os.makedirs(TMP)
    run("pcb", "export", "gerbers", "-o", TMP + os.sep, "--layers",
        "F.Cu,B.Cu,F.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts", "--no-x2", "--no-netlist", PCB)
    run("pcb", "export", "drill", "-o", TMP + os.sep, "--format", "excellon", "--excellon-units", "mm",
        "--excellon-zeros-format", "decimal", "--excellon-separate-th", PCB)     # plated and unplated holes apart
    files = sorted(os.listdir(TMP))
    with zipfile.ZipFile(os.path.join(FAB, NAME + "_gerbers_jlc.zip"), "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            z.write(os.path.join(TMP, f), f)

    comps, nets = read_netlist(NETLIST)
    groups, lcsc = {}, {}
    for ref, c in comps.items():
        if c["fields"].get("Assembly") == "JLCPCB":
            key = (c["fields"].get("LCSC", ""), c["value"], c["footprint"].split(":")[-1])
            groups.setdefault(key, []).append(ref)
            lcsc[ref] = key[0]
    with open(os.path.join(FAB, NAME + "_jlc_bom.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
        for (num, val, fpname), refs in sorted(groups.items(), key=lambda kv: order(min(kv[1], key=order))):
            w.writerow([val, ",".join(sorted(refs, key=order)), fpname, num])

    jlc = json.load(open(PADS, encoding="utf-8"))
    board = pcbnew.LoadBoard(PCB)
    fps = {fp.GetReference(): fp for fp in board.GetFootprints()}
    added, worst = {}, (0.0, "")
    for ref in lcsc:
        if lcsc[ref] not in jlc:
            raise SystemExit("%s: no pad data for %s in jlc_pads.json" % (ref, lcsc[ref]))
        e = jlc[lcsc[ref]]
        same = e.get("same_as", {})                          # JLCPCB pad number -> KiCad pad number
        add, miss = angle_for(fps[ref], {same.get(n, n): tuple(v) for n, v in e["pads"].items()})
        if added.setdefault(lcsc[ref], add) != add:
            raise SystemExit("%s: another angle than the other parts with %s" % (ref, lcsc[ref]))
        if miss > worst[0]:
            worst = (miss, ref)

    pos = os.path.join(FAB, "_pos.csv")
    run("pcb", "export", "pos", "-o", pos, "--format", "csv", "--units", "mm", "--side", "front", "--exclude-dnp", PCB)
    n = 0
    with open(pos, encoding="utf-8", newline="") as f, \
            open(os.path.join(FAB, NAME + "_jlc_cpl.csv"), "w", encoding="utf-8", newline="") as g:
        w = csv.writer(g)
        w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        for row in csv.DictReader(f):
            ref = row["Ref"]
            if ref not in lcsc:
                continue
            fp = fps[ref]
            x, y = pcbnew.ToMM(fp.GetPosition().x), pcbnew.ToMM(fp.GetPosition().y)
            if abs(float(row["PosX"]) - x) > 0.001 or abs(float(row["PosY"]) + y) > 0.001 \
                    or abs((float(row["Rot"]) - fp.GetOrientationDegrees() + 180) % 360 - 180) > 0.001:
                raise SystemExit("%s: the position file and the board differ" % ref)
            w.writerow([ref, row["PosX"] + "mm", row["PosY"] + "mm", "Top",
                        "%g" % ((float(row["Rot"]) + added[lcsc[ref]]) % 360)])
            n += 1
    os.remove(pos)
    shutil.rmtree(TMP)
    if n != len(lcsc):
        raise SystemExit("placement file has %d parts, the BOM %d" % (n, len(lcsc)))

    turned = {}
    for num, add in added.items():
        if add:
            turned.setdefault(add, []).append(num)
    words = "; ".join("%d degrees for %s" % (a, ", ".join(sorted(v, key=lambda c: int(c[1:])))) for a, v in sorted(turned.items()))
    joints = sum(1 for nodes in nets.values() for ref, _pin in nodes if ref in lcsc)
    with open(os.path.join(FAB, "READ_ME_FIRST.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write(README % {"lines": len(groups), "parts": len(lcsc), "turned": words})
    print("gerbers: %d files in the zip: %s" % (len(files), " ".join(files)))
    print("BOM: %d lines, %d parts, %d solder joints; placement file: %d parts" % (len(groups), len(lcsc), joints, n))
    print("angles added to KiCad's rotation: %s; 0 for the other %d part numbers (%s)"
          % (words, len(added) - sum(len(v) for v in turned.values()), ", ".join(sorted((c for c, a in added.items() if not a), key=lambda c: int(c[1:])))))
    print("every part lands on its pads with JLCPCB's footprint; largest difference %.2f mm (%s)" % worst)


if __name__ == "__main__":
    try:
        main()
        code = 0
    except SystemExit as e:
        print(e)
        code = 1
    except Exception:
        import traceback
        traceback.print_exc()
        code = 1
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(code)
