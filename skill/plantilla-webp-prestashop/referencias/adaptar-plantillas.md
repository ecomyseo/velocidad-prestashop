# Adaptar las plantillas con el parcial

## El parcial

`plantillas/webp-si-existe.tpl` se copia a `templates/catalog/_partials/webp-si-existe.tpl` **del tema hijo** (o del
tema, si no hay hijo). Deja en una variable la URL WebP de una foto **solo si el fichero existe**; si no, la JPG.

| Parámetro | Valor |
|---|---|
| `ew_imagen` | `$product.cover`, `$product.default_image` o cada `$image` de `$product.images` |
| `ew_tipo` | `home_default`, `large_default`, `medium_default`, `small_default`, `cart_default`… o los alias `large`, `medium`, `small` (el parcial busca a qué tipo real corresponden) |
| `ew_var` | nombre de la variable que se crea en la plantilla que lo incluye |
| `ew_formato` | opcional: `webp` (por defecto) o `avif` |
| `ew_sin` | opcional: `jpg` (por defecto) o `vacio` (cadena vacía si no hay fichero, para un `<source>`) |

Qué devuelve, por orden: la URL `sources.<formato>` del núcleo (8.1+) si el fichero existe; si existe pero el núcleo no
da URL (1.7, o formato múltiple apagado), la ruta física `_THEME_PROD_DIR_` + carpeta + `id-tipo.webp`; si no existe,
la JPG (o vacío). La variable se asigna **siempre**, así que dentro de un `{foreach}` cada foto lleva la suya.

No hace falta `|escape`: el front de PrestaShop ya escapa la salida (`escape_html`, `config/smartyfront.config.inc.php`).

## Sitio por sitio (antes → después)

### Miniatura del listado (`catalog/_partials/miniatures/product.tpl`)

```smarty
{* antes *}
<img loading="lazy" src="{$product.cover.bySize.home_default.url}" ...>

{* después *}
{include file='catalog/_partials/webp-si-existe.tpl' ew_imagen=$product.cover ew_tipo='home_default' ew_var='urlMiniatura'}
<img loading="lazy" src="{$urlMiniatura}" ...>
```

Si el tema usa `data-src` + un JavaScript de carga diferida, se cambia la URL en `data-src` igual, y **las 4 primeras
miniaturas** del listado van con `src` normal (`{if $product@iteration <= 4}` o el contador del bucle que use el tema):
si no, la imagen LCP espera a ese JavaScript.

### Foto principal de la ficha (`catalog/_partials/product-cover-thumbnails.tpl`)

```smarty
{include file='catalog/_partials/webp-si-existe.tpl' ew_imagen=$product.default_image ew_tipo='large_default' ew_var='urlPortada'}
<img class="js-qv-product-cover img-fluid" src="{$urlPortada}" fetchpriority="high" width="..." height="...">
```

`fetchpriority="high"` solo aquí (la imagen LCP de la ficha). `rel="preload"` en un `<img>` no hace nada: se quita.

### Miniaturas de la galería y lo que cambia la foto grande

El JavaScript del tema lee `data-image-large-src` (y a veces `data-image-medium-src`) al pulsar una miniatura y lo pone
en el `src` de la foto grande: **tiene que llevar también la URL WebP**, o al pulsar se baja el JPG.

```smarty
{foreach from=$product.images item=image}
  {include file='catalog/_partials/webp-si-existe.tpl' ew_imagen=$image ew_tipo='large_default' ew_var='urlGrande'}
  {include file='catalog/_partials/webp-si-existe.tpl' ew_imagen=$image ew_tipo='medium_default' ew_var='urlMediana'}
  <img class="thumb js-thumb" data-image-medium-src="{$urlMediana}" data-image-large-src="{$urlGrande}"
       src="{$urlMediana}" loading="lazy" ...>
{/foreach}
```

Ninguna miniatura de la galería lleva `fetchpriority="high"`.

### Ventana de zoom (`catalog/_partials/product-images-modal.tpl`)

El modal está en el HTML desde el principio aunque no se vea, y su `<img>` **se descarga igual**. Si pide el JPG, la foto
principal se baja dos veces. Misma URL que la foto principal y `loading="lazy"` (una imagen oculta y diferida no se
pide hasta que se abre). El modal suele usar los alias `large`/`medium`: el parcial los acepta.

