"""Crea un WebP al lado de cada imagen JPG/PNG de una o varias carpetas (banners, slider, img/cms...):
banner.png -> banner.png.webp. La imagen original NO se toca nunca.

- aplica la orientación EXIF (la foto no sale girada);
- convierte a sRGB las imágenes con otro perfil de color (Display P3, Adobe RGB) y CMYK a RGB;
- conserva la transparencia y las dimensiones que se ven;
- solo guarda el WebP si pesa al menos un 10 % menos que la original;
- rehace los WebP más viejos que su imagen (si no, se vería la imagen anterior);
- deja un registro JSON con lo creado y lo sustituido, para deshacerlo con --deshacer.

Después hay que hacer que el servidor entregue el WebP (ver plantillas/nginx-webp.conf o htaccess-webp.txt).
Ejecutarlo con el mismo usuario dueño de la web, para que los ficheros nuevos sean suyos.

Requisitos: pip install pillow   (Pillow con WebP y LittleCMS)
Uso:
  python webp_al_lado.py --simular /ruta/web/img/cms /ruta/web/modules/slider/images
  python webp_al_lado.py /ruta/web/img/cms ... [--calidad 80] [--minimo 20000] [--registro webp-registro.json]
  python webp_al_lado.py --deshacer webp-registro.json
Autor: Ecom Experts. Licencia AFL-3.0."""
import argparse, hashlib, io, json, os, shutil, sys, time

from PIL import Image, ImageCms, ImageOps

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
EXT = (".png", ".jpg", ".jpeg")


def a_webp(ruta, calidad):
    im = Image.open(ruta)
    im = ImageOps.exif_transpose(im)
    visto = im.size
    icc = im.info.get("icc_profile")
    if icc and im.mode in ("RGB", "RGBA", "CMYK"):
        origen = ImageCms.ImageCmsProfile(io.BytesIO(icc))
        nombre = ImageCms.getProfileDescription(origen).strip().lower()
        if im.mode == "CMYK" or "srgb" not in nombre:
            im = ImageCms.profileToProfile(im, origen, ImageCms.createProfile("sRGB"),
                                           outputMode="RGBA" if im.mode == "RGBA" else "RGB")
    if im.mode == "CMYK":
        im = im.convert("RGB")
    if im.mode in ("P", "LA", "L", "1", "I;16", "I"):
        im = im.convert("RGBA" if ("transparency" in im.info or im.mode in ("LA", "P")) else "RGB")
    if im.mode == "RGBA" and im.getextrema()[3][0] == 255:
        im = im.convert("RGB")
    buf = io.BytesIO()
    im.save(buf, "WEBP", quality=calidad, method=6)
    return buf.getvalue(), im.size == visto


def convertir(carpetas, calidad, minimo, simular, registro):
    hecho = {"fecha": time.strftime("%Y-%m-%d %H:%M:%S"), "creados": [], "sustituidos": {}, "sin_ventaja": 0}
    copias = registro + ".copias"
    antes = despues = 0
    for carpeta in carpetas:
        for d, _, fs in os.walk(carpeta):
            for f in fs:
                if not f.lower().endswith(EXT):
                    continue
                p = os.path.join(d, f)
                w = p + ".webp"
                st = os.stat(p)
                if st.st_size < minimo:
                    continue
                if os.path.isfile(w) and os.stat(w).st_mtime >= st.st_mtime and os.stat(w).st_size <= st.st_size * 0.9:
                    continue
                try:
                    datos, mismo_tamano = a_webp(p, calidad)
                except Exception as e:
                    print(f"  ERROR {p}: {type(e).__name__}: {e}")
                    continue
                if len(datos) > st.st_size * 0.9 or not mismo_tamano:
                    hecho["sin_ventaja"] += 1
                    continue
                antes += st.st_size
                despues += len(datos)
                print(f"  {st.st_size / 1024:8.0f} KB -> {len(datos) / 1024:7.0f} KB  {p}")
                if simular:
                    continue
                if os.path.isfile(w):
                    clave = hashlib.md5(os.path.abspath(w).encode("utf-8", "surrogateescape")).hexdigest()[:12]
                    copia = os.path.join(copias, f"{clave}-{os.path.basename(w)}")
                    os.makedirs(copias, exist_ok=True)
                    shutil.copy2(w, copia)
                    hecho["sustituidos"][w] = copia
                else:
                    hecho["creados"].append(w)
                tmp = w + ".tmp"
                with open(tmp, "wb") as fh:
                    fh.write(datos)
                os.replace(tmp, w)
    print(f"\n{'SIMULACIÓN: ' if simular else ''}{len(hecho['creados']) + len(hecho['sustituidos'])} WebP"
          f" · {antes / 1048576:.1f} MB -> {despues / 1048576:.1f} MB · sin ventaja: {hecho['sin_ventaja']}")
    if not simular:
        with open(registro, "w", encoding="utf-8") as fh:
            json.dump(hecho, fh, ensure_ascii=False, indent=1)
        print(f"registro para deshacer: {registro}")


def deshacer(registro):
    with open(registro, encoding="utf-8") as fh:
        hecho = json.load(fh)
    n = 0
    for w in hecho["creados"]:
        if os.path.isfile(w):
            os.unlink(w)
            n += 1
    for w, copia in hecho["sustituidos"].items():
        if os.path.isfile(copia):
            shutil.copy2(copia, w)
            n += 1
    print(f"deshecho: {n} ficheros")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("carpetas", nargs="*")
    ap.add_argument("--calidad", type=int, default=80)
    ap.add_argument("--minimo", type=int, default=20000, help="bytes; las imágenes más pequeñas no se tocan")
    ap.add_argument("--simular", action="store_true")
    ap.add_argument("--registro", default="webp-registro.json")
    ap.add_argument("--deshacer", metavar="REGISTRO")
    a = ap.parse_args()
    if a.deshacer:
        deshacer(a.deshacer)
    elif a.carpetas:
        convertir(a.carpetas, a.calidad, a.minimo, a.simular, a.registro)
    else:
        ap.print_help()
