#!/usr/bin/env python3
from core.lite import DBLite, bunch_factory
from core.util import read, inSite, unzip
from core.nginx import Nginx
from core.dwn import DWN, urltopath, FakeDWN
from core.j2 import Jnj2, toTag, relurl, select_txt, iterhref
from os.path import exists, dirname, isfile
from os import makedirs, rename
from urllib.parse import unquote, quote, urljoin, urlparse
import requests
import bbcode
import ssl
import re

ssl._create_default_https_context = ssl._create_unverified_context

dwn = DWN("_out/web/")

if not isfile("sites.db"):
    asset = dwn.getAsset("15hack/web-backup sites.7z")
    db = unzip(asset, get="*sites.db")
    rename(db, "sites.db")

db = DBLite("sites.db", readonly=True)

SITES = tuple(db.select('select substr(url, INSTR(url, "://")+3) from sites'))
re_width = re.compile(r"\?w=\d+$")
re_sp = re.compile(r"\s+")


def https_to_http(html, *args, **kargv):
    soup = toTag(html)
    for n, attr, val in iterhref(soup):
        if not val.lower().startswith("https://"):
            continue
        url = val.split("://", 1)
        url = url[1]
        for s in SITES:
            if url.startswith(s):
                n.attrs[attr] = "http://" + url
                break
    return str(soup)

j2 = Jnj2("templates/", "_out/web/", post=https_to_http)

def page_factory(*args, **kargv):
    p = bunch_factory(*args, **kargv)
    if "title" in p and "url" in p and p.title is None:
        p.title = p.url.split("://", 1)[-1]
        p.title = p.title.rstrip("/?&")
        if p.title.startswith("www."):
            p.title = p.title[4:]
    p.imgs = set()
    if "bbcode" in p and p.bbcode:
        p.content = bbcode.render_html(p.bbcode)
    if p.content is None:
        p.content = ""
    else:
        soup = toTag(p.content, root=p.url, torelurl=False)
        for img in soup.select("img"):
            img = img.attrs.get("src")
            if inSite(img, *SITES):
                img = re_width.sub("", img)
                p.imgs.add(img)
        for n in select_txt(soup, "span.mw-editsection", "[editar]"):
            n.extract()
        #soup = toTag(p.content, root=p.url, torelurl=True)
        p.content = str(soup)
    p.imgs = sorted(p.imgs)
    return p

def select(file, *args, **kargv):
    sql = read(file, *args, **kargv).strip()
    cols = db.get_cols(sql+" limit 0")
    if "url" in cols:
        sql = "select * from ("+sql+") where url is not null"
    row_factory=bunch_factory
    if "content" in cols or "bbcode" in cols:
        row_factory=page_factory
    return db.select(sql, row_factory=row_factory)

for m in select("sql/media.sql"):
    path = urltopath(m.url, file=m.file)
    dwn.dwn(m.url, path)

for p in select("sql/pages.sql"):
    path = urltopath(p.url, file="index.html")
    j2.save("page.html", destino=path, p=p)
    for i in p.imgs:
        dwn.dwn(i, urltopath(i))

for p in list(select("sql/sites.sql")):
    path = urltopath(p.url, file="index.html")
    p.nav = list(select("sql/nav.sql", site=p.id))
    #for n in p.nav:
    #    n.url = relurl(p.url, n.url)
    j2.save("site.html", destino=path, p=p)

for p in list(db.select("select * from phpbb_topics", row_factory=bunch_factory)):
    path = urltopath(p.url, file="index.html")
    p.posts = list(select("sql/topic.sql", site=p.site, topic=p.ID, url=p.url))
    for i in p.posts:
        i.media = list(select("sql/phpbb_media.sql", site=p.site, topic=p.ID, post=i.ID))
    j2.save("topic.html", destino=path, p=p)


n = Nginx(db, "_out/")
n.close()
db.close()
dwn.close()
