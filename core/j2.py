import json
import os
import re
from datetime import date, datetime
from urllib.parse import urljoin

import bs4
from jinja2 import Environment, FileSystemLoader

re_br = re.compile(r"<br/>(\s*</)")
re_emb = re.compile(r"^image/[^;]+;base64,.*", re.IGNORECASE)

def myconverter(o):
    if isinstance(o, (datetime, date)):
        return o.__str__()

def toTag(html, *args, root=None):
    if len(args) > 0:
        html = html.format(*args)
    tag = bs4.BeautifulSoup(html, 'html.parser')
    if root:
        for n in tag.findAll(["img", "form", "a", "iframe", "frame", "link", "script"]):
            attr = "href" if n.name in ("a", "link") else "src"
            if n.name == "form":
                attr = "action"
            val = n.attrs.get(attr)
            if val is None or re_emb.search(val):
                continue
            if not(val.startswith("#") or val.startswith("javascript:")):
                val = urljoin(root, val)
                n.attrs[attr] = val
    return tag


class Jnj2():

    def __init__(self, origen, destino, pre=None, post=None, **kargv):
        self.j2_env = Environment(
            loader=FileSystemLoader(origen), trim_blocks=True)
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
