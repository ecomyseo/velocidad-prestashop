# Procedimiento seguro: copia, compilación, cachés y comprobación

## 1. Copia de cada plantilla antes de tocarla

En el servidor, como el usuario dueño de los ficheros de la web:

```
COPIAS=$HOME/copias-plantilla-webp TIENDA=/ruta/de/la/tienda \
sh copia_y_volver.sh /ruta/de/la/tienda/themes/<tema-hijo> \
   templates/catalog/_partials/miniatures/product.tpl \
   templates/catalog/_partials/product-cover-thumbnails.tpl \
   templates/catalog/_partials/product-images-modal.tpl \
   templates/catalog/_partials/webp-si-existe.tpl
```

- Copia las que existen (comprobando con `cmp` que la copia es idéntica) y apunta las que no existen (el parcial nuevo,
  o una plantilla del padre que se copia al hijo): `volver.sh` las borrará.
- Las copias van **fuera de la carpeta de la web**.
- `volver.sh` repone, comprueba cada fichero con `cmp` y, si se dio `TIENDA`, vacía la caché de Smarty. Sale con 1 si
  algo no se pudo reponer.
- Se nombran **todas** las plantillas que se vayan a tocar, también las del padre que se copian al hijo.

## 2. Compilar antes de subir

Con el Smarty **de la propia tienda** (no otro): en el servidor, o con una copia de su `vendor/smarty` en local.

```
php probar_tpl.php --smarty=<tienda>/vendor/smarty/smarty/libs/Smarty.class.php \
    --tema=<tema-hijo>/templates --padre=<tema-padre>/templates --orig=<copia>/antes/templates \
    catalog/_partials/miniatures/product.tpl catalog/_partials/product-cover-thumbnails.tpl \
    catalog/_partials/product-images-modal.tpl catalog/_partials/webp-si-existe.tpl
php probar_tpl.php --smarty=<tienda>/vendor/smarty/smarty/libs/Smarty.class.php --probar-parcial
```

- No carga PrestaShop: las etiquetas propias (`{l}`, `{url}`, `{hook}`, `{widget}`…) se sustituyen por vacíos y
  `parent:` lee del `--padre`. Registra los modificadores y clases que registra la tienda en
  `config/smarty.config.inc.php`, para que los avisos de obsoleto que salgan sean los mismos que en la tienda.
- Con `--orig`, si una plantilla falla y la original da **el mismo** error, es del banco de pruebas, no del cambio.
- `--probar-parcial` comprueba 13 casos (con y sin fichero, con y sin URL del núcleo, alias, AVIF, sin imagen, dentro de
  un bucle, sin avisos de obsoleto). Medido: 0 fallos con Smarty 3.1.48, 4.3.4, 4.5.5 y 4.5.7, con PHP 7.4 y 8.3.
- Y antes de subir, `python buscar_fotos_sin_webp.py <tema>`: tiene que quedar sin `SIN WEBP` ni `TRAMPA` (o con
  los que se dejan a propósito, explicados).

## 3. Subir y vaciar cachés

- Caché de Smarty: *Parámetros avanzados > Rendimiento > Borrar caché*, o vaciar **entero el contenido** de
  `var/cache/prod/smarty/compile/` y `var/cache/prod/smarty/cache/` (y los de `dev`). No borrar por nombre de
  plantilla: los compilados de plantillas de módulos se llaman `*.module.<módulo>…tpl.php` o `…tpl.cache.php` y los
  carruseles de módulos con caché propia seguirían sirviendo el HTML viejo.
- Con «Recompilar plantillas: nunca» (`PS_SMARTY_FORCE_COMPILE = 0`), sin vaciar la caché los cambios **no se ven**.
- Si la caché de Smarty está en MySQL (`_PS_SMARTY_CACHING_TYPE_ = 'mysql'`), borrar carpetas no basta: el botón del
  back-office.
- Caché de página completa (módulo, Varnish, CDN): vaciarla también, o se seguirá sirviendo el HTML de antes.
- OPcache con revalidación desactivada: los `.tpl` no le afectan, pero los compilados `.php` sí; si tras vaciar Smarty
  sigue saliendo lo viejo, reiniciar PHP-FPM o vaciar OPcache.

## 4. Comprobar de verdad

Primero, el HTML: guardar la portada, una categoría y una ficha (como visitante, sin sesión) y pasar
`python revisar_html.py pagina.html`. Tiene que dar 0 fotos en JPG (salvo las que se dejan a propósito), 0 dobles,
una sola `fetchpriority="high"` y las primeras miniaturas sin `data-src`.

Después, el navegador (las herramientas de desarrollo, pestaña Red, filtro «Img»), en **listado, ficha y modal**:

- Cada foto de producto aparece **una sola vez** y con tipo **`image/webp`** (columna Tipo o la cabecera
  `Content-Type`), no `image/jpeg`.
- En la ficha, **pulsar varias miniaturas**: la foto grande cambia y lo que se pide es `.webp`.
- **Abrir la ventana de zoom**: no se vuelve a bajar la foto principal en JPG.
- Al **cambiar de combinación**, las fotos siguen saliendo en WebP.
- Ninguna petición a un `.webp` da 404.
- **Consola**: los mismos errores de JavaScript que antes del cambio, ni uno más (apuntarlos antes de tocar nada).

Si algo falla: `sh volver.sh` y se vuelve exactamente al estado anterior.
