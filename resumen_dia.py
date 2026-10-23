"""
Resumen del día automático · publica a las 23:30 (o en cuanto todo esté decidido después de las 23:15)
un post "📊 BALANCE DEL <DÍA>" con cada combi publicada hoy en verde o rojo. Telegram, Threads y
Facebook (sin imagen: Instagram se salta). Lo lee de docs/datos.json (publicados_hoy).
"""
import json
from datetime import datetime

from bot import MADRID, RAIZ, leer

DIAS = ["LUNES", "MARTES", "MIÉRCOLES", "JUEVES", "VIERNES", "SÁBADO", "DOMINGO"]
COLA = RAIZ / "publicaciones" / "cola.json"


def main():
    ahora = datetime.now(MADRID)
    hoy = ahora.strftime("%Y-%m-%d")
    pid = f"{hoy}-balance-auto"
    cola = leer(COLA, []) or []
    if ahora.strftime("%H:%M") < "23:15" or any(p["id"] in (pid, f"{hoy}-balance") for p in cola):
        return
    d = leer(RAIZ / "docs" / "datos.json", {}) or {}
    posts = [p for p in d.get("publicados_hoy", []) if p["fecha"][:10] == hoy
             and not p["titulo"].lstrip().startswith(("✅", "🔄", "📊", "📋"))]
    if not posts:
        return
    if any(p["estado"] == "pendiente" for p in posts) and ahora.strftime("%H:%M") < "23:30":
        return
    lineas, verdes = [], 0
    for p in posts:
        t = p["titulo"].replace("🔒", "").replace("💥", "").replace("🤪", "").replace("🍀", "").strip()
        icono = "✅" if p["estado"] == "verde" else "❌" if p["estado"] == "rojo" else "⏳"
        verdes += p["estado"] == "verde"
        lineas.append(f"{icono} {t}" + (f" · {p['cuota']:.2f}".replace(".", ",") if p.get("cuota") else ""))
    decididas = sum(p["estado"] in ("verde", "rojo") for p in posts)
    texto = (f"📊 BALANCE DEL {DIAS[ahora.weekday()]} 📊\n\n" + "\n".join(lineas) +
             f"\n\n💚 {verdes} de {decididas} en verde\n\nMañana más y mejor 💪🍀")
    cola.append({"id": pid, "fecha": ahora.strftime("%Y-%m-%dT%H:%M"), "texto": texto, "foto": None,
                 "origen": "bot", "directo": True, "facebook": "texto", "sin_instagram": True})
    COLA.write_text(json.dumps(cola, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Resumen del día en cola")


if __name__ == "__main__":
    main()
