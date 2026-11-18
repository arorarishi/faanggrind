"""Serve the local FAANGrind mirror with offline replacements for its /api endpoints.

    python3 serve.py [port]      -> http://localhost:3000
"""
import json, os, re, sys
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mirror")
DATA = os.path.join(ROOT, "_data")
load = lambda f: json.load(open(os.path.join(DATA, f), encoding="utf-8"))

PROBLEMS = load("problems.json")
BY_SLUG = {p["slug"]: p for p in PROBLEMS}
_t = load("topics.json")
TOPICS = {t["slug"]: t for t in _t["topics"]}
TOPIC_ORDER = _t["order"]
BY_FREQ = sorted(PROBLEMS, key=lambda p: (-(p.get("frequency") or 0), -(p.get("companyCount") or 0), p["number"]))

COMPANIES = {}
for p in PROBLEMS:
    for c in p["companies"]:
        e = COMPANIES.setdefault(c["slug"], {"name": c["name"], "slug": c["slug"], "logo": c.get("logo"),
                                             "color": c.get("color"), "problemCount": 0})
        e["problemCount"] += 1


def zeroed(v):
    if isinstance(v, bool): return v
    if isinstance(v, (int, float)): return 0
    if isinstance(v, list): return []
    if isinstance(v, dict): return {k: zeroed(x) for k, x in v.items()}
    return v


ANALYTICS = zeroed(load("analytics_sample.json"))
PAGE_SIZE = 60


def api_search(q):
    q = q.strip().lower()
    if not q:
        return {"problems": [], "companies": [], "topics": []}
    probs = [{k: p[k] for k in ("number", "title", "slug", "difficulty")} for p in BY_FREQ if q in p["title"].lower()][:12]
    comps = sorted((c for c in COMPANIES.values() if q in c["name"].lower()), key=lambda c: -c["problemCount"])[:6]
    tops = [{"name": t["name"], "slug": s, "problemCount": len(TOPIC_ORDER.get(s, []))}
            for s, t in TOPICS.items() if q in t["name"].lower()][:6]
    return {"problems": probs, "companies": comps, "topics": tops}


def api_topic(slug, page, q):
    if slug not in TOPICS:
        return 404, {"error": "Topic not found"}
    items = [BY_SLUG[s] for s in TOPIC_ORDER[slug] if s in BY_SLUG]
    if q:
        items = [p for p in items if q.lower() in p["title"].lower()]
    start = (page - 1) * PAGE_SIZE
    return 200, {"items": items[start:start + PAGE_SIZE], "total": len(items), "page": page, "pageSize": PAGE_SIZE}


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def log_message(self, fmt, *args):
        if "--quiet" not in sys.argv:
            super().log_message(fmt, *args)

    def send_json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        u = urlparse(self.path)
        body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
        if u.path == "/api/problems/by-slugs":
            slugs = json.loads(body or b"{}").get("slugs") or []
            return self.send_json({"items": [BY_SLUG[s] for s in slugs if s in BY_SLUG]})
        if u.path == "/api/track" or re.match(r"/[0-9a-f]{16}/", u.path) or u.path.startswith("/_vercel/"):
            self.send_response(204); self.end_headers(); return
        self.send_json({"error": "Not found"}, 404)

    def do_GET(self):
        u = urlparse(self.path)
        qs = {k: v[0] for k, v in parse_qs(u.query).items()}
        path = u.path

        if path == "/api/search":
            return self.send_json(api_search(qs.get("q", "")))
        m = re.fullmatch(r"/api/topics/([\w\-]+)/problems", path)
        if m:
            code, obj = api_topic(m.group(1), max(1, int(qs.get("page", 1) or 1)), qs.get("q", ""))
            return self.send_json(obj, code)
        if path == "/api/analytics":
            return self.send_json({**ANALYTICS, "generatedAt": datetime.now(timezone.utc).isoformat()})
        if path.startswith("/api/") or path.startswith("/_vercel/"):
            return self.send_json({}, 200)
        if re.fullmatch(r"/[0-9a-f]{16}/script\.js", path):  # Vercel analytics/speed-insights: stub out
            self.send_response(200)
            self.send_header("Content-Type", "application/javascript")
            self.send_header("Content-Length", "0")
            self.end_headers(); return

        # Next.js client-side navigation / prefetch asks for an RSC payload we don't have.
        # A non-RSC response makes Next fall back to a normal full-page load, which works.
        if self.headers.get("RSC") == "1" and self.headers.get("Next-Router-Prefetch"):
            self.send_response(204); self.end_headers(); return

        if path.startswith("/_next/") or os.path.isfile(os.path.join(ROOT, path.lstrip("/"))):
            if path.startswith("/_data/"):
                return self.send_json({"error": "Not found"}, 404)
            return super().do_GET()

        page = os.path.join(ROOT, (path.strip("/") or "index") + ".html")
        if not os.path.isfile(page):
            page = os.path.join(ROOT, "404.html") if os.path.isfile(os.path.join(ROOT, "404.html")) else None
            code = 404
        else:
            code = 200
        if not page:
            return self.send_error(404)
        data = open(page, "rb").read()
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)

    def end_headers(self):
        if self.path.startswith("/_next/static/"):
            self.send_header("Cache-Control", "public, max-age=31536000, immutable")
        super().end_headers()


if __name__ == "__main__":
    port = int(next((a for a in sys.argv[1:] if a.isdigit()), 3000))
    print(f"FAANGrind mirror: http://localhost:{port}  ({len(PROBLEMS)} problems, {len(TOPICS)} topics)")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
