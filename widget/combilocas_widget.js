// Combilocas · widget para Scriptable (iPhone y Mac con "Usar widgets del iPhone")
// 01/11 (Marcos): ahora enseña MIS COMBIS en juego (docs/mis/datos.json): partido, minuto, marcador, «4 de 6» y lo
// que le queda según el bot. Antes eran los seguidores de las redes.
//   Pantalla de inicio: pequeño = la combi más importante · mediano = hasta 2 · grande = hasta 6
//   Pantalla de bloqueo: rectangular = la combi más importante · redondo = % que le queda
//   · en línea = una frase
// 01/11 (Marcos): con PARÁMETRO (en el iPhone: mantener pulsado → Editar widget / Personalizar → Parameter) se elige qué
//   combi sigue: un trozo del nombre de un equipo, p. ej. «madrid» o «burgos». Vacío = la más importante.
//   Si esa combi ya terminó, enseña cómo acabó (✅ / ❌).
//   Sin parámetro también se puede fijar una combi desde la app «Mis combis» (botón «📌 En el widget»).
//   «seguidores» = el widget de antes (seguidores de Threads, Instagram y Telegram); «escalera» = reto escalera.
// Se actualiza solo: cada vez que se ejecuta mira si hay una versión nueva de este archivo en GitHub y se
// sobrescribe (la siguiente vez que se pinte ya sale la nueva). Marcos no tiene que tocar nada.
const VERSION = "2026-11-11"   // 11/11: estilo CL (logo CL, estadio de noche, verde neón)
const BASE = "https://raw.githubusercontent.com/marcooshz1234-sudo/bot-futbol/main/"
const URL = BASE + "docs/mis/datos.json"
const CODIGO = BASE + "widget/combilocas_widget.js"

// 11/11 (Marcos: «cámbialo al formato nuevo»): estilo CL, como las fotos: estadio de noche, cajas negras con borde
// verde neón y el logo CL arriba
const FONDO = new Color("#050806"), CARTA = new Color("#070a07", 0.82), CARTA2 = new Color("#0e140e", 0.85), BORDE = new Color("#7ef03a", 0.75)
const VERDE = new Color("#7ef03a"), ROJO = new Color("#f87171"), AMARILLO = new Color("#facc15")
const BLANCO = Color.white(), GRIS = new Color("#b9c7b4")

// imágenes de la marca (se bajan una vez y se guardan en el iPhone)
async function imagen(ruta) {
  const fm = FileManager.local(), f = fm.joinPath(fm.documentsDirectory(), "cl_" + ruta.split("/").pop())
  if (fm.fileExists(f)) return fm.readImage(f)
  try { const i = await new Request(BASE + ruta).loadImage(); fm.writeImage(f, i); return i } catch (e) { return null }
}

// el estadio de noche oscurecido, de fondo
async function fondoCL(w) {
  const foto = await imagen("publicaciones/media/marca/fondo_estadio.jpg")
  if (!foto) { w.backgroundColor = FONDO; return }
  const dc = new DrawContext(); dc.size = new Size(720, 340); dc.opaque = true
  dc.drawImageInRect(foto, new Rect(0, -250, 720, 900))
  dc.setFillColor(new Color("#000000", 0.55)); dc.fillRect(new Rect(0, 0, 720, 340))
  w.backgroundImage = dc.getImage()
}

// «[logo] COMBILOCAS» (o el título que toque)
async function cabeceraCL(st, titulo, tam) {
  const logo = await imagen("publicaciones/media/marca/logo_cl_256.png")
  if (logo) { const i = st.addImage(logo); i.imageSize = new Size(tam + 8, tam + 8); st.addSpacer(6) }
  texto(st, titulo, tam, BLANCO, "negra")
}
const EN_JUEGO = ["1H", "HT", "2H", "ET", "BT", "P", "LIVE", "INT"]

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

const pct = p => p == null ? "—" : p > 0 && p < 0.01 ? "<1%" : Math.round(100 * p) + "%"
const colProb = p => p == null ? GRIS : p >= 0.5 ? VERDE : p >= 0.2 ? AMARILLO : ROJO

