"""Build data.json for the Kennywood app from OSM (all.json) and the official map PDF (bbox.html).

Coordinates are local meters: x east, z south (three.js convention), origin LAT0/LON0.
Official-map markers are georeferenced by a least-squares affine fit against OSM-located
rides, then rubber-sheeted with inverse-distance-weighted residuals of nearby controls.
"""
import json, math, re, sys, heapq
from collections import defaultdict

OSM, BBOX, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
LAT0, LON0 = 40.38775, -79.8634
MLAT = 111132.0
MLON = 111320.0 * math.cos(math.radians(LAT0))


def xz(lat, lon):
    return ((lon - LON0) * MLON, -(lat - LAT0) * MLAT)


els = json.load(open(OSM))["elements"]
ways = [e for e in els if e["type"] == "way" and "geometry" in e]
nodes = [e for e in els if e["type"] == "node"]


def poly(e):
    return [xz(p["lat"], p["lon"]) for p in e["geometry"]]


def centroid(pts):
    if len(pts) > 2 and pts[0] == pts[-1]:
        a = cx = cz = 0.0
        for (x1, z1), (x2, z2) in zip(pts, pts[1:]):
            c = x1 * z2 - x2 * z1
            a += c; cx += (x1 + x2) * c; cz += (z1 + z2) * c
        if abs(a) > 1e-6:
            return (cx / (3 * a), cz / (3 * a))
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))


park = next(e for e in ways if e["id"] == 237755727)
PARK = poly(park)


def inside(pt, pg=PARK):
    x, z = pt; c = False
    for (x1, z1), (x2, z2) in zip(pg, pg[1:] + pg[:1]):
        if (z1 > z) != (z2 > z) and x < (x2 - x1) * (z - z1) / (z2 - z1) + x1:
            c = not c
    return c


def near_park(pt, m=60):
    if inside(pt):
        return True
    return min(math.dist(pt, p) for p in PARK) < m

# ---------- OSM named features ----------
osm_named = defaultdict(list)  # name -> [(kind, (x,z))]
for e in ways:
    t = e.get("tags", {})
    if "name" in t:
        kind = "station" if t.get("roller_coaster") == "station" else ("track" if t.get("roller_coaster") == "track" else "feat")
        if kind != "track":
            osm_named[t["name"]].append((kind, centroid(poly(e))))
for e in nodes:
    t = e.get("tags", {})
    if "name" in t:
        osm_named[t["name"]].append(("node", xz(e["lat"], e["lon"])))


def osm_pt(name, prefer="station", near=None):
    c = osm_named.get(name)
    if not c:
        return None
    if near is not None:
        return min(c, key=lambda k: math.dist(k[1], near))[1]
    for k, p in c:
        if k == prefer:
            return p
    for k, p in c:
        if k == "node":
            return p
    return c[0][1]

