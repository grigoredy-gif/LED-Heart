"""Tight extents of the silkscreen texts near the board edge (strokes with their width), on the saved board."""
import os, sys, traceback
try:
    import pcbnew
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from led_board import PCB, OX, OY, W, H
    mm = pcbnew.ToMM
    b = pcbnew.LoadBoard(PCB)
    for d in b.GetDrawings():
        if d.GetClass() != "PCB_TEXT" or d.GetText() not in ("Dedeghe", "TM", "4.5 V, max 5 V"):
            continue
        ps = pcbnew.SHAPE_POLY_SET()
        d.TransformTextToPolySet(ps, 0, pcbnew.FromMM(0.005), pcbnew.ERROR_INSIDE)
        bb = ps.BBox()
        x0, x1, y0, y1 = mm(bb.GetX()) - OX, mm(bb.GetRight()) - OX, mm(bb.GetY()) - OY, mm(bb.GetBottom()) - OY
        print("%-16r h %.2f  ink x %.2f..%.2f  y %.2f..%.2f  -> to the bottom edge %.2f mm, to the right edge %.2f mm"
              % (d.GetText(), mm(d.GetTextSize().y), x0, x1, y0, y1, H - y1, W - x1))
except Exception:
    traceback.print_exc()
sys.stdout.flush(); os._exit(0)
