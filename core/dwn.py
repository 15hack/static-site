import os
import tempfile
from os import makedirs
from os.path import dirname, exists
from urllib.error import ContentTooShortError, HTTPError
from urllib.parse import parse_qsl, quote, unquote, urlparse
from urllib.request import urlretrieve

import py7zlib
import requests

from .util import readlines


def tuple_url(url):
    prc = None
    slp = url.split("://", 1)
    if len(slp) == 2 and slp[0].lower() in ("http", "https"):
        prc = slp[0].lower()
        url = slp[1]
    slp = url.split("/", 1)
    dom = slp[0]
    url = slp[1] if len(slp) > 1 else None
    r = [
        tuple(reversed(dom.split("."))),
        url,
        prc
    ]
    return tuple(r)


def urltopath(url, file=None):
    url = unquote(url)
    purl = urlparse(url)
    url = url.rstrip("/?#")
    url = url.split("://", 1)[1]
    url = url.split("/", 1)
    if len(url) == 1:
        dom = url[0]
        url = None
    else:
        dom, url = url
    if dom.startswith("www."):
        dom = dom[4:]
    dom = dom.split(".")
    if len(dom) == 2:
        dom.insert(0, "__ROOT__")
    path = [
        ".".join(dom[-2:]),
    ] + list(reversed(dom[:-2]))
    lpath = len(path)
    if purl.query and purl.query.isdigit():
        url = url.split("?", 1)[0]
    elif purl.query:
        qr = parse_qsl(purl.query)
        qr = dict(qr)
        if purl.path.endswith("/viewtopic.php"):
            for k in ("p", "t", "f"):
                if k in qr:
                    path.append(purl.path)
                    path.append(k+"="+qr[k])
                    break
        elif purl.path.endswith("/download/file.php") and "id" in qr:
            path.append(purl.path)
            path.append("id="+qr["id"])
        elif "p" in qr or "page_id" in qr:
            id = qr.get("p", qr.get("page_id"))
            if id is not None and id.isdigit():
                path.append(purl.path)
                path.append("p="+id)
    if len(path) == lpath and url:
        url = url.replace("?", "/__QUERY__/")
        path.append(url)
    if file:
        path.append(file)
    path = "/".join(path)
    path = path.replace("//", "/")
    return path


class FakeDWN:
    def __init__(*args, **kargv):
        pass

    def dwn(self, *args, **kargv):
        pass

    def close(self, *args, **kargv):
        pass


class DWN:
    def __init__(self, out):
        self.log_404 = "log/404.txt"
        self.e404 = set(readlines(self.log_404))
        self.out = out

    def _download(self, source, target):
        if source in self.e404:
            return False
        try:
            urlretrieve(source, target)
            return True
        except HTTPError as e:
            if e.code == 404:
                self.e404.add(source)
            else:
                raise
        except ContentTooShortError:
            r = requests.get(source)
            with open(target, 'wb') as f:
                f.write(r.content)
            return True
        return False

    def download(self, source, *args, **kargv):
        try:
            return self._download(source, *args, **kargv)
        except UnicodeEncodeError:
            source = quote(source, safe=':/')
            return self._download(source, *args, **kargv)
        except:
            print(source)
            self.close()
            raise

    def dwn(self, source, target):
        ok = False
        target = self.out+target
        if exists(target):
            return
        dr = dirname(target)
        makedirs(dr, exist_ok=True)
        ok = self.download(source, target)
        if ok:
            print(source, "->", target[len(self.out):])

    def close(self):
        with open(self.log_404, 'w') as f:
            for l in sorted(self.e404, key=tuple_url):
                f.write(l+"\n")

    def getAsset(self, asset, target=None):
        repo, asset = asset.split()
        url = "https://api.github.com/repos/{}/releases/latest".format(repo)
        r = requests.get(url)
        r = r.json()
        for a in r["assets"]:
            if a["name"] == asset:
                url = a["browser_download_url"]
                if target is None:
                    target = tempfile.mkdtemp()+"/"+os.path.basename(url)
                print(url, "->", target)
                self.download(url, target)
                return target
