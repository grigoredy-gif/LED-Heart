"""
led_box.py - an open box for the LED heart board: the board sits in a pocket at the
top, flush with the rim, screwed onto four corner posts; the 3 x AA holder lies under it. Writes enclosure/led_heart_box.stl (mm).

Plain Python, no libraries. The box is a height field (every point of the floor plan
has solid from z = 0 up to some height), meshed on a grid that is fine only around
the screw holes, and the script checks that the mesh is closed before writing it.

Board (led_heart.kicad_pcb): 85 x 50 mm, M3 holes 2.75 mm in from each edge.
Outside about 89.6 x 54.6 x 25.1 mm.
"""
import math
import os
import struct

PCB_L, PCB_W, PCB_T = 85.0, 50.0, 1.6   # the board
CLR = 0.3                  # gap around the board in its pocket
WALL = 2.0                 # wall thickness
FLOOR = 2.0                # floor thickness
BELOW = 21.5               # under the board: the holder glued to its back (board + holder = 23 mm, Edy) rests on the floor
L = PCB_L + 2 * (CLR + WALL)   # outside: wider than the board, the board sits inside the walls
W = PCB_W + 2 * (CLR + WALL)
POST = FLOOR + BELOW       # top of the corner posts = underside of the board
H = POST + PCB_T           # rim flush with the top of the board
OX, OY = WALL + CLR, WALL + CLR  # board corner in box coordinates
BLOCK = 4.3                # corner posts reach 4.3 mm in from the board edges: the holder starts just past the screw holes
HOLE_R = 1.3               # 2.6 mm pilot hole: an M3 screw cuts its own thread in PLA/PETG
HOLE_DEPTH = 12.0
HOLES = [(OX + 2.75, OY + 2.75), (OX + PCB_L - 2.75, OY + 2.75),
         (OX + 2.75, OY + PCB_W - 2.75), (OX + PCB_L - 2.75, OY + PCB_W - 2.75)]
STEP = 0.2                 # grid step around the holes

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "enclosure", "led_heart_box.stl")


def axis(size, feats, centres):
    v = {0.0, size} | set(feats)
    for c in centres:
        n = int(round(1.8 / STEP))
        for k in range(-n, n + 1):
            v.add(round(c + k * STEP, 4))
    return sorted(x for x in v if 0.0 <= x <= size)


xs = axis(L, [WALL, OX + BLOCK, L - OX - BLOCK, L - WALL], [h[0] for h in HOLES[:2]])
ys = axis(W, [WALL, OY + BLOCK, W - OY - BLOCK, W - WALL], [HOLES[0][1], HOLES[2][1]])


def height(cx, cy):
    if cx < WALL or cx > L - WALL or cy < WALL or cy > W - WALL:
        return H                                   # wall
    for hx, hy in HOLES:
        if (cx - hx) ** 2 + (cy - hy) ** 2 < HOLE_R ** 2:
            return POST - HOLE_DEPTH               # screw hole
    if (cx < OX + BLOCK or cx > L - OX - BLOCK) and (cy < OY + BLOCK or cy > W - OY - BLOCK):
        return POST                                # corner post, the board rests on it
    return FLOOR


NX, NY = len(xs) - 1, len(ys) - 1
h = [[height((xs[i] + xs[i + 1]) / 2, (ys[j] + ys[j + 1]) / 2) for j in range(NY)] for i in range(NX)]


def cell_h(i, j):
    return h[i][j] if 0 <= i < NX and 0 <= j < NY else 0.0


# all heights that meet at each grid node (so the side walls get a vertex there)
node_z = {}
for i in range(NX + 1):
    for j in range(NY + 1):
        node_z[(i, j)] = sorted({0.0} | {cell_h(a, b) for a in (i - 1, i) for b in (j - 1, j)})

tris = []


def quad(a, b, c, d):  # counter-clockwise seen from outside
    tris.append((a, b, c))
    tris.append((a, c, d))


