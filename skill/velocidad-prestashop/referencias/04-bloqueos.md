# 4. Lo que bloquea el pintado: fuentes, iconos, scripts

Un recurso que bloquea el pintado retrasa el FCP de todas las páginas. `scripts/medir.py` lista los que el navegador
marca como bloqueantes (`renderBlockingStatus = blocking`) y los dominios externos que bloquean.

## Fuentes de Google

- **Mirar el CSS del tema antes de tocar el `<head>`.** Es frecuente que la hoja del tema haga `@import` de la MISMA
  URL de Google Fonts que el `<link>` del `<head>`. Mientras las dos URL sean idénticas, el navegador la pide una vez.
  Si se «unifica» o se cambia solo la del `<head>`, el `@import` se convierte en una segunda petición, encadenada y
  tardía: en una tienda el FCP empeoró 1,5 s. Se deshizo.
- **Quitar las familias que no se usan.** Se comprueba en el navegador qué familias se aplican de verdad
  (`getComputedStyle(el).fontFamily` de los textos visibles o `document.fonts`). En una tienda se cargaban tres
  familias y solo se usaba una.
- **`display=swap` puede costar CLS.** Si la fuente de sustitución tiene otras medidas, el texto salta al cambiar. En
  una ficha de producto el CLS pasó a 0,38 y se deshizo. Medir CLS antes de dejarlo.
- Lo ideal es servir las fuentes desde la propia tienda (`woff2` y `@font-face` con `font-display`), con su caché.

## Iconos (Font Awesome y similares)

Si los iconos solo salen en el pie o en zonas que no se ven al cargar, la hoja se carga sin bloquear:

```html
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css"
      media="print" onload="this.media='all'">
<noscript><link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css"></noscript>
```

Si los iconos están arriba (cabecera, menú), esto los hace aparecer tarde: en ese caso mejor un subconjunto de iconos
en SVG.

## jQuery desde un CDN

- Cada dominio externo en el camino crítico es una resolución de DNS, una conexión TLS y un servidor más que puede ir
  lento. Si el tema carga jQuery desde `ajax.googleapis.com` y la tienda ya tiene el mismo fichero
  (`js/jquery/jquery-x.y.z.min.js`), se sirve el local. Comprobar que son idénticos (`md5sum`).
- PrestaShop 1.7/8 ya mete jQuery dentro de `core.js`. Algunos temas lo cargan **otra vez**: son dos copias y la
  segunda pisa a la primera. Quitarla puede romper módulos que se enganchan a la primera: probar en copia.

## reCAPTCHA en todas las páginas

Un reCAPTCHA puesto a mano en el `<head>` del tema descarga unos 350 KB en **todas** las páginas. Se pone solo en las
que tienen formulario. En PrestaShop 1.7/8, `$page.page_name` dice en qué página se está:

```smarty
{if in_array($page.page_name, ['contact', 'authentication', 'registration', 'password', 'checkout', 'identity', 'address'])}
  <script src="https://www.google.com/recaptcha/api.js?render=..." async defer></script>
{/if}
```

Antes de quitarlo hay que comprobar **qué lo usa**: a veces está puesto a mano y nadie lo usa, y el captcha real lo
carga un módulo por su cuenta.

## Combinar, comprimir y cachear (CCC)

- Con CCC apagado hay tiendas con 25 a 46 hojas de estilo y scripts que bloquean. Encenderlo suele ser lo que más
  baja el FCP.
- **Se prueba en una copia**: hay módulos cuyo JavaScript se rompe al combinarlo.
- **La caché CCC no ve un CSS cambiado**: el nombre del fichero combinado sale de las rutas, no del contenido. Tras
  cambiar un CSS hay que vaciarla (*Parámetros avanzados > Rendimiento > Vaciar caché*, o `Media::clearCache()`), o
  la tienda sirve la plantilla nueva con la hoja vieja.

## Scripts propios

- `defer` en todo lo que no tenga que ejecutarse antes de pintar.
- Antes de dar algo por bueno: errores de JavaScript **comparados con la lista de antes**. Un solo error puede cortar
  todo el JavaScript que va detrás.
