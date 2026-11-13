# COMBILOCAS · Manual del proyecto

> **Para la IA que lea esto:** léelo entero antes de tocar nada, y después **`REGLAS.md`** (la lista única de
> reglas de Marcos; si algo de aquí choca con `REGLAS.md`, manda `REGLAS.md`). Lo que pasa cada día está en
> `informes/bitacora/AAAA-MM.md`.
>
> Rehecho el 13/11/2026 en la limpieza del proyecto: solo lo que funciona hoy. Lo antiguo sigue en el historial
> de GitHub.

---

## 1. Qué es

**@combilocas**: canal de pronósticos de fútbol en **Telegram**, **Threads** e **Instagram** (Facebook en pausa
desde el 26/10). Lo hace todo un bot: datos y cuotas, picks, combis, textos con su imagen y publicación a su hora.

- **Casa de referencia:** bet365 (todas las cuotas, de bet365). Pinnacle solo como referencia de «lo justo».
- **Objetivo:** crecer (sobre todo Threads y Telegram) y abrir un canal de pago en Telegram (plan en la memoria
  del proyecto, «combilocas-vip»).
- **Costes:** API-Football (~20 €/mes) y las IA. Mantenerlos bajos.
- El repositorio `marcooshz1234-sudo/bot-futbol` es **público** a propósito (GitHub Actions gratis e imágenes
  servidas desde GitHub para Instagram y Threads). Si deja de ser público, Instagram deja de funcionar.

### Las piezas

| Nombre | Qué es | Dónde |
|---|---|---|
| **El bot** | Datos, picks, combis, posts y publicación | GitHub Actions (`.github/workflows/`) |
| **El bot del móvil** | `@combilocas_publica_bot`: avisos y botones para Marcos | `asistente.py` · `asistente.yml` |
| **La app / panel** | Picks, posts publicados, directo, estadísticas, Oficina y ajustes | `docs/` (GitHub Pages) |
| **Mis combis** | App solo de Marcos: sus combis pata a pata | `docs/mis/`, datos de `mis_datos.py` |
| **El widget** | Widget de Scriptable del iPhone | `widget/combilocas_widget.js` (se actualiza solo) |
| **La Oficina** | Turnos de Claude programados (ojeador, analista, redactor, verificador, community, vigilante) | Tareas programadas de Claude; apuntan con `anotar_rol.py` en `datos/oficina_roles.json` |
| **Obsidian** | Copia de la bitácora en el iPhone de Marcos | Atajo de iPhone «Combilocas → Obsidian» (baja `informes/bitacora/AAAA-MM.md`; cambiar el mes el día 1) |

---

## 2. Claves (secretos de GitHub)

**Ninguna IA pide, ve, copia ni pega tokens o contraseñas. Las pone Marcos** (GitHub → Settings → Secrets).

| Secreto | Para qué |
|---|---|
| `API_FOOTBALL_KEY` | API-Football: partidos, cuotas, estadísticas, alineaciones (~7.500 peticiones/día) |
| `TELEGRAM_TOKEN` | Publicar en el canal y el bot del móvil |
| `TG_SESSION` (+ api_id/hash) | Lector de canales de tipsters con la cuenta de Marcos (`lector_canales.py`; se crea con `sesion_telegram.py`, lo ejecuta Marcos) |
| `THREADS_TOKEN`, `INSTAGRAM_TOKEN` | Threads e Instagram |
| `FACEBOOK_TOKEN`, `FACEBOOK_PAGINA` | Facebook (en pausa: `redes.FACEBOOK_ACTIVO = False`) |
| `ODDSPAPI_KEY` | Cuotas de Pinnacle (`fuentes_extra.py` → `datos/cuotas_sharp.json`) |

Canal de Telegram: `-1003953339107`.

---

## 3. Qué sale cada día

