import re
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from collections import defaultdict
import urllib.request

TIMEOUT = 12
WORKERS = 16
OUTPUT_FILE = "live_global.m3u"

logging.basicConfig(level=logging.INFO, format="%(message)s")

HEADERS = {"User-Agent": "Mozilla/5.0"}

SOURCES = [
    "https://iptv-org.github.io/iptv/index.m3u",
    "https://iptv-org.github.io/iptv/countries/pk.m3u",
    "https://iptv-org.github.io/iptv/countries/us.m3u",
    "https://iptv-org.github.io/iptv/countries/in.m3u",
    "https://iptv-org.github.io/iptv/categories/news.m3u",
    "https://iptv-org.github.io/iptv/categories/sports.m3u",
    "https://iptv-org.github.io/iptv/categories/movies.m3u",
]

@dataclass
class Channel:
    name: str
    url: str
    group: str = "General"

    def to_m3u(self):
        return f'#EXTINF:-1 group-title="{self.group}",{self.name}\n{self.url}'


def fetch(url):
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            data = r.read().decode("utf-8", errors="ignore")
        return data if "#EXTINF" in data else ""
    except:
        return ""


def parse(data):
    channels = []
    name = None
    group = "General"

    for line in data.splitlines():
        line = line.strip()

        if line.startswith("#EXTINF"):
            name = line.split(",")[-1].strip()
            m = re.search(r'group-title="(.*?)"', line)
            group = m.group(1) if m else "General"

        elif line.startswith("http") and name:
            channels.append(Channel(name, line, group))
            name = None

    return channels


def dedupe(channels):
    seen = set()
    out = []

    for c in channels:
        if c.url not in seen:
            seen.add(c.url)
            out.append(c)

    return out


def worker(url):
    return parse(fetch(url))


def main():
    all_channels = []

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        for result in pool.map(worker, SOURCES):
            all_channels.extend(result)

    all_channels = dedupe(all_channels)

    grouped = defaultdict(list)
    for c in all_channels:
        grouped[c.group].append(c)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")

        for g in sorted(grouped):
            for c in sorted(grouped[g], key=lambda x: x.name.lower()):
                f.write(c.to_m3u() + "\n")

    print("DONE CHANNELS:", len(all_channels))


if __name__ == "__main__":
    main()
