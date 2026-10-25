#!/usr/bin/env python3
"""Build an RSS 2.0 feed of idyclub.com 电影 精华 (/thread-1?tab=digest).
Usage: python3 make_feed.py [-o feed.xml] [--pages 1] [--details 30] [--fid 1]
--details N: fetch detail page for the first N items to add English title/year/rating/summary (0 = off).
"""
import argparse, datetime as dt, html, os, re, time, urllib.request
from email.utils import format_datetime
from xml.sax.saxutils import escape

BASE = "https://www.idyclub.com"
UA = "Mozilla/5.0 (X11; Linux x86_64) idyclub-rss/1.0"
TZ = dt.timezone(dt.timedelta(hours=8))

def get(url, tries=3):
    for n in range(tries):
        try:
            return _get(url)
        except Exception:
            if n == tries - 1: raise
            time.sleep(3)

def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "ignore")

def text(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()

def cdata(s):
    # A literal "]]>" inside CDATA would truncate the element and break the feed.
    return s.replace("]]>", "]]]]><![CDATA[>")

def parse_list(page):
    items = []
    for m in re.finditer(r'<li><a href="/read-(\d+)"[^>]*>\s*<img data-echo="([^"]*)"[^>]*>\s*<p>(.*?)</p><p class="newindexbt2">(.*?)</p>', page, re.S):
        tid, img, title, when = m.groups()
        items.append(dict(tid=tid, img=BASE + img if img.startswith("/") else img,
                          title=text(title), when=text(when)))
    return items

def parse_when(s, now):
    s = s.strip()
    m = re.match(r"(?:(\d{4})-)?(\d{1,2})-(\d{1,2})\s+(\d{1,2}):(\d{2})", s)
    if m:
        y, mo, d, h, mi = m.groups()
        d_ = dt.datetime(int(y or now.year), int(mo), int(d), int(h), int(mi), tzinfo=TZ)
        if not y and d_ > now + dt.timedelta(days=1):
            d_ = d_.replace(year=now.year - 1)
        return d_
    m = re.match(r"(今天|昨天|前天)\s*(\d{1,2}):(\d{2})", s)
    if m:
        off = {"今天": 0, "昨天": 1, "前天": 2}[m.group(1)]
        base = (now - dt.timedelta(days=off)).date()
        return dt.datetime(base.year, base.month, base.day, int(m.group(2)), int(m.group(3)), tzinfo=TZ)
    m = re.match(r"(\d+)\s*(分钟|小时)前", s)
    if m:
        n = int(m.group(1)); return now - (dt.timedelta(minutes=n) if m.group(2) == "分钟" else dt.timedelta(hours=n))
    return now

def detail(tid):
    t = text(re.sub(r"<script.*?</script>|<style.*?</style>", "", get(f"{BASE}/read-{tid}"), flags=re.S))
    info = {}
    m = re.search(r"首页 > [^>]+ > (\S+) > (.*?) 订阅更新", t)
    if m:
        info["region"], crumb = m.group(1), m.group(2)
        info["full"] = crumb.split(" ", 1)[1] if " " in crumb else crumb
    for k, pat in [("genre", r"类型: (.*?) 制片"), ("country", r"制片国家/地区: (.*?) 语言"),
                   ("imdb", r"IMDb: (tt\d+)"), ("douban", r"豆瓣 ([\d.]+)分"),
                   ("summary", r"的剧情简介[· ]+(.*?) 下载\(")]:
        m = re.search(pat, t)
        if m: info[k] = m.group(1).strip()
    return info

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", default="feed.xml")
    ap.add_argument("--pages", type=int, default=1)
    ap.add_argument("--details", type=int, default=30)
    ap.add_argument("--fid", default="1", help="1=电影, 18=剧集")
    a = ap.parse_args()
    now = dt.datetime.now(TZ)
    items, seen = [], set()
    for p in range(1, a.pages + 1):
        url = f"{BASE}/thread-{a.fid}?tab=digest" if p == 1 else f"{BASE}/thread-{a.fid}-{p}&tab=digest"
        for it in parse_list(get(url)):
            if it["tid"] not in seen:
                seen.add(it["tid"]); items.append(it)
        time.sleep(1)
    if not items:
        raise SystemExit("no items parsed - page layout may have changed")
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel>',
           f"<title>WMMFLIX 电影 精华</title><link>{BASE}/thread-{a.fid}?tab=digest</link>",
           "<description>idyclub.com 电影 精华 (unofficial, scraped)</description><language>zh-cn</language>",
           f"<lastBuildDate>{format_datetime(now)}</lastBuildDate>"]
    for i, it in enumerate(items):
        link = f"{BASE}/read-{it['tid']}"
        d = {}
        if i < a.details:
            try: d = detail(it["tid"]); time.sleep(1)
            except Exception: d = {}
        title = d.get("full") or it["title"]
        desc = f'<img src="{it["img"]}"/><br/>'
        meta = " | ".join(x for x in [d.get("region"), d.get("genre"), d.get("country"),
                                      f'豆瓣 {d["douban"]}' if d.get("douban") else None,
                                      f'IMDb {d["imdb"]}' if d.get("imdb") else None] if x)
        if meta: desc += escape(meta) + "<br/>"
        if d.get("summary"): desc += escape(d["summary"])
        out.append("<item>"
                   f"<title>{escape(title)}</title><link>{link}</link>"
                   f'<guid isPermaLink="true">{link}</guid>'
                   f"<pubDate>{format_datetime(parse_when(it['when'], now))}</pubDate>"
                   f"<description><![CDATA[{cdata(desc)}]]></description>"
                   f'<enclosure url="{escape(it["img"])}" type="image/jpeg" length="0"/>'
                   "</item>")
    out.append("</channel></rss>")
    tmp = a.out + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    os.replace(tmp, a.out)
    print(f"wrote {len(items)} items to {a.out}")

if __name__ == "__main__":
    main()
