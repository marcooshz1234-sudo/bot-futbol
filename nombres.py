"""
15/11 (Marcos: «El Belarus o el Albania no puede ser: cuando son países, no pongas el delante nunca. Y el país está en
un idioma en un lado y en otro idioma en otro. Es todo en español siempre»).

Un único corrector por el que pasa TODO texto antes de publicarse (Telegram, Threads e imagen de Instagram):
  - selecciones en español (Belarus → Bielorrusia, Latvia → Letonia…)
  - sin artículo delante de un país («el Albania» → «Albania», «del Chipre» → «de Chipre», «al Portugal» → «a Portugal»)
comprobar_post.idioma() bloquea lo que aún se cuele.
"""
import re

from combis_dia import PAISES_ES, SELECCIONES_IGUAL

# más nombres en inglés que da la API y no estaban
EXTRA = {"Turkey": "Turquía", "Czech Rep.": "Chequia", "Republic of Ireland": "Irlanda", "Ireland": "Irlanda",
         "North Macedonia": "Macedonia del Norte", "Bosnia and Herzegovina": "Bosnia", "Bosnia-Herzegovina": "Bosnia",
         "Georgia": "Georgia", "Germany": "Alemania", "Russia": "Rusia", "Morocco": "Marruecos", "Mexico": "México",
         "Brazil": "Brasil", "USA": "Estados Unidos", "United States": "Estados Unidos", "Japan": "Japón",
         "South Korea": "Corea del Sur", "Korea Republic": "Corea del Sur", "Egypt": "Egipto", "Tunisia": "Túnez",
         "Algeria": "Argelia", "Cameroon": "Camerún", "Ivory Coast": "Costa de Marfil", "Peru": "Perú",
         "Canada": "Canadá", "Saudi Arabia": "Arabia Saudí", "Iran": "Irán", "New Zealand": "Nueva Zelanda"}
INGLES = {**PAISES_ES, **EXTRA}
INGLES.pop("Georgia", None)

PAISES = set(INGLES.values()) | set(SELECCIONES_IGUAL) | {"Kosovo", "Israel", "Portugal", "Austria", "Albania"}


def _rx(nombres):
    return "|".join(re.escape(n) for n in sorted(nombres, key=len, reverse=True))


_INGLES_RX = re.compile(rf"(?<![\wÀ-ÿ])({_rx(INGLES)})(?![\wÀ-ÿ])")
_ARTICULO_RX = re.compile(rf"(?<![\wÀ-ÿ])(el|El|EL|del|Del|DEL|al|Al|AL) ({_rx(PAISES)})(?![\wÀ-ÿ])")


_DECIMAL_RX = re.compile(r"(?<![\w/.:,])([+-]?\d{1,2})\.(\d{1,2})(?![\d.\w/])")


def espanol(t):
    """El texto con las selecciones en español y sin artículo delante."""
    if not t:
        return t
    t = _INGLES_RX.sub(lambda m: INGLES[m.group(1)], t)
    # 16/11: «más de 2.5 goles» → «2,5» (las copias traían el punto inglés); no toca horas, enlaces ni versiones
    t = _DECIMAL_RX.sub(lambda m: m.group(0) if m.group(2) in ("00", "15", "30", "45") and len(m.group(1)) == 2 else f"{m.group(1)},{m.group(2)}", t)

    def sin_articulo(m):
        art, pais = m.group(1), m.group(2)
        quita = {"el": "", "del": "de ", "al": "a "}[art.lower()]
        if quita and art[0].isupper():
            quita = quita[0].upper() + quita[1:]
        if not quita and art[0].isupper():   # «El Belarus jugó…» → «Bielorrusia jugó…» (ya empieza en mayúscula)
            return pais
        return quita + pais
    return _ARTICULO_RX.sub(sin_articulo, t)


def fallos(t):
    """Lo que sigue mal en un texto: países en inglés o con artículo."""
    out = [f"«{m.group(1)}» en inglés" for m in _INGLES_RX.finditer(t or "")]
    out += [f"«{m.group(0)}» con artículo" for m in _ARTICULO_RX.finditer(t or "")]
    return out
