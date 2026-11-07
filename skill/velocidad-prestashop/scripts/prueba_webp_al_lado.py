"""Prueba de webp_al_lado.py con imágenes de pega en una carpeta temporal: PNG con transparencia, JPG girado por EXIF,
JPG CMYK y PNG diminuto. Comprueba creación, tamaño visto, transparencia, que no se toca la original, la simulación,
que un WebP viejo se rehace y que --deshacer lo deja todo como estaba.
Uso: python prueba_webp_al_lado.py   (acaba con «FALLOS: 0»)"""
import hashlib, io, os, subprocess, sys, tempfile, time
from pathlib import Path

from PIL import Image

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SCRIPT = str(Path(__file__).with_name("webp_al_lado.py"))
T = Path(tempfile.mkdtemp(prefix="webp-al-lado-"))
d = T / "img"
d.mkdir()
rgb = Image.merge("RGB", [Image.effect_noise((800, 400), s).convert("L") for s in (40, 60, 80)])
alfa = Image.new("L", (800, 400), 255); alfa.paste(0, (0, 0, 20, 400))
im = rgb.convert("RGBA"); im.putalpha(alfa); im.save(d / "banner.png")
ex = Image.Exif(); ex[0x0112] = 6
Image.effect_noise((300, 200), 60).convert("RGB").save(d / "girada.jpg", quality=95, exif=ex.tobytes())
Image.effect_noise((400, 300), 50).convert("CMYK").save(d / "cmyk.jpg", quality=95)
Image.new("P", (16, 16), 3).save(d / "icono.png")
huella = {p.name: hashlib.md5(p.read_bytes()).hexdigest() for p in d.iterdir()}
reg = str(T / "registro.json")
fallos = []


def lanzar(*args):
    r = subprocess.run([sys.executable, SCRIPT, *args], capture_output=True, text=True, encoding="utf-8")
    if r.returncode:
        fallos.append(f"salida {r.returncode}: {r.stderr[-300:]}")
    return r.stdout


lanzar("--simular", str(d))
if list(d.glob("*.webp")):
    fallos.append("la simulación ha escrito ficheros")
print(lanzar(str(d), "--registro", reg).strip().splitlines()[-2])
creados = sorted(p.name for p in d.glob("*.webp"))
if creados != ["banner.png.webp", "cmyk.jpg.webp", "girada.jpg.webp"]:
    fallos.append(f"creados: {creados}")
w = Image.open(d / "banner.png.webp")
if w.size != (800, 400) or w.mode != "RGBA" or w.getpixel((5, 5))[3] != 0:
    fallos.append("banner: tamaño o transparencia")
if Image.open(d / "girada.jpg.webp").size != (200, 300):
    fallos.append("girada: no se aplicó la orientación EXIF")
if any(hashlib.md5((d / n).read_bytes()).hexdigest() != h for n, h in huella.items()):
    fallos.append("se ha tocado una original")
# un WebP viejo (imagen cambiada después) se rehace
viejo = (d / "banner.png.webp").read_bytes()
time.sleep(1.1)
os.utime(d / "banner.png", None)
lanzar(str(d), "--registro", str(T / "registro2.json"))
if (d / "banner.png.webp").stat().st_mtime < (d / "banner.png").stat().st_mtime:
    fallos.append("no rehízo el WebP viejo")
lanzar("--deshacer", str(T / "registro2.json"))
if (d / "banner.png.webp").read_bytes() != viejo:
    fallos.append("deshacer no repuso el WebP anterior")
lanzar("--deshacer", reg)
if list(d.glob("*.webp")):
    fallos.append(f"deshacer dejó {list(d.glob('*.webp'))}")
print("FALLOS:", fallos or 0)
sys.exit(1 if fallos else 0)
