---
name: velocidad-prestashop
description: Medir y mejorar la velocidad de una tienda PrestaShop (1.7, 8 y 9) y de su servidor sin romper nada. Copia y vuelta atrás antes de cada cambio, medición antes y después con navegador real (móvil en 4G), imágenes WebP (núcleo, plantilla, banners y CMS), recursos que bloquean el pintado (fuentes, iconos, jQuery, reCAPTCHA), caché del navegador, ajustes del servidor (OPcache, MariaDB, PHP-FPM, sesiones, DNS) y módulos de terceros que frenan o tumban la tienda. Usar cuando se pida «la tienda va lenta», «mejora la nota de PageSpeed», «optimiza la velocidad», «el LCP es alto», «convierte las imágenes a WebP», «la tienda se cae» o similar.
---

# Velocidad en PrestaShop sin romper nada

Este skill reúne lo que se ha medido y aplicado en tiendas PrestaShop reales: qué mejora de verdad, en qué orden
conviene hacerlo y en qué se tropieza. Todo está anonimizado.

## Las reglas que no se saltan

1. **Copia de seguridad antes de cada cambio.** De cada fichero que se toca, de las filas de configuración que se
   cambian y de la configuración del servidor. Y un `volver.sh` que deshaga ese cambio concreto. Detalle en
   `referencias/01-metodo-seguro.md`.
2. **Medir antes y después, con el mismo método.** Sin una medida de partida no se puede decir que algo ha mejorado.
   El método está en `referencias/02-medir.md` y la herramienta en `scripts/medir.py`.
3. **Un cambio cada vez, y probarlo activando y desactivando.** Para saber si una opción ayuda se mide con ella y sin
   ella, alternando (A, B, A, B) y con varias cargas. Si no mejora, se deshace.
4. **Nada en producción sin el permiso del dueño de la tienda**, diciendo antes qué se va a tocar. Si hay una copia
   de la tienda, se prueba primero allí.
5. **Comprobar el final, no solo el principio.** Mismos códigos HTTP que antes en las páginas clave, cero errores de
   JavaScript nuevos (los que ya había no cuentan, pero se apuntan), imágenes que cargan, y carrito y checkout que
   funcionan.
6. **Avisar de cada cambio**: qué se ha tocado, dónde está la copia, cómo se deshace y qué se ha medido.

## Orden de trabajo, de más rentable a menos

| Paso | Qué | Referencia |
|---|---|---|
| 1 | Medir la situación de partida (móvil 4G, primera y segunda visita) | `referencias/02-medir.md` |
| 2 | Imágenes: WebP en fotos de producto, en la plantilla y en banners/CMS | `referencias/03-imagenes-webp.md` |
| 3 | Recursos que bloquean el pintado: fuentes, iconos, jQuery, reCAPTCHA, CCC | `referencias/04-bloqueos.md` |
| 4 | Caché del navegador para los estáticos | `referencias/05-cache-navegador.md` |
| 5 | Servidor: OPcache, MariaDB, PHP-FPM, sesiones, DNS, CPU | `referencias/06-servidor.md` |
| 6 | Módulos de terceros que llaman fuera o bloquean | `referencias/07-modulos-terceros.md` |
| — | Trampas ya pisadas (leer antes de empezar) | `referencias/08-trampas.md` |

Lo que más pesa casi siempre son las **imágenes**: banners en PNG de 2 a 5 MB son habituales. En una tienda la
portada pasó de 26,5 MB a 4,8 MB solo con WebP en los banners, sin tocar ninguna imagen original.

## Herramientas

| Script | Para qué |
|---|---|
| `scripts/medir.py` | Navegador real (Playwright) en móvil con 4G lenta y CPU ×4: FCP, LCP, carga, KB, peticiones, recursos que bloquean, lo más pesado y errores de JavaScript, en primera y segunda visita. |
| `scripts/revisar_cache.py` | Cuánto tiempo guarda el navegador los CSS, JS, imágenes y fuentes de una web, y que las páginas y el JSON **no** se guarden. Solo lectura. |
| `scripts/webp_al_lado.py` | Crea `imagen.png.webp` junto a cada imagen de una carpeta (sin tocar la original), solo si pesa al menos un 10 % menos. Deja un registro para deshacerlo. |

Plantillas de configuración listas para adaptar en `plantillas/`: negociación de WebP en nginx y en Apache, bloque de
caché del navegador seguro para `.htaccess`, el parcial Smarty que pide el WebP solo si existe y un modelo de aviso al
desarrollador de un módulo.

## Cómo informar al terminar

- Qué se ha cambiado, web por web, con la cifra de antes y la de después.
- Dónde está la copia y la orden exacta para deshacerlo.
- Qué queda pendiente y qué decisión le toca al dueño de la tienda.
- Lo que se ha visto de paso y no se ha tocado (errores que ya estaban, módulos sospechosos).
