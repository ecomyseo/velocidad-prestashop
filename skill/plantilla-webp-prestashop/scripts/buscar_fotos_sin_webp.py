#!/usr/bin/env python3
"""
buscar_fotos_sin_webp.py: lista en las plantillas .tpl de un tema de PrestaShop las líneas que pintan fotos de
producto SIN pedir el WebP (ni por el parcial webp-si-existe.tpl ni por un <picture> con <source> WebP/AVIF), y las
trampas conocidas (file_exists sobre una URL, cambiar .jpg por .webp a ciegas, fetchpriority="high" en un bucle,
precarga en JPG, rel="preload" en un <img>, carga diferida por JavaScript).

@author    Ecom Experts <ecomyseo@gmail.com>
@copyright 2026 Ecom Experts
@license   https://opensource.org/licenses/AFL-3.0 Academic Free License 3.0 (AFL-3.0)

Uso:
  python buscar_fotos_sin_webp.py <carpeta del tema>            (la raíz del tema o su carpeta templates)
  python buscar_fotos_sin_webp.py <carpeta del tema> --todo     (también lo que ya está bien y lo ignorado)
  python buscar_fotos_sin_webp.py <tema hijo> --padre <tema padre>

Si el tema es hijo (parent: en config/theme.yml) y el padre está al lado, se revisan también las plantillas del padre
que el hijo no sustituye: son las que se pintan de verdad. Solo lee ficheros. Sale con 1 si hay algo sin WebP o
alguna trampa.
"""
import argparse
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass

# expresión de Smarty que termina en una URL: $algo.bySize.home_default.url, $image.large.url, $x['url']…
EXPR_URL = re.compile(r"\$[A-Za-z_][\w.$\[\]'\"-]*?(?:\.url\b|\['url'\]|\[\"url\"\])")
EXPR_FUENTES = re.compile(r"\$[A-Za-z_][\w.$\[\]'\"-]*?\.sources\b(?:\.(webp|avif|jpg|png))?")
FOTO = re.compile(r"bySize|cover|default_image|image|img|picture|thumb|\.large\b|\.medium\b|\.small\b", re.I)
NO_PRODUCTO = re.compile(r"categor|manufacturer|brand|supplier|store|subcategor|logo|shop\.|\$urls\.(?!no_picture)", re.I)
SIN_FOTO = re.compile(r"no_picture_image")
PERSONALIZACION = re.compile(r"\$field\.image|customization", re.I)
# atributos data-* que un JavaScript sí usa para cargar o cambiar la foto; el resto son datos que no se descargan solos
DATA_QUE_CARGA = re.compile(r"^data-(image-(large|medium|small)-src|src|srcset|lazy|lazy-src|original|zoom-image|zoom|large|big)$", re.I)
ATRIBUTO_ANTES = re.compile(r"([\w-]+)\s*=\s*[\"'][^\"']*$")
GET_IMAGE_LINK = re.compile(r"getImageLink\s*\(([^)]*)\)")
ASIGNA = re.compile(r"\{\s*assign\s+var\s*=\s*['\"]?(\w+)['\"]?\s+value\s*=\s*(.+?)\}\s*$|\{\s*\$(\w+)\s*=\s*(.+?)\}", re.M)
INCLUDE_PARCIAL = re.compile(r"\{\s*include\b[^}]*\bew_var\s*=\s*['\"](\w+)['\"]")
USO_VAR = re.compile(r"\$(\w+)")
REEMPLAZO_CIEGO = re.compile(r"replace\s*:\s*['\"]\.jpe?g['\"]\s*:\s*['\"]\.(webp|avif)['\"]")
FILE_EXISTS = re.compile(r"file_exists\s*\(\s*\$(\w+)|file_exists\s*\(\s*\"?\$(\w+)")
LLAVES = re.compile(r"\{[^{}]*\}")
SOLO_SMARTY = re.compile(r"^\s*\{\s*(assign|capture|/capture|if|elseif|else|/if|include|foreach|/foreach|block|/block|strip|/strip)\b")
IGNORAR_LINEA = re.compile(r"og:image|twitter:image|application/ld\+json|\"image\"\s*:|'image'\s*:|<meta\b", re.I)
IGNORAR_FICHERO = re.compile(r"microdata|jsonld|json-ld|mail|pdf", re.I)