| Hora | Post (id `AAAA-MM-DD-…`) | Dónde |
|---|---|---|
| 00:00–02:00 | Ganadores con escudos («Partidos de hoy», `ganadores-*`, `ganadores_win.py`) | Threads e Instagram |
| 09:30 | Buenos días con foto y lo que sale hoy (`marca_tg.py`) | Telegram |
| 10:30 | **Pick del día** (`pick-seguro`, 1,50–1,70) | Todas |
| 11:00 | **Reto escalera** (`escalera`, ≈ x2; sale todos los días) | Todas |
| 13:30 | **Combi del día** (`combi-tres`) | Todas |
| 14:30 | Combi larga (`combi-multi`) | Threads e Instagram |
| 16:00 | La loca (`combi-loca`) | Threads e Instagram |
| 17:00–18:30 | ¡Noche europea! (días de Champions / EL / Conference) | Telegram |
| 18:00 | **Segundo pick** (`pick-seguro-2`) | Todas |
| Antes de cada partido | Combi con escudos de un partido (`combi-partido-<id>`; necesita la cuota de «Crear apuesta» de Marcos) | Threads |
| A lo largo del día | Copias de los canales de tipsters (`pick-tip-*`, `combi-tip-*`, `copiar_tipsters.py`) | Todas |
| 9:00–23:00 | Cuotazas de bet365 (`cuotaza-*`, `cazador.py`, con ✅ de Marcos) | Todas |
| Al acabar | Verdes (`verde-auto-*`; varios a la vez → `verde-grupo-*`) | Todas (en Threads, como comentario de su post) |
| 23:00 | Picks para mañana (`picks-manana`) | Todas |
| 23:15 | Resumen de la noche (`balance-auto`, `resumen_dia.py`) | Todas |

- **Telegram (canal gratis):** solo pick del día, segundo pick, escalera, combi del día, copias de canales,
  cuotazas, verdes y lo de la marca (buenos días, noche europea, «en directo» uno cada 3 días, ¡PLENO!). Lo demás,
  `solo_redes` o `solo_en: ["threads"]`.
- **Días buenos** (4 o más partidos de Champions/EL/Conference, selecciones, 5 grandes, Champions femenina o un
  grande): todo lo nuestro sale solo de esos partidos (`combis_dia.fuera_por_dia_bueno`).
- **Quitado por Marcos (no volver a poner):** GIF, encuesta, concurso y ranking del canal (11/11); «quién gana» en
  texto (11/11); rachas, pichichis, previas y posts sin apuesta (27/10); balance de la noche con foto y muñeco (12/11);
  TikTok.

---

## 4. Cómo funciona por dentro

### Workflows (`.github/workflows/`)

| Workflow | Cuándo | Qué hace |
|---|---|---|
| `recoger.yml` («Bot futbol») | cada 6 h (:17 UTC) | `bot.py` (API-Football) → aprendizaje → `picks.py` → `valor.py` → `escalera.py` → `plantillas.py` (`publicaciones/auto.json`) → imágenes → `limpiar_media.py` → informes |
| `telegram.yml` («Publicar en Telegram y redes») | siempre (tandas de 50 min, cada 30 min) | El bucle: `publicar_telegram.py` y `redes.py` cada vuelta; cada 3 min directo, app, verdes, avisos, noticias, lector de canales, copias de tipsters, marca; cada 5 min cuotas frescas y alineaciones; cada 10 min moderación, estadísticas, revisor, Threads, comunidad, calibrar «Crear apuesta», cazador, vigilante e imágenes |
| `asistente.yml` | siempre (tandas de ~6 h) | El bot del móvil (`asistente.py`) |
| `alineaciones.yml` | cada 15 min | Alineaciones y combis de jugadores |
| `escudos.yml` | lunes | Escudos de equipos |
| `validar.yml` | al subir código | Tests |
| `oracle_a1.yml` | tandas cada 10 min | `oracle_a1.py`: reintenta crear el servidor A1 gratis de Oracle hasta que haya hueco; avisa al móvil y se para (13/11) |
| `actualizar_panel.yml`, `leer_registro.yml` | a mano | Rehacer el panel; bajar el registro de una ejecución a `datos/registro_ejecucion.txt` |

