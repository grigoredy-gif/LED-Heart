"""netlist.py - reads a KiCad netlist (.net): parts with their fields, and nets with their (ref, pin) nodes."""
from kisch import parse


def short(net):
    return net.split("/")[-1]


def read_netlist(path):
    with open(path, encoding="utf-8") as f:
        root = parse(f.read())[0]
    comps, nets = {}, {}

    def kid(node, key):
        for e in node:
            if isinstance(e, list) and e and e[0] == key:
                return e
        return None

    for sec in root:
        if not (isinstance(sec, list) and sec):
            continue
        if sec[0] == "components":
            for c in sec[1:]:
                ref = str(kid(c, "ref")[1])
                fields = {}
                fl = kid(c, "fields")
                for fld in (fl[1:] if fl else []):
                    val = [str(x) for x in fld[1:] if not isinstance(x, list)]
                    fields[str(kid(fld, "name")[1])] = val[0] if val else ""
                props = {}
                for e in c:
                    if isinstance(e, list) and e and e[0] == "property":
                        vv = kid(e, "value")
                        props[str(kid(e, "name")[1])] = str(vv[1]) if vv else ""
                sp = kid(c, "sheetpath")
                tst = str(kid(sp, "tstamps")[1]) if sp else "/"
                comps[ref] = dict(value=str(kid(c, "value")[1]), footprint=str(kid(c, "footprint")[1]),
                                  fields=fields, props=props, path=tst + str(kid(c, "tstamps")[1]),
                                  sheetname=props.get("Sheetname", ""), sheetfile=props.get("Sheetfile", ""))
        elif sec[0] == "nets":
            for n in sec[1:]:
                nets[str(kid(n, "name")[1])] = [(str(kid(e, "ref")[1]), str(kid(e, "pin")[1]))
                                                for e in n if isinstance(e, list) and e and e[0] == "node"]
    return comps, nets