// resumen de una combi para pintarla
function resumir(c) {
  const vivo = c.picks.find(p => EN_JUEGO.includes(p.estado_partido))
  const m = c.picks.find(p => p.marcador && p.marcador[0] != null)
  const verdes = c.picks.filter(p => p.estado === "verde").length
  const cuentan = c.picks.filter(p => p.estado !== "anulada").length
  const final = { verde: "✅", rojo: "❌", anulada: "Anul." }[c.estado]
  return {
    titulo: c.titulo, prob: c.prob, estado: c.estado, vivo: !!vivo && !final, final: !!final,
    // lo que va a la derecha: lo que le queda o, si ya terminó, cómo acabó
    valor: final || pct(c.prob), color: c.estado === "verde" ? VERDE : c.estado === "rojo" ? ROJO : colProb(c.prob),
    etiqueta: final ? "final" : "le queda",
    minuto: final ? "Final" : vivo ? (vivo.estado_partido === "HT" ? "Desc." : (vivo.minuto ?? "") + "′") : c.fecha.slice(11, 16),
    marcador: m ? `${m.marcador[0]}-${m.marcador[1]}` : "", cuenta: `${verdes} de ${cuentan}`, corta: `${verdes}/${cuentan}`,
  }
}

const normal = t => String(t || "").toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").trim()

// las de hoy que siguen vivas: primero las que están en juego, luego las que faltan por empezar.
// Con parámetro, la combi de ese equipo va la primera (la de hoy; si no hay, la última que hubo).
const FIJADA = "combilocas_widget_fijada"

function elegir(d, buscar) {
  if (!d) return []
  const hoy = (d.combis || []).filter(c => c.fecha.slice(0, 10) === d.hoy && c.estado === "pendiente").map(resumir)
  hoy.sort((a, b) => (b.vivo - a.vivo))
  if (!buscar) {   // 01/11: la que Marcos fijó desde la app va la primera (aunque ya haya terminado, se ve cómo acabó)
    const id = Keychain.contains(FIJADA) ? Keychain.get(FIJADA) : null
    const fija = id && (d.combis || []).find(c => c.id === id)
    if (!fija) return hoy
    const r = resumir(fija)
    return [r, ...hoy.filter(x => x.titulo !== r.titulo)]
  }
  const cand = (d.combis || []).filter(c => normal(c.titulo).includes(buscar))
    .sort((a, b) => (b.fecha.slice(0, 10) === d.hoy) - (a.fecha.slice(0, 10) === d.hoy) || (b.estado === "pendiente") - (a.estado === "pendiente")
      || b.fecha.localeCompare(a.fecha))
  if (!cand.length) return null   // no hay ninguna combi con ese equipo
  const r = resumir(cand[0])
  return [r, ...hoy.filter(x => x.titulo !== r.titulo)]
}

function fila(w, r, grande) {
  const c = w.addStack(); c.layoutVertically(); c.backgroundColor = CARTA; c.cornerRadius = 14
  c.borderColor = BORDE; c.borderWidth = 1; c.setPadding(7, 10, 7, 10)
  const a = c.addStack(); a.centerAlignContent()
  texto(a, r.minuto, grande ? 14 : 12, r.vivo ? AMARILLO : BLANCO, "negra"); a.addSpacer(7)
  texto(a, r.titulo, grande ? 14 : 12, BLANCO, "semi"); a.addSpacer(6)
  if (r.marcador) texto(a, r.marcador, grande ? 15 : 13, BLANCO, "negra")
  a.addSpacer()
  texto(a, r.valor, grande ? 18 : 16, r.color, "negra")
  const b = c.addStack(); b.centerAlignContent()
  texto(b, r.cuenta + " en verde", 10, GRIS, "semi"); b.addSpacer()
  texto(b, r.final ? "final" : "le queda · según el bot", 9, GRIS)
}

