#!/bin/sh
# copia_y_volver.sh: guarda una copia de cada plantilla del tema ANTES de tocarla y deja escrito un volver.sh que
# las repone tal cual estaban (y borra las que no existían, como el parcial nuevo). Solo copia: no cambia nada.
#
# @author    Ecom Experts <ecomyseo@gmail.com>
# @copyright 2026 Ecom Experts
# @license   https://opensource.org/licenses/AFL-3.0 Academic Free License 3.0 (AFL-3.0)
#
# Uso (en el servidor, como el usuario dueño de los ficheros de la web):
#   sh copia_y_volver.sh <carpeta del tema> <plantilla> [<plantilla> ...]
#   sh copia_y_volver.sh /ruta/themes/mitema-hijo templates/catalog/_partials/miniatures/product.tpl \
#       templates/catalog/_partials/product-cover-thumbnails.tpl templates/catalog/_partials/webp-si-existe.tpl
#
# Variables opcionales:
#   COPIAS=/ruta   dónde guardar las copias (por defecto $HOME/copias-plantilla-webp, FUERA de la web)
#   TIENDA=/ruta   raíz de la tienda: volver.sh vaciará además la caché de Smarty (var/cache/*/smarty)
#
# Para deshacer: sh <carpeta de la copia>/volver.sh
set -eu

if [ "$#" -lt 2 ]; then
    sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'
    exit 2
fi
TEMA=$(cd "$1" && pwd)
shift
FECHA=$(date +%Y%m%d-%H%M%S)
DESTINO="${COPIAS:-$HOME/copias-plantilla-webp}/$(basename "$TEMA")-$FECHA"
mkdir -p "$DESTINO/antes"
VOLVER="$DESTINO/volver.sh"

{
    echo '#!/bin/sh'
    echo "# Repone las plantillas de $TEMA como estaban el $FECHA."
    echo 'set -eu'
    echo 'FALLOS=0'
} > "$VOLVER"

for REL in "$@"; do
    case "$REL" in
        /*|*..*) echo "Ruta no válida (tiene que ser relativa al tema y sin ..): $REL" >&2; exit 2 ;;
    esac
    if [ -f "$TEMA/$REL" ]; then
        mkdir -p "$DESTINO/antes/$(dirname "$REL")"
        cp -p "$TEMA/$REL" "$DESTINO/antes/$REL"
        cmp -s "$TEMA/$REL" "$DESTINO/antes/$REL" || { echo "La copia de $REL no es idéntica" >&2; exit 1; }
        {
            echo "cp -p '$DESTINO/antes/$REL' '$TEMA/$REL'"
            echo "cmp -s '$DESTINO/antes/$REL' '$TEMA/$REL' && echo 'repuesta  $REL' || { echo 'NO SE PUDO REPONER $REL'; FALLOS=1; }"
        } >> "$VOLVER"
        echo "copia      $REL"
    else
        {
            echo "rm -f '$TEMA/$REL'"
            echo "[ ! -e '$TEMA/$REL' ] && echo 'borrada   $REL (no existía antes)' || { echo 'NO SE PUDO BORRAR $REL'; FALLOS=1; }"
        } >> "$VOLVER"
        echo "nueva      $REL (volver.sh la borrará)"
    fi
done

if [ -n "${TIENDA:-}" ]; then
    {
        echo "# caché de Smarty de la tienda: compiladas y renderizadas, de todos los entornos (prod y dev)"
        echo "for D in '$TIENDA'/var/cache/*/smarty/compile '$TIENDA'/var/cache/*/smarty/cache; do"
        echo '    [ -d "$D" ] && find "$D" -mindepth 1 -delete && echo "vaciada   $D"'
        echo 'done'
    } >> "$VOLVER"
else
    echo "echo 'Ahora vacía la caché de Smarty (Parámetros avanzados > Rendimiento > Borrar caché) y la de página si hay.'" >> "$VOLVER"
fi
echo 'exit $FALLOS' >> "$VOLVER"
chmod +x "$VOLVER"
echo
echo "Copias en:  $DESTINO/antes"
echo "Deshacer:   sh '$VOLVER'"
