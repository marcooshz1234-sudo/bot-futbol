"""
10/11 (Marcos: «la oficina… pinchando en cada uno, ver qué hacen y modificar cosas»): los ajustes de cada ROL de la
Oficina Combilocas (pestaña 🏢 del panel). Se guardan como los demás interruptores del panel, en
publicaciones/control.json → "ajustes", y los cambia la mini app del bot (panel_acciones.py, acción «ajuste»).
Los valores por defecto son lo que el bot ya hacía: si nadie toca nada, no cambia nada.
Las reglas de fondo (sin mercados de 1ª parte, no editar posts publicados…) NO están aquí: se cambian hablando con Claude.
"""
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
CONTROL = RAIZ / "publicaciones" / "control.json"

ROLES = {
    "ojeador": {"t": "Ojeador", "d": "Lee los canales de los tipsters y apunta sus picks"},
    "analista": {"t": "Analista", "d": "Elige el pick del día y las combis"},
    "redactor": {"t": "Redactor", "d": "Escribe los posts con el estilo del canal"},
    "verificador": {"t": "Verificador", "d": "Comprueba resultados, verdes y rojos"},
    "community": {"t": "Community", "d": "Propone respuestas a los comentarios"},
    "vigilante": {"t": "Vigilante", "d": "Vigila que el bot funcione y te avisa"},
    "cazador": {"t": "Cazador", "d": "Busca cuotas de bet365 por encima de lo justo (Pinnacle y otras casas) y te avisa"},
}

# misma forma que panel_datos.AJUSTES (+ "rol"); tipo: si_no | num | hora | texto
AJUSTES_ROLES = {
    "pausa_ojeador": {"rol": "ojeador", "t": "En pausa", "d": "No lee canales", "tipo": "si_no", "v": False},
    "pausa_analista": {"rol": "analista", "t": "En pausa", "d": "No saca pick del día nuevo", "tipo": "si_no", "v": False},
    "pick_cuota_min": {"rol": "analista", "t": "Cuota mínima del pick del día", "tipo": "num", "v": 1.5, "paso": 0.05, "min": 1.2, "max": 3},
    "pick_cuota_max": {"rol": "analista", "t": "Cuota máxima del pick del día", "tipo": "num", "v": 1.7, "paso": 0.05, "min": 1.3, "max": 4},
    "hora_pick1": {"rol": "analista", "t": "Hora del 1.er pick", "tipo": "hora", "v": "10:30"},
    "hora_pick2": {"rol": "analista", "t": "Hora del 2.º pick", "tipo": "hora", "v": "18:00"},
    "minimo_diario": {"rol": "analista", "t": "Mínimo diario", "d": "Si no hay pick de 1,50-1,70, plan B: 1,45-1,85, un tipster o el más probable hasta 2,00", "tipo": "si_no", "v": True},
    "tipsters_primero": {"rol": "analista", "t": "Picks de los tipsters primero", "d": "TipsAnalistas y Pérez antes que el modelo", "tipo": "si_no", "v": True},
    "saludo_pick": {"rol": "redactor", "t": "Saludo del pick", "tipo": "texto", "v": "Vamos con el pick de hoy familia 🔥"},
    "pick_razones": {"rol": "redactor", "t": "Poner las razones (👨‍💻)", "tipo": "si_no", "v": True},
    "pick_stake": {"rol": "redactor", "t": "Poner el stake n/10", "tipo": "si_no", "v": True},
    "pausa_verificador": {"rol": "verificador", "t": "En pausa", "d": "No prepara verdes ni rojos", "tipo": "si_no", "v": False},
    "rojos_pick": {"rol": "verificador", "t": "Preparar los rojos del pick del día", "tipo": "si_no", "v": True},
    "pausa_community": {"rol": "community", "t": "En pausa", "d": "El panel no enseña respuestas propuestas", "tipo": "si_no", "v": False},
    "pausa_cazador": {"rol": "cazador", "t": "En pausa", "d": "No busca cuotazas", "tipo": "si_no", "v": False},
    "cazador_umbral": {"rol": "cazador", "t": "Avisar desde (% por encima de lo justo)", "tipo": "num", "v": 8, "paso": 1, "min": 3, "max": 25},
    "cazador_cuota_min": {"rol": "cazador", "t": "Cuota mínima", "d": "Por debajo nadie la quiere aunque sea buena", "tipo": "num", "v": 1.4, "paso": 0.05, "min": 1.25, "max": 3},
    "aviso_guardar": {"rol": "vigilante", "t": "Avisarme si el bot no guarda", "tipo": "si_no", "v": True},
    "aviso_vigilante": {"rol": "vigilante", "t": "Avisarme de los fallos que vea", "d": "Posts sin salir, fotos, textos rotos, repetidos…", "tipo": "si_no", "v": True},
}


def _control():
    try:
        return json.loads(CONTROL.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def valor(k, control=None):
    """Valor de un ajuste de rol: el que puso Marcos desde el panel o, si no, el de por defecto."""
    c = control if control is not None else _control()
    puestos = c.get("ajustes") or {}
    return puestos.get(k, AJUSTES_ROLES[k]["v"])


def pausado(rol, control=None):
    k = f"pausa_{rol}"
    return bool(valor(k, control)) if k in AJUSTES_ROLES else False


def canales_off(control=None):
    """Canales de tipsters que Marcos ha apagado desde la ficha del Ojeador (nombres tal cual)."""
    c = control if control is not None else _control()
    return set(c.get("canales_off") or [])


def hora(k, control=None):
    h, m = (int(x) for x in str(valor(k, control)).split(":"))
    return h, m