// 01/11 (Marcos): el widget de antes (seguidores de las redes y reto escalera) con el parámetro «seguidores»
// («seguidores instagram» / «seguidores telegram» para el redondo de una red) o «escalera» (pequeño)
async function widgetSeguidores(tam, modo) {
  const URL = BASE + "publicaciones/estadisticas.json"
  // 11/11: los colores CL de arriba (los de cada red se quedan para las gráficas)
  const REDES = [
    { k: "threads", nombre: "Threads", color: new Color("#f1fbf5"), icono: "at" },
    { k: "instagram", nombre: "Instagram", color: new Color("#f472b6"), icono: "camera.fill" },
    { k: "telegram", nombre: "Telegram", color: new Color("#38bdf8"), icono: "paperplane.fill" },
  ]

  const num = n => n == null ? "—" : Math.round(n).toLocaleString("es-ES")
  const mas = n => n == null ? "—" : n > 0 ? "+" + n : n < 0 ? "−" + Math.abs(n) : "±0"

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
  let d
  try { d = await new Request(URL + "?t=" + Date.now()).loadJSON() } catch (e) { d = null }

  const w = new ListWidget()
  if (!(config.widgetFamily || "").startsWith("accessory")) await fondoCL(w)
  w.refreshAfterDate = new Date(Date.now() + 15 * 60 * 1000)
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
    await cabeceraCL(cab, "COMBILOCAS", 13)
    cab.addSpacer(); texto(cab, d.actualizado.slice(11), 9, GRIS, "semi")
    w.addSpacer()
    const fila = w.addStack(); fila.spacing = 6
    for (const r of REDES) tarjeta(fila, r, d.redes[r.k] || {}, 101)
    w.addSpacer()
  }
  Script.setWidget(w)
  if (config.runsInApp) tam === "small" ? w.presentSmall() : tam === "accessoryRectangular" ? w.presentAccessoryRectangular()
    : tam === "accessoryCircular" ? w.presentAccessoryCircular() : tam === "accessoryInline" ? w.presentAccessoryInline() : w.presentMedium()
}