def side(n1, n2, lo, hi):
    """Vertical face from node n1 to node n2 between lo and hi, outside on the right
    of n1 -> n2 seen from above; split at every height found at the two nodes."""
    p1 = (xs[n1[0]], ys[n1[1]])
    p2 = (xs[n2[0]], ys[n2[1]])
    z1 = [z for z in node_z[n1] if lo <= z <= hi]
    z2 = [z for z in node_z[n2] if lo <= z <= hi]
    # ladder between the two vertical chains
    a, b = 0, 0
    while a < len(z1) - 1 or b < len(z2) - 1:
        if b < len(z2) - 1 and (a == len(z1) - 1 or z2[b + 1] <= z1[a + 1]):
            tris.append(((*p1, z1[a]), (*p2, z2[b]), (*p2, z2[b + 1])))
            b += 1
        else:
            tris.append(((*p1, z1[a]), (*p2, z2[b]), (*p1, z1[a + 1])))
            a += 1


for i in range(NX):
    for j in range(NY):
        x0, x1, y0, y1, z = xs[i], xs[i + 1], ys[j], ys[j + 1], h[i][j]
        quad((x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z))      # top
        quad((x0, y0, 0), (x0, y1, 0), (x1, y1, 0), (x1, y0, 0))      # bottom

# walls between cells (and to the outside) along x = const lines
for i in range(NX + 1):
    for j in range(NY):
        left, right = cell_h(i - 1, j), cell_h(i, j)
        if left > right:   # face looks towards +x
            side((i, j), (i, j + 1), right, left)
        elif right > left:  # face looks towards -x
            side((i, j + 1), (i, j), left, right)
# along y = const lines
for j in range(NY + 1):
    for i in range(NX):
        below, above = cell_h(i, j - 1), cell_h(i, j)
        if below > above:  # face looks towards +y
            side((i + 1, j), (i, j), above, below)
        elif above > below:  # face looks towards -y
            side((i, j), (i + 1, j), below, above)


def check():
    """Closed and consistently oriented: every directed edge has exactly one opposite."""
    edges = {}
    for t in tris:
        for k in range(3):
            e = (t[k], t[(k + 1) % 3])
            edges[e] = edges.get(e, 0) + 1
    bad = [e for e, n in edges.items() if n != 1 or edges.get((e[1], e[0]), 0) != 1]
    vol = 0.0
    for a, b, c in tris:
        vol += (a[0] * (b[1] * c[2] - b[2] * c[1]) - a[1] * (b[0] * c[2] - b[2] * c[0])
                + a[2] * (b[0] * c[1] - b[1] * c[0])) / 6.0
    return bad, vol


def normal(a, b, c):
    u = [b[k] - a[k] for k in range(3)]
    v = [c[k] - a[k] for k in range(3)]
    n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
    m = math.sqrt(sum(q * q for q in n)) or 1.0
    return tuple(q / m for q in n)


if __name__ == "__main__":
    bad, vol = check()
    inner = (L - 2 * WALL) * (W - 2 * WALL)
    post_area = 4 * (BLOCK + CLR) ** 2
    expect = (L * W * FLOOR + (L * W - inner) * (H - FLOOR) + post_area * (POST - FLOOR)
              - 4 * math.pi * HOLE_R ** 2 * HOLE_DEPTH)
    print(f"{len(tris)} triangles, open or doubled edges: {len(bad)}, "
          f"volume {vol:.0f} mm3 (about {expect:.0f} expected)")
    if bad:
        raise SystemExit("mesh not closed, nothing written")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "wb") as f:
        f.write(b"LED heart box".ljust(80, b" "))
        f.write(struct.pack("<I", len(tris)))
        for a, b, c in tris:
            f.write(struct.pack("<12fH", *normal(a, b, c), *a, *b, *c, 0))
    print("written", os.path.normpath(OUT))
