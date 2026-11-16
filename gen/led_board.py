"""
led_board.py - builds the LED heart board (KiCad 10 pcbnew) from ../led_heart.net.

  place    outline, rules, all footprints at their places
  hand     tracks laid by rule: the 8 row buses (top), the 9 column buses (bottom, one via per LED), the column
           bundle along the north edge to the 270 ohm resistors, the row transistors, the ground vias beside pads
  auto     Freerouting for the rest (chips, buttons, power); its window opens for about a minute
  merge    takes the autorouted tracks into the board      clean   removes the autorouter's dangling stubs
  ground   ground pours on both layers, stitching vias, no bare pockets
  silk     button names, SWIM pad names, + and - on the back, the mark
  drc [types]   kicad-cli DRC with schematic parity

Run each step in its own process with KiCad's Python, KiCad closed:  <KiCad 10>/bin/python.exe led_board.py <step>
Coordinates: mm on the board, x to the right, y down, (0, 0) = top left corner. In the file the corner is at (OX, OY).
"""
import json
import math
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pcbnew  # noqa: E402
import frhelp  # noqa: E402
from netlist import read_netlist, short  # noqa: E402
from pins import BUTTONS  # noqa: E402

OUT = os.path.dirname(HERE)
NAME = "led_heart"
PCB = os.path.join(OUT, NAME + ".kicad_pcb")
PRO = os.path.join(OUT, NAME + ".kicad_pro")
NETLIST = os.path.join(OUT, NAME + ".net")
DSN, SES, FRLOG = (os.path.join(OUT, NAME + e) for e in (".dsn", ".ses", "_freerouting.log"))
KICAD = r"C:\Users\grigo\AppData\Local\Programs\KiCad\10.0"
FPDIR = os.path.join(KICAD, "share", "kicad", "footprints")
PROJ_FP = {"led_heart": os.path.join(OUT, "led_heart.pretty")}
CLI = os.path.join(KICAD, "bin", "kicad-cli.exe")
FM, MM = pcbnew.FromMM, pcbnew.ToMM
F, B = pcbnew.F_Cu, pcbnew.B_Cu
OX, OY = 100.0, 50.0
W, H = 85.0, 50.0           # 80 x 50 until 2026-11-15: widened on the right so that M3 holes fit in all four corners
# Corner mounting holes: M3, 3.2 mm, not plated, 2.75 mm in from both edges, where a 6 mm screw head clears every
# track, pad and part (measured 2026-11-15). Footprints on the board only: not in the schematic, BOM or placement file.
MOUNT_FP = "MountingHole:MountingHole_3.2mm_M3"
MOUNT_INSET = 2.75

# name: (track, clearance, via diameter, via drill, nets)
NETCLASSES = {"PWR": (0.4, 0.2, 0.8, 0.4, ["VDD", "VIN", "VBAT"])}
DEFAULT_CLASS = (0.25, 0.2, 0.7, 0.3)
VIA_D, VIA_DRILL = 0.7, 0.3
VIA_R = VIA_D / 2

# ---- the matrix
NC, NR, PITCH = 9, 8, 5.0
LED_X0, LED_Y0 = 6.0, 7.5
PAD = 0.7875                       # LED pad centre from the LED centre
VIA_UP = 1.9                       # column via: this far north of the LED centre
ROW_W, COL_W = 0.4, 0.25
LANE = {1: 1.35, 2: 2.05, 3: 2.525, 4: 3.0, 5: 3.475, 6: 3.95, 7: 4.425, 8: 4.9, 9: 5.6}    # y of each column's run to the east
RVIA_Y = 1.35                      # vias north of R1 to R7; the pours pass between them and the board edge
Q_X, RB_X = 51.0, 54.6
# ---- microcontroller side
U1 = (63.5, 10.5)
RCOL_Y = 3.2                       # row of the column resistors R1 to R7, north of U1
RCOL_X = {c: 58.2 + 1.6 * (c - 1) for c in range(1, 8)}
R8, R9 = (68.2, 15.225), (59.0, 15.225)     # column resistors of U1 pin 10 and pin 1, south of U1
U2 = (62.5, 29.875)
SW_X, SW_Y = 74.5, [6.5 + 8.4 * k for k in range(5)]
SW_NAME = [b[3] for b in BUTTONS]          # MODE, SPEED, DIM, BRIGHT, ON/OFF (see pins.py)
J1 = (58.8, 38.0)
J1_NAME = ["VDD", "SWIM", "GND", "RST"]
# ground vias laid before the autorouter: (pad x, pad y, via x, via y)
GND_VIAS = [(64.475, 12.9, 64.475, 11.4),                       # U1 pin 7, via under the chip
            (65.0, 16.675, 65.0, 17.85), (66.6, 16.675, 66.6, 17.85),      # C2, C1
            (60.025, 34.32, 61.75, 34.32), (64.975, 29.24, 63.25, 29.24),  # U2 pin 8, pin 13 (via under the chip)
            (68.625, 25.43, 68.625, 24.2),                      # C3
            (68.125, 43.2, 68.125, 42.0)]                       # C4
for _y in SW_Y:
    GND_VIAS += [(71.5, _y + 1.85, 72.75, _y + 1.85), (77.5, _y + 1.85, 76.25, _y + 1.85)]
# name, sign, x of the right end, y of the name's centre, heights. The band between D1's outline (ends at
# y = 47.71) and the board edge is 2.3 mm: a 1.2 mm name fits with the tail of its "g" 0.33 mm from the edge.
SILK_MARK = ("Dedeghe", "TM", 79.2, 48.634, 1.2, 1.0)
# silkscreen boxes that ground vias keep out of: (x0, y0, x1, y1)
KEEP = [(68.0, 47.9, 79.6, 49.7), (57.6, 39.0, 67.6, 43.0)] + [(71.5, y - 4.7, 77.5, y - 3.3) for y in SW_Y]


