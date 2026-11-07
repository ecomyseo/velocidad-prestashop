#!/usr/bin/env python3
"""
revisar_html.py: lee el HTML que sirve una página de la tienda (guardado en un fichero, o pedido a una URL de TU
tienda con permiso) y cuenta cómo pide las fotos de producto: cuáles salen en WebP/AVIF, cuáles en JPG, cuáles se
piden dos veces en formatos distintos (precarga en JPG + foto en WebP, ventana de zoom oculta en JPG…), cuántas
llevan fetchpriority="high" y si las primeras miniaturas del listado van con carga diferida.

@author    Ecom Experts <ecomyseo@gmail.com>
@copyright 2026 Ecom Experts
@license   https://opensource.org/licenses/AFL-3.0 Academic Free License 3.0 (AFL-3.0)

Uso:
  python revisar_html.py pagina.html            (guardada con «Guardar como» o con curl)
  python revisar_html.py https://<tu tienda>/…  (una petición GET, nada más)

Reconoce las fotos de producto por su URL: /<id>-<tipo>/<nombre>.<ext> (URL amigable) o /img/p/<1/2/3>/<id>-<tipo>.<ext>.
No sustituye a mirar las peticiones en el navegador: aquí se ve lo que PIDE el HTML, no lo que el servidor contesta.
Sale con 1 si hay fotos sin WebP o pedidas en dos formatos.
"""
import re
import sys
import urllib.request
from html.parser import HTMLParser

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass

FOTO_AMIGABLE = re.compile(r"(?<!/c)/(\d+)-([a-z][\w-]*?)(?:-\d+)?/[^/?#\"'\s]+\.(jpe?g|png|webp|avif)\b", re.I)
FOTO_FISICA = re.compile(r"/img/p/(?:\d/)+(\d+)-([a-z][\w-]*?)\.(jpe?g|png|webp|avif)\b", re.I)
URL_EN_CSS = re.compile(r"url\(\s*['\"]?([^'\")]+)")


def foto(url):
    """(id_image, tipo, formato) si la URL es una foto de producto; None si no."""
    if not url:
        return None
    m = FOTO_FISICA.search(url) or FOTO_AMIGABLE.search(url)
    if not m:
        return None
    fmt = m.group(3).lower()
    return m.group(1), m.group(2), "jpg" if fmt in ("jpg", "jpeg") else fmt


def urls_de_srcset(valor):
    return [p.strip().split()[0] for p in (valor or "").split(",") if p.strip()]


