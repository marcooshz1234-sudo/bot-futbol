// Combilocas · widget para Scriptable (iPhone y Mac con "Usar widgets del iPhone")
// Tamaño mediano = todo · pequeño = seguidores · pequeño con parámetro "escalera" = reto escalera
const URL = "https://raw.githubusercontent.com/marcooshz1234-sudo/bot-futbol/main/publicaciones/estadisticas.json"
const FONDO = new Color("#0b2418"), CHIP = new Color("#123a27"), VERDE = new Color("#5ee39a")
const SUAVE = new Color("#8fc9a8"), BLANCO = new Color("#eafaf1"), AMARILLO = new Color("#f5c542")
const NOMBRES = { instagram: "Instagram", threads: "Threads", facebook: "Facebook", telegram: "Telegram" }

const num = n => n == null ? "—" : Math.round(n).toLocaleString("es-ES")
const mas = n => n == null ? "" : (n >= 0 ? "+" : "") + n

function linea(serie, ancho, alto, grosor) {
  const dc = new DrawContext()
  dc.size = new Size(ancho, alto); dc.opaque = false; dc.respectScreenScale = true
  if (serie && serie.length > 1) {
    const min = Math.min(...serie), max = Math.max(...serie), r = (max - min) || 1
    const p = new Path()
    serie.forEach((v, i) => {
      const pt = new Point(i * ancho / (serie.length - 1), alto - 2 - (v - min) / r * (alto - 4))
      i ? p.addLine(pt) : p.move(pt)
    })
    dc.addPath(p); dc.setStrokeColor(VERDE); dc.setLineWidth(grosor); dc.strokePath()
  }
  return dc.getImage()
}

function texto(st, t, tam, color, negrita) {
  const x = st.addText(t); x.textColor = color; x.font = negrita ? Font.semiboldSystemFont(tam) : Font.systemFont(tam)
  x.lineLimit = 1; x.minimumScaleFactor = 0.6; return x
}

let d
try { d = await new Request(URL + "?t=" + Date.now()).loadJSON() } catch (e) { d = null }

const w = new ListWidget()
w.backgroundColor = FONDO
w.setPadding(12, 14, 12, 14)
w.refreshAfterDate = new Date(Date.now() + 15 * 60 * 1000)
const tam = config.widgetFamily || "medium"
const modo = (args.widgetParameter || "").toLowerCase()

if (!d) {
  texto(w, "COMBILOCAS", 13, BLANCO, true); w.addSpacer(6); texto(w, "Sin conexión", 12, SUAVE)
} else if (tam === "small" && modo.startsWith("esc")) {
  const e = d.escalera
  texto(w, "Reto escalera", 11, SUAVE); w.addSpacer()
  const fila = w.addStack(); fila.bottomAlignContent()
  texto(fila, "Día " + (e ? e.dia : "—"), 28, BLANCO, true); texto(fila, "/7", 14, SUAVE)
  w.addSpacer(6)
  const barras = w.addStack(); barras.spacing = 3
  for (let i = 1; i <= 7; i++) {
    const b = barras.addStack(); b.size = new Size(15, 8); b.cornerRadius = 3
    b.backgroundColor = !e ? CHIP : i < e.dia ? VERDE : i === e.dia ? AMARILLO : CHIP
  }
  w.addSpacer()
  texto(w, e ? `${num(e.stake)}€ → ${num(e.objetivo)}€` : "", 11, SUAVE)
} else if (tam === "small") {
  texto(w, "Seguidores totales", 11, SUAVE); w.addSpacer()
  texto(w, num(d.total), 30, BLANCO, true)
  texto(w, mas(d.total_hoy) + " hoy", 11, VERDE)
  w.addSpacer(4)
  const tot = {}
  Object.values(d.historial || {}).forEach((h, i) => { tot[i] = Object.values(h).reduce((a, b) => a + b, 0) })
  w.addImage(linea(Object.values(tot).filter(x => x), 120, 26, 2.5)).imageSize = new Size(120, 26)
} else {
  const cab = w.addStack()
  texto(cab, "COMBILOCAS", 13, BLANCO, true); cab.addSpacer(); texto(cab, "act. " + d.actualizado.slice(11), 10, SUAVE)
  w.addSpacer(8)
  const redes = ["instagram", "threads", "facebook", "telegram"]
  for (let f = 0; f < 2; f++) {
    const fila = w.addStack(); fila.spacing = 8
    for (const r of redes.slice(f * 2, f * 2 + 2)) {
      const x = d.redes[r] || {}
      const c = fila.addStack(); c.layoutVertically(); c.backgroundColor = CHIP; c.cornerRadius = 10
      c.setPadding(6, 9, 6, 9); c.size = new Size(142, 0)
      const t = c.addStack(); texto(t, NOMBRES[r], 10, SUAVE); t.addSpacer(); texto(t, mas(x.hoy), 10, VERDE)
      texto(c, num(x.seguidores), 17, BLANCO, true)
      c.addImage(linea(x.serie, 124, 14, 2)).imageSize = new Size(124, 14)
    }
    if (f === 0) w.addSpacer(6)
  }
  w.addSpacer(8)
  const pie = w.addStack(); pie.centerAlignContent()
  const pr = d.proximo
  texto(pie, pr ? `⏱ ${pr.hora} · ${pr.titulo}` : "Sin posts pendientes", 11, BLANCO)
  pie.addSpacer()
  if (d.ayer) {
    const chip = pie.addStack(); chip.backgroundColor = VERDE; chip.cornerRadius = 7; chip.setPadding(2, 7, 2, 7)
    texto(chip, `Ayer ${d.ayer.aciertos}/${d.ayer.total}`, 11, FONDO, true)
  }
  w.addSpacer(3)
  const pie2 = w.addStack()
  const e = d.escalera
  texto(pie2, e ? `🪜 Escalera día ${e.dia}/7 · ${num(e.stake)}€` : "", 10, SUAVE)
  pie2.addSpacer()
  if (d.likes_hoy != null) texto(pie2, `♥ ${num(d.likes_hoy)} likes hoy`, 10, SUAVE)
}

Script.setWidget(w)
if (config.runsInApp) tam === "small" ? w.presentSmall() : w.presentMedium()
Script.complete()
