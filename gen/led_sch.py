"""
led_sch.py - writes the schematic of the LED heart board (KiCad 10), then runs ERC and exports netlist and PDF.

Run: <KiCad 10>/bin/python.exe led_sch.py        (KiCad closed)
Every pin gets a stub with a net label (kisch.py), so the connections are made by net name.
The circuit is the one in ../README.md; the free pin choices are in pins.py.
"""
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kisch  # noqa: E402
from pins import COLPIN, PINNAME, ROWOUT  # noqa: E402

OUT = os.path.dirname(HERE)
NAME = "led_heart"
CLI = os.path.join(kisch.KICAD, "bin", "kicad-cli.exe")
POWER = ("GND",)
PRETTY = os.path.join(OUT, "led_heart.pretty")

FP = {"led": "LED_SMD:LED_0603_1608Metric", "r": "Resistor_SMD:R_0603_1608Metric",
      "c": "Capacitor_SMD:C_0603_1608Metric", "q": "Package_TO_SOT_SMD:SOT-23",
      "u1": "Package_SO:TSSOP-20_4.4x6.5mm_P0.65mm", "u2": "Package_SO:SOIC-16_3.9x9.9mm_P1.27mm",
      "d": "Diode_SMD:D_SMA", "sw": "led_heart:SW_TS-1187A", "bat": "led_heart:BatPad_4x6",
      "j": "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical",
      "jp": "Jumper:SolderJumper-2_P1.3mm_Bridged_Pad1.0x1.5mm"}


def jlc(num):
    return {"LCSC": num, "Assembly": "JLCPCB"}


FONT = '(effects (font (size 1 1) (thickness 0.15)))'


