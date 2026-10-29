// Combilocas · widget para Scriptable (iPhone y Mac con "Usar widgets del iPhone")
// Tamaño mediano = todo · pequeño = seguidores · pequeño con parámetro "escalera" = reto escalera
// 29/10 (Marcos): rediseño. Solo Instagram, Threads y Telegram (fuera Facebook).
// Se actualiza solo: cada vez que se ejecuta mira si hay una versión nueva de este archivo en GitHub y se
// sobrescribe (la siguiente vez que se pinte ya sale la nueva). Marcos no tiene que tocar nada.
const VERSION = "2026-10-29"
const BASE = "https://raw.githubusercontent.com/marcooshz1234-sudo/bot-futbol/main/"
const URL = BASE + "publicaciones/estadisticas.json"
const CODIGO = BASE + "widget/combilocas_widget.js"

const FONDO = new Color("#08140f"), CARTA = new Color("#11241b"), BORDE = new Color("#1d3a2c")
const VERDE = new Color("#4ade80"), ROJO = new Color("#f87171"), GRIS = new Color("#7d9b8b")
const BLANCO = new Color("#f1fbf5"), AMARILLO = new Color("#facc15")
const REDES = [
  { k: "threads", nombre: "Threads", color: new Color("#f1fbf5"), icono: "at" },
  { k: "instagram", nombre: "Instagram", color: new Color("#f472b6"), icono: "camera.fill" },
  { k: "telegram", nombre: "Telegram", color: new Color("#38bdf8"), icono: "paperplane.fill" },
]

const num = n => n == null ? "—" : Math.round(n).toLocaleString("es-ES")
const mas = n => n == null ? "—" : n > 0 ? "+" + n : n < 0 ? "−" + Math.abs(n) : "±0"

async function actualizarme() {
  if (typeof CARGADOR !== "undefined") return   // 29/10: con el cargador corto ya se baja la última versión cada vez
  try {
    const nuevo = await new Request(CODIGO + "?t=" + Date.now()).loadString()
    if (!nuevo.includes("Script.setWidget") || !nuevo.includes("const VERSION")) return
    const fm = module.filename.includes("Mobile Documents") ? FileManager.iCloud() : FileManager.local()
    const actual = fm.readString(module.filename)
    if (actual !== nuevo) fm.writeString(module.filename, nuevo)
  } catch (e) { }
}

function texto(st, t, tam, color, peso) {
  const x = st.addText(t); x.textColor = color
  x.font = peso === "negra" ? Font.heavyRoundedSystemFont(tam) : peso === "semi" ? Font.semiboldRoundedSystemFont(tam)
    : Font.mediumRoundedSystemFont(tam)
  x.lineLimit = 1; x.minimumScaleFactor = 0.5; return x
}

// línea con relleno degradado debajo (crecimiento de los últimos días)
function grafica(serie, ancho, alto, color) {
  const dc = new DrawContext()
  dc.size = new Size(ancho, alto); dc.opaque = false; dc.respectScreenScale = true
  const s = (serie || []).filter(v => v != null)
  if (s.length < 2) {
    dc.setFillColor(BORDE); dc.fillRect(new Rect(0, alto - 2, ancho, 1.5)); return dc.getImage()
  }
  const min = Math.min(...s), max = Math.max(...s), r = (max - min) || 1
  const pts = s.map((v, i) => new Point(i * ancho / (s.length - 1), alto - 3 - (v - min) / r * (alto - 7)))
  const relleno = new Path(); relleno.move(new Point(0, alto)); pts.forEach(p => relleno.addLine(p))
  relleno.addLine(new Point(ancho, alto)); relleno.closeSubpath()
  dc.addPath(relleno); dc.setFillColor(new Color(color.hex, 0.16)); dc.fillPath()
  const l = new Path(); pts.forEach((p, i) => i ? l.addLine(p) : l.move(p))
  dc.addPath(l); dc.setStrokeColor(color); dc.setLineWidth(2.2); dc.strokePath()
  const u = pts[pts.length - 1]
  dc.setFillColor(color); dc.fillEllipse(new Rect(u.x - 3, u.y - 3, 6, 6))
  return dc.getImage()
}