### Archivos clave

| Archivo | Para qué |
|---|---|
| `REGLAS.md` + `comprobar_post.py` | Las reglas y su comprobación: `publicar_telegram.py` y `redes.py` no publican nada que falle una regla grave |
| `bot.py` | Datos de API-Football → `datos/`; constantes de cuotas (`CUOTA_MINIMA_POST`, `CUOTA_MAXIMA_PATA`…) |
| `picks.py`, `aprender.py`, `calibrar_historico.py`, `modelo_patas.py`, `sharp.py` | Picks y probabilidad aprendida (con Pinnacle de referencia) |
| `combis_dia.py` | Combis (del día, larga, loca, de partido), pick del día, días buenos |
| `crear_apuesta.py` | **Calculadora del «Crear apuesta»** (combis de un partido); aprende de cada cuota real de Marcos (`datos/crear_medidas.json`) |
| `escalera.py` | Reto escalera (`datos/escalera.json`) |
| `plantillas.py`, `estilo_threads.py` | Textos y horas → `publicaciones/auto.json`; estilo de Threads |
| `imagenes.py`, `fotos.py`, `marca.py`, `ganadores_img.py`, `ganadores_win.py`, `ticket_verde.py` | Imágenes (logo CL en `publicaciones/media/marca/logo_cl_*.png`) |
| `publicar_telegram.py`, `redes.py` | Publicar (Telegram; Threads e Instagram) |
| `verdes_auto.py`, `confirmar.py`, `resumen_dia.py` | Verdes (seguros solos, con duda a Marcos; varios juntos), confirmación de resultados, resumen de la noche |
| `lector_canales.py`, `tipsters_auto.py`, `anotar_tipster.py`, `tipsters.py`, `copiar_tipsters.py` | Canales de tipsters: leer → apuntar → corregir y aprender → copiar |
| `revision.py`, `noticias.py`, `vigilante.py` | Bajas en prensa, estrellas, cuotas movidas; avisos a Marcos |
| `marca_tg.py`, `cazador.py` | Posts de la marca en Telegram; cuotazas |
| `tarjeta_tg.py` | Tarjeta de Telegram (13/11): banderas/escudos, logo de la competición, el pick escrito en la foto y texto corto; tras 3 posts con foto, uno en texto |
| `asistente.py` | Bot del móvil |
| `app_datos.py`, `panel_datos.py`, `mis_datos.py`, `oficina_datos.py` | Datos de la app, el panel, Mis combis y la Oficina |
| `ajustes.py` | Ajustes de cada rol (panel → `control.json`) |
| `limpiar_media.py` | Borra imágenes de posts de hace más de 3 días, fotos de boletos y partidos en directo de hace más de 7 |
| `preparar_logo.py`, `sesion_telegram.py` | Herramientas a mano (logo de competición que manda Marcos; crear la sesión de Telegram) |
| `publicaciones/auto.json` | Posts del bot (estado en `enviados.json` y `enviados_redes.json`) |
| `publicaciones/cola.json` | Posts a mano, verdes, copias, cuotazas (estado dentro) |
| `publicaciones/control.json` | Cancelados, pausa, textos cambiados, `cuota_dada`, `aprobados`, ajustes |

### Cada post
Cada combi guarda `sel` (`"partido_id|mercado|opción"`) y `cuotas` (una por pata). Sin eso no se puede seguir
ni dar el verde. Para quitar un post que no ha salido: id en `control.json → cancelados` (nunca borrarlo de la cola).

### Bot del móvil (`@combilocas_publica_bot`)
- Comandos: `/hoy`, `/picks`, `/manana`, `/combis`, `/editar`, `/borrar`, `/pausa`, `/reanudar`, `/ayuda`.
- Borradores 60 min antes (✅ Vale / ✏️ Cambiar / ❌ Cancelar); verdes con duda, rojos y cuotazas con ✅ Publicar;
  combis de un partido piden la cuota de «Crear apuesta» (`pide_cuota`).
