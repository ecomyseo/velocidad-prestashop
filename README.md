# Velocidad en PrestaShop

Skills para que una IA (Claude Code, Codex u otra que lea skills) mida y mejore la velocidad de una tienda PrestaShop
1.7, 8 o 9 **sin romper nada**, y el módulo `ecom_webpauto` para servir los banners en WebP.

Todo lo que hay aquí sale de trabajo real sobre tiendas en producción, anonimizado: cifras medidas, cambios hechos y
trampas pisadas.

## Contenido

| Carpeta | Qué es |
|---|---|
| `skill/velocidad-prestashop/` | El skill principal: método seguro (copia, antes y después, vuelta atrás), medición, imágenes WebP, recursos que bloquean, caché del navegador, servidor, módulos de terceros y trampas. Con scripts y plantillas. |
| `skill/plantilla-webp-prestashop/` | Skill para adaptar un tema de PrestaShop a WebP: qué plantillas tocar, el parcial «WebP solo si existe» y cómo comprobarlo. |
| `modulo/ecom_webpauto/` | Módulo de PrestaShop (1.7.6 a 9.x) que crea el WebP de banners, slider, páginas CMS y logos al subirlos y lo entrega a los navegadores que lo aceptan. |

## Resultados en tiendas reales (anonimizados)

Cambios aplicados en noviembre de 2026 en siete webs reales, cada uno con copia, medida antes y después y vuelta
atrás. Salvo que se diga otra cosa, las medidas son con navegador real; «4G» es un móvil con 4G lenta (150 ms,
1,6 Mbit/s) y CPU ×4, como en `scripts/medir.py`.

### Tienda A — PrestaShop 8.2, tema de terceros

**Qué se aplicó:**
- WebP del núcleo para las fotos de producto, con calidad 75 (con 85 pesaban lo mismo que los JPG).
- Plantillas del tema cambiadas para que pidan el WebP.
- Banners y slider en WebP.
- reCAPTCHA solo en las páginas con formulario.
- Fondo parallax en WebP.
- Caché del navegador.
- Iconos sin bloquear el pintado y jQuery servido desde la propia tienda.
- La foto principal de la ficha se descargaba dos veces (precarga y ventana de zoom); ahora, una.

| Página | Antes | Después |
|---|---|---|
| Portada: peso / carga | 4,29 MB / 2,9 s | 1,54 MB / 1,1 s |
| Portada: carga en 4G | 3,6 s | 1,5 s |
| Portada: LCP en 4G | 2,37 s | 1,03 s |
| Categoría: peso / carga en 4G | 1,71 MB / 2,0 s | 1,09 MB / 1,0 s |
| Ficha: peso / carga en 4G | 1,11 MB / 1,5 s | 0,68 MB / 0,8 s |
| Miniaturas de producto en disco (25.937) | 733 MB | 504 MB |

### Tienda B — PrestaShop 1.7.8 en un VPS nuevo

**Qué se aplicó:**
- Fuera `open_basedir`: PHP no usaba su caché de rutas.
- `cpuidle_haltpoll` en la máquina virtual.
- Tienda conectada a MariaDB por socket.
- MariaDB: tablas abiertas, temporales y caché de consultas.
- Grupo de procesos de PHP propio y memoria de cadenas de OPcache.
- nginx entrega WebP de los banners.
- WebP de producto regenerados: había 408 productos que enseñaban la foto anterior.
- Primeras fotos del listado sin carga diferida.

| Medida | Antes | Después |
|---|---|---|
| Portada, tiempo del servidor | 1,67 s | 0,80 s |
| Media de todas las páginas, tiempo del servidor | 1,67 s | 0,74 s |
| Peticiones por segundo que aguanta | 3,4 | 7,6 |
| Ida y vuelta a MariaDB | 0,22 ms | 0,06 ms |
| Banner principal | 717 KB | 58 KB |

### Tienda C — PrestaShop con banners de campaña en PNG

**Qué se aplicó:**
- WebP al lado de cada imagen de las páginas CMS y negociación en nginx; ninguna original tocada.
- Índice en la tabla de vistas del blog.
- Purga de visitas de robots de más de 30 días, con copia.
- Más memoria de intercambio, y fuera el antivirus y el antispam del correo, que no se usaban.

| Medida | Antes | Después |
|---|---|---|
| Imágenes de banners de la portada (PC + móvil) | 26,5 MB | 4,8 MB |
| Imágenes de la carpeta CMS en disco (525) | 560 MB | 56,5 MB en WebP |
| Consulta del blog por cada visita a una entrada | 0,26 s | 0,03 s |
| Base de datos | 1.603 MB | 1.317 MB |

### Tienda D — PrestaShop 8.1 en un VPS de 2 GB

**Qué se aplicó:**
- WebP del slider, los banners y las imágenes CMS, con negociación en nginx.
- Rehechos los WebP que eran más viejos o más pesados que su imagen.
- Fuera `open_basedir`.