def V(x, y):
    return pcbnew.VECTOR2I(FM(x + OX), FM(y + OY))


def led_xy(c, r):
    """Centre of the LED in column c (1 to 9), row r (1 to 8)."""
    return LED_X0 + PITCH * (c - 1), LED_Y0 + PITCH * (r - 1)


def row_y(r):
    return LED_Y0 + PITCH * (r - 1) + PAD          # the cathode pads of a row, and its bus


def placement():
    """ref -> (x, y, angle, on the back)."""
    p = {}
    for r in range(1, NR + 1):
        for c in range(1, NC + 1):
            x, y = led_xy(c, r)
            p["LED%d" % (NC * (r - 1) + c)] = (x, y, 90, False)             # anode north, cathode south
        p["Q%d" % r] = (Q_X, row_y(r), 180, False)                           # collector west, on the row bus
        p["R%d" % (9 + r)] = (RB_X, row_y(r) + 0.95, 180, False)             # base resistor, pad 2 (base) west
    p["U1"] = U1 + (90, False)                                               # pins 11 to 20 north, 1 to 10 south
    for c, x in RCOL_X.items():
        p["R%d" % c] = (x, RCOL_Y, 90, False)                                # pad 2 (column) north
    p["R8"] = R8 + (270, False)                                              # pad 2 (column) south
    p["R9"] = R9 + (270, False)
    p["C2"] = (65.0, 15.9, 270, False)
    p["C1"] = (66.6, 15.9, 270, False)
    p["U2"] = U2 + (0, False)
    p["C3"] = (67.85, 25.43, 0, False)
    for k, y in enumerate(SW_Y, 1):
        p["SW%d" % k] = (SW_X, y, 0, False)
    p["R18"] = (69.0, 27.0, 0, False)
    p["R19"] = (69.0, 35.2, 0, False)
    p["J1"] = J1 + (90, False)                                               # pins 1 to 4 from west to east
    p["TP1"] = (64.0, 44.5, 0, True)
    p["TP2"] = (58.5, 44.5, 0, True)
    p["D1"] = (69.5, 46.0, 180, False)                                       # anode west, cathode east
    p["C4"] = (68.9, 43.2, 180, False)
    p["JP1"] = (75.0, 46.0, 0, False)
    return p


# ============================================================================ step: place
def draw_outline(board):
    for d in list(board.GetDrawings()):
        if d.GetLayer() == pcbnew.Edge_Cuts:
            board.Delete(d)
    for a, b in (((0, 0), (W, 0)), ((W, 0), (W, H)), ((W, H), (0, H)), ((0, H), (0, 0))):
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(V(*a))
        s.SetEnd(V(*b))
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(FM(0.1))
        board.Add(s)


def add_holes(board):
    """The four corner mounting holes H1 to H4 (see MOUNT_FP); an earlier set is replaced. Returns their centres."""
    for fp in list(board.GetFootprints()):
        if re.match(r"H\d+$", fp.GetReference()):
            board.Delete(fp)
    spots = [(MOUNT_INSET, MOUNT_INSET), (W - MOUNT_INSET, MOUNT_INSET),
             (MOUNT_INSET, H - MOUNT_INSET), (W - MOUNT_INSET, H - MOUNT_INSET)]
    for k, (x, y) in enumerate(spots, 1):
        fp = load_fp(MOUNT_FP)
        fp.SetReference("H%d" % k)
        fp.SetValue("M3")
        for f in fp.GetFields():
            f.SetVisible(False)
        fp.SetBoardOnly(True)
        fp.SetExcludedFromBOM(True)
        fp.SetExcludedFromPosFiles(True)
        board.Add(fp)
        fp.SetPosition(V(x, y))
    return spots


def widen():
    """2026-11-15: the routed board gets the outline of W x H and the four corner holes, without re-routing. The ground
    stitching vias that would sit under a screw head are removed. Run 'ground', 'silk' and 'drc' after this step."""
    board = pcbnew.LoadBoard(PCB)
    draw_outline(board)
    spots = add_holes(board)
    gone = []
    for t in list(board.GetTracks()):
        if t.GetClass() == "PCB_VIA" and t.GetNetname() == "GND" and not t.IsLocked():
            x, y = MM(t.GetPosition().x) - OX, MM(t.GetPosition().y) - OY
            if any(math.hypot(x - hx, y - hy) < 3.0 + VIA_R + 0.2 for hx, hy in spots):
                gone.append("(%.2f, %.2f)" % (x, y))
                board.Delete(t)
    near = []                                   # anything else of copper inside a screw head (6 mm) plus 0.2 mm
    for t in board.GetTracks():
        if t.GetClass() == "PCB_VIA":
            x, y = MM(t.GetPosition().x) - OX, MM(t.GetPosition().y) - OY
            if any(math.hypot(x - hx, y - hy) < 3.2 + MM(t.GetWidth(F)) / 2 for hx, hy in spots):
                near.append("via %s (%.2f, %.2f)" % (t.GetNetname(), x, y))
        else:
            seg = dict(x1=MM(t.GetStart().x) - OX, y1=MM(t.GetStart().y) - OY, x2=MM(t.GetEnd().x) - OX, y2=MM(t.GetEnd().y) - OY)
            for hx, hy in spots:
                if _seg_dist(hx, hy, (seg["x1"], seg["y1"], seg["x2"], seg["y2"])) - MM(t.GetWidth()) / 2 < 3.2:
                    near.append("track %s" % t.GetNetname())
    for fp in board.GetFootprints():
        if not re.match(r"H\d+$", fp.GetReference()):
            for q in fp.Pads():
                c = q.GetPosition()
                bb = q.GetBoundingBox()
                b = (MM(bb.GetX()) - OX, MM(bb.GetY()) - OY, MM(bb.GetRight()) - OX, MM(bb.GetBottom()) - OY)
                if any(_box_dist(hx, hy, b) < 3.2 for hx, hy in spots):
                    near.append("pad %s.%s" % (fp.GetReference(), q.GetNumber()))
    pcbnew.SaveBoard(PCB, board)
    print("widen: outline %.0f x %.0f mm; holes at %s; ground vias removed under the heads: %s; other copper under a head: %s"
          % (W, H, ", ".join("(%.2f, %.2f)" % s for s in spots), ", ".join(gone) or "none", ", ".join(near) or "none"))


