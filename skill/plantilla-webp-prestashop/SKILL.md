---
name: plantilla-webp-prestashop
description: Adaptar la plantilla (tema) de una tienda PrestaShop 1.7, 8 o 9 para que pida las imágenes WebP (o AVIF) de las fotos de producto, solo cuando el fichero existe. Usar cuando se diga «la plantilla no carga los WebP», «adapta el tema a WebP», «PageSpeed pide formatos de imagen modernos / servir imágenes en formatos de próxima generación», «el núcleo genera WebP pero la web sigue bajando JPG», «la foto se descarga dos veces», o al revisar miniaturas, ficha, galería, ventana de zoom o precarga de la foto LCP de un tema propio, de terceros o hijo.
---

# Plantilla WebP en PrestaShop

El núcleo puede generar `N-tipo.webp` al lado de cada miniatura, pero **la web solo los usa si la plantilla los
pide**. Muchos temas de terceros pintan `{$…bySize.home_default.url}` (JPG) a pelo, o intentan elegir el WebP con
trucos que no funcionan. Este skill adapta el tema **sin romper nada**: el WebP se pide solo si el fichero existe; si
no, sale el JPG de siempre.

## Flujo (en este orden)

1. **Diagnóstico** → `referencias/nucleo-y-diagnostico.md`
   - ¿Hay WebP en disco? `ls img/p/1/2/12-home_default.*` y `python scripts/revisar_img_p.py <tienda>/img/p`
     (cobertura por tipo, WebP más viejos que su JPG, peso WebP/JPG). Solo lee.
   - ¿Qué versión? 1.7 no genera WebP; 8.1/8.2 necesitan el interruptor `multiple_image_format` **y** WebP marcado en
     *Diseño > Ajustes de imagen*; 9.x solo lo segundo.
   - ¿Tema hijo? `config/theme.yml` con `parent:` → **se cambia en el hijo**, nunca en el padre.
   - ¿Dónde pinta fotos? `python scripts/buscar_fotos_sin_webp.py <carpeta del tema>` (revisa también las plantillas del
     padre que el hijo no sustituye) y lista líneas SIN WEBP, TRAMPAS y AVISOS.
2. **Copia antes de tocar**: `sh scripts/copia_y_volver.sh <tema> <plantillas…>` deja las copias fuera de la web y un
   `volver.sh` que las repone. → `referencias/procedimiento-seguro.md`
3. **Adaptar** con el parcial `plantillas/webp-si-existe.tpl` (copiarlo a `templates/catalog/_partials/` del tema
   hijo) en cada sitio: miniatura del listado, foto principal, miniaturas de la galería **y su
   `data-image-large-src`**, ventana de zoom, quickview, precarga. → `referencias/adaptar-plantillas.md`
4. **Compilar antes de subir**: `php scripts/probar_tpl.php --smarty=<tienda>/vendor/smarty/smarty/libs/Smarty.class.php --tema=<tema>/templates [--padre=…] [--orig=<copia>] <plantillas…>`
   (con el Smarty de la propia tienda) y `--probar-parcial` para el parcial.
5. **Subir, vaciar caché de Smarty** (y la de página si la hay) y **comprobar** que cada foto se baja **una vez y en
   `image/webp`** en listado, ficha (pulsando miniaturas) y modal, con los mismos errores de JavaScript que antes.
   Ayuda estática: `python scripts/revisar_html.py pagina.html`. → `referencias/procedimiento-seguro.md`

## Reglas que no se negocian

- **WebP solo si existe en disco.** Un `<source>` o un `src` a un `.webp` que no existe deja la foto rota.
- **`file_exists()` sobre una URL es siempre falso.** Se comprueba la ruta `_PS_IMG_DIR_ . 'p/' . carpeta . id-tipo.webp`.
- **No usar `_PS_PROD_IMG_DIR_` ni `Image::getImgFolderStatic()` en la plantilla**: la constante no existe en
  PrestaShop 9 (el parcial devolvería siempre JPG, sin error) y la clase sin registrar da aviso de obsoleto en el
  Smarty 4.5 de PS 9. El parcial de este skill no usa ninguna de las dos (medido con Smarty 3.1.48, 4.3.4, 4.5.5 y 4.5.7).
- **`<picture>` solo si el JavaScript del tema actualiza los `<source>`** al cambiar de foto. Si el JS solo cambia
  `img.src`, el `<source>` manda y la foto grande deja de cambiar: entonces se cambia el `src` y el `data-image-large-src`.
- **Una foto, un formato, una descarga**: la ventana de zoom oculta y la precarga piden la **misma URL** que la foto
  principal; el modal lleva `loading="lazy"`.
- **`fetchpriority="high"` en una sola imagen** (la LCP); las 4 primeras miniaturas del listado con `src` normal, sin
  carga diferida por JavaScript.
- Datos estructurados (`og:image`, JSON-LD) y correos se dejan en JPG.
- Nada se toca en producción sin copia y sin `volver.sh`; nada se da por bueno sin mirar las peticiones reales.

## Ficheros

| Fichero | Qué es |
|---|---|
| `plantillas/webp-si-existe.tpl` | El parcial (Smarty, PS 1.7/8/9). Parámetros documentados en su cabecera. |
| `scripts/buscar_fotos_sin_webp.py` | Lista en un tema las líneas que pintan fotos sin WebP y las trampas. Solo lee. |
| `scripts/probar_tpl.php` | Compila `.tpl` con el Smarty de la tienda sin cargar PrestaShop; `--probar-parcial` prueba el parcial. |
| `scripts/copia_y_volver.sh` | Copia las plantillas antes de tocarlas y escribe `volver.sh`. |
| `scripts/revisar_html.py` | Cuenta en el HTML servido fotos en JPG, dobles descargas, `fetchpriority` y miniaturas diferidas. |
| `scripts/revisar_img_p.py` | En `img/p`: WebP que faltan, WebP más viejos que su JPG, peso WebP/JPG. Solo lee. |
| `referencias/nucleo-y-diagnostico.md` | Qué hace el núcleo en cada versión (verificado en el código) y cómo diagnosticar. |
| `referencias/adaptar-plantillas.md` | Dónde y cómo incluir el parcial, ejemplos antes/después y trampas. |
| `referencias/procedimiento-seguro.md` | Copias, compilación, cachés y comprobación final. |
