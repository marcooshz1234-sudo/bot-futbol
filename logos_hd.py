"""12/11 (Marcos: «busca siempre la máxima calidad del logo, que no se vea borroso»).

Los logos de API-Football son de 150 px y se ven borrosos al agrandarlos. Este script busca cada logo de
competición en grande (TheSportsDB, la API libre) y lo guarda como publicaciones/media/escudos/liga-<id>-hd.png
(recortado al contenido, sin márgenes). Las plantillas usan el -hd si existe (ganadores_img.logo_liga).
Se ejecuta en el bot de GitHub (aquí hay red); no rehace los que ya están.
"""
import io
import json
import sys
from pathlib import Path
from urllib.request import Request, urlopen

RAIZ = Path(__file__).parent
ESCUDOS = RAIZ / "publicaciones" / "media" / "escudos"

# id de API-Football → (palabras que tiene que tener el nombre en TheSportsDB, ids candidatos de TheSportsDB)
COMPETICIONES = {
    5: (("nations",), (4490, 4855)),
    143: (("copa del rey",), (4483,)),
    140: (("la liga", "laliga"), (4335,)),
    39: (("premier",), (4328,)),
    2: (("champions",), (4480,)),
    3: (("europa league",), (4481,)),
    848: (("conference",), (5071,)),
    135: (("serie a",), (4332,)),
    78: (("bundesliga",), (4331,)),
    61: (("ligue 1",), (4334,)),
    525: (("women", "champions"), (4878, 5052)),
}
MIN_LADO = 300


def bajar(url, json_=False):
    with urlopen(Request(url, headers={"User-Agent": "Mozilla/5.0 combilocas-bot"}), timeout=25) as r:
        datos = r.read()
    return json.loads(datos) if json_ else datos


def candidatos(palabras, ids):
    for i in ids:
        try:
            ligas = (bajar(f"https://www.thesportsdb.com/api/v1/json/3/lookupleague.php?id={i}", True) or {}).get("leagues") or []
        except Exception as e:
            print(f"  TheSportsDB {i}: {e}")
            continue
        for l in ligas:
            nombre = (l.get("strLeague") or "").lower() + " " + (l.get("strLeagueAlternate") or "").lower()
            if all(p in nombre for p in palabras[:1]) and all(p in nombre for p in palabras):
                for k in ("strBadge", "strLogo"):
                    if l.get(k):
                        yield l[k]


def guardar(url, destino):
    from PIL import Image
    im = Image.open(io.BytesIO(bajar(url))).convert("RGBA")
    caja = im.getbbox()
    if caja:
        im = im.crop(caja)
    if max(im.size) < MIN_LADO:
        raise ValueError(f"pequeño ({im.size})")
    im.thumbnail((800, 800))
    im.save(destino, optimize=True)
    return im.size


def main(forzar=False):
    ESCUDOS.mkdir(parents=True, exist_ok=True)
    for liga, (palabras, ids) in COMPETICIONES.items():
        destino = ESCUDOS / f"liga-{liga}-hd.png"
        if destino.exists() and not forzar:
            continue
        ok = False
        for url in candidatos(palabras, ids):
            try:
                tam = guardar(url, destino)
                print(f"Logo HD {liga}: {url} {tam}")
                ok = True
                break
            except Exception as e:
                print(f"  {liga} {url}: {e}")
        if not ok:
            print(f"Logo HD {liga}: no encontrado (se usa el de API-Football)")


if __name__ == "__main__":
    main(forzar="--forzar" in sys.argv)