- Capturas de bet365 → flujo de boleto (recorta el dinero, lee la cuota y las patas).
- Seguidores: `/pick` por privado (`comunidad.py` los corrige; ya no se publica nada de esto en el canal).

### Mis combis y widget
- `datos/mis_combis.json` → `mis_datos.py` → `docs/mis/datos.json`. Sin dinero; nada de esto va a la app pública.
- Widget: sin parámetro, sus combis en juego; con parámetro, un equipo, «seguidores» o «escalera».

---

## 5. Trabajar con Marcos

Las reglas de trabajo están en `REGLAS.md` (apartado 10). Lo esencial: español, corto y con tablas; enseñar antes
de cambiar; nunca decir «hecho» sin comprobarlo; nunca tokens; nunca borrar publicaciones ni editar un post
publicado; bet365 solo mirar; todo cambio con test y en la bitácora.

Cuando pide combis en el chat: patas con lógica de partido, cuotas de bet365, la cuota de un mismo partido con
`python3 crear_apuesta.py <id>` (nunca a ojo), y rehacerlas con los onces oficiales.

---

## 6. Mantenimiento

1. **¿Publica?** `datos/bucle_log.txt` (hora UTC reciente) y GitHub → Actions («Publicar en Telegram y redes»
   siempre en marcha). Si lleva >40 min parado: `gh api -X POST repos/marcooshz1234-sudo/bot-futbol/actions/workflows/telegram.yml/dispatches -f ref=main`.
2. **¿Qué sale hoy y cumple las reglas?** `python3 comprobar_post.py` (todo lo pendiente) o con un id.
3. **Tests** antes de subir nada: `python3 -m unittest discover -s tests` y `node tests/test_panel.cjs`.
4. **Subir:** `for i in 1 2 3 4; do git pull -q --rebase --autostash -X theirs; git push -q && break; sleep 10; done`.
   El bucle escribe en `cola.json`, `auto.json` y `datos/` sin parar: cambia `cola.json` justo después de un pull.
5. **Regenerar los posts** sin esperar 6 h: `gh api -X POST repos/marcooshz1234-sudo/bot-futbol/actions/workflows/recoger.yml/dispatches -f ref=main`.
6. «Arreglado» = que no vuelva a pasar: con test en `tests/` y una línea en la bitácora.

---

## 7. Errores que no pueden volver a pasar

| Qué pasó | Cómo se evita |
|---|---|
| Se dijo a Marcos que algo funcionaba sin probarlo | Comprobar de verdad antes de decirlo |
| Cuotas de un mismo partido multiplicadas (se anunciaba más de lo que paga bet365) | `crear_apuesta.py` + la cuota real de Marcos (`pide_cuota`) |
| Cuotas viejas | `cuotas_frescas.py` antes de publicar |
| Verdes con goles de la prórroga | Todo a los 90 min (`picks.a_90()`) |
| Un post aprobado no salió y nadie avisó | El asistente publica y contesta; el vigilante avisa |
| JSON roto por choques de git | `reparar_json.py` tras cada pull |
| Posts quitados con `"caducada": true` (falsa alarma) | Quitar con `control.json → cancelados` |
| Logos de la marca pasados a .jpg y las fotos sin logo (12/11) | `tests/test_archivos_marca.py` |
| Tarjeta de ganadores vieja (otra plantilla y otros equipos) (13/11) | Se rehace si cambian los equipos o la plantilla |
| Errores de reglas en combis hechas a mano | `comprobar_post.py` antes de meter nada |

---

## 8. Pendiente / ideas
- Calibrar la calculadora del «Crear apuesta» con 15–20 cuotas reales (capturas de Marcos).
- Instagram orgánico (idea del 13/11).
- Canal de pago en Telegram cuando haya seguidores suficientes. App pública: todavía no.
- Facebook en pausa. TikTok descartado.

## 9. Otro proyecto: la guía (tucanalconia)
Guía de pago sobre cómo montar un canal automático con IA. **No menciona combilocas ni apuestas.** Va en otro chat.