```smarty
{include file='catalog/_partials/webp-si-existe.tpl' ew_imagen=$product.cover ew_tipo='large' ew_var='webpModal'}
<img loading="lazy" class="js-modal-product-cover product-cover-modal" src="{$webpModal}" ...>
{foreach from=$product.images item=image}
  {include file='catalog/_partials/webp-si-existe.tpl' ew_imagen=$image ew_tipo='large' ew_var='webpModalGrande'}
  {include file='catalog/_partials/webp-si-existe.tpl' ew_imagen=$image ew_tipo='medium' ew_var='webpModalMini'}
  <img loading="lazy" data-image-large-src="{$webpModalGrande}" class="thumb js-modal-thumb" src="{$webpModalMini}" ...>
{/foreach}
```

### Quickview, ventana del carrito y carruseles de módulos

`quickview.tpl` suele incluir `product-cover-thumbnails.tpl` (queda cubierto). La ventana del carrito
(`modules/ps_shoppingcart/modal.tpl` dentro del tema) y los carruseles de módulos sobrescritos en
`themes/<tema>/modules/…` se adaptan igual. Al cambiar de combinación, el núcleo vuelve a pedir
`product-cover-thumbnails` por AJAX (`ProductController.php:522` en 8.2.7): si el parcial está dentro, sigue en WebP.

### Precarga de la foto LCP

Si el tema o un módulo pinta `<link rel="preload" as="image">`, tiene que pedir **la misma URL** que el `<img>`:

```smarty
{include file='catalog/_partials/webp-si-existe.tpl' ew_imagen=$product.default_image ew_tipo='large_default' ew_var='webpPrecarga' ew_sin='vacio'}
{if $webpPrecarga}
  <link rel="preload" as="image" href="{$webpPrecarga}" type="image/webp">
{else}
  <link rel="preload" as="image" href="{$product.default_image.bySize.large_default.url}">
{/if}
```

Una precarga en JPG con la foto pintada en WebP = dos descargas de la misma foto.

### Variante `<picture>` (solo si el JavaScript no cambia el `src` de esa foto)

Para miniaturas del listado y sitios donde ningún JS toca la imagen:

```smarty
{include file='catalog/_partials/webp-si-existe.tpl' ew_imagen=$product.cover ew_tipo='home_default' ew_var='webpMiniatura' ew_sin='vacio'}
<picture>
  {if $webpMiniatura}<source srcset="{$webpMiniatura}" type="image/webp">{/if}
  <img src="{$product.cover.bySize.home_default.url}" loading="lazy" width="..." height="...">
</picture>
```

**No** en la foto grande de la ficha si el JavaScript del tema hace `img.src = data-image-large-src`: el `<source>`
manda sobre el `src` y la foto deja de cambiar al pulsar las miniaturas. El tema classic de 8.x sí actualiza los
`<source>` (lee `data-image-large-sources`); la mayoría de temas de terceros, no. Se mira en su JS antes de elegir.

## Trampas encontradas en temas reales

| Trampa | Qué pasa | Arreglo |
|---|---|---|
| `{if file_exists($urlDelWebp)}` | `file_exists` con una URL es siempre falso: nunca elige el WebP | Ruta de disco, como el parcial |
| `{$url\|replace:'.jpg':'.webp'}` sin comprobar | Si el WebP no existe, foto rota; en 1.7 la URL amigable `.webp` ni se sirve | El parcial |
| `_PS_PROD_IMG_DIR_` / `Image::getImgFolderStatic()` en la plantilla | En 9.x la constante no existe: siempre JPG, sin error; la clase da aviso de obsoleto | El parcial (calcula la carpeta él mismo) |
| `<picture>` + JS que cambia el `src` | La foto grande no cambia al pulsar miniaturas | Cambiar `src` y `data-image-large-src` |
| Modal de zoom oculto en JPG | La foto principal se baja dos veces | Misma URL WebP + `loading="lazy"` |
| Precarga en otro formato | Dos descargas de la foto LCP | Misma URL en la precarga |
| Primeras miniaturas con `data-src` + JS | El LCP espera al JavaScript | Las 4 primeras con `src` normal |
| `fetchpriority="high"` en todas las miniaturas de un bucle | Ninguna tiene prioridad de verdad | Solo en la imagen LCP |
| WebP más viejo que su JPG | Quien acepta WebP ve la foto ANTERIOR | `scripts/revisar_img_p.py` y regenerar |
| WebP a calidad alta sobre JPG ya comprimidos | Pesa casi lo mismo que el JPG (medido: a 85 no se ganaba nada; a 75, un 31 % menos) | Bajar «Compresión WebP» y medir |
| Compilados de Smarty de plantillas de módulos (`*.module.*.tpl.php` y `*.tpl.cache.php`) | No caen con un borrado por el nombre de las plantillas del tema: el carrusel de un módulo sigue pintando el HTML viejo | Vaciar la carpeta de compilados entera (ver `procedimiento-seguro.md`) |