function pastilla(st, t, color) {
  const p = st.addStack(); p.backgroundColor = new Color(color.hex, 0.16); p.cornerRadius = 7
  p.setPadding(1, 5, 1, 5); texto(p, t, 9, color, "semi"); return p
}

function tarjeta(fila, red, x, ancho) {
  const c = fila.addStack(); c.layoutVertically(); c.backgroundColor = CARTA; c.cornerRadius = 14
  c.borderColor = BORDE; c.borderWidth = 1; c.setPadding(7, 9, 6, 9); c.size = new Size(ancho, 0)
  const cab = c.addStack(); cab.centerAlignContent()
  const ic = cab.addImage(SFSymbol.named(red.icono).image); ic.imageSize = new Size(10, 10); ic.tintColor = red.color
  cab.addSpacer(4); texto(cab, red.nombre, 10, GRIS, "semi")
  c.addSpacer(3)
  texto(c, num(x.seguidores), 25, BLANCO, "negra")
  c.addSpacer(2)
  const d = c.addStack(); d.centerAlignContent()
  pastilla(d, mas(x.hoy) + " hoy", x.hoy > 0 ? VERDE : x.hoy < 0 ? ROJO : GRIS)
  c.addSpacer(7)
  const g = c.addImage(grafica(x.serie, ancho - 18, 30, red.color)); g.imageSize = new Size(ancho - 18, 30)
}

await actualizarme()
let d
try { d = await new Request(URL + "?t=" + Date.now()).loadJSON() } catch (e) { d = null }

const w = new ListWidget()
if (!(config.widgetFamily || "").startsWith("accessory")) w.backgroundColor = FONDO
const grad = new LinearGradient(); grad.colors = [new Color("#0d2118"), FONDO]; grad.locations = [0, 1]
if (!(config.widgetFamily || "").startsWith("accessory")) w.backgroundGradient = grad
w.refreshAfterDate = new Date(Date.now() + 15 * 60 * 1000)
const tam = config.widgetFamily || "medium"
const modo = (args.widgetParameter || "").toLowerCase()
const total = d ? REDES.reduce((a, r) => a + ((d.redes[r.k] || {}).seguidores || 0), 0) : null
const totalHoy = d ? REDES.reduce((a, r) => a + ((d.redes[r.k] || {}).hoy || 0), 0) : null

