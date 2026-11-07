import csv, json, os, re, sys, time, urllib.request, urllib.parse
from PIL import Image
API = "https://api.openverse.org/v1/images/"
os.makedirs("img/q", exist_ok=True)
meta = json.load(open("img/meta.json")) if os.path.exists("img/meta.json") else {}
used = {m["id"] for m in meta.values()}
override = json.load(open("img/override.json")) if os.path.exists("img/override.json") else {}
def search(q, page=1):
    p = dict(q=q, license="cc0,pdm", source="wordpress,stocksnap", category="photograph", page_size=20, page=page)
    with urllib.request.urlopen(urllib.request.Request(API + "?" + urllib.parse.urlencode(p), headers={"User-Agent": "podcast-editor"}), timeout=30) as r:
        return json.load(r)["results"]
def slug(q): return re.sub(r"[^a-z0-9]+", "_", q.lower()).strip("_")
queries = []
for row in csv.reader(open("scenes.tsv"), delimiter="\t"):
    if not row or row[0].startswith("#"): continue
    q = row[1]
    if not q.startswith("@") and q not in queries: queries.append(q)
for q in queries:
    if q in meta and q not in override: continue
    skip = set(override.get(q, {}).get("skip", []))
    try: res = search(q)
    except Exception as e: print("ERR", q, e); continue
    def score(r):
        w, h = r.get("width") or 0, r.get("height") or 1
        return (r["id"] in used or r["id"] in skip, w/h < 1.3, r["source"] != "wordpress", -w)
    ok = None
    for r in sorted(res, key=score):
        if r["id"] in skip: continue
        path = f"img/q/{slug(q)}.jpg"
        try:
            req = urllib.request.Request(r["url"], headers={"User-Agent": "podcast-editor"})
            open(path, "wb").write(urllib.request.urlopen(req, timeout=60).read())
            Image.open(path).convert("RGB").save(path, quality=95)
        except Exception as e: print("dl fail", q, e); continue
        ok = r; break
    if not ok: print("NONE", q); continue
    used.add(ok["id"])
    meta[q] = dict(id=ok["id"], path=path, title=ok["title"][:100], creator=ok.get("creator"), license=ok["license"], source=ok["source"], landing=ok["foreign_landing_url"], w=ok["width"], h=ok["height"])
    print(f"{q:30s} {ok['source']:10s} {ok['width']}x{ok['height']} {ok['title'][:60]}", flush=True)
    json.dump(meta, open("img/meta.json", "w"), indent=1)
