import json, colorsys, sys
PRINT = False
d = json.load(open("premium_gift.json"))
d["layers"] = [l for l in d["layers"] if l["nm"] not in ("STAR", "Gold")]

def tone(rgb, kind):
    h, l, s = colorsys.rgb_to_hls(*rgb)
    deg = h * 360
    if 180 <= deg <= 240 and s > .2:                       # the blue box -> deep navy
        if kind == "st": nl, ns = .1, .4                    # outlines go near-black navy
        elif PRINT: return (.95, .96, 1)                    # the starry print is white, like Wallet's
        elif l > .78: nl, ns = .5, .3                       # rim highlights: a soft slate
        else: nl, ns = .12 + l * .3, .34
        return colorsys.hls_to_rgb(225 / 360, nl, ns)
    if 20 <= deg <= 65 and s > .3:                          # the yellow ribbon -> satin orange
        nh = (deg * .45 + 8) / 360
        nl = min(.86, l * .85 + .13) if kind != "st" else l * .55
        return colorsys.hls_to_rgb(nh, nl, min(.82, s * .82))
    return rgb

def walk(o, kind=None):
    if isinstance(o, dict):
        ty = o.get("ty")
        if ty in ("fl", "st") and "c" in o:
            k = o["c"].get("k")
            if isinstance(k, list) and k and not isinstance(k[0], dict):
                o["c"]["k"] = list(tone(k[:3], ty)) + k[3:]
        if ty in ("gf", "gs") and "g" in o:
            p, k = o["g"]["p"], o["g"]["k"].get("k")
            if isinstance(k, list) and k and not isinstance(k[0], dict):
                for i in range(p):
                    k[i*4+1:i*4+4] = list(tone(k[i*4+1:i*4+4], ty))
        for v in o.values(): walk(v)
    elif isinstance(o, list):
        for v in o: walk(v)

for l in d["layers"]:
    if l["nm"].startswith("conf"): continue
    PRINT = l["nm"] in ("Layer 10", "Layer 11", "Layer 12", "Layer 23", "Layer 24")
    if PRINT: l.setdefault("ks", {})["o"] = {"a": 0, "k": 48}
    walk(l)
for l in d["layers"]:
    if l["nm"] == "B0":                                      # Wallet's bow is much bigger than the box lid
        l["ks"]["s"] = {"a": 0, "k": [158, 158, 100]}; l["ks"]["p"]["k"][1] -= 6
json.dump(d, open("gift_wallet.json", "w"), separators=(",", ":"))
print("ok", len(d["layers"]))