if (tam.startsWith("accessory")) {
  // 29/10: pantalla de bloqueo (iOS la pinta en un solo color). Rectangular = las tres redes · redondo = una red
  // (parámetro «threads», «instagram» o «telegram»; sin parámetro, Threads) · en línea = Threads
  if (tam === "accessoryRectangular") {
    w.setPadding(2, 4, 2, 4)
    for (const r of REDES) {
      const x = d ? (d.redes[r.k] || {}) : {}
      const f = w.addStack(); f.centerAlignContent()
      const ic = f.addImage(SFSymbol.named(r.icono).image); ic.imageSize = new Size(11, 11); ic.tintColor = Color.white()
      f.addSpacer(5); texto(f, r.nombre, 12, new Color("#ffffff", 0.75), "semi"); f.addSpacer()
      texto(f, num(x.seguidores), 14, Color.white(), "negra"); f.addSpacer(5)
      const h = texto(f, mas(x.hoy), 11, new Color("#ffffff", x.hoy ? 1 : 0.6), "semi"); h.rightAlignText()
      if (r !== REDES[REDES.length - 1]) w.addSpacer(2)
    }
  } else if (tam === "accessoryCircular") {
    w.addAccessoryWidgetBackground = true
    const r = REDES.find(r => modo.startsWith(r.k.slice(0, 3))) || REDES[0]
    const x = d ? (d.redes[r.k] || {}) : {}
    const col = w.addStack(); col.layoutVertically(); col.centerAlignContent()
    const f1 = col.addStack(); f1.addSpacer()
    const ic = f1.addImage(SFSymbol.named(r.icono).image); ic.imageSize = new Size(12, 12); ic.tintColor = Color.white(); f1.addSpacer()
    const f2 = col.addStack(); f2.addSpacer(); texto(f2, num(x.seguidores), 15, Color.white(), "negra"); f2.addSpacer()
    const f3 = col.addStack(); f3.addSpacer(); texto(f3, mas(x.hoy), 10, Color.white(), "semi"); f3.addSpacer()
  } else {
    const x = d ? (d.redes.threads || {}) : {}
    texto(w, `Threads ${num(x.seguidores)} · ${mas(x.hoy)} hoy`, 12, Color.white(), "semi")
  }
} else if (!d) {
  w.setPadding(14, 14, 14, 14)
  texto(w, "COMBILOCAS", 13, BLANCO, "negra"); w.addSpacer(6); texto(w, "Sin conexión", 12, GRIS)
} else if (tam === "small" && modo.startsWith("esc")) {
  w.setPadding(14, 14, 14, 14)
  const e = d.escalera
  texto(w, "RETO ESCALERA", 10, GRIS, "semi"); w.addSpacer()
  const fila = w.addStack(); fila.bottomAlignContent()
  texto(fila, "Día " + (e ? e.dia : "—"), 30, BLANCO, "negra"); texto(fila, " /7", 14, GRIS, "semi")
  w.addSpacer(8)
  const barras = w.addStack(); barras.spacing = 3
  for (let i = 1; i <= 7; i++) {
    const b = barras.addStack(); b.size = new Size(15, 8); b.cornerRadius = 4
    b.backgroundColor = !e ? CARTA : i < e.dia ? VERDE : i === e.dia ? AMARILLO : CARTA
  }
  w.addSpacer()
  texto(w, e ? `${num(e.stake)}€ → ${num(e.objetivo)}€` : "", 11, GRIS, "semi")
} else if (tam === "small") {
  w.setPadding(14, 14, 12, 14)
  texto(w, "SEGUIDORES", 10, GRIS, "semi"); w.addSpacer(2)
  texto(w, num(total), 32, BLANCO, "negra")
  pastilla(w.addStack(), mas(totalHoy) + " hoy", totalHoy > 0 ? VERDE : totalHoy < 0 ? ROJO : GRIS)
  w.addSpacer()
  for (const r of REDES) {
    const f = w.addStack(); f.centerAlignContent()
    const ic = f.addImage(SFSymbol.named(r.icono).image); ic.imageSize = new Size(9, 9); ic.tintColor = r.color
    f.addSpacer(5); texto(f, num((d.redes[r.k] || {}).seguidores), 11, BLANCO, "semi"); f.addSpacer()
    const h = (d.redes[r.k] || {}).hoy
    texto(f, mas(h), 10, h > 0 ? VERDE : h < 0 ? ROJO : GRIS, "semi")
  }
} else {
  // 29/10 (Marcos): sin total arriba ni línea de abajo: solo las tres redes
  w.setPadding(12, 12, 12, 12)
  const cab = w.addStack(); cab.centerAlignContent()
  texto(cab, "COMBILOCAS", 13, BLANCO, "negra")
  cab.addSpacer(); texto(cab, d.actualizado.slice(11), 9, GRIS, "semi")
  w.addSpacer()
  const fila = w.addStack(); fila.spacing = 6
  for (const r of REDES) tarjeta(fila, r, d.redes[r.k] || {}, 101)
  w.addSpacer()
}

Script.setWidget(w)
if (config.runsInApp) tam === "small" ? w.presentSmall() : tam === "accessoryRectangular" ? w.presentAccessoryRectangular()
  : tam === "accessoryCircular" ? w.presentAccessoryCircular() : tam === "accessoryInline" ? w.presentAccessoryInline() : w.presentMedium()
Script.complete()