async function widgetCombis(tam) {
  let d
  try { d = await new Request(URL + "?t=" + Date.now()).loadJSON() } catch (e) { d = null }
  const buscar = normal(args.widgetParameter)
  const elegidas = elegir(d, buscar)
  const combis = elegidas || []
  const hay = combis.length > 0
  // sin combis: por qué
  const vacio = !d ? "Sin conexión" : elegidas === null ? `No hay combi de «${args.widgetParameter.trim()}»` : "Nada en juego hoy"
  const vivas = combis.filter(r => r.vivo).length

  const w = new ListWidget()
  const bloqueo = tam.startsWith("accessory")
  if (!bloqueo) await fondoCL(w)
  // con combis en juego, que iOS lo repinte lo antes posible
  w.refreshAfterDate = new Date(Date.now() + (vivas ? 5 : 15) * 60 * 1000)

  if (bloqueo) {
    // pantalla de bloqueo: iOS la pinta en un solo color, así que todo va en blanco con distinta opacidad
    const B = Color.white(), B6 = new Color("#ffffff", 0.65)
    if (tam === "accessoryRectangular") {
      w.setPadding(2, 4, 2, 4)
      if (!hay) { texto(w, "MIS COMBIS", 11, B6, "semi"); texto(w, vacio, 14, B, "negra").lineLimit = 2 }
      // 01/11: una sola combi en tres líneas (con dos no se leía nada); la más importante (la que va en juego)
      const r = combis[0]
      if (r) {
        const a = w.addStack(); a.centerAlignContent()
        texto(a, r.minuto, 15, B, "negra"); a.addSpacer(); texto(a, r.marcador, 15, B, "negra")
        texto(w, r.titulo, 12, B6, "semi")
        const b = w.addStack(); b.centerAlignContent()
        texto(b, r.cuenta, 12, B6, "semi"); b.addSpacer(); texto(b, r.final ? r.valor : "le queda " + r.valor, 13, B, "negra")
      }
    } else if (tam === "accessoryCircular") {
      w.addAccessoryWidgetBackground = true
      const r = combis[0]
      const col = w.addStack(); col.layoutVertically()
      for (const [t, tm, peso] of [[r ? r.minuto : "", 10, "semi"], [r ? r.valor : "—", 16, "negra"], [r ? r.corta : "", 10, "semi"]]) {
        const f = col.addStack(); f.addSpacer(); texto(f, t, tm, Color.white(), peso); f.addSpacer()
      }
    } else {
      const r = combis[0]
      texto(w, r ? [r.minuto, r.titulo, r.marcador].filter(Boolean).join(" ") + ` · ${r.corta} · ${r.valor}` : "Mis combis: " + vacio.toLowerCase(), 12, Color.white(), "semi")
    }
  } else if (!d) {
    w.setPadding(14, 14, 14, 14)
    texto(w, "MIS COMBIS", 13, BLANCO, "negra"); w.addSpacer(6); texto(w, vacio, 12, GRIS)
  } else if (!hay) {
    w.setPadding(14, 14, 14, 14)
    texto(w, "MIS COMBIS", 13, BLANCO, "negra"); w.addSpacer()
    texto(w, vacio, 15, GRIS, "semi"); w.addSpacer()
    texto(w, "act. " + d.generado.slice(11), 9, GRIS, "semi")
  } else if (tam === "small") {
    const r = combis[0]
    w.setPadding(13, 13, 12, 13)
    const cab = w.addStack(); cab.centerAlignContent()
    texto(cab, r.minuto, 14, r.vivo ? AMARILLO : BLANCO, "negra"); cab.addSpacer()
    if (r.marcador) texto(cab, r.marcador, 16, BLANCO, "negra")
    w.addSpacer(4)
    const t = texto(w, r.titulo, 13, BLANCO, "semi"); t.lineLimit = 2
    w.addSpacer()
    texto(w, r.etiqueta.toUpperCase(), 9, GRIS, "semi")
    texto(w, r.valor, 34, r.color, "negra")
    const pie = w.addStack(); pie.centerAlignContent()
    texto(pie, r.cuenta + " en verde", 10, GRIS, "semi"); pie.addSpacer()
    if (combis.length > 1) texto(pie, "+" + (combis.length - 1), 10, GRIS, "semi")
  } else {
    w.setPadding(12, 12, 12, 12)
    const cab = w.addStack(); cab.centerAlignContent()
    await cabeceraCL(cab, "MIS COMBIS", 13); cab.addSpacer(6)
    if (vivas) texto(cab, `${vivas} en juego`, 10, AMARILLO, "semi")
    cab.addSpacer(); texto(cab, "act. " + d.generado.slice(11), 9, GRIS, "semi")
    w.addSpacer(8)
    const n = tam === "large" ? 6 : 2   // en el mediano no caben más de 2 con su segunda línea
    for (const r of combis.slice(0, n)) { fila(w, r, tam === "large"); w.addSpacer(5) }
    w.addSpacer()
  }
  Script.setWidget(w)
  if (config.runsInApp) tam === "small" ? w.presentSmall() : tam === "large" ? w.presentLarge()
    : tam === "accessoryRectangular" ? w.presentAccessoryRectangular() : tam === "accessoryCircular" ? w.presentAccessoryCircular()
    : tam === "accessoryInline" ? w.presentAccessoryInline() : w.presentMedium()
}

// 01/11 (Marcos): la combi del widget se elige desde la app «Mis combis» (botón «📌 En el widget»): la app abre
// scriptable:///run/Combilocas?fijar=<id> y aquí se guarda en el llavero del iPhone. ?fijar= vacío = quitarla.
async function fijar(id) {
  if (id) Keychain.set(FIJADA, id)
  else if (Keychain.contains(FIJADA)) Keychain.remove(FIJADA)
  const a = new Alert()
  a.title = id ? "📌 Combi en el widget" : "Widget en automático"
  a.message = id ? "Tus widgets sin parámetro enseñan ahora esta combi. Ya puedes volver." : "Enseña la combi más importante del día."
  a.addAction("OK")
  await a.presentAlert()
}

await actualizarme()
const tam = config.widgetFamily || "medium"
const param = normal(args.widgetParameter)
const q = args.queryParameters || {}
if (config.runsInApp && "fijar" in q) await fijar(q.fijar)
else if (/^(seguidores|escalera)/.test(param)) await widgetSeguidores(tam, param.replace(/^seguidores\s*/, ""))
else await widgetCombis(tam)
Script.complete()
