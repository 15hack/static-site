from os import makedirs
from os.path import dirname, realpath
from textwrap import dedent
from urllib.parse import unquote, urlparse

from bunch import Bunch

from .dwn import urltopath


def get_dom(url):
    url = unquote(url)
    purl = urlparse(url)
    dom = purl.netloc
    if dom.startswith("www."):
        dom = dom[4:]
    return dom


class Nginx:
    def __init__(self, db, root):
        self.db = db
        self.root = realpath(root)
        self.files = {}
        doms = set()
        ng_include = {}
        for url, in db.select("select url from sites where type!='phpbb'order by id"):
            dom = get_dom(url)
            root = dom.split(".")
            root = root[-2:]
            root = ".".join(root)
            doms.add(root)
        doms = sorted(doms, key=lambda x: tuple(reversed(x.split("."))))
        all_doms = doms + ["*."+i for i in doms]

        for site, url in db.to_list('''
                select
                    id, url
                from
                    sites
                where
                    type='wp' and
                    id in (
                        select site from wp_posts
                        where url like '%?p=%' or url like '%?page_id=%'
                    )
                order
                    by id
            '''):
            dom = get_dom(url)
            url_path = urlparse(url)
            if url_path.path:
                url_path = url_path.path
            else:
                url_path = ""
            root = str(dom)
            if root not in doms:
                doms.insert(0, root)
            if root not in ng_include:
                ng_include[root] = []
            ng_include[root].append("wp.nginx")

        for site, url in db.to_list("select id, url from sites where type='phpbb' order by id"):
            dom = get_dom(url)
            url_path = urlparse(url)
            if url_path.path:
                url_path = url_path.path
            else:
                url_path = ""
            root = str(dom)
            if root not in doms:
                doms.insert(0, root)
            ng_file = get_dom(url)+url_path
            ng_file = ng_file.rstrip("/")
            ng_file = ng_file.replace("/", "_")
            ng_file = "phpbb/"+ng_file
            if root not in ng_include:
                ng_include[root] = []
            ng_include[root].append(ng_file)

            path = urltopath(url)
            media = []
            for id, m, file in db.to_list("select ID, url, file from phpbb_media where site="+str(site)):
                file_path = urltopath(m, file=file)
                name = file_path.split("/download/file.php/", 1)[-1]
                media.append('''
                    if ($args ~* ".*id=%(id)s") {
                        set $args '';
                        set $file_name "%(file)s";
                        set $file_path "%(file_path)s";
                    }
                    if ($args ~* ".*id=%(id)s[^0-9].*") {
                        set $args '';
                        set $file_name "%(file)s";
                        set $file_path "%(file_path)s";
                    }
                ''' % {"id": id, "file": file, "path": name, "file_path": file_path})
            phpbb = '''
                location ~ ^%(url_path)s/viewtopic\\.php/?.*$ {
                    if ($args ~* ".*(p=[0-9]+).*") {
                        set $mid $1;
                        set $args '';
                        rewrite ^(.*/viewtopic\\.php).* $1/$mid/ last;
                    }
                    if ($args ~* ".*(t=[0-9]+).*") {
                        set $mid $1;
                        set $args '';
                        rewrite ^(.*/viewtopic\\.php).* $1/$mid/ last;
                    }
                    if ($args ~* ".*(f=[0-9]+).*") {
                        set $mid $1;
                        set $args '';
                        rewrite ^(.*/viewtopic\\.php).* $1/$mid/ last;
                    }
                }
            ''' % {"url_path": url_path}
            if media:
                phpbb = phpbb+('''
                location ~ ^%(url_path)s/download/file\\.php/?.*$ {
                    set $file_name 'not found';
                    set $file_path $document_root$uri;
                    %(media)s
                    add_header Content-disposition 'attachment; filename="$file_name"';
                    alias "%(root)s/web/$file_path";
                }
                ''') % {"url_path": url_path, "media": "\n".join(media), "root": self.root}
            self.write(phpbb, site=dom, root=self.root,
                       path=path, file=ng_file)

        l_dom = max(len(d) for d in doms)
        l_dom = l_dom*2+4
        if l_dom > 64:
            self.write("server_names_hash_bucket_size %s;" % l_dom)
        self.write('''
            server {
                listen 443 ssl;
                server_name %s;
                # rewrite ^(.*) http://$host$1 permanent;
                # https://www.digitalocean.com/community/tutorials/how-to-create-a-self-signed-ssl-certificate-for-nginx-in-ubuntu-16-04
                ssl_certificate /etc/ssl/certs/nginx-selfsigned.crt;
                ssl_certificate_key /etc/ssl/private/nginx-selfsigned.key;
                return 301 http://$http_host$request_uri;
            }
        ''' % " ".join(all_doms))
        for site in doms:
            include = ng_include.get(site, "")
            if isinstance(include, list):
                include = "\n                        ".join(
                    "include {root}/nginx/%s;" % i for i in include
                )
            path = urltopath("http://"+site)
            if site == "tomalatele.tv":
                self.write('''
                    server {
                        listen 80;
                        index index.html;
                        server_name {site} www.{site};
                        root {root}/web/{path};
                        location /main.css {
                            alias {root}/web/main.css;
                        }
                        %s
                        location ~ ^/$ {
                            return 301 /web/;
                        }
                    }
                ''' % include, site=site, root=self.root, path=path)
            else:
                self.write('''
                    server {
                        listen 80;
                        index index.html;
                        server_name {site} www.{site};
                        root {root}/web/{path};
                        location /main.css {
                            alias {root}/web/main.css;
                        }
                        %s
                    }
                ''' % include, site=site, root=self.root, path=path)
            if len(site.split(".")) == 2:
                self.write('''
                    server {
                        listen 80;
                        index index.html;
                        server_name ~^(www\.)?(?<subdomain>.+)\.{site}$;
                        root {root}/web/{path}/$subdomain;
                        location /main.css {
                            alias {root}/web/main.css;
                        }
                        %s
                    }
                ''' % include, site=site, root=self.root, path=path.rsplit("/", 1)[0])

    def close(self):
        for f in self.files.values():
            f.close()

    def write(self, txt, *args, end="\n", file="sites.nginx", **kargv):
        file = self.root + "/nginx/" + file
        if file not in self.files:
            makedirs(dirname(file), exist_ok=True)
            self.files[file] = open(file, "w")
        if args or kargv:
            flag = "---------"
            txt = txt.replace("{\n", "["+flag)
            txt = txt.replace("}\n", "]"+flag)
            txt = txt.format(*args, **kargv)
            txt = txt.replace("["+flag, "{\n")
            txt = txt.replace("]"+flag, "}\n")
        txt = dedent(txt).strip()
        txt = "\n".join(l for l in txt.split("\n") if l.strip())
        self.files[file].write(txt+end)


if __name__ == "__main__":
    from .lite import DBLite, bunch_factory
    db = DBLite("sites.db", readonly=True)
    n = Nginx(db, "_out/")
    n.close()
