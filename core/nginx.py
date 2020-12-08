from textwrap import dedent
from .dwn import urltopath
from urllib.parse import unquote, quote, urlparse, parse_qsl
from bunch import Bunch
from os.path import realpath

class Nginx:
    def __init__(self, db, config, root):
        self.db = db
        self.root = realpath(root)
        self.config = open(config, "w")
        self.write('''
            server {
                listen 443;
                server_name _;
                # rewrite ^(.*) http://$host$1 permanent;
                return 301 http://$http_host$request_uri;
            }
        ''')
        doms=set()
        for url, in db.select("select url from sites order by id"):
            url = unquote(url)
            purl = urlparse(url)
            dom = purl.netloc
            if dom.startswith("www."):
                dom = dom[4:]
            root = dom.split(".")
            root = root[-2:]
            root = ".".join(root)
            doms.add(root)
        doms = sorted(doms, key=lambda x:tuple(reversed(x.split("."))))
        for site in doms:
            path = urltopath("http://"+site)
            self.write('''
                server {
                    listen 80;
                    server_name {site} www.{site};
                    root {root}/{path};
                    include {root}/common_config.nginx;
                }
            ''', site=site, root=self.root, path=path)
            self.write('''
                server {
                    listen 80;
                    listen 443;
                    server_name ~^(www\.)?(?<subdomain>.+)\.{site}$;
                    root {root}/{path}/$subdomain;
                    include {root}/common_config.nginx;
                }
            ''', site=site, root=self.root, path=path.rsplit("/", 1)[0])

    def close(self):
        self.config.close()

    def write(self, txt, *args, end="\n", **kargv):
        if args or kargv:
            flag = "---------"
            txt = txt.replace("{\n", "["+flag)
            txt = txt.replace("}\n", "]"+flag)
            txt = txt.format(*args, **kargv)
            txt = txt.replace("["+flag, "{\n")
            txt = txt.replace("]"+flag, "}\n")
        txt = dedent(txt).strip()
        self.config.write(txt+end)

if __name__ == "__main__":
    from .lite import DBLite, bunch_factory
    db = DBLite("sites.db", readonly=True)
    n = Nginx(db, "_out/sites.nginx", "_out/")
    n.close()
