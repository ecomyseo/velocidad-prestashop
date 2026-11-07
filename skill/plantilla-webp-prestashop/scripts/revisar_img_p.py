#!/usr/bin/env python3
"""
revisar_img_p.py: recorre la carpeta img/p de una tienda PrestaShop (SOLO LEE) y cuenta, por tipo de imagen,
cuántas miniaturas JPG tienen su WebP (o AVIF) al lado, cuántas no, cuántos WebP son MÁS VIEJOS que su JPG o que la
foto original (enseñarían la foto anterior a quien acepta WebP) y cuánto pesan unos y otros.

@author    Ecom Experts <ecomyseo@gmail.com>
@copyright 2026 Ecom Experts
@license   https://opensource.org/licenses/AFL-3.0 Academic Free License 3.0 (AFL-3.0)

Uso (en el servidor, como el usuario de la web o con permisos de lectura):
  python3 revisar_img_p.py /ruta/de/la/tienda/img/p
  python3 revisar_img_p.py /ruta/img/p --formato avif
  python3 revisar_img_p.py /ruta/img/p --lista viejos.txt     (escribe la ruta de cada WebP viejo, uno por línea)

No borra ni convierte nada. Con la lista, lo viejo se regenera con la herramienta de la tienda (Diseño > Ajustes de
imagen > Regenerar miniaturas) o se aparta para que la plantilla vuelva al JPG hasta regenerarlo.
Sale con 1 si hay WebP viejos.
"""
import argparse
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass

MINIATURA = re.compile(r"^(\d+)-([A-Za-z][\w-]*)\.jpg$")


def main():
    ap = argparse.ArgumentParser(description="WebP de las fotos de producto: cobertura, antigüedad y peso")
    ap.add_argument("carpeta", help="carpeta img/p de la tienda")
    ap.add_argument("--formato", default="webp", choices=("webp", "avif"))
    ap.add_argument("--lista", help="fichero donde escribir las rutas de los WebP más viejos que su JPG")
    a = ap.parse_args()
    if not os.path.isdir(a.carpeta):
        print("No existe la carpeta: " + a.carpeta)
        return 2

    tipos = {}
    viejos = []
    for base, _dirs, ficheros in os.walk(a.carpeta):
        conjunto = set(ficheros)
        for f in ficheros:
            m = MINIATURA.match(f)
            if not m:
                continue
            ident, tipo = m.group(1), m.group(2)
            t = tipos.setdefault(tipo, {"jpg": 0, "con": 0, "sin": 0, "viejos": 0, "bytes_jpg": 0, "bytes_otro": 0})
            t["jpg"] += 1
            otro = "%s-%s.%s" % (ident, tipo, a.formato)
            if otro not in conjunto:
                t["sin"] += 1
                continue
            t["con"] += 1
            ruta_jpg = os.path.join(base, f)
            ruta_otro = os.path.join(base, otro)
            ruta_orig = os.path.join(base, ident + ".jpg")
            try:
                st_jpg = os.stat(ruta_jpg)
                st_otro = os.stat(ruta_otro)
                st_orig = os.stat(ruta_orig) if ident + ".jpg" in conjunto else None
            except OSError:
                continue
            t["bytes_jpg"] += st_jpg.st_size
            t["bytes_otro"] += st_otro.st_size
            # más viejo que su JPG o que la foto original: la foto cambió y el WebP no se rehízo
            referencia = max(st_jpg.st_mtime, st_orig.st_mtime if st_orig else 0)
            if st_otro.st_mtime + 1 < referencia:
                t["viejos"] += 1
                viejos.append(ruta_otro)

    if not tipos:
        print("No hay miniaturas N-tipo.jpg en " + a.carpeta)
        return 2
    fmt = a.formato.upper()
    print("%-22s %8s %8s %8s %8s %12s %12s %7s" % ("tipo", "JPG", "con " + fmt, "sin " + fmt, "viejos", "MB JPG*", "MB " + fmt + "*", fmt + "/JPG"))
    total = {"jpg": 0, "con": 0, "sin": 0, "viejos": 0, "bytes_jpg": 0, "bytes_otro": 0}
    for tipo in sorted(tipos):
        t = tipos[tipo]
        for k in total:
            total[k] += t[k]
        ratio = (100.0 * t["bytes_otro"] / t["bytes_jpg"]) if t["bytes_jpg"] else 0
        print("%-22s %8d %8d %8d %8d %12.1f %12.1f %6.0f %%" % (
            tipo, t["jpg"], t["con"], t["sin"], t["viejos"], t["bytes_jpg"] / 1048576.0, t["bytes_otro"] / 1048576.0, ratio))
    ratio = (100.0 * total["bytes_otro"] / total["bytes_jpg"]) if total["bytes_jpg"] else 0
    print("%-22s %8d %8d %8d %8d %12.1f %12.1f %6.0f %%" % (
        "TOTAL", total["jpg"], total["con"], total["sin"], total["viejos"], total["bytes_jpg"] / 1048576.0,
        total["bytes_otro"] / 1048576.0, ratio))
    print("* el peso se suma solo de las parejas que tienen los dos formatos.")
    if total["con"] and ratio >= 85:
        print("AVISO: el %s pesa el %.0f %% del JPG: con JPG ya comprimidos, baja la calidad (prueba 75) y mide otra vez." % (fmt, ratio))
    if viejos:
        print("AVISO: %d ficheros %s más viejos que su JPG u original: quien acepta %s vería la foto ANTERIOR." % (len(viejos), fmt, fmt))
        for r in viejos[:10]:
            print("   " + r)
        if a.lista:
            with open(a.lista, "w", encoding="utf-8") as f:
                f.write("\n".join(viejos) + "\n")
            print("Lista completa en " + a.lista)
    return 1 if viejos else 0


if __name__ == "__main__":
    sys.exit(main())
