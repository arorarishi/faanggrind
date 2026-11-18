"""Build a self-contained local mirror of faangrind.vercel.app in ./mirror.

Pages are stored as mirror/<path>.html (home = index.html); static files at their
original paths. Run crawl.py first (it caches HTML in scrape/raw). Serve with serve.py.
"""
import json, os, re, shutil, sys
from concurrent.futures import ThreadPoolExecutor
import requests
from urllib.parse import unquote

BASE = "https://faangrind.vercel.app"
ROOT = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(ROOT, "scrape", "raw")
OUT = os.path.join(ROOT, "mirror")
S = requests.Session(); S.headers["User-Agent"] = "Mozilla/5.0 (compatible; personal-mirror)"
FILE_RE = re.compile(r"\.(js|css|woff2?|ttf|png|jpe?g|webp|gif|svg|ico|webmanifest|json|txt|xml|mp4|webm)$", re.I)
redirects = {}


def page_file(path):
    path = path.strip("/")
    return os.path.join(OUT, (path or "index") + ".html")


def get(url_path, dest):
    if os.path.exists(dest):
        return True
    try:
        r = S.get(BASE + url_path, timeout=30, allow_redirects=True)
    except requests.RequestException as e:
        print("ERR", url_path, e); return False
    if r.status_code != 200:
        print("HTTP", r.status_code, url_path); return False
    final = r.url.replace(BASE, "") or "/"
    if final.rstrip("/") != url_path.rstrip("/"):
        redirects[url_path] = final
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    open(dest, "wb").write(r.content)
    return True


def refs_in(text):
    out = set()
    for m in re.finditer(r'(?:href|src|srcSet|content)="([^"]+)"', text):
        for part in m.group(1).split(","):
            p = part.strip().split(" ")[0]
            if p.startswith("/") and not p.startswith("//"):
                out.add(p.split("?")[0].split("#")[0])
    # paths inside JS / CSS / RSC payloads
    out |= {"/_next/" + m for m in re.findall(r"(?<![\w/])/?_next/(static/[\w\-./\[\]()@%]+?\.(?:js|css|woff2?|png|svg|webp|jpg))", text)}
    out |= {"/_next/static/" + m for m in re.findall(r'"(?:\.\./)?(?:static/)?((?:chunks|css|media)/[\w\-./\[\]()@%]+?\.(?:js|css|woff2?|png|svg|webp|jpg))"', text)}
    out |= set(re.findall(r'url\((/[^)"\']+)\)', text))
    out |= {p for p in re.findall(r'"(/(?:logos|img|images|icons|fundamentals|ai|devops|system-design)/[\w\-./]+\.(?:png|webp|svg|ico|jpg|jpeg|gif))', text)}
    return out


def webpack_chunks(js):
    """Parse the webpack runtime's chunk-id -> hash maps to list lazily loaded chunks."""
    out = set()
    # e.g. return "static/chunks/"+(({1:"name"})[e]||e)+"."+({1:"abc123",...})[e]+".js"
    for prefix, ext in (("static/chunks/", ".js"), ("static/css/", ".css")):
        i = js.find('"' + prefix + '"')
        while i != -1:
            seg = js[i:i + 200000]
            maps = re.findall(r"\{(\s*\d+\s*:\s*\"[^\"]+\"(?:\s*,\s*\d+\s*:\s*\"[^\"]+\")*)\}", seg[:150000])
            names, hashes = {}, {}
            parsed = [dict(re.findall(r"(\d+)\s*:\s*\"([^\"]+)\"", m)) for m in maps[:2]]
            if len(parsed) == 2:
                names, hashes = parsed
            elif parsed:
                hashes = parsed[0]
            for cid, h in hashes.items():
                out.add(f"/_next/{prefix}{names.get(cid, cid)}.{h}{ext}")
            i = js.find('"' + prefix + '"', i + 1)
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    # 1. copy scraped pages
    seen_pages = set()
    for dp, _, fs in os.walk(RAW):
        for f in fs:
            src = os.path.join(dp, f)
            rel = os.path.relpath(src, RAW)[:-5]
            dst = os.path.join(OUT, rel + ".html")
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(src, dst)
            seen_pages.add("/" + ("" if rel == "index" else rel))

    seen = set(seen_pages)
    queue = set()
    for p in seen_pages:
        queue |= refs_in(open(page_file(p), encoding="utf-8", errors="ignore").read())
    queue |= {"/favicon.ico", "/manifest.webmanifest", "/icon.png", "/apple-icon.png", "/robots.txt",
              "/dashboard", "/settings", "/analytics", "/sitemap.xml"}

    rnd = 0
    while queue - seen:
        todo = sorted(queue - seen); seen |= set(todo); rnd += 1
        print(f"round {rnd}: {len(todo)} new urls", flush=True)

        def job(p):
            if p.startswith("/api/") or p.startswith("/_vercel/"):
                return p, None
            dest = os.path.join(OUT, unquote(p).lstrip("/")) if FILE_RE.search(p) or p.startswith("/_next/") else page_file(p)
            return p, dest if get(p, dest) else None

        with ThreadPoolExecutor(8) as ex:
            results = list(ex.map(job, todo))
        new = set()
        for p, dest in results:
            if dest and re.search(r"\.(html|js|css|webmanifest)$", dest):
                text = open(dest, encoding="utf-8", errors="ignore").read()
                new |= refs_in(text)
                if "/webpack-" in dest:
                    new |= webpack_chunks(text)
        queue |= new

    n = sum(len(fs) for _, _, fs in os.walk(OUT))
    print(f"mirror complete: {n} files, {len(redirects)} redirects")


if __name__ == "__main__":
    main()
