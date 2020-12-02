#!/usr/bin/env python3
from core.lite import DBLite, bunch_factory
from core.util import read, inSite, unzip
from core.dwn import DWN
from core.j2 import Jnj2, toTag
from os.path import exists, dirname, isfile
from os import makedirs, rename
from urllib.parse import unquote, quote
import requests
import ssl
import re

ssl._create_default_https_context = ssl._create_unverified_context

dwn = DWN("_out/")
j2 = Jnj2("templates/", "_out/")

if not isfile("sites.db"):
    asset = dwn.getAsset("15hack/web-backup sites.7z")
    db = unzip(asset, get="*sites.db")
    rename(db, "sites.db")

db = DBLite("sites.db", readonly=True)

sites = tuple(db.select('select substr(url, INSTR(url, "://")+3) from sites'))
re_width = re.compile(r"\?w=\d+$")

def page_factory(*args, **kargv):
    p = bunch_factory(*args, **kargv)
    p.imgs = set()
    if p.content is None:
        p.content = ""
    else:
        soup = toTag(p.content, root=p.url)
        for img in soup.select("img"):
            img = img.attrs.get("src")
            if inSite(img, *sites):
                img = re_width.sub("", img)
                p.imgs.add(img)
    p.imgs = sorted(p.imgs)
    return p

def select(file):
    sql = read(file).strip()
    cols = db.get_cols(sql+" limit 0")
    if "url" in cols:
        sql = "select * from ("+sql+") where url is not null"
    row_factory=bunch_factory
    if "content" in cols:
        row_factory=page_factory
    return db.select(sql, row_factory=row_factory)

for m in select("sql/media.sql"):
    path = dwn.urltopath(m.url, file=m.file)
    dwn.dwn(m.url, path)

for p in select("sql/pages.sql"):
    path = dwn.urltopath(p.url, file="index.html")
    j2.save("pages.html", destino=path, p=p)
    for i in p.imgs:
        dwn.dwn(i, dwn.urltopath(i))

db.close()
dwn.close()