| Medida | Antes | Después |
|---|---|---|
| Imágenes de banners de la portada (PC + móvil) | 10,1 MB | 1,1 MB |
| Banner principal (elemento LCP) | 4,4 MB | 277 KB |
| Tiempo del servidor | 1,61 s | 1,45 s |

### Tienda E — PrestaShop 1.7 con varias webs en un servidor Plesk

**Qué se aplicó:**
- Memoria de caché de MariaDB: Plesk la fijaba en 128 MB en una máquina de 128 GB.
- Más procesos de PHP en las webs que daban 503.
- DNS lento cambiado.
- Desactivado un guion de «limpieza» que reiniciaba MariaDB cada 4 horas.
- Limitada la tarea del módulo de pago aplazado que tumbaba la tienda, y aviso al desarrollador.
- `robots.txt` sin filtros.
- Caché del navegador, con páginas y JSON excluidos.

| Medida | Antes | Después |
|---|---|---|
| Memoria de caché de MariaDB | 128 MB | 10,4 GB |
| Cada consulta de DNS | 1-2 s | 1 ms |
| Lanzamientos por hora de la tarea «diaria» del módulo de pago | 461 | como mucho 1 cada 3 h |
| Páginas lentas esperando a esa tarea (en una hora) | 110 de 234 | 0 |
| Caídas por reinicio de MariaDB | cada 4 h | ninguna |

### Tienda F — PrestaShop con cinco tiendas en el mismo servidor

**Qué se aplicó:** OPcache no cabía, y los ficheros que no entraban se compilaban en cada petición.

| Medida | Antes | Después |
|---|---|---|
| Ficheros PHP / límite de OPcache | 20.924 / 20.000 | 20.924 / 100.000 |

### Web G — WordPress

**Qué se aplicó:** caché del navegador (el módulo de Apache estaba apagado y sus reglas no hacían nada).

| Visitante que vuelve… | Ficheros que tenía que volver a pedir antes | Después |
|---|---|---|
| al día siguiente | 6 (116 KB) | 0 |
| a los 30 días | 12 (613 KB) | 0 |

La primera visita no cambia: la caché del navegador mejora las visitas repetidas y la nota de PageSpeed.

## Instalar los skills

**Claude Code**, para todos tus proyectos:

```
cp -r skill/velocidad-prestashop ~/.claude/skills/
cp -r skill/plantilla-webp-prestashop ~/.claude/skills/
```

o solo para un proyecto, en `<proyecto>/.claude/skills/`. Después basta con pedir «la tienda va lenta» o «mejora la
nota de PageSpeed» y la IA cargará el skill.

**Codex** y otras: copiar las carpetas a su directorio de skills (por ejemplo `~/.codex/skills/`) o indicar a la IA
que lea `SKILL.md` antes de empezar.

## Requisitos de los scripts

- Python 3.9 o posterior.
- `pip install requests pillow playwright` y `python -m playwright install chromium` (solo para `medir.py`).
- `webp_al_lado.py` necesita Pillow con WebP y LittleCMS (las ruedas oficiales de Pillow los traen).
- Prueba de `webp_al_lado.py`: `python skill/velocidad-prestashop/scripts/prueba_webp_al_lado.py` → `FALLOS: 0`.

## Avisos

- **Nada se aplica en producción sin copia de seguridad y sin permiso del dueño de la tienda.** El skill obliga a la
  IA a hacer copia, medir antes y después, probar activando y desactivando cada opción y dejar una vuelta atrás.
- Las cifras de los documentos son de tiendas concretas: en otra tienda pueden ser distintas. Hay que medir.
- Los cambios en módulos de terceros se pierden al actualizarlos: se documentan y se avisa al desarrollador.

## El módulo ecom_webpauto

- Crea el WebP de cada imagen que se sube en el back-office (slider, banners, CMS, categorías, logo), al lado de la
  original y sin tocarla, y solo si pesa menos.
- Añade al `.htaccess` la regla que entrega el WebP en la misma URL. **Si nginx sirve las imágenes directamente**
  (Hestia, Plesk con estáticos en nginx), esa regla no se aplica: el panel del módulo lo detecta y avisa, y hay que
  añadir la configuración de `skill/velocidad-prestashop/plantillas/nginx-webp.conf`.
- Tiene una tarea programada opcional (con token) para las imágenes subidas por FTP.
- Una vez por semana, al abrir su configuración, consulta en `modules.gmartos.es` si hay versión nueva; para ello
  envía el nombre del módulo, su versión, el dominio de la tienda y el correo de la tienda. Si falla, no hace nada.
- Instalación: subir la carpeta `modulo/ecom_webpauto` comprimida en ZIP desde *Módulos > Subir un módulo*.

## Licencia

Academic Free License 3.0 (AFL-3.0). Autor: Ecom Experts.