# ---------- official map markers ----------
s = open(BBOX).read()
words = re.findall(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">([^<]*)</word>', s)
markers = defaultdict(list)
for w in words:
    x = (float(w[0]) + float(w[2])) / 2; y = (float(w[1]) + float(w[3])) / 2
    if re.fullmatch(r"\d{1,2}", w[4]) and y < 400 and 30 < x < 600:
        markers[int(w[4])].append((x, y))

# legend: num -> (name, area, type, flags)  flags: s=☼ rides 12-6 Sat/Sun, a=★ open all day, f=🏁, p=Speedy Pass
A = {}
def L(area, typ, rows):
    for r in rows:
        n, name = r[0], r[1]
        A[n] = dict(name=name, area=area, type=typ, flags=r[2] if len(r) > 2 else "")
L("entrance", "service", [(1, "Customer Service & Group Sales"), (2, "Season Pass Processing Center"), (3, "Rider Safety Center")])
L("entrance", "shop", [(4, "Entrance Plaza Gift Shop")])
L("midway", "ride", [(5, "Sky Rocket", "safp"), (6, "Old Mill", "sfp"), (7, "Kangaroo", "safp"), (8, "Jack Rabbit", "safp")])
L("midway", "food", [(9, "Cotton Candy Wagon"), (11, "1898 Coffee Co."), (12, "Carousel Burger Co."), (13, "Midway Refreshments"), (14, "Pepsi Fast Fill")])
L("midway", "shop", [(10, "Kandy Kaleidoscope"), (17, "Kennywood Gift Shop")])
L("midway", "service", [(16, "Speedy Pass Information")])
L("lagoon", "ride", [(19, "Racer", "safp"), (20, "Aero 360", "safp"), (21, "Auto Race", "s"), (22, "Merry-Go-Round", "s")])
L("lagoon", "food", [(23, "Jack Rabbit Dippin' Dots"), (24, "Grab-N-Go"), (25, "Auntie Anne's"), (26, "Star Refreshments"), (27, "Pepsi Fast Fill"), (28, "Rogue BBQ"), (29, "Beer Garden"), (30, "Pizza Warehouse"), (31, "Golden Nugget"), (32, "Fire-Breathing Sausage"), (33, "Pagoda Creamery"), (34, "Parkside Cafe"), (35, "Fall Fest Tasting")])
L("lagoon", "show", [(36, "Garden Stage")])
L("steelers", "ride", [(37, "Steel Curtain", "safp")])
L("steelers", "food", [(38, "End Zone Cafe"), (39, "Punts Bar")])
L("steelers", "shop", [(40, "Steelers Country Gift Shop")])
L("kiddieland", "ride", [(41, "Steel City Choppers", "s"), (43, "Whirlwind", "s"), (44, "Whippersnapper", "s"), (45, "Wacky Wheel", "s"), (46, "Lil' Phantom", "s"), (47, "Turtle Chase", "s"), (48, "Crazy Trolley", "s"), (49, "Dizzy Dynamo", "s"), (50, "Red Baron", "s")])
L("kiddieland", "food", [(51, "Snack-A-Saurus")])
L("junction", "ride", [(52, "Olde Kennywood Railroad", "s"), (53, "Fire Bustin' Brigade", "s"), (54, "Coal Haulin' Convoy", "s"), (55, "Parker's Cloud Cruisers", "s"), (56, "Kenny's Cargo Drop", "s")])
L("junction", "show", [(57, "Character Junction")])
L("junction", "shop", [(58, "Junction Toys & Gifts"), (59, "Celebration Station")])
L("kennyville", "ride", [(63, "Turtle", "safp"), (64, "Noah's Ark", "sa")])
L("kennyville", "food", [(65, "Jeeters' Pub"), (66, "Potato Patch"), (67, "Lucky"), (68, "Pepsi Fast Fill"), (69, "Big Dipper"), (70, "Ark Dippin' Dots"), (71, "Mix-It-Up Slush Factory")])
L("kennyville", "show", [(72, "Kennyville Stage")])
L("kennyville", "service", [(73, "Guest Service Center")])
L("lost", "ride", [(74, "Black Widow", "sap"), (76, "Exterminator", "safp"), (77, "Whip", "s"), (78, "Wave Swinger", "sa"), (79, "SwingShot", "safp")])
L("lost", "food", [(80, "Small Fry's"), (81, "Centennial Grill"), (82, "Pedro's")])
L("lost", "shop", [(83, "Lost Kennywood Gift Shop")])
L("lane", "ride", [(84, "Phantom's Revenge", "safp"), (85, "Musik Express", "sa"), (86, "Pirate", "sa"), (87, "Potato Smash", "sa")])
L("lane", "food", [(88, "Auntie Anne's"), (89, "Phantom Dippin' Dots")])
L("area412", "ride", [(91, "Spinvasion", "sap"), (92, "Cosmic Chaos", "sa")])
L("area412", "shop", [(93, "Gift Ship")])

# haunts / scare zones: label centers on the PDF (points)
HAUNTS = [
    ("Kennyville Cemetery", "kennyville", "haunt", (355.0, 253.0)),
    ("Detached", "midway", "haunt", (441.4, 215.0)),
    ("Ghostwood Estate: Open House", "junction", "haunt", (255.0, 69.5)),
    ("Malice in Wonderland Unleashed", "steelers", "haunt", (529.5, 27.0)),
    ("Shady Grove Memorial Hospital", "steelers", "haunt", (437.0, 48.0)),
    ("Dark Shadows", "steelers", "haunt", (445.0, 27.0)),
    ("Voodoo Bayou", "junction", "haunt", (272.0, 48.0)),
    ("Fear Fest", "midway", "scare", (368.0, 216.0)),
    ("Dead Light District", "kennyville", "scare", (296.0, 188.0)),
    ("Hellbilly Hollow", "lost", "scare", (83.0, 153.0)),
    ("The Welcoming", "midway", "scare", (420.0, 300.0)),
]
# The Welcoming label sits near the gate tunnel (map ~ x 630px/1210 * 792); measured from render
HAUNTS[-1] = ("The Welcoming", "midway", "scare", (632 / 1210 * 792, 478 / 935 * 612))

CONTROL = {5: "Sky Rocket", 6: "Old Mill", 7: "Kangaroo", 8: "Jack Rabbit", 9: "Cotton Candy Wagon", 10: "Kandy Kaleidoscope",
           12: "Carousel Burger Co.", 19: "Racer", 20: "Aero360", 21: "Auto Race", 22: "Merry-Go-Round", 30: "Pizza Warehouse",
           31: "Golden Nugget", 34: "Parkside Cafe", 37: "Steel Curtain", 38: "End Zone Cafe", 41: "Steel City Choppers",
           44: "Whippersnapper", 45: "Wacky Wheel", 46: "Lil' Phantom", 47: "Turtle Chase", 48: "Crazy Trolley", 49: "Dizzy Dynamo",
           50: "Red Baron", 52: "Olde Kennywood RR", 53: "Fire Bustin' Brigade", 54: "Coal Haulin' Convoy", 55: "Parker's Cloud Cruisers",
           63: "Turtle", 64: "Noah's Ark", 66: "Potato Patch", 74: "Black Widow", 76: "Exterminator", 77: "Whip", 78: "Wave Swinger",
           79: "Swing Shot", 80: "Small Fry", 84: "Phantom's Revenge", 86: "Pirate", 87: "Pototo Smash",
           1: "Guest Relations & Group Sales", 2: "Season Pass Center", 3: "Rider Safety Center"}


def lstsq_affine(src, dst):
    # solve dst = [u v 1] @ M (3x2) by normal equations
    import itertools
    n = len(src)
    ATA = [[0.0] * 3 for _ in range(3)]; ATb = [[0.0] * 2 for _ in range(3)]
    for (u, v), d in zip(src, dst):
        r = (u, v, 1.0)
        for i in range(3):
            for j in range(3):
                ATA[i][j] += r[i] * r[j]
            for k in range(2):
                ATb[i][k] += r[i] * d[k]
    # gaussian elimination
    M = [ATA[i] + ATb[i] for i in range(3)]
    for c in range(3):
        p = max(range(c, 3), key=lambda r: abs(M[r][c])); M[c], M[p] = M[p], M[c]
        for r in range(3):
            if r != c:
                f = M[r][c] / M[c][c]
                M[r] = [a - f * b for a, b in zip(M[r], M[c])]
    return [[M[i][3 + k] / M[i][i] for k in range(2)] for i in range(3)]


def apply(M, uv):
    u, v = uv
    return (u * M[0][0] + v * M[1][0] + M[2][0], u * M[0][1] + v * M[1][1] + M[2][1])

pairs = []
for n, name in CONTROL.items():
    if n in markers and markers[n]:
        p = osm_pt(name)
        if p:
            pairs.append((n, markers[n][0], p))
M = lstsq_affine([p[1] for p in pairs], [p[2] for p in pairs])
for it in range(2):
    res = [math.dist(apply(M, uv), xy) for _, uv, xy in pairs]
    med = sorted(res)[len(res) // 2]
    keep = [p for p, r in zip(pairs, res) if r < max(3 * med, 25)]
    M = lstsq_affine([p[1] for p in keep], [p[2] for p in keep])
pairs = keep
res = [(n, math.dist(apply(M, uv), xy)) for n, uv, xy in pairs]
rms = math.sqrt(sum(r * r for _, r in res) / len(res))
print(f"affine fit: {len(pairs)} controls, RMS {rms:.1f} m, worst {max(res, key=lambda r: r[1])}")


def georef(uv):
    base = apply(M, uv)
    # rubber sheet: IDW of control residuals
    wsum = dx = dz = 0.0
    for _, cuv, cxy in pairs:
        cb = apply(M, cuv)
        d = math.dist(apply(M, uv), cb) + 8.0
        w = 1.0 / (d * d)
        wsum += w; dx += w * (cxy[0] - cb[0]); dz += w * (cxy[1] - cb[1])
    return (base[0] + dx / wsum, base[1] + dz / wsum)

# leave-one-out check of the rubber sheet (outside judge for georeferencing)
loo = []
for i, (n, uv, xy) in enumerate(pairs):
    saved = pairs[:]
    pairs = saved[:i] + saved[i + 1:]
    loo.append(math.dist(georef(uv), xy))
    pairs = saved
loo.sort()
print(f"leave-one-out error: median {loo[len(loo)//2]:.1f} m, p90 {loo[int(len(loo)*0.9)]:.1f} m, max {loo[-1]:.1f} m")

places = []
for n, info in sorted(A.items()):
    pts = markers.get(n, [])
    if not pts:
        print("no marker for", n, info["name"]); continue
    for k, uv in enumerate(pts):
        src = "map"
        pos = georef(uv)
        if n in CONTROL and k == 0:
            o = osm_pt(CONTROL[n], near=pos)
            if o and math.dist(o, pos) < 60:
                pos, src = o, "osm"
        pid = f"{n}" if len(pts) == 1 else f"{n}-{k}"
        places.append(dict(id=pid, num=n, name=info["name"], area=info["area"], type=info["type"], flags=info["flags"],
                           x=round(pos[0], 1), z=round(pos[1], 1), src=src))
for name, area, typ, uv in HAUNTS:
    pos = georef(uv); src = "map"
    if name.startswith("Ghostwood"):
        o = osm_pt("Ghostwood Estate"); pos, src = (o, "osm") if o else (pos, src)
    places.append(dict(id="h-" + re.sub(r"\W+", "", name.lower())[:14], num=None, name=name, area=area, type=typ,
                       flags="p" if typ == "haunt" else "", x=round(pos[0], 1), z=round(pos[1], 1), src=src))

# restrooms from OSM + map "Family Restroom" labels
for e in ways + nodes:
    t = e.get("tags", {})
    if t.get("amenity") == "toilets":
        p = centroid(poly(e)) if e["type"] == "way" else xz(e["lat"], e["lon"])
        if near_park(p):
            places.append(dict(id=f"wc{e['id']}", num=None, name="Restroom", area="", type="restroom", flags="",
                               x=round(p[0], 1), z=round(p[1], 1), src="osm"))
for uv in [(473.7, 66.5), (394.9, 241.3)]:
    p = georef(uv)
    places.append(dict(id=f"fam{int(uv[0])}", num=None, name="Family Restroom", area="", type="restroom", flags="",
                       x=round(p[0], 1), z=round(p[1], 1), src="map"))

print("places:", len(places), "from osm:", sum(p["src"] == "osm" for p in places))

# ---------- geometry layers ----------
def r1(v):
    return round(v, 1)

def flat(pts):
    out = []
    for x, z in pts:
        out += [r1(x), r1(z)]
    return out

bbox_ok = lambda pts: any(near_park(p, 150) for p in pts[:: max(1, len(pts) // 4)])

buildings, water, parking, roads, rails = [], [], [], [], []
tracks = defaultdict(list)
WALK = {"footway", "path", "steps", "service", "pedestrian", "track", "living_street", "unclassified"}
walk_ways = []
for e in ways:
    t = e.get("tags", {}); pts = poly(e)
    if e["id"] == 237755727:
        continue
    if t.get("roller_coaster") == "track":
        tracks[t.get("name", f"track{e['id']}")].append(flat(pts)); continue
    if t.get("attraction") in ("log_flume", "river_rafting"):
        if pts[0] == pts[-1]:
            water.append(flat(pts))
        else:
            tracks[t.get("name")].append(flat(pts))
        continue
    if "building" in t or t.get("roller_coaster") == "station":
        if pts[0] != pts[-1] or not bbox_ok(pts):
            continue
        lv = t.get("building:levels"); h = t.get("height")
        try:
            hh = float(h) if h else (float(lv) * 3.4 if lv else None)
        except ValueError:
            hh = None
        if hh is None:
            hh = {"pavilion": 5, "roof": 5, "kiosk": 3.5, "house": 7, "apartments": 10, "warehouse": 8}.get(t["building"], 6.5)
            if t.get("roller_coaster") == "station": hh = 7
            if t.get("name") == "Exterminator": hh = 13
        roof_only = t["building"] in ("roof", "pavilion")
        buildings.append(dict(p=flat(pts[:-1]), h=hh, r=1 if roof_only else 0, inp=1 if inside(centroid(pts)) else 0,
                              n=t.get("name", "")))
        continue
    if t.get("natural") == "water" or t.get("leisure") == "swimming_pool":
        if pts[0] == pts[-1]: water.append(flat(pts))
        continue
    if t.get("amenity") == "parking" and pts[0] == pts[-1]:
        parking.append(flat(pts)); continue
    if t.get("railway") == "miniature":
        tracks["Olde Kennywood Railroad"].append(flat(pts)); continue
    if t.get("railway") in ("rail",):
        rails.append(flat(pts)); continue
    hw = t.get("highway")
    if hw:
        if (hw in WALK and any(inside(p) for p in pts)) or (hw in ("footway", "steps", "path", "pedestrian") and any(near_park(p, 140) for p in pts)):
            walk_ways.append(e)
        elif hw != "raceway":
            roads.append(dict(p=flat(pts), w=9 if hw == "primary" else 6))
        if hw == "raceway":
            tracks["Auto Race"].append(flat(pts))

# relation water (Lagoon multipolygon)
for e in els:
    if e["type"] == "relation" and e.get("tags", {}).get("name") == "Lagoon":
        for m in e.get("members", []):
            if m.get("role") == "outer" and "geometry" in m:
                water.append(flat([xz(p["lat"], p["lon"]) for p in m["geometry"]]))

trees = []
for e in nodes:
    if e.get("tags", {}).get("natural") == "tree":
        p = xz(e["lat"], e["lon"])
        if near_park(p, 100): trees.append([r1(p[0]), r1(p[1])])

# ---------- walking graph ----------
gnodes = {}  # osm node id -> idx
coords = []
adj = defaultdict(dict)
def nid(osm_id, p):
    if osm_id not in gnodes:
        gnodes[osm_id] = len(coords); coords.append(p)
    return gnodes[osm_id]
for e in walk_ways:
    ids = e["nodes"]; geo = e["geometry"]
    prev = None
    for oid, g in zip(ids, geo):
        i = nid(oid, xz(g["lat"], g["lon"]))
        if prev is not None and prev != i:
            d = math.dist(coords[prev], coords[i])
            adj[prev][i] = adj[i][prev] = d
        prev = i

def components():
    seen = [-1] * len(coords); comps = []
    for s0 in range(len(coords)):
        if seen[s0] >= 0: continue
        stack = [s0]; seen[s0] = len(comps); members = []
        while stack:
            u = stack.pop(); members.append(u)
            for v in adj[u]:
                if seen[v] < 0: seen[v] = len(comps); stack.append(v)
        comps.append(members)
    return comps, seen
comps, _ = components()
print("walk graph:", len(coords), "nodes,", sum(len(a) for a in adj.values()) // 2, "edges,", len(comps), "components, sizes", sorted(map(len, comps), reverse=True)[:8])
# stitch components: connect each smaller component to the main one by its closest node pair (< 40 m)
for _ in range(40):
    comps, cid = components()
    if len(comps) == 1: break
    main = max(range(len(comps)), key=lambda i: len(comps[i]))
    best = None
    for ci, cm in enumerate(comps):
        if ci == main: continue
        for u in cm:
            for v in comps[main]:
                d = math.dist(coords[u], coords[v])
                if best is None or d < best[0]: best = (d, u, v)
    if best is None or best[0] > 40: break
    d, u, v = best
    adj[u][v] = adj[v][u] = d * 1.2
comps, cid = components()
main = max(range(len(comps)), key=lambda i: len(comps[i]))
keep = set(comps[main])
print("after stitching:", len(comps), "components; main has", len(keep), "of", len(coords))
remap = {o: i for i, o in enumerate(sorted(keep))}
gcoords = [[r1(coords[o][0]), r1(coords[o][1])] for o in sorted(keep)]
gedges = []
for u in keep:
    for v, d in adj[u].items():
        if v in keep and u < v:
            gedges.append([remap[u], remap[v]])

# judge: every place reachable within 35 m of graph
far = []
for p in places:
    d = min(math.dist((p["x"], p["z"]), c) for c in gcoords)
    if d > 35: far.append((p["name"], round(d)))
print("places >35 m from a walkway:", far)

# entrance: Gate / Rider Safety Center area
ent = next(p for p in places if p["name"] == "The Welcoming")

# procedural tree cover: grid samples clear of walkways, buildings, water, tracks and pins
import random
random.seed(7)
segs = [(gcoords[a], gcoords[b]) for a, b in gedges]
for r in roads:
    q = r["p"]; pr = [(q[i], q[i + 1]) for i in range(0, len(q), 2)]
    segs += list(zip(pr, pr[1:]))
def segd(p, a, b):
    ax, az = a; bx, bz = b; dx, dz = bx - ax, bz - az; L2 = dx * dx + dz * dz or 1e-9
    t = max(0, min(1, ((p[0] - ax) * dx + (p[1] - az) * dz) / L2))
    return math.hypot(p[0] - ax - t * dx, p[1] - az - t * dz)
track_pts = [(sg[i], sg[i + 1]) for segs_ in tracks.values() for sg in segs_ for i in range(0, len(sg), 2)]
polys = [[(b["p"][i], b["p"][i + 1]) for i in range(0, len(b["p"]), 2)] for b in buildings]
polys += [[(w[i], w[i + 1]) for i in range(0, len(w), 2)] for w in water + parking]
pbox = [(min(x for x, _ in pg) - 3, max(x for x, _ in pg) + 3, min(z for _, z in pg) - 3, max(z for _, z in pg) + 3) for pg in polys]
xs = [p[0] for p in PARK]; zs = [p[1] for p in PARK]
for gx in range(int(min(xs)) - 160, int(max(xs)) + 160, 7):
    for gz in range(int(min(zs)) - 160, int(max(zs)) + 160, 7):
        p = (gx + random.uniform(-3, 3), gz + random.uniform(-3, 3))
        inn = inside(p)
        if not inn:
            if not near_park(p, 150) or random.random() > 0.45: continue
        elif random.random() > 0.6: continue
        if any(b[0] < p[0] < b[1] and b[2] < p[1] < b[3] and (inside(p, pg) or min(math.dist(p, v) for v in pg) < 3) for b, pg in zip(pbox, polys)): continue
        if any(abs(p[0] - t[0]) < 4.5 and abs(p[1] - t[1]) < 4.5 for t in track_pts): continue
        if any(abs(p[0] - q["x"]) < 8 and abs(p[1] - q["z"]) < 8 for q in places): continue
        if any(segd(p, a, b) < (5 if inn else 9) for a, b in segs if abs(a[0] - p[0]) < 80 and abs(a[1] - p[1]) < 80): continue
        trees.append([r1(p[0]), r1(p[1])])
print("trees:", len(trees))

COASTER_H = {"Phantom's Revenge": 48, "Steel Curtain": 58, "Sky Rocket": 29, "Racer": 20, "Jack Rabbit": 13,
             "Thunderbolt": 21, "Lil' Phantom": 5, "Coal Haulin' Convoy": 4, "Turtle": 2.5, "Olde Kennywood Railroad": 0.6,
             "Auto Race": 0.4, "Raging Rapids": 0.3, "Pittsburg Plunge": 12}
coasters = []
for name, segs in tracks.items():
    st = osm_pt(name, prefer="station") if name in osm_named else None
    coasters.append(dict(n=name, h=COASTER_H.get(name, 10), s=[r1(st[0]), r1(st[1])] if st else None, segs=segs))

out = dict(origin=[LAT0, LON0], m=[MLAT, MLON], park=flat(PARK), buildings=buildings, water=water, parking=parking,
           roads=roads, rails=rails, coasters=coasters, trees=trees, places=places, graph=dict(n=gcoords, e=gedges),
           entrance=[ent["x"], ent["z"]], fit=dict(controls=len(pairs), rms=round(rms, 1), loo_median=round(loo[len(loo)//2], 1)))
json.dump(out, open(OUT, "w"), separators=(",", ":"))
print("wrote", OUT, len(json.dumps(out, separators=(",", ":"))) // 1024, "KB")