def setup_rules(board):
    ds = board.GetDesignSettings()
    for attr, val in (("m_MinClearance", 0.15), ("m_TrackMinWidth", 0.15), ("m_ViasMinSize", 0.6),
                      ("m_MinThroughDrill", 0.3), ("m_CopperEdgeClearance", 0.3), ("m_HoleClearance", 0.25),
                      ("m_HoleToHoleMin", 0.5), ("m_ViasMinAnnularWidth", 0.15)):
        if hasattr(ds, attr):
            setattr(ds, attr, FM(val))
    if hasattr(ds, "m_MinResolvedSpokes"):
        ds.m_MinResolvedSpokes = 1
    ns = ds.m_NetSettings
    dflt = ns.GetDefaultNetclass()
    tw, cl, vd, vdr = DEFAULT_CLASS
    dflt.SetTrackWidth(FM(tw))
    dflt.SetClearance(FM(cl))
    dflt.SetViaDiameter(FM(vd))
    dflt.SetViaDrill(FM(vdr))
    ns.ClearNetclassPatternAssignments()
    for name, (tw, cl, vd, vdr, nets) in NETCLASSES.items():
        nc = pcbnew.NETCLASS(name)
        nc.SetTrackWidth(FM(tw))
        nc.SetClearance(FM(cl))
        nc.SetViaDiameter(FM(vd))
        nc.SetViaDrill(FM(vdr))
        ns.SetNetclass(name, nc)
        for nn in nets:
            ns.SetNetclassPatternAssignment("/" + nn, name)


def class_patterns_saved():
    """Net-class assignments live in the .kicad_pro; a scripted save can skip that file without a word."""
    with open(PRO, encoding="utf-8") as f:
        pro = json.load(f)
    have = {(p.get("pattern"), p.get("netclass")) for p in pro.get("net_settings", {}).get("netclass_patterns") or []}
    want = {("/" + nn, name) for name, v in NETCLASSES.items() for nn in v[4]}
    return sorted(want - have)


def load_fp(fpid):
    lib, name = fpid.split(":", 1)
    fp = pcbnew.FootprintLoad(PROJ_FP.get(lib) or os.path.join(FPDIR, lib + ".pretty"), name)
    if fp is None:
        raise RuntimeError("footprint not found: " + fpid)
    fp.SetFPID(pcbnew.LIB_ID(lib, name))
    return fp


def dress(fp, ref, c):
    fp.SetReference(ref)
    fp.SetValue(c["value"])
    for k in ("LCSC", "Assembly"):
        if c["fields"].get(k):
            fp.SetField(k, c["fields"][k])
    for f in fp.GetFields():
        f.SetVisible(False)                 # 115 references do not fit on the silkscreen; they are on F.Fab
    fp.SetPath(pcbnew.KIID_PATH(c["path"]))
    fp.SetSheetname(c["sheetname"])
    fp.SetSheetfile(c["sheetfile"])
    fp.SetDNP("dnp" in c["props"])
    fp.SetExcludedFromBOM("exclude_from_bom" in c["props"])
    fp.SetExcludedFromPosFiles(c["fields"].get("Assembly") != "JLCPCB")


def place():
    comps, nets = read_netlist(NETLIST)
    where = placement()
    if set(where) != set(comps):
        raise KeyError("placement and netlist differ: %s" % sorted(set(where) ^ set(comps)))
    if os.path.exists(PCB):
        os.remove(PCB)
    board = pcbnew.NewBoard(PCB)
    board.SetCopperLayerCount(2)
    board.GetDesignSettings().SetBoardThickness(FM(1.6))
    setup_rules(board)
    tb = board.GetTitleBlock()
    tb.SetTitle("LED heart: 9 x 8 LED matrix")
    tb.SetRevision("1")
    tb.SetCompany("Edy Grigore")
    draw_outline(board)
    netinfo = {}
    for name in nets:
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        netinfo[name] = ni
    net_of_pad = {(ref, pin): name for name, nodes in nets.items() for ref, pin in nodes}
    for ref, c in sorted(comps.items()):
        fp = load_fp(c["footprint"])
        dress(fp, ref, c)
        board.Add(fp)
        x, y, ang, back = where[ref]
        fp.SetPosition(V(x, y))
        if back:
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        fp.SetOrientationDegrees(ang)
        for p in fp.Pads():
            nn = net_of_pad.get((ref, p.GetNumber()))
            if nn:
                p.SetNet(netinfo[nn])
    add_holes(board)
    pcbnew.SaveBoard(PCB, board)
    missing = class_patterns_saved()
    if missing:                              # write them into the project file ourselves
        with open(PRO, encoding="utf-8") as f:
            pro = json.load(f)
        ns = pro.setdefault("net_settings", {})
        pats = ns.get("netclass_patterns") or []
        pats += [{"netclass": n, "pattern": p} for p, n in missing]
        ns["netclass_patterns"] = pats
        classes = ns.setdefault("classes", [])
        for name, (tw, cl, vd, vdr, _n) in NETCLASSES.items():
            if not any(k.get("name") == name for k in classes):
                base = dict(classes[0]) if classes else {}
                base.update({"name": name, "track_width": tw, "clearance": cl, "via_diameter": vd, "via_drill": vdr})
                classes.append(base)
        with open(PRO, "w", encoding="utf-8") as f:
            json.dump(pro, f, indent=2)
    print("place: %d parts, %d nets; net-class patterns missing from the project file after saving: %s"
          % (len(comps), len(nets), missing or "none"))