def raiz_de_tema(ruta):
    ruta = os.path.abspath(ruta)
    if os.path.basename(ruta) == "templates" and os.path.isfile(os.path.join(os.path.dirname(ruta), "config", "theme.yml")):
        return os.path.dirname(ruta)
    return ruta


def padre_declarado(raiz):
    yml = os.path.join(raiz, "config", "theme.yml")
    if not os.path.isfile(yml):
        return None
    with open(yml, encoding="utf-8", errors="replace") as f:
        for linea in f:
            m = re.match(r"\s*parent\s*:\s*['\"]?([\w-]+)", linea)
            if m:
                return m.group(1)
    return None


def plantillas(raiz):
    salida = {}
    for base, dirs, ficheros in os.walk(raiz):
        dirs[:] = [d for d in dirs if d not in ("node_modules", "_dev", ".git", "assets", "cache")]
        for f in ficheros:
            if f.endswith(".tpl"):
                completo = os.path.join(base, f)
                salida[os.path.relpath(completo, raiz).replace("\\", "/")] = completo
    return salida


def solo_en_datos(linea, exprs):
    """True si todas las expresiones están dentro de atributos data-* que ningún JavaScript usa para cargar la foto."""
    if not exprs:
        return False
    for e in exprs:
        pos = linea.find(e)
        m = ATRIBUTO_ANTES.search(linea[:pos]) if pos >= 0 else None
        if not m or not m.group(1).lower().startswith("data-") or DATA_QUE_CARGA.match(m.group(1)):
            return False
    return True


def es_foto(expr):
    if SIN_FOTO.search(expr) or PERSONALIZACION.search(expr):
        return False
    return bool(FOTO.search(expr)) and not NO_PRODUCTO.search(expr) and not re.match(r"\$product\.url\b", expr)


