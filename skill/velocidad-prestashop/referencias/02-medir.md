# 2. Medir

## Lo que ve el cliente: navegador real en móvil

El tiempo que tarda el servidor en responder (TTFB medido con `curl` desde el propio servidor) **engaña**: en una
auditoría, 15 de 16 webs con un servidor rápido pasaban de 1,3 s en un navegador real por culpa de imágenes de varios
MB, redirecciones y peticiones rotas.

Se mide con un navegador de verdad y en las condiciones del cliente más lento:

- móvil (390 × 844, pantalla ×2);
- 4G lenta: 150 ms de latencia y 1,6 Mbit/s;
- CPU 4 veces más lenta que la del ordenador que mide;
- primera visita (sin caché) y segunda visita (con la caché del navegador);
- 3 cargas por página y la mediana.

`scripts/medir.py` hace exactamente eso:

```
pip install playwright
python -m playwright install chromium
python scripts/medir.py https://tienda.ejemplo/ https://tienda.ejemplo/categoria https://tienda.ejemplo/producto.html --etiqueta antes
python scripts/medir.py ...las mismas URL... --etiqueta despues
```

Por cada página da FCP, LCP, carga, KB transferidos, número de peticiones, la URL del elemento LCP, los recursos que
bloquean el pintado (`renderBlockingStatus` del navegador), los dominios externos que bloquean, los 8 ficheros más
pesados y los errores de JavaScript. Guarda todo en `medida-<etiqueta>.json` para comparar.

Páginas mínimas: portada, una categoría, una ficha de producto y el carrito.

## Datos de campo de Google

- PageSpeed Insights y CrUX dan los datos de los visitantes reales de los **últimos 28 días**. Sirven para saber dónde
  está el problema, pero un cambio tarda semanas en reflejarse ahí.
- La API sin clave se queda sin cuota enseguida (429). Con clave, se consulta desde un servidor propio.
- El origen importa: si la tienda está en `https://www.`, CrUX con el dominio sin `www` dice «sin datos».

## El servidor

- **Consultas por página:** el perfilador de PrestaShop (`_PS_DEBUG_PROFILING_`) en una copia de la tienda, nunca en
  producción. Una categoría con más de 1.000 consultas suele tener un módulo que consulta producto a producto.
- **Peticiones lentas de PHP:** `request_slowlog_timeout = 3s` y `slowlog` en el pool de PHP-FPM. La traza dice qué
  línea de qué módulo estaba esperando. Es lo que más rápido encuentra a un módulo que llama a un servicio externo.
- **Consultas lentas de MariaDB:** `slow_query_log=1` y `long_query_time=2`.
- **Procesos atascados:** si muchos procesos de PHP están en `locks_lock_inode_wait`, están haciendo cola por la sesión
  PHP de un mismo usuario (ver `06-servidor.md`).

## Trampas al medir

- En Windows, `localhost` resuelve primero a `::1` y cada conexión a un servidor que solo escucha en IPv4 tarda 2 s
  más. Se mide contra `127.0.0.1`.
- Interceptar el documento HTML en Playwright falsea los tiempos (se pierde la conexión reutilizada). Si hay que
  simular un cambio, se calcula por bytes.
- Medir con la caché de página caliente y fría por separado: la primera petición tras vaciarla no es representativa.
- Una medida de tiempo con un solo intento no vale: la red varía. Mediana de 3 a 5.
- Si la tienda tiene el modo desarrollo activado **solo para una IP** (`config/defines.inc.php` con un
  `$_SERVER['REMOTE_ADDR'] == '...'`), quien mide desde esa IP ve la tienda más lenta que los clientes.
