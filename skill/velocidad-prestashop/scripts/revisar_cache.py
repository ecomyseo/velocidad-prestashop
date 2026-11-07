"""SOLO LECTURA. Cuánto tiempo guarda el navegador los estáticos de una web (CSS, JS, imagen y fuente de su portada) y
que las páginas y el JSON NO se guarden. Sirve para el aviso de PageSpeed «Usar tiempos de vida de caché eficientes»
y para comprobar que encender una caché no ha dado caché larga a lo que cambia.

Requisitos: pip install requests
Uso: python revisar_cache.py https://tienda.ejemplo/ [https://otra.ejemplo/ ...]
Autor: Ecom Experts. Licencia AFL-3.0."""
import re, sys, time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin, urlparse

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"


def segundos(h):
    cc = (h.get("Cache-Control") or "").lower()
    if "no-store" in cc or "no-cache" in cc:
        return 0
    m = re.search(r"max-age=(\d+)", cc)
    if m:
        return int(m.group(1))
    if h.get("Expires"):
        try:
            base = parsedate_to_datetime(h["Date"]) if h.get("Date") else datetime.now(timezone.utc)
            return int((parsedate_to_datetime(h["Expires"]) - base).total_seconds())
        except Exception:
            return 0
    return None


def texto(s):
    if s is None:
        return "SIN CABECERA (el navegador decide)"
    if s <= 0:
        return "no se guarda"
    for n, d in ((31536000, "año"), (86400, "día"), (3600, "hora")):
        if s >= n:
            v = s // n
            return f"{v} {d}" + ("s" if v > 1 else "")
    return f"{s} s"


def mismo_sitio(u, base):
    a, b = (urlparse(u).hostname or ""), (urlparse(base).hostname or "")
    a, b = a.removeprefix("www."), b.removeprefix("www.")
    return a == b or a.endswith("." + b)


def revisar(url):
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept-Language": "es-ES,es;q=0.9"})
    r = s.get(url, headers={"Accept": "text/html"}, timeout=40)
    print(f"\n== {r.url}  ({r.status_code})")
    sp = segundos(r.headers)
    print(f"  página HTML: {texto(sp)}" + ("   <-- OJO: una página no debe guardarse" if sp and sp > 60 else ""))
    html, base = r.text, r.url
    cand = {
        "css": re.findall(r"<link[^>]+rel=[\"']?stylesheet[^>]*?href=[\"']([^\"']+)", html, re.I)
               + re.findall(r"<link[^>]+href=[\"']([^\"']+\.css[^\"']*)[\"'][^>]*rel=[\"']?stylesheet", html, re.I),
        "js": re.findall(r"<script[^>]+src=[\"']([^\"']+)", html, re.I),
        "imagen": re.findall(r"<img[^>]+(?:data-src|src)=[\"']([^\"']+\.(?:jpe?g|png|webp|gif|svg|avif)(?:\?[^\"']*)?)", html, re.I),
    }
    fuente = None
    for tipo, lista in cand.items():
        propios = [urljoin(base, u.replace("&amp;", "&")) for u in lista]
        propios = [u for u in propios if u.startswith("http") and mismo_sitio(u, base)]
        if not propios:
            print(f"  {tipo:7}: (ninguno propio en la portada)")
            continue
        time.sleep(0.8)
        a = s.get(propios[0], timeout=40, headers={"Accept": "image/avif,image/webp,*/*" if tipo == "imagen" else "*/*"})
        print(f"  {tipo:7}: {texto(segundos(a.headers)):34} {propios[0][-70:]}")
        if tipo == "css" and fuente is None:
            m = re.search(r"url\(\s*[\"']?([^\"')]+\.(?:woff2?|ttf)(?:\?[^\"')]*)?)", a.text, re.I)
            if m:
                fuente = urljoin(propios[0], m.group(1))
    if fuente and mismo_sitio(fuente, base):
        time.sleep(0.8)
        a = s.get(fuente, timeout=40)
        print(f"  {'fuente':7}: {texto(segundos(a.headers)):34} {fuente[-70:]}")


for u in sys.argv[1:]:
    try:
        revisar(u)
    except Exception as e:
        print(f"\n== {u}: ERROR {type(e).__name__}: {e}")