class Lector(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.picture = []          # pila de <picture>: lista de formatos de sus <source>
        self.ocultos = []          # pila: True si estamos dentro de un elemento oculto (modal, display:none)
        self.pila = []
        self.imgs = []             # dicts: clave, formato, lazy, en_picture_con, oculto, prioridad, miniatura
        self.precargas = []        # (clave, formato)
        self.cambios_js = []       # (clave, formato, atributo)
        self.miniatura = 0         # contador de miniaturas de listado abiertas
        self.dentro_miniatura = []

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        clase = a.get("class", "")
        oculto = bool(re.search(r"\bmodal\b", clase)) or "display:none" in a.get("style", "").replace(" ", "")
        es_miniatura = bool(re.search(r"\b(js-)?product-miniature\b", clase))
        if tag not in ("img", "source", "link", "meta", "br", "input", "hr"):
            self.pila.append(tag)
            self.ocultos.append(oculto)
            self.dentro_miniatura.append(es_miniatura)
            if es_miniatura:
                self.miniatura += 1
            if tag == "picture":
                self.picture.append([])
        if tag == "source" and self.picture:
            tipo = a.get("type", "")
            for u in urls_de_srcset(a.get("srcset")):
                f = foto(u)
                if f:
                    self.picture[-1].append(f[2])
            if "webp" in tipo:
                self.picture[-1].append("webp")
            if "avif" in tipo:
                self.picture[-1].append("avif")
        if tag == "link" and "preload" in a.get("rel", "").lower() and a.get("as", "").lower() == "image":
            for u in [a.get("href")] + urls_de_srcset(a.get("imagesrcset")):
                f = foto(u)
                if f:
                    self.precargas.append(((f[0], f[1]), f[2]))
        for nombre, valor in a.items():
            if nombre.startswith("data-") and nombre not in ("data-src", "data-srcset", "data-lazy", "data-original"):
                f = foto(valor)
                if f:
                    self.cambios_js.append(((f[0], f[1]), f[2], nombre))
            if nombre == "style":
                for u in URL_EN_CSS.findall(valor):
                    f = foto(u)
                    if f:
                        self.imgs.append(self._img(f, lazy=False, prioridad="", diferida=False))
        if tag == "img":
            lazy = a.get("loading", "").lower() == "lazy"
            diferida = False
            candidatas = [a.get("src")] + urls_de_srcset(a.get("srcset"))
            for nombre in ("data-src", "data-srcset", "data-lazy", "data-original"):
                if a.get(nombre):
                    diferida = True
                    candidatas += urls_de_srcset(a.get(nombre)) if "srcset" in nombre else [a.get(nombre)]
            vistas = set()
            for u in candidatas:
                f = foto(u)
                if f and (f[0], f[1], f[2]) not in vistas:
                    vistas.add((f[0], f[1], f[2]))
                    self.imgs.append(self._img(f, lazy, a.get("fetchpriority", "").lower(), diferida))

    def _img(self, f, lazy, prioridad, diferida):
        return {
            "clave": (f[0], f[1]), "formato": f[2], "lazy": lazy, "diferida": diferida,
            "picture": list(self.picture[-1]) if self.picture else None,
            "oculto": any(self.ocultos), "prioridad": prioridad,
            "miniatura": self.miniatura if any(self.dentro_miniatura) else 0,
        }

    def handle_endtag(self, tag):
        if tag in ("img", "source", "link", "meta", "br", "input", "hr"):
            return
        while self.pila:
            t = self.pila.pop()
            self.ocultos.pop()
            self.dentro_miniatura.pop()
            if t == "picture" and self.picture:
                self.picture.pop()
            if t == tag:
                break


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    origen = sys.argv[1]
    if re.match(r"https?://", origen):
        req = urllib.request.Request(origen, headers={
            "User-Agent": "Mozilla/5.0 (revisar_html.py)", "Accept": "text/html,image/avif,image/webp,*/*"})
        html = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")
    else:
        with open(origen, encoding="utf-8", errors="replace") as f:
            html = f.read()
    lector = Lector()
    lector.feed(html)

    problemas = 0
    imgs = lector.imgs
    efectivo = []   # (img, formato que baja un navegador con WebP)
    for i in imgs:
        fmt = i["formato"]
        if i["picture"] and ("avif" in i["picture"] or "webp" in i["picture"]) and fmt == "jpg":
            fmt = "avif" if "avif" in i["picture"] else "webp"
        efectivo.append((i, fmt))
    claves = sorted({i["clave"] for i in imgs} | {c for c, _ in lector.precargas})
    print("Fotos de producto distintas (id-tipo): %d   <img>: %d   precargas: %d   data-* para JS: %d" % (
        len(claves), len(imgs), len(lector.precargas), len(lector.cambios_js)))

    sin_webp = [(i, f) for i, f in efectivo if f == "jpg"]
    print("\n== Fotos que un navegador con WebP baja en JPG: %d" % len(sin_webp))
    for i, f in sin_webp[:25]:
        nota = " (oculta: modal o display:none)" if i["oculto"] else ""
        nota += " (loading=lazy)" if i["lazy"] else ""
        print("   %s-%s.jpg%s" % (i["clave"][0], i["clave"][1], nota))
    problemas += len(sin_webp)

    print("\n== La misma foto pedida en dos formatos (descarga doble):")
    dobles = 0
    por_clave = {}
    for i, f in efectivo:
        if not (i["oculto"] and i["lazy"]):
            por_clave.setdefault(i["clave"], set()).add(f)
    for c, fmt in lector.precargas:
        por_clave.setdefault(c, set()).add(fmt)
    for c in claves:
        if len(por_clave.get(c, ())) > 1:
            dobles += 1
            origenes = []
            if any(pc == c for pc, _ in lector.precargas):
                origenes.append("precarga en " + "/".join(sorted({fm for pc, fm in lector.precargas if pc == c})))
            if any(i["clave"] == c and i["oculto"] for i, _ in efectivo):
                origenes.append("<img> oculto sin loading=lazy")
            print("   %s-%s: %s  [%s]" % (c[0], c[1], ", ".join(sorted(por_clave[c])), "; ".join(origenes) or "varios <img>"))
    if not dobles:
        print("   ninguna")
    problemas += dobles

    altas = [i for i in imgs if i["prioridad"] == "high"]
    print("\n== fetchpriority=\"high\" en fotos de producto: %d %s" % (
        len(altas), "(bien: una, la LCP)" if len(altas) <= 1 else "(AVISO: solo la imagen LCP debe llevarlo)"))

    primeras = []
    for i in imgs:
        if i["miniatura"] and i["miniatura"] <= 4 and i["miniatura"] not in [p["miniatura"] for p in primeras]:
            primeras.append(i)
    malas = [p for p in primeras if p["diferida"]]
    if primeras:
        print("\n== Primeras %d miniaturas del listado: %s" % (len(primeras), (
            "%d con carga diferida por JavaScript (data-src): el LCP espera al JS" % len(malas)) if malas else "con src normal (bien)"))

    js_jpg = [(c, f, n) for c, f, n in lector.cambios_js if f == "jpg" and n in ("data-image-large-src", "data-image-medium-src")]
    if js_jpg:
        print("\n== Miniaturas de galería que al pulsarlas ponen la foto en JPG (%d), p. ej. %s-%s (%s)" % (
            len(js_jpg), js_jpg[0][0][0], js_jpg[0][0][1], js_jpg[0][2]))
        problemas += len(js_jpg)

    print("\nRESUMEN: %d fotos, %d en JPG, %d dobles, %d fetchpriority=high, %d primeras miniaturas diferidas" % (
        len(claves), len(sin_webp), dobles, len(altas), len(malas)))
    return 1 if problemas else 0


if __name__ == "__main__":
    sys.exit(main())
