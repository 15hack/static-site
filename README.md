Crea un versión minimalista y estática de los sitios web capturados por https://github.com/15hack/web-backup

Para generar los ficheros hay que lanzar `run.py` (o `run.py --dwn` para
también descargar los archivos multimedia), esto generara en:

* `_out/web` las versiones estáticas de las web
* `_out/nginx/sites.nginx` la configuración del servidor para servir las páginas

Para minimizar el mantenimiento, se escribe `sites.nginx` para que redirigía
todo el tráfico `https` a `http` y así no tener que estar renovando certificados.

Para que esto funcione, se ha de generar un [certificado autofirmado](https://www.digitalocean.com/community/tutorials/how-to-create-a-self-signed-ssl-certificate-for-nginx-in-ubuntu-16-04) en `/etc/ssl/certs/nginx-selfsigned.{crt,key}`.
