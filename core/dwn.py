import py7zlib
import tempfile
from urllib.request import urlretrieve
import os
from glob import glob
import requests
from urllib.parse import unquote, quote
from urllib.error import HTTPError, ContentTooShortError
from .util import readlines
from os.path import exists, dirname, isfile
from os import makedirs, rename

def tuple_url(url):
    prc = None
    slp = url.split("://", 1)
    if len(slp)==2 and slp[0].lower() in ("http", "https"):
        prc = slp[0].lower()
        url = slp[1]
    slp = url.split("/", 1)
    dom = slp[0]
    url = slp[1] if len(slp)>1 else None
    r = [
        tuple(reversed(dom.split("."))),
        url,
        prc
    ]
    return tuple(r)

class DWN:
    def __init__(self, out):
        self.log_404 = "log/404.txt"
        self.e404 = set(readlines(self.log_404))
        self.out = out

    def urltopath(self, url, file=None):
        url = unquote(url)
        url = url.rstrip("/")
        url = url.split("://", 1)[1]
        url = url.split("/", 1)
        if len(url)==1:
            dom = url[0]
            url = None
        else:
            dom, url = url
        if dom.startswith("www."):
            dom = dom[4:]
        dom = dom.split(".")
        if len(dom)==2:
            dom.insert(0, "__ROOT__")
        path=[
            ".".join(dom[-2:]),
        ] + list(reversed(dom[:-2]))
        if url:
            url = url.replace("?", "/__QUERY__/")
            url = url.replace("//", "/")
            path.append(url)
        if file:
            path.append(file)
        path = "/".join(path)
        return path

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
        release, asset = asset.split()
        url = "https://api.github.com/repos/{}/releases/latest".format(release)
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
