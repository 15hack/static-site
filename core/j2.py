import json
import os
import posixpath
import re
from datetime import date, datetime
from urllib.parse import urljoin, urlparse

import bs4
from jinja2 import Environment, FileSystemLoader

re_br = re.compile(r"<br/>(\s*</)")
re_sp = re.compile(r"\s+")
re_emb = re.compile(r"^image/[^;]+;base64,.*", re.IGNORECASE)


def relurl(base, target):
    base = urlparse(base)
    trg = urlparse(target)
    if base.netloc != trg.netloc:
        return target
        #raise ValueError('target and base netlocs (%s != %s) do not match' % (base.netloc, target.netloc))
    base_dir = '.'+posixpath.dirname(base.path)
    target = '.'+target[len(trg.scheme)+len(trg.netloc)+3:]
    return posixpath.relpath(target, start=base_dir)


def myconverter(o):
    if isinstance(o, (datetime, date)):
        return o.__str__()


def iterhref(tag):
    for n in tag.findAll(["img", "form", "a", "iframe", "frame", "link", "script"]):
        attr = "href" if n.name in ("a", "link") else "src"
        if n.name == "form":
            attr = "action"
        val = n.attrs.get(attr)
        if val is None or re_emb.search(val):
            continue
        if not(val.startswith("#") or val.startswith("javascript:")):
            yield n, attr, val


def select_txt(soup, select, txt, leaf=False):
    lw = txt.lower() == txt
    sp = ""
    if " " in txt:
        sp = " "
    for n in soup.select(select):
        if leaf and len(n.select(":scope *")) > 0:
            continue
        t = n.get_text()
        t = re_sp.sub(sp, t)
        t = t.strip()
        if lw:
            t = t.lower()
        if t == txt:
            yield n


def toTag(html, *args, root=None, torelurl=False):
    if len(args) > 0:
        html = html.format(*args)
    tag = bs4.BeautifulSoup(html, 'html.parser')
    if root:
        for n, attr, val in iterhref(tag):
            val = urljoin(root, val)
            n.attrs[attr] = val
    if torelurl:
        for n, attr, val in iterhref(tag):
            val = relurl(root, val)
            n.attrs[attr] = val
    return tag


def webarchive(url):
    url = url.split("://")[-1]
    return "https://web.archive.org/web/"+url


class Jnj2():

    def __init__(self, origen, destino, pre=None, post=None, **kargv):
        self.j2_env = Environment(
            loader=FileSystemLoader(origen), trim_blocks=True)
        self.j2_env.filters["webarchive"] = webarchive
        for k, v in kargv.items():
            if callable(v):
                self.j2_env.filters[k] = v
        self.destino = destino
        self.pre = pre
        self.post = post
        self.lastArgs = None

    def save(self, template, destino=None, parse=None, **kwargs):
        self.lastArgs = kwargs
        if destino is None:
            destino = template
        out = self.j2_env.get_template(template)
        html = out.render(**kwargs)
        if self.pre:
            html = self.pre(html, **kwargs)
        if parse:
            html = parse(html, **kwargs)
        if self.post:
            html = self.post(html, **kwargs)

        destino = self.destino + destino
        directorio = os.path.dirname(destino)

        if not os.path.exists(directorio):
            os.makedirs(directorio)

        with open(destino, "wb") as fh:
            fh.write(bytes(html, 'UTF-8'))
        return html

    def create_script(self, destino, indent=2, replace=False, **kargv):
        destino = self.destino + destino
        if not replace and os.path.isfile(destino):
            return
        separators = (',', ':') if indent is None else None
        with open(destino, "w") as f:
            for i, (k, v) in enumerate(kargv.items()):
                if i > 0:
                    f.write(";\n")
                f.write("var "+k+" = ")
                json.dump(v, f, indent=indent,
                          separators=separators, default=myconverter)
                f.write(";")

    def exists(self, destino):
        destino = self.destino + destino
        return os.path.isfile(destino)
