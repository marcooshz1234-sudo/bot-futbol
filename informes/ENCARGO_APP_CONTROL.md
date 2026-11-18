# Encargo: app de control de Combilocas («Centro de mando»)

> Para la sesión de Claude que la construya. Léelo entero antes de empezar.
> Repo: `marcooshz1234-sudo/bot-futbol` (trabajar en la nube, en `/home/claude/bot-futbol`; la copia del Mac está vieja).
> Antes de nada: `CLAUDE.md`, `REGLAS.md` y `MANUAL_PROYECTO.md` del repo.

## 1. El problema (palabras de Marcos, 18/11)
- «Me lo envían todos por el mismo chat y gestionar todo del mismo sitio no renta, es un lío.»
- «Quítame los avisos que nunca leo. Los de Threads, si falla algo, no pasa nada. En Telegram quiero que esté todo perfecto.»
- «Igual lo suyo es que tenga yo una app y desde la propia app lo pueda gestionar todo.»

Hoy todo pasa por el privado de `@combilocas_publica_bot` (`asistente.py`): avisos, verdes con «✅ Publicar»,
posts en espera, comandos. Desde el 18/11 solo le llegan avisos de Telegram (`privado.py`, ajuste
`avisos_solo_telegram`), pero sigue siendo un único chat para todo.

## 2. Qué quiere (objetivo)
Una app en el móvil (Marcos casi siempre está en el iPhone) donde ver y decidir todo, separado por secciones,
y que el chat del bot quede solo para lo urgente.

## 3. Recomendación de cómo hacerla
**No empezar de cero: convertir el panel que ya existe en la app.**
- `docs/panel/index.html` (GitHub Pages, PWA instalable, ya tiene icono y manifest) hoy SOLO LEE
  (`docs/panel/datos.json`, `oficina.json`, que generan `panel_datos.py` y `oficina_datos.py` en el bucle).
- Para que pueda **actuar** (aprobar, cancelar, cambiar ajustes) sin servidor: escribir en
  `publicaciones/control.json` con la API de GitHub (contents API, commit pequeño). El bucle ya lee ese fichero:
  `aprobados` (lo que sale con «✅ Publicar»), `cancelados`, ajustes (`ajustes.py`).
- Clave: un **token fino de GitHub** (fine-grained, solo este repo, solo «Contents: read/write») que **pone
  Marcos en la app la primera vez y se guarda solo en su móvil** (localStorage). Claude NUNCA lo pide, ve ni pega.
  Explicarle los pasos para crearlo y dónde pegarlo.
- Alternativa si el token no le convence: los botones de la app abren el bot con un `start=` (deep link)
  y el bot hace la acción (ya sabe aprobar/cancelar). Menos cómodo, cero claves nuevas.

## 4. Secciones de la app (por orden de importancia)
1. **📲 Telegram (lo importante)**
   - Lo que sale hoy en el canal, con hora, foto y texto tal cual saldrá.
   - **Por aprobar**: verdes con dudas, resumen de la noche, posts con `requiere_ok` → botones «✅ Publicar» / «❌ No sale».
   - Lo publicado hoy (`mensaje_id`) con su estado en directo (verde / va bien / va mal / rojo), marcador y minuto.
   - Avisos del vigilante SOLO de Telegram (los de `privado.aviso_vigilante_tg`).
   - Botón «Cancelar» en lo que aún no ha salido.
2. **🧵 Threads / Instagram** (consultar, sin avisos): lo programado y lo publicado, combis vivas, verdes x5+.
3. **🎯 Tipsters**: picks de hoy de los canales (`datos/tipsters_raw.json` + fotos `datos/tipsters_fotos/`), con la
   foto visible y filtro «solo fútbol / solo baloncesto / últimas 6 h». Botón «Proponer para Telegram» (lo deja
   en la cola con `requiere_ok`, nunca publica directo).
4. **📊 Resultados**: acierto de Telegram por día y semana, por mercado (las tarjetas se vigilan), escalera.
5. **⚙️ Ajustes**: los de `ajustes.py` (pausas, horas, cuotas, avisos) como interruptores.
6. **🛠️ Sistema** (sin avisos): salud del bucle, pasos que fallan, claves que caducan, cuota de la API.

## 5. Avisos (push)
- El chat del bot se queda SOLO para lo urgente de Telegram (algo por aprobar, un post de Telegram que falla).
- Opcional: un **grupo privado de Telegram con Temas** (Telegram / Threads / Sistema). Un solo bot, cada aviso a
  su tema (`message_thread_id`); Marcos silencia los temas que no quiera. Lo crea Marcos (crear grupo → activar
  Temas → añadir el bot como admin); no hace falta token nuevo.

## 6. Reglas que no se pueden romper
- Español, corto, con tablas. Pensada para móvil.
- **Nada se publica en Telegram sin su OK.** La app nunca publica directo: aprueba lo que ya está en la cola.
- Nunca borrar ni editar posts ya publicados. Nunca tokens/contraseñas a la vista. bet365 solo lectura.
- **Enseñar antes de subir**: primero un prototipo (capturas o la página con datos de ejemplo) y su visto bueno.
- Cada cambio con su test (`tests/`), una línea en `informes/bitacora/AAAA-MM.md` y, si es norma nueva, en `REGLAS.md`.
- Antes de commit: `timeout 300 python3 -m unittest discover -s tests` y `node tests/test_panel.cjs`.
- No romper lo que ya hay: `docs/index.html` (app pública), `docs/mis/` (Mis combis + widget: solo combis de Marcos).
- Ahorrar crédito: nada de tareas programadas nuevas ni bucles de vigilancia.

## 7. Por dónde empezar (plan)
1. Leer `docs/panel/index.html`, `panel_datos.py`, `asistente.py` (cómo aprueba/cancela) y `ajustes.py`.
2. Prototipo de la sección 📲 Telegram con los datos reales de un día (el 17/11 fue 8 de 8: buen ejemplo).
3. Enseñárselo a Marcos. Con su OK: botones que escriben en `control.json` (o deep link al bot).
4. Luego el resto de secciones, una a una, enseñando cada una.
