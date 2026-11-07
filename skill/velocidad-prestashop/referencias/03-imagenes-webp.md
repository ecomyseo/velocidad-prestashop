# 3. Imágenes y WebP

Las imágenes son casi siempre lo que más pesa. Resultados reales, anonimizados:

| Qué | Antes | Después |
|---|---|---|
| Portada con banners en PNG (PC + móvil) | 26,5 MB | 4,8 MB |
| Portada de otra tienda (banners del slider) | 10,1 MB | 1,1 MB |
| Un banner principal (elemento LCP) | 4,4 MB | 277 KB |
| Miniaturas de producto de una tienda (25.937 ficheros) | 733 MB | 504 MB |

Hay tres frentes y conviene atacarlos en este orden.

## A. Fotos de producto: el WebP del núcleo (PrestaShop 8.1 y posteriores)

1. En *Diseño > Ajustes de imagen* activar el formato WebP (por debajo es la función `multiple_image_format`) y
   regenerar las miniaturas.
2. **La calidad importa más de lo que parece.** Si los JPG originales ya están comprimidos (calidad ~75), un WebP a
   85 pesa lo mismo que el JPG. Hay que medir: en una tienda, con calidad 85 no se ganaba nada y con 75 se ganó un 31 %.
3. **Un WebP más viejo que su imagen enseña la foto anterior.** Si alguien cambia la foto de un producto y el WebP no
   se regenera, el navegador que acepta WebP ve la vieja. En una tienda había 408 productos así. Toda generación de
   WebP rehace los que son más antiguos que su imagen original.
4. Las tareas programadas que dicen convertir a WebP **hay que comprobarlas**: una llamaba a `cwebp`, que no estaba
   instalado, y escribía ficheros con un nombre que nadie servía. Llevaba meses sin hacer nada.

## B. La plantilla tiene que pedir el WebP

El tema *classic* de PrestaShop 8 ya usa `<picture>` con `sources.webp`. **Muchos temas de terceros no**, y entonces
el WebP del núcleo existe en disco pero nadie lo pide.

### El parcial que se ha usado (anónimo)

`plantillas/webp-si-existe.tpl` deja en una variable la URL del WebP de una foto de producto **solo si el fichero
existe**, y si no, la del JPG de siempre:

```smarty
{include file='catalog/_partials/webp-si-existe.tpl' ew_imagen=$product.cover ew_tipo='home_default' ew_var='urlMiniatura'}
<img loading="lazy" src="{$urlMiniatura}" ...>
```

Se incluye en los cuatro sitios donde la plantilla pinta fotos de producto:

| Sitio | Fichero habitual | Tipo de imagen |
|---|---|---|
| Miniatura del listado | `catalog/_partials/miniatures/product.tpl` | `home_default` |
| Foto principal de la ficha | `catalog/_partials/product-cover-thumbnails.tpl` | `large_default` |
| Miniaturas de la galería (y el `data-image-large-src` que cambia la foto grande) | el mismo | `medium_default` / `large_default` |
| Ventana de zoom (modal) | `catalog/_partials/product-images-modal.tpl` | `large_default` / `home_default` |

### Lo que se encontró en los temas, y cómo se arregló

- **`file_exists()` sobre una URL.** El tema intentaba elegir el WebP con
  `{if file_exists($urlDelWebp)}`: con una URL, `file_exists` devuelve siempre falso. El parcial comprueba la ruta en
  disco (`_PS_PROD_IMG_DIR_` + carpeta de la imagen).
- **No usar `<picture>` si el JavaScript del tema cambia el `src` de la foto grande** al pulsar una miniatura: el
  `<source>` de delante manda y la foto deja de cambiar. En ese caso se cambia el `src` (y el `data-image-large-src`).
- **La ventana de zoom oculta descargaba la foto otra vez, en JPG.** El modal está en el HTML desde el principio,
  aunque no se vea, y su `<img>` pedía la URL JPG. Resultado: la foto principal se bajaba dos veces. Se le puso la
  misma URL WebP que a la foto principal y `loading="lazy"`.
