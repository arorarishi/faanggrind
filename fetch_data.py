"""Snapshot the data behind the site's /api endpoints into mirror/_data/ so serve.py works offline."""
import json, os, re
import requests

BASE = "https://faangrind.vercel.app"
ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "mirror", "_data")
S = requests.Session(); S.headers["User-Agent"] = "Mozilla/5.0 (compatible; personal-mirror)"
os.makedirs(OUT, exist_ok=True)

# all problem slugs: sitemap + any /problems/<slug> link in the mirror
slugs = set(re.findall(r"/problems/([\w\-]+)</loc>", S.get(BASE + "/sitemap.xml").text))
for dp, _, fs in os.walk(os.path.join(ROOT, "mirror")):
    for f in fs:
        if f.endswith(".html"):
            slugs |= set(re.findall(r'href="/problems/([\w\-]+)"', open(os.path.join(dp, f), encoding="utf-8").read()))
slugs = sorted(slugs)
print(len(slugs), "candidate slugs")

items = {}
for i in range(0, len(slugs), 50):
    r = S.post(BASE + "/api/problems/by-slugs", json={"slugs": slugs[i:i + 50]}, timeout=60)
    r.raise_for_status()
    for it in r.json()["items"]:
        items[it["slug"]] = it
print(len(items), "problems")
json.dump(sorted(items.values(), key=lambda x: x["number"]), open(os.path.join(OUT, "problems.json"), "w"))

# exact topic order as served by the live site (unfiltered pages)
topics = {}
for it in items.values():
    for t in it["topics"]:
        topics[t["slug"]] = t
topic_order = {}
for slug in topics:
    order, page = [], 1
    while True:
        d = S.get(f"{BASE}/api/topics/{slug}/problems", params={"page": page}, timeout=60).json()
        order += [x["slug"] for x in d.get("items", [])]
        if not d.get("items") or len(order) >= d.get("total", 0):
            break
        page += 1
    topic_order[slug] = order
print(len(topic_order), "topics")
json.dump({"topics": sorted(topics.values(), key=lambda t: t["order"]), "order": topic_order},
          open(os.path.join(OUT, "topics.json"), "w"))

# search response samples, used to mirror the shape of companies/topics results
samples = {q: S.get(BASE + "/api/search", params={"q": q}).json() for q in ["amazon", "array", "two"]}
json.dump(samples, open(os.path.join(OUT, "search_samples.json"), "w"), indent=1)
print("done")