# ============================================================================ step: hand
def find_net(board, name):
    n = board.FindNet(name)
    if n:
        return n
    for full, net in board.GetNetsByName().items():
        if str(full).split("/")[-1] == name:
            return net
    raise KeyError("net not found: " + name)


class Router:
    def __init__(self, board):
        self.board = board
        self.n = {"tracks": 0, "vias": 0}

    def track(self, net, layer, w, pts, lock=True):
        ni = find_net(self.board, net)
        for a, b in zip(pts, pts[1:]):
            if math.hypot(a[0] - b[0], a[1] - b[1]) < 1e-6:
                continue
            t = pcbnew.PCB_TRACK(self.board)
            t.SetStart(V(*a))
            t.SetEnd(V(*b))
            t.SetWidth(FM(w))
            t.SetLayer(layer)
            t.SetNet(ni)
            t.SetLocked(lock)
            self.board.Add(t)
            self.n["tracks"] += 1

    def via(self, net, x, y, d=VIA_D, drill=VIA_DRILL, lock=True):
        v = pcbnew.PCB_VIA(self.board)
        v.SetPosition(V(x, y))
        v.SetViaType(pcbnew.VIATYPE_THROUGH)
        v.SetLayerPair(F, B)
        v.SetDrill(FM(drill))
        v.SetWidth(F, FM(d))
        v.SetNet(find_net(self.board, net))
        v.SetLocked(lock)
        self.board.Add(v)
        self.n["vias"] += 1


def hand():
    board = pcbnew.LoadBoard(PCB)
    r = Router(board)
    for row in range(1, NR + 1):
        y = row_y(row)
        r.track("ROW%d" % row, F, ROW_W, [(led_xy(c, 1)[0], y) for c in range(1, NC + 1)] + [(Q_X - 0.9375, y)])   # bus through the 9 cathodes
        r.track("B%d" % row, F, 0.25, [(Q_X + 0.9375, y + 0.95), (RB_X - 0.825, y + 0.95)])
        r.track("GND", F, 0.3, [(Q_X + 0.9375, y - 0.95), (53.3, y - 0.95)])        # emitter to its ground via
        r.via("GND", 53.3, y - 0.95)
    for c in range(1, NC + 1):
        net = "COL%d" % c
        x = led_xy(c, 1)[0]
        for row in range(1, NR + 1):
            yc = led_xy(c, row)[1]
            r.via(net, x, yc - VIA_UP)
            r.track(net, F, COL_W, [(x, yc - VIA_UP), (x, yc - PAD)])
        ly = LANE[c]
        south = led_xy(c, NR)[1] - VIA_UP
        r.track(net, B, COL_W, [(x, led_xy(c, row)[1] - VIA_UP) for row in range(NR, 0, -1)])     # bus through the 8 vias
        south = led_xy(c, 1)[1] - VIA_UP
        if c <= 7:                                   # along the north edge to its resistor in the row above U1
            xr = RCOL_X[c]
            r.track(net, B, COL_W, [(x, south), (x, ly), (xr, ly), (xr, RVIA_Y)])
            r.via(net, xr, RVIA_Y)
            r.track(net, F, COL_W, [(xr, RVIA_Y), (xr, RCOL_Y - 0.825)])
        else:                                        # under U1's end to the resistor south of U1
            xr, yr = R8 if c == 8 else R9
            r.track(net, B, COL_W, [(x, south), (x, ly), (xr, ly), (xr, yr + 1.925)])
            r.via(net, xr, yr + 1.925)
            r.track(net, F, COL_W, [(xr, yr + 1.925), (xr, yr + 0.825)])
    for px, py, vx, vy in GND_VIAS:
        r.track("GND", F, 0.3, [(px, py), (vx, vy)])
        r.via("GND", vx, vy)
    # 595 output QA (pin 15, on the far side of U2) to the base resistor of row 1: under the chip, then north
    y1 = row_y(1) + 0.95
    r.track("SR1", F, 0.25, [(U2[0] + 2.475, U2[1] - 3.175), (U2[0] + 0.8, U2[1] - 3.175), (U2[0] + 0.8, 24.6),
                             (57.8, 24.6), (57.8, y1), (RB_X + 0.825, y1)])
    # battery plus: from its pad on the back through a via to the diode
    r.track("VBAT", B, 0.5, [(64.0, 44.5), (66.9, 44.5), (66.9, 44.2)])
    r.via("VBAT", 66.9, 44.2, 0.8, 0.4)
    r.track("VBAT", F, 0.5, [(66.9, 44.2), (66.9, 45.6), (67.5, 46.0)])
    pcbnew.SaveBoard(PCB, board)
    print("hand: %(tracks)d locked track segments, %(vias)d vias" % r.n)


# ============================================================================ step: auto, merge, clean
def auto(minutes=6):
    board = pcbnew.LoadBoard(PCB)
    ok = pcbnew.ExportSpecctraDSN(board, DSN)
    frhelp.strip_net(DSN, "GND")
    print("DSN export:", ok, flush=True)
    saved = frhelp.run_freerouting(DSN, SES, FRLOG, minutes)
    with open(FRLOG, encoding="utf-8", errors="replace") as lf:
        lines = [l for l in lf.read().splitlines() if "pass #" in l or "completed" in l or "ERROR" in l]
    print("\n".join(lines[-4:]), flush=True)
    print("session file written:", saved, flush=True)
    return 0 if saved else 2