def revisar(rel, ruta, etiqueta, informe):
    with open(ruta, encoding="utf-8", errors="replace") as f:
        crudo = f.read()
    # los comentarios {* … *} no pintan nada: se vacían conservando los saltos de línea (y los números de línea)
    crudo = re.sub(r"\{\*.*?\*\}", lambda m: "\n" * m.group(0).count("\n"), crudo, flags=re.S)
    lineas = crudo.splitlines()
    texto = "\n".join(lineas)
    vars_parcial = set(INCLUDE_PARCIAL.findall(texto))
    vars_foto = {}   # variable -> (origen) asignada desde una URL de foto
    vars_url = set()
    for m in ASIGNA.finditer(texto):
        nombre, valor = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
        exprs = EXPR_URL.findall(valor)
        if exprs:
            vars_url.add(nombre)
        if any(es_foto(e) for e in exprs) or REEMPLAZO_CIEGO.search(valor):
            vars_foto[nombre] = valor.strip()[:60]
    for v in list(vars_foto):
        for m in ASIGNA.finditer(texto):
            nombre, valor = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
            if re.search(r"\$" + re.escape(v) + r"\b", valor):
                vars_foto.setdefault(nombre, "$" + v)
                vars_url.add(nombre)
    vars_foto = {k: o for k, o in vars_foto.items() if k not in vars_parcial}

    en_picture = False
    picture_con_fuente = False
    picture_ini = 0
    en_img = False
    profundidad_bucle = 0
    ignorar_fichero = bool(IGNORAR_FICHERO.search(rel))

    def apunta(tipo, n, motivo):
        informe.append((tipo, etiqueta + rel, n, motivo, lineas[n - 1].strip()[:150]))

    for n, linea in enumerate(lineas, 1):
        profundidad_bucle += len(re.findall(r"\{\s*(foreach|section)\b", linea))
        bajo_bucle = profundidad_bucle > 0
        profundidad_bucle -= len(re.findall(r"\{\s*/(foreach|section)\s*\}", linea))
        profundidad_bucle = max(profundidad_bucle, 0)

        if re.search(r"<picture\b", linea, re.I):
            en_picture, picture_ini = True, n
            # mira por delante hasta </picture> si hay un <source> WebP/AVIF (la etiqueta puede ocupar varias líneas)
            bloque = []
            for siguiente in lineas[n - 1:]:
                bloque.append(siguiente)
                if re.search(r"</picture>", siguiente, re.I):
                    break
            junto = "\n".join(bloque).replace("->", "")
            picture_con_fuente = bool(re.search(r"<source\b[^>]*(webp|avif)", junto, re.I | re.S))
        sin_llaves = LLAVES.sub("", linea)
        if re.search(r"<img\b", sin_llaves, re.I):
            en_img = True
        dentro_img = en_img

        # trampas que no dependen de dónde se pinte
        if REEMPLAZO_CIEGO.search(linea):
            apunta("TRAMPA", n, "cambia .jpg por .webp sin comprobar que el fichero exista (o la ruta de 1.7 no lo sirve)")
        for m in FILE_EXISTS.finditer(linea):
            v = m.group(1) or m.group(2)
            if v in vars_url or v in vars_foto:
                apunta("TRAMPA", n, "file_exists() sobre una URL: siempre es falso, nunca elige el WebP")
        solo_primera = re.search(r"@first|@index\s*==\s*0|@iteration\s*==\s*1|\.first\b",
                                 " ".join(lineas[max(0, n - 4):n]), re.I)
        if re.search(r"fetchpriority\s*=\s*['\"]high", linea, re.I) and bajo_bucle and not solo_primera:
            apunta("AVISO", n, "fetchpriority=\"high\" dentro de un bucle: solo la imagen LCP (una) debe llevarlo")
        if dentro_img and re.search(r"\brel\s*=\s*['\"]preload", sin_llaves, re.I):
            apunta("AVISO", n, "rel=\"preload\" en un <img> no hace nada (la precarga es <link rel=\"preload\" as=\"image\">)")

        es_salida = not SOLO_SMARTY.match(linea) or re.search(r"<\w|\w+\s*=\s*\"", sin_llaves)
        exprs = [e for e in EXPR_URL.findall(linea)]
        fuentes = EXPR_FUENTES.findall(linea)
        usa_parcial = [v for v in USO_VAR.findall(linea) if v in vars_parcial]
        usa_foto = [v for v in USO_VAR.findall(linea) if v in vars_foto]
        fotos = [e for e in exprs if es_foto(e)]
        sin_foto = [e for e in exprs if SIN_FOTO.search(e)]
        personalizada = [e for e in exprs if PERSONALIZACION.search(e)]
        gil = GET_IMAGE_LINK.findall(linea)

        if es_salida and not re.match(r"^\s*\{\s*assign\b", linea):
            precarga = re.search(r"<link\b[^>]*rel\s*=\s*['\"]preload", linea, re.I) and re.search(r"as\s*=\s*['\"]image", linea, re.I)
            if ignorar_fichero or IGNORAR_LINEA.search(linea):
                if fotos or usa_foto or gil:
                    apunta("IGNORADA", n, "datos estructurados / redes / correo: se deja en JPG a propósito")
            elif fotos or usa_foto or gil:
                lazy_js = re.search(r"\bdata-(src|lazy|original)\s*=", linea, re.I)
                if precarga:
                    if fuentes or usa_parcial:
                        apunta("OK", n, "precarga con la misma URL del parcial / del núcleo")
                    else:
                        apunta("AVISO", n, "precarga de la foto en JPG: si la plantilla pinta el WebP, se descarga dos veces")
                elif usa_parcial and not fotos and not usa_foto and not gil:
                    apunta("OK", n, "por el parcial (" + ", ".join(sorted(set(usa_parcial))) + ")")
                elif en_picture and picture_con_fuente:
                    apunta("OK-PICTURE", n, "dentro de un <picture> con <source> WebP/AVIF (línea %d)" % picture_ini)
                elif not usa_foto and not gil and solo_en_datos(linea, fotos):
                    apunta("INFO", n, "solo en un atributo data-* que no carga la foto: mira si algún JS del tema lo usa")
                else:
                    if gil:
                        motivo = "getImageLink() sin WebP (en 8.1+ admite un 4.º argumento 'webp', pero sin comprobar que exista)"
                    elif usa_foto:
                        motivo = "variable con la URL JPG: $" + ", $".join(sorted(set(usa_foto)))
                    else:
                        motivo = "URL JPG: " + ", ".join(sorted(set(fotos)))[:90]
                    if lazy_js:
                        motivo += " [carga diferida por JS: las 4 primeras del listado, con src normal]"
                    apunta("SIN WEBP", n, motivo)
            elif usa_parcial:
                if precarga:
                    apunta("OK", n, "precarga con la misma URL del parcial (" + ", ".join(sorted(set(usa_parcial))) + ")")
                else:
                    apunta("OK", n, "por el parcial (" + ", ".join(sorted(set(usa_parcial))) + ")")
            elif fuentes and re.search(r"\bsrcset\s*=|\bdata-[\w-]*sources\s*=", linea):
                apunta("OK-NUCLEO", n, "sources del núcleo (8.1+): el <source> se pinta aunque el fichero no exista")
            elif sin_foto:
                apunta("INFO", n, "imagen de «sin foto» (no está en img/p/ por id): se deja")
            elif personalizada:
                apunta("INFO", n, "imagen de personalización subida por el cliente (no está en img/p/): se deja")

        if re.search(r"</picture>", linea, re.I):
            en_picture = False
        if dentro_img and ">" in sin_llaves.split("<img", 1)[-1]:
            en_img = False
        elif dentro_img and not re.search(r"<img\b", sin_llaves, re.I) and ">" in sin_llaves:
            en_img = False


