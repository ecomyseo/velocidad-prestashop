"""Mide páginas como las ve un cliente con móvil en 4G lenta (150 ms, 1,6 Mbit/s, CPU x4), en primera visita (sin
caché) y segunda (con la caché del navegador): FCP, LCP y su imagen, carga, KB por la red, peticiones, recursos que
bloquean el pintado, dominios externos que bloquean, los ficheros más pesados y los errores de JavaScript.

Requisitos: pip install playwright && python -m playwright install chromium
Uso:
  python medir.py URL [URL...] [--etiqueta antes] [--repeticiones 3] [--escritorio]
Guarda medida-<etiqueta>.json junto al script para comparar el antes y el después.
Autor: Ecom Experts. Licencia AFL-3.0."""
import argparse, json, statistics, sys, time
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ap = argparse.ArgumentParser()
ap.add_argument("urls", nargs="+")
ap.add_argument("--etiqueta", default="medida")
ap.add_argument("--repeticiones", type=int, default=3)
ap.add_argument("--escritorio", action="store_true", help="pantalla de escritorio y red sin limitar")
a = ap.parse_args()

UA_MOVIL = "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36"
UA_PC = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
METRICAS = r"""async () => {
  const n = performance.getEntriesByType('navigation')[0] || {};
  const fcp = (performance.getEntriesByName('first-contentful-paint')[0] || {}).startTime || null;
  const lcp = await new Promise(res => { let v = null, u = '';
    try { new PerformanceObserver(l => { for (const e of l.getEntries()) { v = e.startTime; u = e.url || (e.element ? e.element.tagName : ''); } })
      .observe({type: 'largest-contentful-paint', buffered: true}); } catch (x) {}
    setTimeout(() => res([v, u]), 300); });
  const rs = performance.getEntriesByType('resource');
  const bloq = rs.filter(r => r.renderBlockingStatus === 'blocking').map(r => r.name.split('?')[0]);
  const ext = [...new Set(bloq.map(u => new URL(u).hostname).filter(h => h !== location.hostname))];
  const rotas = [...document.images].filter(i => i.complete && i.naturalWidth === 0 && i.currentSrc).map(i => i.currentSrc);
  return {fcp, lcp: lcp[0], lcp_elemento: lcp[1], carga: n.loadEventEnd || null, bloquean: bloq,
          externos_que_bloquean: ext, imagenes_rotas: rotas};
}"""


def una_carga(ctx, url):
    p = ctx.new_page()
    cdp = ctx.new_cdp_session(p)
    cdp.send("Network.enable")
    if not a.escritorio:
        cdp.send("Network.emulateNetworkConditions", {"offline": False, "latency": 150, "downloadThroughput": 1.6e6 / 8,
                                                      "uploadThroughput": 750e3 / 8})
        cdp.send("Emulation.setCPUThrottlingRate", {"rate": 4})
    peticiones, tamanos, desde_cache = {}, {}, [0]
    cdp.on("Network.requestWillBeSent", lambda e: peticiones.__setitem__(e["requestId"], e["request"]["url"]))
    cdp.on("Network.loadingFinished", lambda e: tamanos.__setitem__(e["requestId"], e.get("encodedDataLength", 0)))
    cdp.on("Network.requestServedFromCache", lambda e: desde_cache.__setitem__(0, desde_cache[0] + 1))
    errores = []
    p.on("pageerror", lambda e: errores.append(str(e)[:200]))
    p.goto(url, wait_until="load", timeout=180000)
    time.sleep(2.5)
    m = p.evaluate(METRICAS)
    pesadas = sorted(((tamanos[i], peticiones.get(i, "")) for i in tamanos), reverse=True)[:8]
    m.update(kb=round(sum(tamanos.values()) / 1024), peticiones=len(peticiones), desde_cache=desde_cache[0],
             errores_js=errores, pesadas=[[round(b / 1024), u[:160]] for b, u in pesadas])
    p.close()
    return m


res = {}
with sync_playwright() as pw:
    nav = pw.chromium.launch(headless=True)
    try:
        for url in a.urls:
            filas = []
            for _ in range(a.repeticiones):
                if a.escritorio:
                    ctx = nav.new_context(user_agent=UA_PC, viewport={"width": 1366, "height": 900})
                else:
                    ctx = nav.new_context(user_agent=UA_MOVIL, viewport={"width": 390, "height": 844}, is_mobile=True,
                                          has_touch=True, device_scale_factor=2)
                primera = una_carga(ctx, url)
                segunda = una_carga(ctx, url)
                ctx.close()
                filas.append((primera, segunda))
            med = lambda k, i: round(statistics.median([(f[i][k] or 0) for f in filas]))
            p0 = filas[0][0]
            r = res[url] = {
                "primera": {k: med(k, 0) for k in ("fcp", "lcp", "carga", "kb", "peticiones")},
                "segunda": {k: med(k, 1) for k in ("fcp", "lcp", "carga", "kb", "desde_cache")},
                "lcp_elemento": p0["lcp_elemento"], "bloquean": p0["bloquean"],
                "externos_que_bloquean": p0["externos_que_bloquean"], "pesadas": p0["pesadas"],
                "imagenes_rotas": p0["imagenes_rotas"],
                "errores_js": sorted({e for f in filas for v in f for e in v["errores_js"]}),
            }
            print(f"\n{url}")
            print(f"  1.ª visita: FCP {r['primera']['fcp']} ms · LCP {r['primera']['lcp']} ms · carga {r['primera']['carga']} ms"
                  f" · {r['primera']['kb']} KB · {r['primera']['peticiones']} peticiones")
            print(f"  2.ª visita: FCP {r['segunda']['fcp']} ms · LCP {r['segunda']['lcp']} ms · carga {r['segunda']['carga']} ms"
                  f" · {r['segunda']['kb']} KB · {r['segunda']['desde_cache']} desde la caché")
            print(f"  LCP: {str(r['lcp_elemento'])[:120]}")
            print(f"  bloquean el pintado: {len(r['bloquean'])} (externos: {', '.join(r['externos_que_bloquean']) or 'ninguno'})")
            for kb, u in r["pesadas"][:5]:
                print(f"    {kb:6} KB  {u[:110]}")
            if r["imagenes_rotas"]:
                print(f"  imágenes rotas: {len(r['imagenes_rotas'])}")
            print(f"  errores de JavaScript: {len(r['errores_js'])}")
            for e in r["errores_js"][:5]:
                print(f"    {e[:150]}")
    finally:
        nav.close()
salida = Path(__file__).with_name(f"medida-{a.etiqueta}.json")
salida.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"\nguardado en {salida}")
