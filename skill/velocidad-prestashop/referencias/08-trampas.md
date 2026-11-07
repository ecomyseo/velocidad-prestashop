# 8. Trampas ya pisadas

Cada una costó horas en una tienda real. Leer antes de empezar.

## Imágenes

- **WebP en disco que nadie sirve:** la regla del `.htaccess` no se aplica si nginx sirve las imágenes directamente.
- **`file_exists()` sobre una URL** en la plantilla: siempre falso, el WebP nunca se pide.
- **`<picture>` con un JavaScript que cambia el `src`** de la foto grande: el `<source>` manda y la foto no cambia.
- **El modal de zoom oculto descarga la foto otra vez** en otro formato.
- **Precarga en un formato y plantilla en otro:** la foto LCP se baja dos veces.
- **WebP más viejos que su imagen:** se ve la foto anterior del producto.
- **WebP más pesado que la original** (PNG pequeños de pocos colores): si el servidor negocia por `Accept`, lo sirve
  igual. Solo se guarda el WebP si pesa al menos un 10 % menos.
- **Perfil de color sin convertir:** capturas de Mac (Display P3) o fotos en Adobe RGB salen apagadas si no se pasan
  a sRGB.
- **Orientación EXIF sin aplicar:** la foto sale girada.
- **Una imagen enlazada que ya daba 404** no es un fallo del cambio: comparar con antes, no exigir «todo 200».
- **nginx pierde `$1` al evaluar un `map` con expresión regular**: `try_files $uri$webp $1$webp` busca «.webp» a
  secas. Para quitar la extensión, captura con nombre: `location ~* ^(?<base>.+)\.(png|jpe?g)$`.
- **Dos nombres de WebP**: `banner.png.webp` (al lado, con la extensión) y `banner.webp` (cambiando la extensión). La
  configuración del servidor tiene que buscar el que crea la herramienta que se use, o los dos.
- **Un servidor que no puede pedirse a sí mismo por HTTPS** (cortafuegos o nginx escuchando solo en la IP pública): las
  tareas «por URL» de los módulos no funcionan desde su propio cron; se lanzan por línea de órdenes.

## Plantillas y cachés

- **Caché CCC:** el nombre del fichero combinado sale de las rutas, no del contenido; un CSS cambiado no se ve hasta
  vaciarla.
- **Caché de página completa** (si un módulo la hace): tras cambiar una plantilla hay que caducarla y comprobar con dos
  peticiones seguidas que la segunda vuelve a salir de la caché.
- **Compilados de Smarty de plantillas de módulos** (`*.module.*.cache.php`) no se borran con el patrón de las del tema.
- **OPcache sin revalidar** (`validate_timestamps=0`): el PHP nuevo no se ejecuta.

## Fuentes y bloqueos

- **Cambiar la URL de Google Fonts del `<head>`** cuando el CSS del tema hace `@import` de la misma: segunda petición
  tardía (+1,5 s de FCP).
- **`display=swap`** con una fuente de sustitución de otras medidas: CLS alto.

## Caché del navegador

- **`mod_expires` apagado:** las reglas del `.htaccess` están dentro de `<IfModule>` y no hacen nada, sin aviso.
- **`ExpiresDefault` sin excepciones** en algún `.htaccess` del servidor: al encender el módulo, páginas y JSON con un
  mes de caché.
- **`mod_expires` no toca los 4xx:** un JSON de prueba que da 404 no demuestra nada.
- **Caché de nginx (`proxy_cache`)** en el dominio: lo que Apache marque con caché larga se guarda para todos.

## Servidor

- **Sesiones en Redis sin bloqueo:** «The CSRF token is invalid» al guardar en el back-office.
- **Plesk `db-performance.cnf`** gana a todo lo de `mariadb.conf.d/`.
- **Plesk regenera el pool** al cambiar ajustes de PHP y quita lo puesto a mano.
- **Hestia con la versión de PHP delante del nombre de la plantilla:** una actualización automática la pasa al PHP por
  defecto.
- **`echo OK` detrás de `;`:** imprime «OK» aunque la orden anterior haya fallado. Siempre `&&`.
- **`php-fpm -t` no imprime nada** cuando está bien: mirar el código de salida.

## Medir

- **PageSpeed es bimodal:** la misma página sin cambios da resultados muy distintos. No sirve para comparar dos
  variantes.
- **`localhost` en Windows** resuelve a IPv6 primero: 2 s de más por conexión.
- **El TTFB desde el propio servidor** no es lo que ve el cliente.
- **Modo desarrollo por IP:** quien mide desde esa IP ve la tienda más lenta que los clientes.
- **Chrome ya cachea sin cabeceras:** no prometer una mejora grande por poner la caché del navegador.
