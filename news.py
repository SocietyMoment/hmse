from typing import Optional, Final
import threading
import random
import time
import dataclasses
from collections import defaultdict
import requests
import lxml.etree
import lxml.html
from models import Stonk

@dataclasses.dataclass
class Article:
    title: str
    link: str
    description: Optional[str]
    image_url: Optional[str]

news_articles: defaultdict[int, list[Article]] = defaultdict(list)

ARICLES_NUM_LIM: Final = 3

def get_metadata(link: str) -> tuple[Optional[str], Optional[str]]:
    resp = requests.get(
        link,
        headers = { # These are just from my local chrome
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "accept-encoding": "gzip, deflate, br",
            "accept-language": "en-US,en;q=0.9",
            "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.51 Safari/537.36",
        }
    )
    html = lxml.html.fromstring(resp.content)

    desc = (html.xpath("//meta[@property='og:description']/@content") or [None])[0]
    img = (html.xpath("//meta[@property='og:image']/@content") or [None])[0]
    return desc, img

def update_news():
    print("updating news", flush=True)

    for stonk in Stonk.select(Stonk.id, Stonk.search_term):
        rss_url = "https://news.google.com/rss/search?q=%s&hl=en-US&gl=US&ceid=US:en" % stonk.search_term
        resp = requests.get(rss_url)
        root = lxml.etree.fromstring(resp.content)

        ret: list[Article] = []
        for item in root.find("channel").iter("item"):
            link = item.find("link").text
            desc, img = get_metadata(link)
            title = item.find("title").text

            ret.append(Article(
                title = title,
                link = link,
                description = desc,
                image_url = img
            ))

            if len(ret)==ARICLES_NUM_LIM:
                break

        news_articles[stonk.id] = ret

    print("updated news", flush=True)

def news_updater_thread():
    while 1:
        update_news()
        # we randomize to prevent all the workers
        # going down at once
        time.sleep(3600 + random.randrange(-20, 20)*60)

def start_news_thread():
    thread = threading.Thread(target=news_updater_thread)
    thread.daemon = True # This only matters for local dev
    thread.start()

