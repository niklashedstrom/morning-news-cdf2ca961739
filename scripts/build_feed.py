#!/usr/bin/env python3
"""Add an episode and rebuild feed.xml (last 14 episodes).

Usage:
  python3 scripts/build_feed.py add <mp3> <YYYY-MM-DD> <headlines.txt>

headlines.txt: one headline per line. The MP3 is copied to episodes/,
episodes.json is updated, episodes older than the newest 14 are removed
from the working tree, and feed.xml is regenerated.
"""
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from email.utils import format_datetime
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo

BASE_URL = "https://niklashedstrom.github.io/morning-news-cdf2ca961739"
KEEP = 14
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EP_DIR = os.path.join(ROOT, "episodes")
DB = os.path.join(ROOT, "episodes.json")
FEED = os.path.join(ROOT, "feed.xml")
TZ = ZoneInfo("Europe/Stockholm")


def duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return int(round(float(out)))


def hms(sec):
    return f"{sec // 3600:02d}:{sec % 3600 // 60:02d}:{sec % 60:02d}"


def load():
    if os.path.exists(DB):
        with open(DB, encoding="utf-8") as f:
            return json.load(f)
    return []


def add(mp3, date, headlines_file):
    os.makedirs(EP_DIR, exist_ok=True)
    name = f"morning-news-{date}.mp3"
    dst = os.path.join(EP_DIR, name)
    shutil.copyfile(mp3, dst)
    with open(headlines_file, encoding="utf-8") as f:
        headlines = [l.strip().lstrip("-•* ").strip() for l in f if l.strip()]
    d = datetime.strptime(date, "%Y-%m-%d")
    pub = datetime(d.year, d.month, d.day, 7, 0, tzinfo=TZ)
    eps = [e for e in load() if e["date"] != date]
    eps.append({
        "date": date,
        "file": f"episodes/{name}",
        "title": f"Morning news – {d.strftime('%A %-d %B %Y')}",
        "headlines": headlines,
        "duration": duration(dst),
        "size": os.path.getsize(dst),
        "pub": pub.isoformat(),
        # unique per audio file, so a re-published date shows up as a new episode in apps
        "guid": f"morning-news-{date}-{os.path.getsize(dst)}",
    })
    eps.sort(key=lambda e: e["date"], reverse=True)
    keep, drop = eps[:KEEP], eps[KEEP:]
    for e in drop:
        p = os.path.join(ROOT, e["file"])
        if os.path.exists(p):
            os.remove(p)
    with open(DB, "w", encoding="utf-8") as f:
        json.dump(keep, f, ensure_ascii=False, indent=2)
    build(keep)


def build(eps):
    now = format_datetime(datetime.now(timezone.utc))
    items = []
    for e in eps:
        text = "\n".join(f"• {h}" for h in e["headlines"])
        html = "<ul>" + "".join(f"<li>{escape(h)}</li>" for h in e["headlines"]) + "</ul>"
        url = f"{BASE_URL}/{e['file']}"
        guid = e.get("guid", f"morning-news-{e['date']}")
        items.append(f"""    <item>
      <title>{escape(e['title'])}</title>
      <description>{escape(text)}</description>
      <content:encoded><![CDATA[{html}]]></content:encoded>
      <itunes:summary>{escape(text)}</itunes:summary>
      <enclosure url="{url}" length="{e['size']}" type="audio/mpeg"/>
      <guid isPermaLink="false">{escape(guid)}</guid>
      <pubDate>{format_datetime(datetime.fromisoformat(e['pub']))}</pubDate>
      <itunes:duration>{hms(e['duration'])}</itunes:duration>
      <itunes:episodeType>full</itunes:episodeType>
      <itunes:explicit>false</itunes:explicit>
    </item>""")
    feed = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" xmlns:content="http://purl.org/rss/1.0/modules/content/" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>Morning News for Niklas</title>
    <link>{BASE_URL}/</link>
    <atom:link href="{BASE_URL}/feed.xml" rel="self" type="application/rss+xml"/>
    <description>A short weekday morning briefing: top news from Sweden and the world, plus tech.</description>
    <language>en</language>
    <lastBuildDate>{now}</lastBuildDate>
    <itunes:author>Claude</itunes:author>
    <itunes:image href="{BASE_URL}/cover.png"/>
    <image><url>{BASE_URL}/cover.png</url><title>Morning News for Niklas</title><link>{BASE_URL}/</link></image>
    <itunes:category text="News"/>
    <itunes:explicit>false</itunes:explicit>
    <itunes:block>Yes</itunes:block>
{chr(10).join(items)}
  </channel>
</rss>
"""
    with open(FEED, "w", encoding="utf-8") as f:
        f.write(feed)


if __name__ == "__main__":
    if len(sys.argv) == 5 and sys.argv[1] == "add":
        add(sys.argv[2], sys.argv[3], sys.argv[4])
    elif len(sys.argv) == 2 and sys.argv[1] == "build":
        build(load())
    else:
        sys.exit(__doc__)
