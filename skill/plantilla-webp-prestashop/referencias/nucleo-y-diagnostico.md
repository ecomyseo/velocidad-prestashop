# Núcleo por versión y diagnóstico

Todo lo de esta tabla está comprobado en el código de PrestaShop 1.7.8.11, 8.1.7, 8.2.7 y 9.1.1 (rutas y líneas
de esas versiones). La 8.0 no se ha comprobado: mirar su código antes de dar nada por hecho.

| | 1.7.8 | 8.1 / 8.2 | 9.1 |
|---|---|---|---|
| El núcleo genera WebP de las fotos de producto | **No** | Sí, con dos condiciones (abajo) | Sí, con una condición |
| `sources` en cada tamaño (`$image.bySize.<tipo>.sources.webp`) | **No existe** | Sí (`src/Adapter/Image/ImageRetriever.php:223-269`) | Sí (`ImageRetriever.php:196-239`) |
| Condición | — | interruptor `multiple_image_format` (`install/data/xml/feature_flag.xml:18`, **apagado** por defecto) **y** WebP marcado en *Diseño > Ajustes de imagen* (`PS_IMAGE_FORMAT`, por defecto `jpg`) | Solo `PS_IMAGE_FORMAT` (`src/Core/Image/ImageFormatConfiguration.php`, ya sin interruptor) |
| Genera la miniatura que falta al pintar la página | Solo JPG | Sí, en cada formato configurado (`ImageRetriever::checkOrGenerateImageType`, `:304-335`) | Sí |
| URL amigable `.webp` servida por el `.htaccess` | **No**: las reglas solo reescriben `.jpg` (`classes/Tools.php:2666-2682`) | Sí: `jpe?g\|webp\|png\|avif` (`Tools.php:2512-2525` en 8.2.7) | Sí |
| `Link::getImageLink()` | `($name, $ids, $type)` | 4.º argumento `$extension = 'jpg'` (`classes/Link.php:990`) | Igual (`Link.php:941`) |
| Constante de la carpeta | solo `_PS_PROD_IMG_DIR_` | `_PS_PRODUCT_IMG_DIR_` y `_PS_PROD_IMG_DIR_` (obsoleta) (`config/defines.inc.php:155-157`) | **solo `_PS_PRODUCT_IMG_DIR_`** (`defines.inc.php:153`) |
| `_PS_IMG_DIR_` y `_THEME_PROD_DIR_` | existen | existen | existen |
| Smarty | 3.1.48 | 4.3.4 | 4.5.x: avisa de obsoleto con funciones y clases **sin registrar**; PrestaShop registra `file_exists` (`config/smarty.config.inc.php:120`) y 9 clases (`Configuration`, `Tools`…), **no `Image`** |
| Calidad del WebP | — | `PS_WEBP_QUALITY`, 80 por defecto (`configuration.xml:401`), campo «Compresión WebP» en *Ajustes de imagen* | Igual |
| Tema por defecto | classic sin `<picture>` | classic con `<picture>` + `sources` y `data-image-large-sources` (su JS cambia los `<source>`) | Hummingbird con `<picture>` |

Consecuencias:

- En **1.7** no hay `sources`: si los WebP existen en disco (generados por otra herramienta), la URL amigable `.webp`
  da 404 con el `.htaccess` del núcleo. El parcial usa entonces la **ruta física** `/img/p/1/2/12-tipo.webp`, que se
  sirve en todas las versiones.
- `$smarty.const.X` compila a `(defined('X') ? constant('X') : null)`: una constante que no existe **no da error**.
  Medido: un parcial que usaba `_PS_PROD_IMG_DIR_` devolvía el WebP en un Smarty de 8.x y **siempre el JPG** con la
  constante ausente (como en 9.x), sin un aviso.
- El `<picture>` del tema classic de 8.x pinta el `<source>` en cuanto el núcleo da la URL, sin mirar el disco. Si la
  generación falla (GD sin WebP, memoria), el navegador pide un `.webp` que no existe y la foto sale rota.

## Diagnóstico, paso a paso

1. **¿Genera el núcleo WebP?**
   - Base de datos: `SELECT value FROM <prefijo>configuration WHERE name='PS_IMAGE_FORMAT'` (`jpg,webp`) y, en 8.1/8.2,
     `SELECT state FROM <prefijo>feature_flag WHERE name='multiple_image_format'` (1).
   - Disco: `ls <tienda>/img/p/1/2/12-*` para un `id_image` conocido.
   - Conjunto: `python3 scripts/revisar_img_p.py <tienda>/img/p` → cuántos tienen WebP, cuántos están **viejos** (más
     antiguos que su JPG: el visitante vería la foto anterior) y cuánto pesa el WebP frente al JPG (si pasa del 85 %,
     los JPG ya venían comprimidos: bajar la calidad a ~75 y medir otra vez).
2. **¿Los pide la plantilla?** Ver el código fuente de una ficha y de una categoría: `.webp` en `src`/`srcset` o en un
   `<source type="image/webp">`. Con la página guardada: `python scripts/revisar_html.py pagina.html`.
3. **¿Qué tema y de quién hereda?** `themes/<tema>/config/theme.yml`: si tiene `parent:`, es hijo. Las plantillas que
   están en el hijo mandan; las que no, salen del padre. Lo que se cambie se pone **en el hijo** (copiando la plantilla
   del padre si el hijo no la tiene).
4. **¿Dónde pinta fotos de producto?** `python scripts/buscar_fotos_sin_webp.py themes/<tema>`. A mano, estos `grep`:

   ```
   grep -rnE "bySize|\.cover\.|default_image|large_default|home_default|medium_default|small_default|cart_default" themes/<tema> --include=*.tpl
   grep -rnE "data-image-(large|medium)-src|data-src|getImageLink|rel=.preload|fetchpriority|file_exists|replace:'\.jpg'" themes/<tema> --include=*.tpl
   grep -rln "product-images-modal\|quickview\|js-qv-product-cover\|js-modal-product-cover" themes/<tema>
   ```

   Sitios habituales: `catalog/_partials/miniatures/product.tpl` (listado), `catalog/_partials/product-cover-thumbnails.tpl`
   (foto principal y galería), `catalog/_partials/product-images-modal.tpl` (zoom), `catalog/_partials/quickview.tpl`,
   `catalog/product.tpl` (a veces una segunda foto o una precarga), `modules/ps_shoppingcart/modal.tpl` (ventana del
   carrito), y las plantillas de módulos de carruseles dentro de `themes/<tema>/modules/`.
   Hasta los temas oficiales dejan una en JPG: la ventana del carrito (`modules/ps_shoppingcart/modal.tpl`), en el
   classic de 8.2.7 y en el Hummingbird de una 9.1 de pruebas (medido con `buscar_fotos_sin_webp.py`).
5. **JavaScript del tema**: buscar en sus `.js` `data-image-large-src`, `js-qv-product-cover`, `.attr('src'`, `srcset`.
   Decide si se puede usar `<picture>` o hay que cambiar el `src` (ver `adaptar-plantillas.md`).