def footprints():
    """Two project footprints: the tact switch TS-1187A (pads as in JLCPCB's footprint of C318884) and the
    4 x 6 mm battery pad."""
    os.makedirs(PRETTY, exist_ok=True)
    pads = "".join('\t(pad "%s" smd rect (at %g %g) (size 1 0.75) (layers "F.Cu" "F.Mask" "F.Paste"))\n' % p
                   for p in (("1", -3, -1.85), ("2", 3, -1.85), ("3", -3, 1.85), ("4", 3, 1.85)))
    sw = ('(footprint "SW_TS-1187A"\n\t(version 20241229)\n\t(generator "led_sch")\n\t(layer "F.Cu")\n'
          '\t(descr "Tact switch TS-1187A, 5.1 x 5.1 mm, LCSC C318884. Pads 1+2 are joined inside, pads 3+4 are joined inside.")\n'
          '\t(property "Reference" "REF**" (at 0 -3.5 0) (layer "F.SilkS") %s)\n'
          '\t(property "Value" "SW_TS-1187A" (at 0 3.5 0) (layer "F.Fab") %s)\n\t(attr smd)\n'
          '\t(fp_rect (start -2.55 -2.55) (end 2.55 2.55) (stroke (width 0.1) (type solid)) (fill no) (layer "F.Fab"))\n'
          '\t(fp_circle (center 0 0) (end 1.5 0) (stroke (width 0.1) (type solid)) (fill no) (layer "F.Fab"))\n'
          '\t(fp_rect (start -3.75 -2.8) (end 3.75 2.8) (stroke (width 0.05) (type solid)) (fill no) (layer "F.CrtYd"))\n'
          '\t(fp_line (start -2.55 -2.7) (end 2.55 -2.7) (stroke (width 0.12) (type solid)) (layer "F.SilkS"))\n'
          '\t(fp_line (start -2.55 2.7) (end 2.55 2.7) (stroke (width 0.12) (type solid)) (layer "F.SilkS"))\n'
          '\t(fp_line (start -2.7 -1.1) (end -2.7 1.1) (stroke (width 0.12) (type solid)) (layer "F.SilkS"))\n'
          '\t(fp_line (start 2.7 -1.1) (end 2.7 1.1) (stroke (width 0.12) (type solid)) (layer "F.SilkS"))\n'
          '%s)\n' % (FONT, FONT, pads))
    bat = ('(footprint "BatPad_4x6"\n\t(version 20241229)\n\t(generator "led_sch")\n\t(layer "F.Cu")\n'
           '\t(descr "Solder pad 4 x 6 mm for a battery wire")\n'
           '\t(property "Reference" "REF**" (at 0 -4 0) (layer "F.SilkS") %s)\n'
           '\t(property "Value" "BatPad_4x6" (at 0 4 0) (layer "F.Fab") %s)\n'
           '\t(attr smd exclude_from_pos_files exclude_from_bom)\n'
           '\t(fp_rect (start -2.25 -3.25) (end 2.25 3.25) (stroke (width 0.05) (type solid)) (fill no) (layer "F.CrtYd"))\n'
           '\t(pad "1" smd roundrect (at 0 0) (size 4 6) (layers "F.Cu" "F.Mask") (roundrect_rratio 0.1))\n)\n' % (FONT, FONT))
    for name, text in (("SW_TS-1187A", sw), ("BatPad_4x6", bat)):
        with open(os.path.join(PRETTY, name + ".kicad_mod"), "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    with open(os.path.join(OUT, "fp-lib-table"), "w", encoding="utf-8", newline="\n") as f:
        f.write('(fp_lib_table\n  (version 7)\n  (lib (name "led_heart")(type "KiCad")(uri "${KIPRJMOD}/led_heart.pretty")'
                '(options "")(descr "LED heart board: project footprints"))\n)\n')
    kisch.FPLIBS["led_heart"] = PRETTY


def cli(*args):
    r = subprocess.run([CLI] + list(args), capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout[-600:], r.stderr[-600:])
        raise SystemExit("kicad-cli failed: " + " ".join(args[:3]))


def build(paper, width):
    kisch.ROOT_TITLE = "LED heart: 9 x 8 LED matrix, STM8S003, 74HC595"
    kisch.REV = "1"
    kisch.SHOW = ()
    P = kisch.Project(NAME, OUT)
    s = P.root
    s.paper = paper
    s.start_layout(width=width)
    A = lambda *a, **k: s.auto(*a, power=POWER, **k)                                     # noqa: E731

    s.block("Power", ["Battery wires on the two pads on the back: 3 x AAA or AA (4.5 V), 5 V USB or one Li-ion cell. Not 12 V.",
                      "D1 protects against swapped wires. JP1 is bridged by a trace: cut it and wire a switch across its pads to add a hard switch."])
    A("TP1", "Connector:TestPoint", "BAT+", {"1": "VBAT"}, FP["bat"])
    A("TP2", "Connector:TestPoint", "BAT-", {"1": "GND"}, FP["bat"])
    A("D1", "Device:D_Schottky", "SS14", {"2": "VBAT", "1": "VIN"}, FP["d"], jlc("C2480"))
    A("C4", "Device:C", "1u", {"1": "VIN", "2": "GND"}, FP["c"], jlc("C15849"))
    A("JP1", "Jumper:SolderJumper_2_Bridged", "bridged", {"1": "VIN", "2": "VDD"}, FP["jp"])
    s.auto_flag("VDD", power=POWER)
    s.auto_flag("GND", power=POWER)

    s.block("Microcontroller and shift register",
            ["U1 drives the 9 columns (high = on) through 270 ohm. U2 selects the row: output high = row on. Its two clocks are tied together,",
             "so the outputs lag the shift register by one clock. J1 (not fitted): VDD, SWIM, GND, NRST for the ST-Link."])
    u1 = {2: "SER", 3: "SCK", 4: "NRST", 5: "SW1", 6: "SW2", 7: "GND", 8: "VCAP", 9: "VDD", 11: "SW5", 12: "SW4", 18: "SWIM"}
    for c, pin in COLPIN.items():
        u1[pin] = "DRV%d" % c
    A("U1", "MCU_ST_STM8:STM8S003F3P", "STM8S003F3P6TR", u1, FP["u1"], jlc("C52717"))
    A("C1", "Device:C", "1u", {"1": "VDD", "2": "GND"}, FP["c"], jlc("C15849"))
    A("C2", "Device:C", "1u", {"1": "VCAP", "2": "GND"}, FP["c"], jlc("C15849"))
    u2 = {14: "SER", 11: "SCK", 12: "SCK", 13: "GND", 10: "VDD", 16: "VDD", 8: "GND", 9: None}
    for r, pin in ROWOUT.items():
        u2[pin] = "SR%d" % r
    A("U2", "74xx:74HC595", "74HC595D", u2, FP["u2"], jlc("C5947"))
    A("C3", "Device:C", "1u", {"1": "VDD", "2": "GND"}, FP["c"], jlc("C15849"))
    A("J1", "Connector_Generic:Conn_01x04", "SWIM", {1: "VDD", 2: "SWIM", 3: "GND", 4: "NRST"}, FP["j"], dnp=True)

    s.block("Column resistors: about 6.5 mA peak per LED at 4.5 V")
    for c in range(1, 10):
        A("R%d" % c, "Device:R", "270", {"1": "DRV%d" % c, "2": "COL%d" % c}, FP["r"], jlc("C22966"))

    s.block("Row switches: S8050 (SOT-23: 1 base, 2 emitter, 3 collector), 1 k base resistors")
    for r in range(1, 9):
        A("R%d" % (9 + r), "Device:R", "1k", {"1": "SR%d" % r, "2": "B%d" % r}, FP["r"], jlc("C21190"))
        A("Q%d" % r, "Transistor_BJT:MMBT3904", "S8050", {"1": "B%d" % r, "2": "GND", "3": "ROW%d" % r}, FP["q"], jlc("C2146"))

    s.block("Buttons: pads 1 + 2 are joined inside the switch, pads 3 + 4 are joined; pressing connects the two pairs. Pad 2 is left free.",
            ["SW1 mode, SW2 speed, SW3 dimmer (shares PD1 with SWIM), SW4 brighter, SW5 on/off: it wakes the chip from halt.",
             "On/off is not on SW1: PA1 cannot wake the chip from halt (ST data sheet, table 6, note 2).",
             "PB4 and PB5 are true open-drain pins without an internal pull-up: R18 and R19."])
    for k, net in ((1, "SW1"), (2, "SW2"), (3, "SWIM"), (4, "SW4"), (5, "SW5")):
        A("SW%d" % k, "Switch:SW_Push_Dual", "TS-1187A", {"1": net, "2": None, "3": "GND", "4": "GND"}, FP["sw"], jlc("C318884"))
    A("R18", "Device:R", "1k", {"1": "VDD", "2": "SW4"}, FP["r"], jlc("C21190"))
    A("R19", "Device:R", "1k", {"1": "VDD", "2": "SW5"}, FP["r"], jlc("C21190"))

    s.block("LED matrix: LED n = 9 x (row - 1) + column; anode (pin 2) to COL, cathode (pin 1) to ROW",
            ["Red 0603, KT-0603R. JLCPCB's footprint numbers the pads the other way round (pad 1 = anode): the placement file allows for it.",
             "Drawn as on the board: 8 rows of 9, row 1 at the top, column 1 at the left."])
    s.page_w = 375.0                                     # nine LEDs fit on one line of the drawing
    for r in range(1, 9):
        for c in range(1, 10):
            A("LED%d" % (9 * (r - 1) + c), "Device:LED", "red", {"2": "COL%d" % c, "1": "ROW%d" % r}, FP["led"], jlc("C2286"))
    return P, s


def main():
    footprints()
    P, s = build("A1", 800.0)
    if s.max_y > 560:
        raise SystemExit("the schematic does not fit on the sheet: used height %.0f mm" % s.max_y)
    print("sheet %s, used height %.0f mm, %d symbols" % (s.paper, s.max_y, len(s.parts)))
    P.write()
    pro = os.path.join(OUT, NAME + ".kicad_pro")
    if not os.path.exists(pro):
        shutil.copy(os.path.join(kisch.KICAD, "share", "kicad", "template", "kicad.kicad_pro"), pro)
    sch = os.path.join(OUT, NAME + ".kicad_sch")
    erc = os.path.join(OUT, "erc.json")
    cli("sch", "erc", "--format", "json", "--severity-all", "-o", erc, sch)
    cli("sch", "export", "netlist", "-o", os.path.join(OUT, NAME + ".net"), sch)
    cli("sch", "export", "pdf", "-o", os.path.join(OUT, NAME + ".pdf"), sch)
    with open(erc, encoding="utf-8") as f:
        rep = json.load(f)
    count, example = {}, {}
    for sh in rep.get("sheets", []):
        for v in sh.get("violations", []):
            k = (v.get("severity", "?"), v.get("type", "?"))
            count[k] = count.get(k, 0) + 1
            example.setdefault(k, "%s | %s" % (v.get("description", ""),
                                               "; ".join(x.get("description", "") for x in v.get("items", []))))
    for k in sorted(count):
        print("ERC %-8s %-26s x%-3d e.g. %s" % (k[0], k[1], count[k], example[k][:230]))
    print("ERC: %d errors, %d warnings" % (sum(c for k, c in count.items() if k[0] == "error"),
                                           sum(c for k, c in count.items() if k[0] == "warning")))


if __name__ == "__main__":
    main()
