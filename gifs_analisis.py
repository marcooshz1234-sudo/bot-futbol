"""Saca de GIPHY los datos (título, canal, etiquetas) de los GIF que Marcos ha votado, para aprender su gusto."""
import json, os
from urllib.parse import urlencode
from urllib.request import urlopen
from bot import DATOS
v = json.load(open(DATOS / "gifs_votos.json"))
ids_si = [x["giphy"] for xs in v["si"].values() for x in xs]
ids_no = v["no"]
def meta(ids):
    out = []
    for i in range(0, len(ids), 50):
        q = urlencode({"api_key": os.environ["GIPHY_API_KEY"], "ids": ",".join(ids[i:i + 50])})
        with urlopen(f"https://api.giphy.com/v1/gifs?{q}", timeout=30) as r:
            for g in json.load(r).get("data") or []:
                out.append({"id": g["id"], "titulo": g.get("title"), "usuario": g.get("username"),
                            "fuente": g.get("source_tld"), "tipo": g.get("type"), "alt": g.get("alt_text"),
                            "verificado": (g.get("user") or {}).get("is_verified")})
    return out
json.dump({"si": meta(ids_si), "no": meta(ids_no)}, open(DATOS / "gifs_analisis.json", "w"), ensure_ascii=False, indent=1)
