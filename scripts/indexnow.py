"""Avisa a Bing y demás buscadores de IndexNow de las páginas de la web tras cada publicación.

Lee el sitemap publicado y envía sus URL. No necesita cuenta: la clave está en
config/sitio.json > indexnow_clave y el archivo <clave>.txt se publica con la web.
"""
import json
import re
import sys
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

cfg = json.loads((Path(__file__).resolve().parent.parent / "config" / "sitio.json").read_text("utf-8"))
clave = cfg.get("indexnow_clave")
if not clave:
    sys.exit("Sin indexnow_clave en config/sitio.json")
base = cfg["url_base"].rstrip("/")

xml = ""
for intento in range(6):  # GitHub Pages tarda unos segundos en servir la versión nueva
    try:
        xml = urllib.request.urlopen(f"{base}/sitemap.xml?v={time.time():.0f}", timeout=30).read().decode()
        urllib.request.urlopen(f"{base}/{clave}.txt", timeout=30).read()
        break
    except Exception as e:  # noqa: BLE001
        print("Esperando a la web publicada:", e)
        time.sleep(20)
urls = re.findall(r"<loc>([^<]+)</loc>", xml)
if not urls:
    sys.exit("No hay URL en el sitemap")

cuerpo = json.dumps({"host": urlparse(base).netloc, "key": clave,
                     "keyLocation": f"{base}/{clave}.txt", "urlList": urls[:10000]}).encode()
req = urllib.request.Request("https://api.indexnow.org/indexnow", data=cuerpo,
                             headers={"Content-Type": "application/json; charset=utf-8"})
try:
    r = urllib.request.urlopen(req, timeout=60)
    print(f"IndexNow: {len(urls)} URL enviadas, respuesta {r.status}")
except urllib.error.HTTPError as e:
    print(f"IndexNow respondió {e.code}: {e.read()[:300]!r}")
    sys.exit(0 if e.code in (202, 429) else 1)