def merge():
    session = frhelp.read_session(SES)
    board = pcbnew.LoadBoard(PCB)
    have, have_via = {}, []
    for t in board.GetTracks():
        if t.GetClass() == "PCB_VIA":
            have_via.append((MM(t.GetPosition().x), MM(t.GetPosition().y)))
        else:
            a, b = t.GetStart(), t.GetEnd()
            have.setdefault(t.GetNetname(), []).append((board.GetLayerName(t.GetLayer()), MM(a.x), MM(a.y), MM(b.x), MM(b.y)))

    def on_segment(p, s, tol=0.02):
        (x, y), (_l, x1, y1, x2, y2) = p, s
        dx, dy = x2 - x1, y2 - y1
        n = math.hypot(dx, dy)
        if n < 1e-9:
            return math.hypot(x - x1, y - y1) < tol
        t = ((x - x1) * dx + (y - y1) * dy) / (n * n)
        return -tol / n <= t <= 1 + tol / n and abs((x - x1) * dy - (y - y1) * dx) / n < tol

    nets = {str(k): v for k, v in board.GetNetsByName().items()}
    added = {"tracks": 0, "vias": 0, "kept": 0, "bottom": 0}
    for name, d in session.items():
        ni = nets.get(name)
        if ni is None:
            print("  session net not on the board (skipped): %s" % name)
            continue
        mine = have.get(name, [])
        for layer, width, pts in d["wires"]:
            lid = F if layer == "F.Cu" else B
            for a, b in zip(pts, pts[1:]):
                if any(s[0] == layer and on_segment(a, s) and on_segment(b, s) for s in mine):
                    added["kept"] += 1
                    continue
                t = pcbnew.PCB_TRACK(board)
                t.SetStart(pcbnew.VECTOR2I(FM(a[0]), FM(a[1])))
                t.SetEnd(pcbnew.VECTOR2I(FM(b[0]), FM(b[1])))
                t.SetWidth(FM(width))
                t.SetLayer(lid)
                t.SetNet(ni)
                board.Add(t)
                added["tracks"] += 1
                added["bottom"] += lid == B
        for pad, x, y in d["vias"]:
            if any(math.hypot(x - vx, y - vy) < 0.05 for vx, vy in have_via):
                continue
            m = re.search(r"_(\d+):(\d+)_um", pad)
            dia, drill = (int(m.group(1)) / 1000.0, int(m.group(2)) / 1000.0) if m else (VIA_D, VIA_DRILL)
            v = pcbnew.PCB_VIA(board)
            v.SetPosition(pcbnew.VECTOR2I(FM(x), FM(y)))
            v.SetViaType(pcbnew.VIATYPE_THROUGH)
            v.SetLayerPair(F, B)
            v.SetDrill(FM(drill))
            v.SetWidth(F, FM(dia))
            v.SetNet(ni)
            board.Add(v)
            added["vias"] += 1
    pcbnew.SaveBoard(PCB, board)
    print("merge: %(tracks)d autorouted segments (%(bottom)d on the bottom layer) and %(vias)d vias added, "
          "%(kept)d hand-laid pieces left alone" % added)


def clean():
    """Remove the autorouter's dangling leftovers that the last DRC run reported (locked copper stays)."""
    with open(os.path.join(OUT, "drc.json"), encoding="utf-8") as f:
        rep = json.load(f)
    marks = []
    for v in rep.get("violations", []):
        if v["type"] not in ("track_dangling", "via_dangling"):
            continue
        i = v["items"][0]
        d = i["description"]
        m = re.search(r"on (F\.Cu|B\.Cu), length ([0-9.,]+) mm", d)
        marks.append((i["pos"]["x"], i["pos"]["y"], "via" if d.startswith("Via") else "track",
                      m.group(1) if m else None, float(m.group(2).replace(",", ".")) if m else None))
    board = pcbnew.LoadBoard(PCB)
    kill = []
    for t in list(board.GetTracks()):
        if t.IsLocked():
            continue
        is_via = t.GetClass() == "PCB_VIA"
        pts = [t.GetPosition()] if is_via else [t.GetStart(), t.GetEnd(), t.GetPosition()]
        for mx, my, kind, layer, length in marks:
            if (kind == "via") != is_via:
                continue
            if not any(abs(MM(q.x) - mx) < 0.02 and abs(MM(q.y) - my) < 0.02 for q in pts):
                continue
            if not is_via and (board.GetLayerName(t.GetLayer()) != layer or abs(MM(t.GetLength()) - length) > 0.02):
                continue
            kill.append(t)
            break
    for t in kill:
        board.Delete(t)
    pcbnew.SaveBoard(PCB, board)
    print("clean: %d dangling marks, removed %d autorouted tracks / vias" % (len(marks), len(kill)))


# ============================================================================ step: ground
def _obstacles(board, code):
    segs, vias, pads, yards = [], [], [], []
    for t in board.GetTracks():
        same = t.GetNetCode() == code
        if t.GetClass() == "PCB_VIA":
            vias.append((MM(t.GetPosition().x) - OX, MM(t.GetPosition().y) - OY, MM(t.GetWidth(F)) / 2, same))
        else:
            a, b = t.GetStart(), t.GetEnd()
            segs.append((MM(a.x) - OX, MM(a.y) - OY, MM(b.x) - OX, MM(b.y) - OY, MM(t.GetWidth()) / 2, same))
    for fp in board.GetFootprints():
        back = fp.GetLayer() == B
        cy = fp.GetCourtyard(B if back else F).BBox()
        if not back:
            yards.append((MM(cy.GetX()) - OX, MM(cy.GetY()) - OY, MM(cy.GetRight()) - OX, MM(cy.GetBottom()) - OY))
        for q in fp.Pads():
            bb = q.GetBoundingBox()
            box = (MM(bb.GetX()) - OX, MM(bb.GetY()) - OY, MM(bb.GetRight()) - OX, MM(bb.GetBottom()) - OY)
            pads.append(box + (q.GetNetCode() == code, q.GetAttribute() == pcbnew.PAD_ATTRIB_PTH))
    return segs, vias, pads, yards


