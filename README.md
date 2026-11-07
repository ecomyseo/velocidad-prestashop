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