- **La precarga tiene que pedir la misma URL que pinta la plantilla.** Si algo (un módulo o el propio tema) hace
  `<link rel="preload" as="image" href="...jpg">` y la plantilla pinta el `.webp`, la foto se descarga dos veces. La
  precarga lleva el mismo formato y `type="image/webp"`.
- **Las primeras fotos del listado sin carga diferida.** Si la primera fila del listado usa `data-src` y la pinta un
  JavaScript, el LCP espera al JavaScript. Las 4 primeras van con `src` normal; el resto, diferidas.
- **`fetchpriority="high"` solo en la imagen LCP** (la primera diapositiva del slider o la foto de la ficha), nunca en
  todas.
- **Un carrusel con carga diferida en la primera diapositiva** hace que el banner principal espere al JavaScript. La
  primera diapositiva, sin diferir.

**Cómo se comprueba:** listar las peticiones de la ficha (`scripts/medir.py` da las más pesadas) y ver que cada foto se
baja **una sola vez** y en WebP.

## C. Banners, slider, páginas CMS y logos

El núcleo no crea WebP de lo que suben los módulos del tema (slider, banners) ni de `img/cms`. Lo que mejor ha
funcionado sin tocar plantillas ni originales:

1. **Un WebP al lado de cada imagen**: `banner.png` → `banner.png.webp`. La original no se toca nunca.
2. **El servidor entrega el WebP en la misma URL** al navegador que lo acepta (cabecera `Accept: image/webp`), con
   `Vary: Accept`. El que no lo acepta recibe la original.

### Con Apache sirviendo las imágenes

`plantillas/htaccess-webp.txt`: un `RewriteCond %{HTTP_ACCEPT} image/webp` + `RewriteCond %{REQUEST_FILENAME}.webp -f`.

### Con nginx delante (Hestia, Plesk con «servir estáticos con nginx», muchos VPS)

**El `.htaccess` no se aplica**: nginx sirve la imagen directamente y Apache no se entera. Es la causa más frecuente
de «tengo los WebP y no se sirven». `plantillas/nginx-webp.conf` trae:

- un `map $http_accept $webp_sufijo` (en el `http {}`, por ejemplo `/etc/nginx/conf.d/`);
- un `location ^~ /img/cms/ { ... }` por carpeta. **El `^~` es imprescindible**: las plantillas de los paneles ponen
  una `location ~* \.(jpg|png|...)$` de estáticos, y una location con expresión regular gana a cualquier location
  normal que se añada al final. Con `^~` se gana a las expresiones regulares;
- dentro, una location para `png|jpe?g` con `try_files $uri$webp_sufijo $uri @fallback;`, otra que niega los ficheros
  ocultos, otra que repite la de estáticos de la plantilla, y para todo lo demás (por ejemplo un `index.php`)
  `try_files` a la location que pasa a Apache. Así no se sirve nunca un PHP como texto.

### Convertir bien

`scripts/webp_al_lado.py` (Pillow):

- aplica la **orientación EXIF** (si no, una foto de móvil sale girada);
- convierte a **sRGB** las imágenes con otro perfil de color (las capturas de pantalla de Mac vienen en Display P3, y
  muchas fotos en Adobe RGB): sin eso los colores salen apagados;
- pasa **CMYK** a RGB y **conserva la transparencia**;
- **no cambia las dimensiones** (si una imagen se reduce por debajo de lo que la página pinta, el diseño cambia);
- solo guarda el WebP si pesa **al menos un 10 % menos** (un PNG pequeño de pocos colores puede pesar más en WebP, y
  el servidor lo serviría igual);
- deja un registro de lo creado para deshacerlo.

### Que siga funcionando con los banners nuevos

Un banner nuevo subido sin su WebP vuelve a pesar 3 MB. Hace falta algo que lo cree al subirlo o una tarea
programada: el módulo `ecom_webpauto` de este repositorio lo hace al guardar la imagen en el back-office y entrega el
WebP por `.htaccess` (con nginx delante, además, la configuración de arriba).

## D. Tamaño

- Una imagen de 1.500 px pintada a 365 px pesa diez veces lo necesario. Lo bueno es subirla al tamaño correcto.
- Si se reduce automáticamente, nunca por debajo del **doble** del ancho que se pinta (pantallas de alta densidad), y
  midiendo ese ancho en la pantalla más grande.
