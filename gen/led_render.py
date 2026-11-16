"""
led_render.py - 3D pictures of the board in ../preview/: top.png, bottom.png, angle.png, closeup.png.

Renders from a temporary copy of the board, changed for the pictures only (the board file stays as it is):
- the five buttons get KiCad's E-Switch TL3342 model. KiCad has no model of the XKB TS-1187A; the TL3342 is
  5.2 x 5.2 mm with its legs at +-3.15/+-1.9 mm, the TS-1187A 5.1 x 5.1 mm with its pads at +-3/+-1.85 mm.
- J1 shows no pin header (not fitted).
- a stackup with the colours of the order: black solder mask (Edy ordered it black, 2026-11-16), white print,
  HASL.
Run: <KiCad 10>/bin/python.exe led_render.py   (about 10 s per picture)
"""
import os
import shutil
import subprocess
import sys
import tempfile

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from led_board import PCB, CLI, OUT, NAME  # noqa: E402

SW_MODEL = "${KICAD10_3DMODEL_DIR}/Button_Switch_SMD.3dshapes/SW_SPST_TL3342.step"
STACKUP = """(stackup
 (layer "F.SilkS" (type "Top Silk Screen") (color "White"))
 (layer "F.Paste" (type "Top Solder Paste"))
 (layer "F.Mask" (type "Top Solder Mask") (color "Black") (thickness 0.01))
 (layer "F.Cu" (type "copper") (thickness 0.035))
 (layer "dielectric 1" (type "core") (thickness 1.51) (material "FR4") (epsilon_r 4.5) (loss_tangent 0.02))
 (layer "B.Cu" (type "copper") (thickness 0.035))
 (layer "B.Mask" (type "Bottom Solder Mask") (color "Black") (thickness 0.01))
 (layer "B.Paste" (type "Bottom Solder Paste"))
 (layer "B.SilkS" (type "Bottom Silk Screen") (color "White"))
 (copper_finish "HAL SnPb")
 (dielectric_constraints no))
"""
FLAT = ["--width", "2400", "--height", "1412", "--zoom", "1.6"]
TILT = ["--width", "2400", "--height", "1600", "--perspective", "--floor"]
VIEWS = {
    "top.png": FLAT + ["--side", "top"],
    "bottom.png": FLAT + ["--side", "bottom"],
    "angle.png": TILT + ["--rotate", "-42,0,-25", "--zoom", "1.08", "--pan", "0,1.3,0"],
    "closeup.png": TILT + ["--rotate", "-40,0,-25", "--zoom", "2.3", "--pan", "-2.5,0.3,0"],
}


def main():
    tmp = tempfile.mkdtemp()
    try:
        copy = os.path.join(tmp, NAME + ".kicad_pcb")
        board = pcbnew.LoadBoard(PCB)
        for fp in board.GetFootprints():
            ref = fp.GetReference()
            if ref.startswith("SW") or ref == "J1":
                fp.Models().clear()
            if ref.startswith("SW"):
                m = pcbnew.FP_3DMODEL()
                m.m_Filename = SW_MODEL
                m.m_Show = True
                fp.Models().push_back(m)
        pcbnew.SaveBoard(copy, board)
        text = open(copy, encoding="utf-8").read()
        if "(stackup" in text or text.count("(setup") != 1:
            raise SystemExit("the board file has a stackup now, or not one (setup: look at this script again")
        with open(copy, "w", encoding="utf-8", newline="\n") as f:
            f.write(text.replace("(setup", "(setup\n" + STACKUP, 1))
        os.makedirs(os.path.join(OUT, "preview"), exist_ok=True)
        for name, args in VIEWS.items():
            out = os.path.join(OUT, "preview", name)
            r = subprocess.run([CLI, "pcb", "render", "-o", out, "--quality", "high", "--background", "opaque"]
                               + args + [copy], capture_output=True, text=True)
            if r.returncode != 0 or not os.path.isfile(out):
                print(r.stdout[-500:], r.stderr[-500:])
                raise SystemExit("render failed: " + name)
            print("preview/" + name)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


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
