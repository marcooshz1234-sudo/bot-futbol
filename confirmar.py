"""
31/10 (Marcos): no dar nada por seguro hasta que los datos estén confirmados (ayer el VAR anuló el gol del Espanyol
y el bot ya lo había dado por bueno).

  - Partido aplazado, cancelado o suspendido del todo (PST, CANC, ABD, AWD, WO): la pata queda «anulada», como en
    bet365, y la combi sigue con las demás.
  - En juego: una pata que se pone en verde (o en rojo) antes del final sale «comprobando» durante 10 min. Si en ese
    tiempo cambia (gol anulado), vuelve a como estaba y no se ha celebrado nada.
  - Al final del partido: «comprobando» durante 15 min después de ver el FT (la fuente corrige tiros, córners,
    tarjetas… unos minutos después). Pasado eso, verde o rojo definitivo.
Estado en datos/confirmar.json. Lo usa app_datos.py con las patas de cada post publicado.
"""
import json
from datetime import datetime, timedelta

from bot import DATOS, MADRID, leer

ESTADO = DATOS / "confirmar.json"
ANULA = {"PST", "CANC", "ABD", "AWD", "WO"}
FIN = {"FT", "AET", "PEN"}
EN_JUEGO_MIN = 10
FINAL_MIN = 15


def _t(s):
    return datetime.fromisoformat(s).replace(tzinfo=MADRID)


class Confirmador:
    def __init__(self, ahora=None):
        self.ahora = ahora or datetime.now(MADRID)
        self.antes = leer(ESTADO, {}) or {}
        # la primera vez (sin estado guardado) lo que ya estaba terminado se da por confirmado
        self.semilla = None if ESTADO.exists() else (self.ahora - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")
        self.patas = {}     # clave de pata → {"e": estado visto, "desde": cuándo}
        self.fin = {}       # partido → cuándo se vio terminado por primera vez

    def pata(self, f):
        """Cambia f["estado"] según lo confirmado. f: fila con estado, partido_id, estado_partido, texto."""
        ep, pid = f.get("estado_partido"), f.get("partido_id")
        if not pid:
            return f
        if ep in ANULA:
            f["estado"], f["definitivo"] = "anulada", True
            return f
        ahora_s = self.ahora.strftime("%Y-%m-%dT%H:%M")
        if ep in FIN:
            k = str(pid)
            self.fin[k] = self.fin.get(k) or (self.antes.get("fin") or {}).get(k) or self.semilla or ahora_s
            if f.get("estado") in ("verde", "rojo") and self.ahora - _t(self.fin[k]) < timedelta(minutes=FINAL_MIN):
                f["confirmando"], f["estado"], f["definitivo"] = f["estado"], "comprobando", False
            return f
        if f.get("estado") in ("verde", "rojo"):
            k = f"{pid}|{f.get('texto')}"
            prev = (self.antes.get("patas") or {}).get(k)
            desde = prev["desde"] if prev and prev.get("e") == f["estado"] else ahora_s
            self.patas[k] = {"e": f["estado"], "desde": desde}
            if self.ahora - _t(desde) < timedelta(minutes=EN_JUEGO_MIN):
                f["confirmando"], f["estado"], f["definitivo"] = f["estado"], "comprobando", False
        return f

    def guardar(self):
        limite = (self.ahora - timedelta(hours=36)).strftime("%Y-%m-%dT%H:%M")
        fin = {k: v for k, v in {**(self.antes.get("fin") or {}), **self.fin}.items() if v >= limite}
        ESTADO.write_text(json.dumps({"patas": self.patas, "fin": fin}, ensure_ascii=False) + "\n", encoding="utf-8")


def estado_combi(filas):
    """verde: todas en verde o anuladas (y al menos una verde); rojo: alguna roja; si no, pendiente."""
    if any(x["estado"] == "rojo" for x in filas):
        return "rojo"
    if filas and all(x["estado"] in ("verde", "anulada") for x in filas):
        return "verde" if any(x["estado"] == "verde" for x in filas) else "anulada"
    return "pendiente"
