"""Crawl every public page listed in faangrind.vercel.app/sitemap.xml.

Outputs (under scrape/):
  raw/<path>.html      original HTML
  pages/<path>.md      main content converted to Markdown
  pages.jsonl          one record per page: url, section, slug, title, description, markdown
"""
import json, os, re, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md

BASE = "https://faangrind.vercel.app"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scrape")
UA = {"User-Agent": "Mozilla/5.0 (compatible; personal-scraper)"}
S = requests.Session(); S.headers.update(UA)


def urls():
    xml = S.get(f"{BASE}/sitemap.xml", timeout=30).text
    return re.findall(r"<loc>([^<]+)</loc>", xml)


def rel(url):
    p = url.replace(BASE, "").strip("/")
    return p or "index"


def fetch(url):
    path = rel(url)
    raw = os.path.join(OUT, "raw", path + ".html")
    if os.path.exists(raw):
        html = open(raw, encoding="utf-8").read()
    else:
        for attempt in range(4):
            try:
                r = S.get(url, timeout=30)
                if r.status_code == 200:
                    html = r.text
                    break
                if r.status_code in (429, 500, 502, 503, 504):
                    time.sleep(2 ** attempt); continue
                return {"url": url, "error": r.status_code}
            except requests.RequestException as e:
                time.sleep(2 ** attempt); err = str(e)
        else:
            return {"url": url, "error": "failed"}
        os.makedirs(os.path.dirname(raw), exist_ok=True)
        open(raw, "w", encoding="utf-8").write(html)

    soup = BeautifulSoup(html, "lxml")
    title = soup.title.get_text(strip=True) if soup.title else ""
    d = soup.find("meta", attrs={"name": "description"})
    desc = d["content"] if d and d.has_attr("content") else ""
    for t in soup.find_all(["script", "style", "svg", "noscript", "button"]):
        t.decompose()
    # Next.js streams real content into hidden <div id="S:n"> blocks; <main> is often a placeholder.
    blocks = [soup.find("main")] + soup.find_all("div", id=re.compile(r"^S:\d+$"))
    blocks = [b for b in blocks if b and b.get_text(strip=True)]
    text = "\n\n".join(md(str(b), heading_style="ATX") for b in blocks)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    mdpath = os.path.join(OUT, "pages", path + ".md")
    os.makedirs(os.path.dirname(mdpath), exist_ok=True)
    with open(mdpath, "w", encoding="utf-8") as f:
        f.write(f"# {title}\n\nSource: {url}\n\n{text}\n")
    parts = path.split("/")
    return {"url": url, "section": parts[0], "slug": parts[-1], "title": title,
            "description": desc, "markdown": text}


def main():
    all_urls = urls()
    print(f"{len(all_urls)} urls", flush=True)
    results, errors = [], []
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = [ex.submit(fetch, u) for u in all_urls]
        for i, f in enumerate(as_completed(futs), 1):
            r = f.result()
            (errors if "error" in r else results).append(r)
            if i % 100 == 0:
                print(f"{i}/{len(all_urls)} done, {len(errors)} errors", flush=True)
    results.sort(key=lambda r: r["url"])
    with open(os.path.join(OUT, "pages.jsonl"), "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"done: {len(results)} ok, {len(errors)} errors")
    for e in errors:
        print("ERR", e)


if __name__ == "__main__":
    main()
