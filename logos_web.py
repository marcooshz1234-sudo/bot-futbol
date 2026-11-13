"""13/11 (Marcos: «ese logo no me gusta, no tiene calidad; revísalos todos bien, búscalos en internet»
→ «en paladarnegro.net y football-logos.cc»).

Descarga los logos de competición grandes (700 px, football-logos.cc; ligas también de paladarnegro.net) en
publicaciones/media/escudos/candidatos/ para elegirlos con Marcos. NO cambia los que usan las tarjetas
(liga-<id>-hd.png): eso se hace a mano cuando Marcos dé el OK. Va en el bot de GitHub (escudos.yml: aquí no hay red).
"""
import urllib.request
from pathlib import Path

DEST = Path(__file__).parent / "publicaciones" / "media" / "escudos" / "candidatos"
FL = "https://assets.football-logos.cc/logos/"
PN = "https://paladarnegro.net/escudoteca/ligas/ligas/png/"
URLS = {   # id de API-Football → [(origen, url)]
    61: [("fl", FL + "france/700x700/ligue-1.9fc5cb7b.png"), ("pn", PN + "francia.png")],
    140: [("fl", FL + "spain/700x700/la-liga.362cd1ca.png"), ("pn", PN + "espana.png"), ("pn2", PN + "espana2.png")],
    5: [("fl", FL + "tournaments/700x700/uefa-nations-league.178b1e72.png")],
    2: [("fl", FL + "tournaments/700x700/uefa-champions-league.c16cec3d.png")],
    3: [("fl", FL + "tournaments/700x700/uefa-europa-league.cec59481.png")],
    848: [("fl", FL + "tournaments/700x700/uefa-conference-league.4a977457.png")],
    39: [("fl", FL + "england/700x700/english-premier-league.ee1e9b08.png"), ("pn", PN + "inglaterra.png")],
    78: [("fl", FL + "germany/700x700/bundesliga.dd519ce6.png"), ("pn", PN + "alemania.png")],
    135: [("fl", FL + "italy/700x700/serie-a.15e58b67.png"), ("pn", PN + "italia.png")],
    525: [("fl", FL + "tournaments/700x700/uefa-womens-champions-league.b386ab02.png")],
    143: [("fl", FL + "spain/700x700/copa-del-rey.a3ebbbe0.png")],
}


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    for lid, fuentes in URLS.items():
        for origen, url in fuentes:
            out = DEST / f"liga-{lid}-{origen}.png"
            if out.exists():
                continue
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                out.write_bytes(urllib.request.urlopen(req, timeout=20).read())
                print("ok", out.name)
            except Exception as e:
                print("fallo", lid, origen, e)


if __name__ == "__main__":
    main()
