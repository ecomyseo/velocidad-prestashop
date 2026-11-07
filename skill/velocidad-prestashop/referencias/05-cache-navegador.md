# 5. Caché del navegador

PageSpeed lo llama «Usar tiempos de vida de caché eficientes». Se comprueba con `scripts/revisar_cache.py`, que mide
el tiempo de caché de los CSS, JS, imágenes y fuentes de cada web y verifica que las páginas y el JSON no se guarden.

## Qué esperar de verdad

- **La primera visita no cambia.** La caché solo actúa cuando el visitante vuelve o pasa a otra página.
- **Chrome ya guarda los ficheros por su cuenta** si no hay cabeceras: un 10 % de su antigüedad (un CSS de hace un
  año, unos 36 días). Medido en una portada de 31 ficheros: sin cabeceras, quien volvía al día siguiente tenía que
  volver a pedir 6 ficheros, y a los 30 días 12; con cabeceras, ninguno.
- La mejora es sobre todo en visitas repetidas y en la nota de PageSpeed. Se dice así al dueño de la tienda.

## Apache: el módulo puede estar apagado

El `.htaccess` de PrestaShop trae las reglas dentro de `<IfModule mod_expires.c>`. **Si el módulo no está cargado, no
pasa nada y no hay ningún aviso.** Se mira con `apache2ctl -M | grep expires` (o en Plesk
`/usr/local/psa/admin/sbin/httpd_modules_ctl -s -o expires`).

### Antes de encenderlo: buscar `ExpiresDefault`

Encender `mod_expires` afecta a **todas las webs del servidor**. Antes, se buscan en todos los `.htaccess` del
servidor las reglas que se van a activar:

```
grep -rn "ExpiresDefault\|ExpiresByType" /var/www/vhosts/*/httpdocs/.htaccess
```

Un `ExpiresDefault "access plus 1 month"` sin excepciones **da un mes de caché a las páginas y al JSON**: filtros del
listado, carrito por AJAX, búsqueda. Los clientes verían precios, stock o filtros de hace días. Se añade, justo
después:

```apache
ExpiresByType text/html "access plus 0 seconds"
ExpiresByType application/json "access plus 0 seconds"
ExpiresByType application/xml "access plus 0 seconds"
ExpiresByType text/xml "access plus 0 seconds"
```

`plantillas/htaccess-cache-seguro.txt` trae un bloque completo.

### Cómo se comporta `mod_expires`

- No toca una respuesta que ya trae `Expires` (por ejemplo, el carrito, que PHP manda con `Expires: 1981`).
- **No toca las respuestas 4xx ni 5xx.** Para comprobar un JSON hace falta uno que responda 200.
- `Header set Cache-Control ...` (mod_headers) se aplica después y gana.
- Plesk: `httpd_modules_ctl -e expires`, `apachectl configtest`, `systemctl reload apache2`.

## nginx delante

- Hestia ya pone `expires max` a los estáticos que sirve nginx: ahí el módulo de Apache da igual.
- En Plesk con «servir estáticos con nginx», los ficheros que existen en disco los sirve nginx **sin** las cabeceras
  de Apache: hay que ponerlas en las directivas de nginx del dominio.
- **Si nginx tiene `proxy_cache`** (la caché de nginx de Plesk), lo que Apache marque con caché larga se guarda en el
  servidor y se sirve a todos. Antes de dar caché larga a algo dinámico, mirar si el dominio tiene caché de nginx.

## Tiempos razonables

| Tipo | Tiempo |
|---|---|
| CSS y JS con versión en el nombre o en `?v=` | 1 año |
| CSS y JS sin versión | 1 semana |
| Imágenes | 1 mes |
| Fuentes | 1 año |
| HTML, JSON, XML | 0 |