def _seg_dist(x, y, sg):
    x1, y1, x2, y2 = sg[:4]
    dx, dy = x2 - x1, y2 - y1
    n2 = dx * dx + dy * dy
    t = 0.0 if n2 < 1e-12 else max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / n2))
    return math.hypot(x - (x1 + t * dx), y - (y1 + t * dy))


def _box_dist(x, y, bx):
    return math.hypot(max(bx[0] - x, 0, x - bx[2]), max(bx[1] - y, 0, y - bx[3]))


def _free(x, y, segs, vias, pads, pitch=1.2, r=VIA_R, c=0.25):
    """Room for a ground via of radius r at (x, y), c away from other copper? It goes through the board, so
    copper of both layers counts."""
    if not (1.0 <= x <= W - 1.0 and 1.0 <= y <= H - 1.0):
        return False
    if any(k[0] <= x <= k[2] and k[1] <= y <= k[3] for k in KEEP):
        return False
    for sg in segs:
        if not sg[5] and _seg_dist(x, y, sg) - sg[4] < r + c:
            return False
    for vx, vy, vr, same in vias:
        d = math.hypot(x - vx, y - vy)
        if d < pitch or (not same and d - vr < r + c + 0.05):
            return False
    for bx in pads:
        if _box_dist(x, y, bx) < r + (0.4 if bx[5] else c):       # not in or beside any pad
            return False
    return True