def main():
    ap = argparse.ArgumentParser(description="Fotos de producto que el tema pinta sin pedir el WebP")
    ap.add_argument("tema", help="carpeta del tema (raíz o templates)")
    ap.add_argument("--padre", help="carpeta del tema padre (si no está al lado del hijo)")
    ap.add_argument("--todo", action="store_true", help="enseña también lo que ya está bien y lo ignorado")
    a = ap.parse_args()

    raiz = raiz_de_tema(a.tema)
    if not os.path.isdir(raiz):
        print("No existe la carpeta: " + raiz)
        return 2
    propias = plantillas(raiz)
    informe = []
    for rel in sorted(propias):
        revisar(rel, propias[rel], "", informe)

    padre = a.padre
    nombre_padre = padre_declarado(raiz)
    if not padre and nombre_padre:
        candidato = os.path.join(os.path.dirname(raiz), nombre_padre)
        padre = candidato if os.path.isdir(candidato) else None
        if not padre:
            print("OJO: tema hijo de «%s», pero el padre no está al lado: pásalo con --padre" % nombre_padre)
    if padre:
        heredadas = plantillas(raiz_de_tema(padre))
        sueltas = [r for r in heredadas if r not in propias]
        print("Tema hijo: se revisan también %d plantillas del padre que el hijo no sustituye [padre]" % len(sueltas))
        for rel in sorted(sueltas):
            revisar(rel, heredadas[rel], "[padre] ", informe)

    orden = {"TRAMPA": 0, "SIN WEBP": 1, "AVISO": 2, "INFO": 3, "OK": 4, "OK-PICTURE": 5, "OK-NUCLEO": 6, "IGNORADA": 7}
    visibles = ("TRAMPA", "SIN WEBP", "AVISO")
    for tipo, fichero, n, motivo, texto in sorted(informe, key=lambda x: (orden[x[0]], x[1], x[2])):
        if a.todo or tipo in visibles:
            print("%-10s %s:%d  %s\n           %s" % (tipo, fichero, n, motivo, texto))
    cuenta = {}
    for x in informe:
        cuenta[x[0]] = cuenta.get(x[0], 0) + 1
    print("\nRESUMEN: " + ", ".join("%s %d" % (t, cuenta.get(t, 0)) for t in sorted(orden, key=orden.get)))
    return 1 if cuenta.get("SIN WEBP") or cuenta.get("TRAMPA") else 0


if __name__ == "__main__":
    sys.exit(main())