def ground():
    board = pcbnew.LoadBoard(PCB)
    gnd = find_net(board, "GND")
    r = Router(board)
    for z in list(board.Zones()):
        board.Delete(z)
    segs, vias, pads, yards = _obstacles(board, gnd.GetNetCode())
    P = lambda x, y: pcbnew.VECTOR2I(FM(x + OX), FM(y + OY))                    # noqa: E731
    grid = 0
    for i in range(int(W // 5.0)):                  # the stitching grid, 5 mm, over the whole width
        for j in range(9):
            x, y = 3.5 + 5.0 * i, 4.5 + 5.0 * j
            if any(c[0] - 0.3 <= x <= c[2] + 0.3 and c[1] - 0.3 <= y <= c[3] + 0.3 for c in yards):
                continue
            if _free(x, y, segs, vias, pads, pitch=2.0):
                r.via("GND", x, y, lock=False)
                vias.append((x, y, VIA_R, True))
                grid += 1
    zones = {}
    for layer, name in ((F, "GND top"), (B, "GND bottom")):
        z = pcbnew.ZONE(board)
        ls = pcbnew.LSET()
        ls.AddLayer(layer)
        z.SetLayerSet(ls)
        ol = z.Outline()
        ol.NewOutline()
        for x, y in ((0.3, 0.3), (W - 0.3, 0.3), (W - 0.3, H - 0.3), (0.3, H - 0.3)):
            ol.Append(FM(x + OX), FM(y + OY))
        z.SetNet(gnd)
        z.SetZoneName(name)
        z.SetAssignedPriority(0)
        z.SetMinThickness(FM(0.25))
        z.SetLocalClearance(FM(0.3))
        z.SetThermalReliefGap(FM(0.3))
        z.SetThermalReliefSpokeWidth(FM(0.4))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_NEVER)
        board.Add(z)
        zones[layer] = z
    filler = pcbnew.ZONE_FILLER(board)
    gnd_pts = {F: [], B: []}                        # points where ground copper of a layer holds a pour piece
    for fp in board.GetFootprints():
        for q in fp.Pads():
            if q.GetNetCode() == gnd.GetNetCode():
                c = q.GetPosition()
                for layer in (F, B):
                    if q.IsOnLayer(layer):
                        gnd_pts[layer].append((MM(c.x) - OX, MM(c.y) - OY))
    ring = [(math.cos(k * math.pi / 4) * (VIA_R + 0.05), math.sin(k * math.pi / 4) * (VIA_R + 0.05)) for k in range(8)]
    added, bare = 0, []
    for _round in range(4):
        filler.Fill(board.Zones())
        new, bare = 0, []
        for layer in (F, B):
            polys = zones[layer].GetFilledPolysList(layer)
            for i in range(polys.OutlineCount()):
                ol = polys.Outline(i)
                bb = ol.BBox()
                x0, y0, x1, y1 = MM(bb.GetX()) - OX, MM(bb.GetY()) - OY, MM(bb.GetRight()) - OX, MM(bb.GetBottom()) - OY
                inbox = lambda p: x0 <= p[0] <= x1 and y0 <= p[1] <= y1                      # noqa: E731
                if any(v[3] and inbox(v) and polys.Contains(P(v[0], v[1]), i) for v in vias):
                    continue
                if any(inbox(p) and polys.Contains(P(p[0], p[1]), i) for p in gnd_pts[layer]):
                    continue
                size = abs(ol.Area()) / 1e12
                spot = None
                # first a normal via well inside the piece, then anywhere in it, last a 0.6 mm via at the
                # smallest distances the design rules allow (the DRC run afterwards checks them)
                for step, vr, vc in ((0.25, VIA_R, 0.25), (0.1, VIA_R, 0.25), (0.05, 0.3, 0.21)):
                    yy = y0 + 0.2
                    while yy < y1 - 0.2 + 1e-6 and not spot:
                        xx = x0 + 0.2
                        while xx < x1 - 0.2 + 1e-6 and not spot:
                            if polys.Contains(P(xx, yy), i) and _free(xx, yy, segs, vias, pads, 0.9, vr, vc) and \
                                    (step < 0.2 or all(polys.Contains(P(xx + dx, yy + dy), i) for dx, dy in ring)):
                                spot = (xx, yy, vr)
                            xx += step
                        yy += step
                    if spot:
                        break
                if spot:
                    r.via("GND", spot[0], spot[1], 2 * spot[2], lock=False)
                    vias.append((spot[0], spot[1], spot[2], True))
                    new += 1
                else:
                    bare.append((size, board.GetLayerName(layer), x0, y0, x1, y1))
        added += new
        if not new:
            break
    area_never = {l: zones[l].GetFilledPolysList(l).Area() / 1e12 for l in (F, B)}
    for z in zones.values():
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    filler.Fill(board.Zones())
    area = {l: zones[l].GetFilledPolysList(l).Area() / 1e12 for l in (F, B)}
    pcbnew.SaveBoard(PCB, board)
    print("ground: %d stitching vias on the grid, %d more to tie pour pieces" % (grid, added))
    print("pour area: top %.0f mm2, bottom %.0f mm2; dropped as islands: top %.1f mm2, bottom %.1f mm2"
          % (area[F], area[B], area_never[F] - area[F], area_never[B] - area[B]))
    bare.sort(reverse=True)
    print("pieces without room for a via: %d, %.1f mm2 together" % (len(bare), sum(b[0] for b in bare)))
    for size, layer, x0, y0, x1, y1 in bare[:12]:
        print("   %.2f mm2  %s  x %.1f..%.1f  y %.1f..%.1f" % (size, layer, x0, x1, y0, y1))


# ============================================================================ step: silk
def _text(board, text, x, y, hgt, ang=0, layer=pcbnew.F_SilkS, just=pcbnew.GR_TEXT_H_ALIGN_CENTER):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(text)
    t.SetLayer(layer)
    t.SetPosition(V(x, y))
    t.SetTextSize(pcbnew.VECTOR2I(FM(hgt), FM(hgt)))
    t.SetTextThickness(FM(max(0.15, hgt * 0.15)))
    t.SetHorizJustify(just)
    t.SetTextAngleDegrees(ang)
    if layer == pcbnew.B_SilkS:
        t.SetMirrored(True)
    board.Add(t)
    return t


def _ink(t):
    """The box around a text's ink (strokes with their width): (x0, y0, x1, y1) in board mm."""
    ps = pcbnew.SHAPE_POLY_SET()
    t.TransformTextToPolySet(ps, 0, FM(0.005), pcbnew.ERROR_INSIDE)
    bb = ps.BBox()
    return MM(bb.GetX()) - OX, MM(bb.GetY()) - OY, MM(bb.GetRight()) - OX, MM(bb.GetBottom()) - OY


def _move_ink(t, x=None, y=None, left=None, top=None, bottom=None):
    """Move a text so that its ink box is centred on x / y, or starts at left / top, or ends at bottom."""
    x0, y0, x1, y1 = _ink(t)
    dx = x - (x0 + x1) / 2 if x is not None else (left - x0 if left is not None else 0.0)
    dy = y - (y0 + y1) / 2 if y is not None else (top - y0 if top is not None else (bottom - y1 if bottom is not None else 0.0))
    p = t.GetPosition()
    t.SetPosition(pcbnew.VECTOR2I(p.x + FM(dx), p.y + FM(dy)))
    return _ink(t)


def _back_clash(box, board, gap=0.1):
    """What a text box on the back would touch: a via (all of them go through the board) or a back pad."""
    x0, y0, x1, y1 = box
    for t in board.GetTracks():
        if t.GetClass() == "PCB_VIA":
            hx, hy, r = MM(t.GetPosition().x) - OX, MM(t.GetPosition().y) - OY, MM(t.GetWidth(F)) / 2
            if math.hypot(max(x0 - hx, 0, hx - x1), max(y0 - hy, 0, hy - y1)) < r + gap:
                return "via at (%.2f, %.2f)" % (hx, hy)
    for fp in board.GetFootprints():
        for q in fp.Pads():
            if q.IsOnLayer(B):
                bb = q.GetBoundingBox()
                b = (MM(bb.GetX()) - OX, MM(bb.GetY()) - OY, MM(bb.GetRight()) - OX, MM(bb.GetBottom()) - OY)
                if not (x1 + gap < b[0] or b[2] < x0 - gap or y1 + gap < b[1] or b[3] < y0 - gap):
                    return "pad %s.%s" % (fp.GetReference(), q.GetNumber())
    return None


def _pad_box(board, ref):
    bb = [fp for fp in board.GetFootprints() if fp.GetReference() == ref][0].Pads()[0].GetBoundingBox()
    return MM(bb.GetX()) - OX, MM(bb.GetY()) - OY, MM(bb.GetRight()) - OX, MM(bb.GetBottom()) - OY


def silk_back(board):
    """Back silkscreen. The battery signs sit under their own pads, by the board edge. Until 2026-11-15 they sat
    between J1 and the battery pads, right under J1's GND and VDD holes, where they could be read as J1's: battery
    wires soldered into J1 by them would put a reversed supply straight on VDD (fourth check). J1's pin names go
    above its holes, away from the battery pads."""
    placed = []
    plus, minus = _pad_box(board, "TP1"), _pad_box(board, "TP2")
    t = _text(board, "+", 0.0, 0.0, 1.5, layer=pcbnew.B_SilkS)
    box = _move_ink(t, x=(plus[0] + plus[2]) / 2, top=plus[3] + 0.6)
    yc = (box[1] + box[3]) / 2
    placed.append(("+", box))
    t = _text(board, "-", 0.0, 0.0, 1.5, layer=pcbnew.B_SilkS)
    placed.append(("-", _move_ink(t, x=(minus[0] + minus[2]) / 2, y=yc)))
    # not 5.5 V, the chip's own limit: a full row would then draw about 100 mA through the chip's supply pin
    t = _text(board, "4.5 V, max 5 V", 0.0, 0.0, 1.0, layer=pcbnew.B_SilkS)
    placed.append(("4.5 V, max 5 V", _move_ink(t, left=plus[2] + 1.6, y=yc)))
    for k, name in enumerate(J1_NAME):
        px = J1[0] + 2.54 * k
        t = _text(board, name, 0.0, 0.0, 1.0, ang=90, layer=pcbnew.B_SilkS)
        for dx in (0.0, -0.2, 0.2, -0.4, 0.4, -0.6, 0.6, -0.7, 0.7):  # stay over the 1.7 mm pad
            box = _move_ink(t, x=px + dx, bottom=J1[1] - 0.85 - 0.3)
            if not _back_clash(box, board):
                break
        else:
            raise RuntimeError("no room on the back for the J1 name " + name)
        placed.append((name, box))
    for name, box in placed:
        why = _back_clash(box, board)
        if why or box[0] < 0.4 or box[1] < 0.4 or box[2] > W - 0.4 or box[3] > H - 0.4:
            raise RuntimeError("back text %r at %s touches %s" % (name, box, why or "the board edge"))
    return placed


def silk():
    board = pcbnew.LoadBoard(PCB)
    for d in list(board.GetDrawings()):
        if d.GetLayer() in (pcbnew.F_SilkS, pcbnew.B_SilkS):
            board.Delete(d)
    for name, y in zip(SW_NAME, SW_Y):
        _text(board, name, SW_X, y - 4.0, 1.0)
    for k, name in enumerate(J1_NAME):
        _text(board, name, J1[0] + 2.54 * k, J1[1] + 1.5, 1.0, ang=90, just=pcbnew.GR_TEXT_H_ALIGN_RIGHT)
    _text(board, "JP1", 75.0, 43.9, 1.0)
    for name, box in silk_back(board):
        print("silk back: %-15r ink x %.2f..%.2f  y %.2f..%.2f" % ((name,) + (box[0], box[2], box[1], box[3])))
    name, sign, xr, yc, h1, h2 = SILK_MARK
    ys = yc - h1 / 2 + h2 / 2                            # the sign's top is level with the name's top
    a = _text(board, name, 0.0, yc, h1, just=pcbnew.GR_TEXT_H_ALIGN_LEFT)
    b = _text(board, sign, 0.0, ys, h2, just=pcbnew.GR_TEXT_H_ALIGN_LEFT)
    wa, wb = MM(a.GetBoundingBox().GetWidth()), MM(b.GetBoundingBox().GetWidth())
    b.SetPosition(V(xr - wb, ys))
    a.SetPosition(V(xr - wb - 0.3 - wa, yc))
    pcbnew.SaveBoard(PCB, board)
    print("silk: mark from x %.1f to %.1f (name %.1f mm wide, sign %.1f mm)" % (xr - wb - 0.3 - wa, xr, wa, wb))


# ============================================================================ step: drc
def drc(show=()):
    out = os.path.join(OUT, "drc.json")
    subprocess.run([CLI, "pcb", "drc", "--format", "json", "--severity-all", "--schematic-parity", "-o", out, PCB],
                   capture_output=True)
    with open(out, encoding="utf-8") as f:
        rep = json.load(f)
    counts = {}
    for v in rep.get("violations", []):
        counts[(v["severity"], v["type"])] = counts.get((v["severity"], v["type"]), 0) + 1
    for k, n in sorted(counts.items()):
        print("DRC %-8s %-34s %d" % (k[0], k[1], n))
    print("violations: %d | unconnected items: %d | schematic parity: %d" % (
        len(rep.get("violations", [])), len(rep.get("unconnected_items", [])), len(rep.get("schematic_parity", []))))
    missing = class_patterns_saved()
    if missing:
        print("WARNING: net-class patterns missing from the project file: %s" % missing)
    for v in rep.get("schematic_parity", [])[:12]:
        print("  PARITY %s: %s" % (v["type"], "; ".join(i.get("description", "") for i in v.get("items", []))[:200]))
    n = 0
    for v in rep.get("violations", []):
        if (v["type"] in show or "all" in show) and n < 40:
            n += 1
            pos = v.get("items", [{}])[0].get("pos", {})
            print("  %-22s (%.2f, %.2f) %s" % (v["type"], pos.get("x", 0) - OX, pos.get("y", 0) - OY,
                                               "; ".join(i.get("description", "") for i in v.get("items", []))[:220]))
    if "unconnected" in show or "all" in show:
        for v in rep.get("unconnected_items", [])[:40]:
            pos = v.get("items", [{}])[0].get("pos", {})
            print("  unconnected (%.2f, %.2f) %s" % (pos.get("x", 0) - OX, pos.get("y", 0) - OY,
                                                     "; ".join(i.get("description", "") for i in v.get("items", []))[:220]))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    code = 0
    try:
        steps = {"place": place, "hand": hand, "merge": merge, "clean": clean, "ground": ground, "silk": silk, "widen": widen}
        if cmd in steps:
            steps[cmd]()
        elif cmd == "auto":
            code = auto(float(sys.argv[2]) if len(sys.argv) > 2 else 6)
        elif cmd == "drc":
            drc(sys.argv[2:])
        else:
            print(__doc__)
    except Exception:
        import traceback
        traceback.print_exc()
        code = 1
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(code)
