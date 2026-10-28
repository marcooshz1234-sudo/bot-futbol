# COMBILOCAS · Manual completo del proyecto

> **Para la IA que lea esto (Claude, ChatGPT o la que sea):** este archivo es la memoria entera del proyecto.
> Léelo completo antes de tocar nada. Aquí están las reglas de Marcos, cómo funciona el sistema, cómo
> mantenerlo y los errores que ya pasaron y no pueden repetirse. Si algo de lo que vas a hacer
> contradice este documento, pregunta a Marcos antes.
>
> Última actualización: 27/10/2026. Copia de este archivo en el repositorio: `MANUAL_PROYECTO.md`.

---

## 1. Qué es el proyecto

**@combilocas** es un canal de pronósticos de fútbol en **Telegram**, **Threads** e **Instagram**
(Facebook está en pausa desde el 26/10). Todo lo hace un bot automático: recoge datos de partidos
y cuotas, elige picks, monta combinadas, prepara los posts con su imagen y los publica solo,
a su hora, en todas las redes a la vez.

- **Casa de apuestas de referencia:** bet365 (todas las cuotas tienen que ser las de bet365).
- **Objetivo:** que las cuentas crezcan (sobre todo Threads) y más adelante lanzar un canal de pago en
  Telegram. Es un proyecto de ingresos automáticos: todo tiene que funcionar solo, de punta a punta.
- **Costes actuales:** API de fútbol (~20 €/mes), cuentas de IA. Hay que mantener los costes bajos.
- **La app (panel)** es privada: no se ha lanzado al público.

### Las piezas (nombres que usa Marcos)

| Nombre | Qué es | Dónde vive |
|---|---|---|
| **El Analista** | El bot: datos, picks, combis, posts | Repositorio GitHub `marcooshz1234-sudo/bot-futbol` (público), se ejecuta en GitHub Actions |
| **El Publicador** | Bot de Telegram `@combilocas_publica_bot`: asistente en el móvil de Marcos | `asistente.py`, workflow `asistente.yml` |
| **La app** | Panel web con picks, combis publicadas, resultados en directo, estadísticas | `docs/` (GitHub Pages), datos en `docs/datos.json` |
| ~~El Bot Asesor~~ | IA local en el Mac (Ollama + AnythingLLM) | Descartado el 22/10, no se usa |

El repositorio es **público** a propósito: así los minutos de GitHub Actions son gratis e ilimitados.

---

## 2. Claves y cuentas (secretos)

Las claves están en GitHub → repositorio → Settings → Secrets and variables → Actions.
**Ninguna IA debe pedir, ver, copiar ni pegar tokens o contraseñas. Las pone Marcos.**

| Secreto | Para qué |
|---|---|
| `API_FOOTBALL_KEY` | API-Football (api-sports.io): partidos, cuotas, estadísticas, alineaciones. Plan con ~7.500 peticiones/día |
| `TELEGRAM_TOKEN` | Bot de Telegram (publica en el canal y habla con Marcos por privado) |
| `THREADS_TOKEN` | Publicar en Threads |
| `INSTAGRAM_TOKEN` | Publicar en Instagram (reels, historias) |
| `FACEBOOK_TOKEN`, `FACEBOOK_PAGINA` | Facebook (en pausa) |

Canal de Telegram: id `-1003953339107` (está en los workflows).
Gmail del proyecto de la guía (otro proyecto): soporte.tucanalconia@gmail.com.

---

## 3. Calendario diario de contenido (formato desde el 28/10)

| Hora (Madrid) | Post | Dónde |
|---|---|---|
| **01:00** | ⚽ **Quién gana hoy**: lista de equipos «Gana» (prob ≥60 %) o «Gana o empata» (45–60 %) | Telegram, Threads, Instagram |
| **10:00** | 🎟️ Por **privado a Marcos**: 2 combis «Crear apuesta» para que las monte en bet365 (no se publican) | Telegram (privado) |
| **11:00** | 🪜 **Reto escalera** (cada día; si ese día no hay 2 picks fiables, no sale y espera al siguiente) | Todas |
| **13:30** | 🔥 **Combi x3** (cuota 2,5–4, 2–4 patas de partidos distintos) | Todas |
| **16:00** | 🤪 **La loca** (cuota 7–10, 4–7 patas de partidos distintos) | Todas |
| **Kickoff − 50 min** | ✅ **COMBI LOCAS** de un partido (hasta 8 al día, los mejores partidos; menos si hay pocos), con la foto-tarjeta del partido | Telegram, Threads (con foto), Instagram (reel + historia) |
| **23:00** | 🔥 **Picks para mañana** (lista de ✅ con bandera, sin horas) | Todas + historia de Instagram |
| Al momento | ✅💚 **Verdes**: en cuanto una combi publicada sale verde, se publica sola | Todas |
| Sábado 12:00 | 🧮 De 1 € a 500 € (solo si el bot encuentra una) | Todas |
| Lunes 10:00 / domingo 22:30 | 🏆 Concurso de picks de seguidores / ranking | Telegram |
| 19:30–21:00 (diaria) | 📊 Encuesta «De la combi de hoy, ¿qué pata crees que falla?» sobre la loca (o la x3) publicada ese día | Telegram |
| Cuando Marcos quiera | 🎟️ **Boleto de bet365** (captura recortada) | Telegram y Threads |

Si dos combis de partido coinciden en hora, se separan 30 min hacia atrás.

**Quitados por Marcos (no volver a poner):** rachas, pichichis, previas, «datos» sin apuesta,
la combi «segura» vieja, la doble, «la del día», tema/liga/«nadie se atreve», TikTok.

---

## 3 bis. Catálogo de contenido: cada tipo de post, tal cual sale

El contenido es **siempre el mismo** todos los días (lo hace el bot solo). No inventar formatos nuevos ni
cambiar estos sin que Marcos lo pida. Ejemplos reales:

**⚽ Quién gana hoy** (01:00 · id `AAAA-MM-DD-ganadores` · `ganadores.py`)
```
⚽ QUIÉN GANA HOY · COMBILOCAS ⚽

✅1. 🇵🇹 Benfica — Gana
✅2. 🇪🇸 Mallorca — Gana o empata
...
📊 Según nuestros datos, no las cuotas

🍀 ¿LA PINTAMOS DE VERDE? 👀💚
```

**🪜 Reto escalera** (11:00 · `escalera`) — lleva el dinero, también en Instagram
```
🪜 RETO ESCALERA · DÍA 1/7 · x1,92 🍀

❌ El domingo se cayó el día 2. Aquí no se borra nada: otra vez desde 20€ 💪

✅ 🇮🇹 Lazio o empate
✅ 🇮🇹 Torino marca

🎯 CUOTA 1,92 💎 · 20,00€ → 38,40€

🍀 ¿LA PINTAMOS DE VERDE? 👀💚
```

**🔥 Combi x3** (13:30 · `combi-tres`) y **🤪 La loca** (16:00 · `combi-loca`) — patas de partidos distintos
```
🔥⚽ COMBILOCAS — ¡COMBI DEL MARTES x3,02! 🍀

✅ 🇩🇪 Gana el Borussia Dortmund
✅ 🇮🇹 Torino marca
✅ 🇪🇸 Girona gana al descanso

🎯 CUOTA 3,02 💎

🍀 ¿LA PINTAMOS DE VERDE? 👀💚
```
(La loca: «🤪🔥 COMBILOCAS — ¡LA LOCA DEL MARTES x8,30! 🤪», 4–7 patas, cuota 7–10.)

**✅ COMBI LOCAS de un partido** (kickoff − 50 min · `combi-partido-<id del partido>`) — siempre con la
**foto-tarjeta del partido**: imagen apaisada 1180×340 al estilo de la tarjeta de partido de Threads
(fondo degradado, los dos escudos guardados en `publicaciones/media/escudos`, la hora y «Hoy»).
Se genera sola (`imagenes.tarjeta()` → `publicaciones/media/<id>.tarjeta.jpg`). Ver formato en la sección 4.

**🔥 Picks para mañana** (23:00 · `picks-manana`)
```
🔥⚽ COMBILOCAS — ¡7 PICKS PARA MAÑANA! 🍀

✅ 🇪🇸 Sevilla o empate
✅ 🇪🇸 Granada CF marca
...
⚽ ¡Combina máximo 2 o 3! ✅

💚 Más picks GRATIS en @combilocas
```

**✅💚 Verde** (al momento · `verde-auto-<id del post>`)
```
✅💚 ¡VERDE x1,84! LA COMBI DEL LUNES 💚✅

✅ El PSG mete entre 2 y 4 goles (PSG–Lyon)
✅ Sevilla o empate (Sevilla–Osasuna)

🎯 Cuota 1,84
💶 10€ → 18,40€

¿Quién la llevaba? 👇💚
```
(Verde de combi de partido: «¡VERDE xN! COMBI LOCAS · SASSUOLO vs LAZIO». Verde de un boleto: sin las
patas, con «📲 Montada en bet365, partido a partido 👇» y la foto del boleto en Telegram y Threads.)

**🎟️ Boleto de bet365** (cuando Marcos lo manda): foto recortada + 3 líneas (sección 4).

**🧮 De 1 € a 500 €** (sábados 12:00) y **🏆 Concurso** (lunes 10:00, ranking domingo 22:30 · `comunidad.py`).

### Cómo se sube en cada red

| Tipo | Telegram (canal) | Threads | Instagram | Facebook |
|---|---|---|---|---|
| Quién gana, x3, loca, escalera, 500 | Texto | Texto | **Reel** del texto convertido en imagen (no foto suelta en el feed) | En pausa |
| Combi de partido | **Foto-tarjeta del partido + texto** (desde el 27/10) | **Foto-tarjeta del partido + texto** | Reel + **historia** | En pausa |
| Picks para mañana | Texto | Texto | Reel + historia | En pausa |
| Verde | Texto (boleto: foto recortada) | Texto (boleto: foto recortada) | Reel + historia (sin dinero salvo escalera, sin boleto) | En pausa |
| Boleto de bet365 | **Foto recortada + texto** | **Foto recortada + texto** | **No va** | No |

- Instagram: la imagen la crea `imagenes.py` a partir del texto (fondo verde oscuro, «COMBILOCAS», cada
  línea en una tarjeta, la cuota destacada). Se sirve desde GitHub (raw) porque el repo es público:
  **si el repo deja de ser público, Instagram y las fotos de Threads dejan de funcionar.**
- Threads: máximo 500 caracteres. Sin tope diario de posts. Sin etiqueta de tema (sección 4).
- Telegram: texto; foto con pie si el post tiene `foto` o si es combi de partido (va con su foto-tarjeta).
- Todo sale a la vez en todas las redes. Si una red falla, se reintenta hasta 45 min. Llega aviso al móvil si falla
  Telegram o Threads (los fallos de Instagram quedan apuntados en el post, `errores_redes`, pero no avisan).

---

## 4. Reglas de contenido (TODAS obligatorias)

### Cuotas y picks
1. **Todas las cuotas son de bet365.** Si no se sabe la cuota segura, la selección no va.
2. **Cada pata vale como mínimo 1,25.**
3. **Nunca «menos de X goles»** (ni menos de 2,5 ni menos de 3,5). **Nunca «12» / «sin empate».**
4. **«Más de 2,5 goles» solo si está muy respaldado** (probabilidad aprendida ≥70 %), también cuando va
   con «ambos marcan». Vale para combis y para las listas de picks. Falla mucho.
5. **Como mucho 1 pata de tiros totales del partido** por combi (tiros o tiros a puerta).
6. **Variedad de mercados**: en cada combi, tipos distintos (tarjetas, córners, jugador, resultado,
   goles, faltas…). Combis de partido: al menos 3 tipos (si tiene 4+ patas), máx. 2 de goles y 2 de resultado.
   x3 y loca: una pata por partido y máx. 2 del mismo tipo.
7. **Se prefieren**: tarjetas, **tiros de jugadores que siempre tiran** (1+), **faltas de jugadores que
   siempre hacen falta** (1+). En las combis de partido van **2–3 patas de tiros de jugadores** si hay.
8. Los picks se eligen por **lo probable que es que pase**, no solo por «valor» («cosas que vayan a pasar»).
9. **Ganador del partido** es de los mercados más importantes. En las 5 grandes ligas bet365 lo da por
   ganado si el equipo se pone 2 goles arriba («2 goles de ventaja»). En jugadores, si lo cambian,
   cuenta lo que haga el que entra (Sustituto+).
9 bis. **Todo se cierra a los 90 minutos (más el descuento). La prórroga y los penaltis NO cuentan** para ningún
   mercado: ganador, «gana alguna de las dos partes», goles, ambos marcan, «2 goles de ventaja», córners, tarjetas,
   tiros, faltas, jugadores… (regla de Marcos, 27/10). Solo contaría la prórroga en un mercado de «se clasifica»
   (el bot no lo usa). Cómo lo hace el bot (`picks.a_90()`):
   - Goles y resultado: marcador del minuto 90 (`goles_90`, o los goles de los eventos hasta el 90).
   - Estadísticas de equipo: 1ª + 2ª parte (`stats_partes`, de fixtures/statistics?half=true); tarjetas, de los
     eventos hasta el 90 si no hay partes.
   - Jugadores: goles, asistencias y tarjetas, de los eventos hasta el 90. Tiros, faltas y paradas no se pueden
     separar: si el jugador jugó la prórroga y no llega ni contándola, roja; si llega, queda «sin datos» (revisar a mano).
   - Si algo no se puede saber, la pata queda «sin datos»: nunca se da un verde dudoso.
10. **No repetir la misma selección** en muchos posts (**máx. 2 posts por selección**, contando combis de partido, escalera, x3, loca y lista de picks;
    el bot lo aplica solo).
11. Usar todo lo que tiene el bot: forma, xG, clasificación (contexto 1º vs 18º), árbitro, bajas,
    estadísticas de jugadores, movimiento de cuotas. «Quiero la mejor apuesta, no cualquier cosa».

### Combis de un partido («COMBI LOCAS») — fórmula de Marcos
- Una por partido, **hasta 8 partidos al día** (Marcos pidió 5–8; si hay pocos partidos buenos salen menos), primero los de **equipos grandes** (dan más visitas).
- **4–6 patas** (bet365 solo deja 6 mercados por partido en «Crear apuesta», 28/10), **cuota real 7–10**, cada pata ≥1,25. Que varíen en longitud y cuota (no todas en 4 patas y x7).
- Si entre los 3 mejores partidos no hay un equipo español (LaLiga, Segunda o Copa del Rey), entra el mejor
  partido español (bet365 suele dar aumentos/aseguradas con equipos españoles). El bot lo aplica solo.
- Formato del texto:
  ```
  ✅ COMBI LOCAS | SERIE A
  🇮🇹 SASSUOLO vs LAZIO 🇮🇹

  🎯 LAZIO VE MÁS DE 1,5 TARJETAS [x1.50]
  ✅ LAZIO GANA ALGUNA DE LAS DOS PARTES [x1.57]
  ...
  🔥 Resultado probable: 1-1 | 0-1 | 1-2
  💥 Cuota total aprox.: 7,05
  🟢 VERDE A VERDE 🟢
  ```
- Va con la **foto-tarjeta del partido** (escudos, hora, «Hoy»), estilo tarjeta de Threads.

### ⚠️ La cuota real de «Crear apuesta» (MUY IMPORTANTE)
Cuando las patas son **del mismo partido**, bet365 **NO multiplica**: recorta según lo relacionadas que
estén. Medido en bet365 el 27/10:

| Combi | Multiplicando | bet365 paga | Recorte |
|---|---|---|---|
| Monza–Napoli: McTominay 2+ remates, gol 1ª parte, Napoli gana alguna mitad, Varela 1+ a puerta, Napoli más remates a puerta | 5,36 | 4,60 | 0,86 |
| Monza–Napoli: McTominay 2+ remates, Varela 1+ a puerta, Monza marca, Monza +3 córners, +28,5 remates | 9,46 | 6,00 | 0,63 |
| Milan: Ramos marca + Pulisic asiste + gana el Milan | 16,0 | 8,50 | 0,53 |
| Dortmund–Werder: +2,5 goles + Werder marca | 2,26 | ~1,80 | 0,80 |
| Monza marca + Varela 1+ a puerta | 2,26 | 2,05 | 0,91 |
| Juve gana alguna mitad + Genoa +1 tarjetas | 2,14 | 2,10 | 0,98 |
| City gana alguna mitad + Brighton marca + Brighton +1,5 tarjetas + +9,5 tiros a puerta (28/10) | 5,18 | 4,25 | 0,82 |
| Milan gana + Bologna marca + Bologna +2,5 córners + Milan +1,5 tarjetas + Ferguson 1+ faltas (28/10) | ~8,6 | 10,50 | >1 |
| Milan más tiros a puerta + Bologna marca + gana Milan + más de 3,5 tarjetas (28/10) | 7,14 | 8,00 | 1,12 |

**Entre partidos distintos bet365 multiplica tal cual** (comprobado: boleto x33,75 exacto).

**Desde el 28/10, patas de goles y resultado: modelo de goles (`modelo_goles.py`).** Con el 1X2 y el más/menos
de 2,5 de bet365 se estiman los goles esperados de cada equipo (Poisson; 1ª parte 45 %, 2ª 55 %) y se calcula la
probabilidad de que pasen TODAS a la vez. Si van juntas (más de 2,5 + ambos marcan) paga menos que multiplicar; si
van en contra (gana el Milan + Bologna marca) paga más. Comprobado: Milan–Bologna sale 10,43 y bet365 pagaba 10,50.
Tope del ajuste: 0,45–1,6. El resto de patas (tarjetas, córners, tiros, jugadores) va por parejas:

El bot lo calcula por parejas de patas (`combis_dia.py` → `pareja()`, `factor_crear()`, `cuota_real_sel()`):
- mismo equipo, «gana/o empata» + «ese equipo marca»: 0,80
- dos de resultado del mismo equipo («o empate» + «gana alguna parte»): 0,85
- ese equipo marca + tiros de su jugador: 0,90 · ese equipo marca + sus córners: 0,88
- goles del partido + «X marca»: 0,80 · goles con goles: 0,90 · goles + resultado: 0,97 · córners con córners: 0,95
- jugador + córners del mismo equipo: 0,93 · tiros del partido + tiros de un jugador: 0,94
- resto del mismo equipo: 0,97 · tiros del partido con tiros: 0,99 · tarjetas, fueras de juego y patas de
  equipos contrarios: 1,0 · el recorte total nunca baja de 0,45

**Regla de oro: la cuota que pone un post tiene que ser la que paga bet365 de verdad.** Si se montan combis
a mano, se calculan con `combis_dia.cuota_real_sel(sel, cuotas)`, nunca multiplicando.

### Formato y textos
- **Nunca** «🔞 +18 | Juega responsable» (quitado el 27/10), **nunca** «jugarbien.es» en Telegram.
- **Nunca el nombre de Marcos** en ninguna publicación.
- En listas de picks, **sin horas ni relojes**. Las listas van con ✅ y la bandera de la liga; «Quién gana» va
  numerada (✅1., ✅2.…), que es el formato que mejor funciona en Threads.
- Variar el estilo entre posts (ticks, banderas…). Comprobar límites de caracteres (Threads 500).
- **Threads**: actualmente **sin etiqueta de tema** (26/10: con la etiqueta «Apuestas deportivas» se veían
  3–10 veces menos). Texto solo, salvo combis de partido y boletos, que van con foto.
- **Instagram**: el texto del post se convierte en imagen + reel (solo reel en el feed) y historia en algunos.
  **Nunca dinero ni boletos en imágenes de Instagram**, con UNA excepción: **el reto escalera sí lleva el dinero**
  («20€ → 38,40€», en eso consiste). Los boletos de bet365 no van a Instagram.
- Todo va **enlazado**: lo que sale en una red sale en todas (Telegram, Threads, Instagram) a la vez.

### Reto escalera
Empieza con 20 € y cada día juega una combi de 2 picks (cuota 1,85–2,40) con lo ganado. Si sale verde,
sube un escalón al día siguiente; si falla, vuelve al día 1. 7 días: 20 → 40 → 80 → … → 1.280 €.
El post sale a las 11:00 (si un día no hay 2 picks fiables, ese día no sale y se espera al siguiente).
Se corrige solo con los resultados y el día siguiente pone si se superó el escalón o si se cayó.

### Boletos de bet365 (flujo creado el 27/10)
1. A las 10:00 el bot manda por privado a Marcos 2 combis «Crear apuesta» (4–6 partidos, 2 patas por
   partido a ~2,00, total ~20–45; si hay pocos partidos buenos llega solo 1, o ninguna con aviso). Son una propuesta; él puede cambiarlas.
2. Marcos la monta en bet365 y **manda la captura al chat del bot** cuando quiera.
3. El bot pregunta qué es → «🎟️ Es un boleto de bet365».
4. El bot **recorta el dinero** (quita «Imp», «Ganancias» y el botón verde), **lee la cuota sola**
   (Ganancias ÷ Importe, con OCR antes de recortar) y **lee las patas** (solo para la app, no se publican).
5. Enseña la foto recortada y el texto → Marcos pulsa **✅ Subir** (o ✏️ Otra cuota / 🗑️ Descartar).
6. Sale en **Telegram y Threads**: solo la foto recortada + texto corto:
   ```
   🎟️ COMBILOCAS — ¡CREAR APUESTA x33,75! 🍀
   📲 Montada en bet365, partido a partido 👇
   🍀 ¿LA PINTAMOS DE VERDE? 👀💚
   ```
7. La app sigue el boleto pata a pata; si sale verde se publica el verde solo (con la foto, sin listar patas).

---

## 5. Reglas de trabajo con Marcos (cómo tiene que trabajar la IA)

1. **Lee el mensaje entero. Primero responde a lo que pregunta, luego te pones a hacer cosas.**
2. **Nunca subas, programes ni cambies a mano ningún post sin enseñárselo antes** («no vuelvas a subir nada
   sin enseñármelo»). Lo que publica el bot solo cada día (el calendario de la sección 3) ya está aprobado:
   le llega el borrador 60 min antes por si quiere cambiarlo o cancelarlo. Los verdes salen al momento.
3. **Nunca digas que algo está hecho, programado y funcionando si no lo has comprobado de verdad.**
   Anoche (26–27/10) se le dijo que algo funcionaba y por la mañana no se había subido nada. No puede repetirse.
4. **Las pruebas se hacen sin crear contenido real** (nada que luego haya que borrar). Si una prueba
   necesita publicar algo, se le pregunta antes.
5. **Nunca borres publicaciones de forma permanente.** Para quitar un post programado: `"caducada": "quitada"`
   en `cola.json` o cancelarlo desde el bot (control.json). Nunca `"caducada": true` a mano (eso significa
   «no salió a su hora» y salta un aviso de fallo).
6. **Pregunta antes de actuar en sus dispositivos o cuentas.** Nunca pidas ni metas contraseñas o tokens.
7. En bet365 (en su Chrome), **solo mirar cuotas, no crear apuestas** salvo que lo pida.
8. Si puedes hacer algo tú, hazlo; no le devuelvas instrucciones paso a paso.
9. No des nada por supuesto: comprueba lo que ya existe y corrígele si se equivoca.
10. Si algo es ambiguo, pregunta. Guarda el progreso tras cada paso largo (puede quedarse sin créditos).
11. Respuestas en español, claras y cortas.

---

### Cuando Marcos pide combis a mano en el chat (no las del bot)
- Primero la explicación con los datos de cada pata; después una lista limpia solo con las selecciones.
- Cuotas solo de bet365 (si no se puede ver una cuota segura, esa selección no va). Si bet365 se queda
  colgado o pone «página no disponible», recargar.
- Mezclar tipos de mercado y estructuras distintas entre combis, sin repetir selecciones entre ellas ni con
  las apuestas que Marcos ya tiene hechas. Patas con lógica de partido (si pasa X, es más fácil Y).
- Dos versiones: antes de las alineaciones y, cuando las mande, otra corregida con los titulares.
- Guardar cada día un archivo en el Escritorio, carpeta «combis», con nombre tipo «Combis martes 13».
- Winamax: cuando juegan Real Madrid o Barça suele dar una supercuota (p. ej. 1,50 → 2,00, máx. 10 €);
  Marcos la coge siempre.

## 6. Cómo funciona por dentro

### Workflows de GitHub Actions (`.github/workflows/`)

| Workflow | Cuándo | Qué hace |
|---|---|---|
| `recoger.yml` («Bot futbol») | cada 6 h (minuto 17 UTC: 01:17, 07:17, 13:17, 19:17 en horario de invierno de Madrid; en verano, una hora más) | `bot.py` (descarga partidos, cuotas, estadísticas de API-Football) → `aciertos.py`, `calibrar_historico.py`, `aprender.py` (aprende de los fallos) → `picks.py` → `valor.py` → `escalera.py` → `plantillas.py` (crea `publicaciones/auto.json`) → `imagenes.py` (imágenes y reels) |
| `telegram.yml` («Publicar en Telegram y redes») | cada 30 min se pone en cola una tanda de 50 min (no se solapan: siempre hay una corriendo) | Bucle: `publicar_telegram.py`, `redes.py` (Threads/Instagram), cada 3 min `directo.py`, `app_datos.py`, `verdes_auto.py`, `avisos.py`; cada 5 min `cuotas_frescas.py`, `alineaciones_posts.py`; cada 10 min moderación, estadísticas, revisor, Threads, comunidad, **imágenes desactualizadas**. Guarda en git cada 5 min o al momento si cambia un post |
| `asistente.yml` | siempre (tandas de ~6 h) | El bot de Telegram del móvil (`asistente.py`) + **vigilante** |
| `alineaciones.yml` | cada 15 min | Alineaciones y combis de jugadores |
| `escudos.yml` | lunes | Guarda escudos de equipos (`publicaciones/media/escudos`) |
| `validar.yml` | al subir código | Tests y validación |
| `revisar_contenido.yml`, `actualizar_panel.yml`, `diagnostico.yml`, `prueba.yml`, `estadisticas.yml` | a mano / al cambiar ciertos archivos | Utilidades |

### Archivos clave
| Archivo | Para qué |
|---|---|
| `bot.py` | Descarga de datos (API-Football) → `datos/` |
| `picks.py` | Elige picks, evalúa resultados (`evaluar_pick`), mercados de jugador (`JUG_MERCADOS`) |
| `aprender.py`, `calibrar_historico.py`, `contexto.py` | Probabilidad aprendida (corrige lo que prometen las estadísticas con los aciertos reales), contexto de tabla |
| `combis_dia.py` | **Combis nuevas**: de partido, x3, loca, boletos «Crear apuesta», recorte de bet365 |
| `plantillas.py` | Textos de todos los posts y horas → `publicaciones/auto.json` |
| `ganadores.py` | «Quién gana hoy» |
| `escalera.py` | Reto escalera (`datos/escalera.json`) |
| `imagenes.py` | Imagen de Instagram, reel, historia y tarjeta del partido (quita el dinero salvo en escalera) |
| `publicar_telegram.py` | Publica en el canal de Telegram (auto.json + cola.json) |
| `redes.py` | Publica en Threads e Instagram (Facebook en pausa) |
| `verdes_auto.py` | Detecta combis verdes y crea el post de verde |
| `avisos.py` | Avisos por privado a Marcos: verdes, fallos al publicar, **cuotas que no cuadran**, combis de las 10:00 |
| `asistente.py` | Bot de Telegram del móvil: comandos, borradores 60 min antes, boletos, **vigilante** |
| `boleto_foto.py`, `boleto_patas.py` | Recorte del dinero + lectura de la cuota y de las patas de capturas de bet365 |
| `cuotas_frescas.py` | Antes de publicar, actualiza cuotas que han cambiado (y la cuota total real) |
| `alineaciones_posts.py` | Quita de los posts a jugadores que no son titulares |
| `app_datos.py` | Datos de la app (`docs/datos.json`) |
| `publicaciones/auto.json` | Posts que genera el bot (su estado en `enviados.json` y `enviados_redes.json`) |
| `publicaciones/cola.json` | Posts a mano / verdes / boletos (estado dentro) |
| `publicaciones/control.json` | Cancelados, pausa y textos cambiados desde el móvil |
| `publicaciones/asistente.json` | Lo publicado desde el móvil (boletos con sus patas) |
| `publicaciones/media/` | Imágenes, reels, tarjetas, escudos |
| `datos/` | Partidos, cuotas, historial, aprendizaje, escalera, avisos… |
| `tests/` | Tests (`python3 -m unittest discover -s tests -q`) |

### Cómo se guarda cada post (para seguirlo y corregirlo)
Cada combi lleva `sel` = lista de `"partido_id|mercado|opción"` y `cuotas` = cuota de cada pata.
Con eso la app sabe cómo va cada pata y `verdes_auto.py` sabe cuándo es verde. **Un post de combi sin
`sel` no se puede seguir** → siempre hay que guardarlo.

### El bot del móvil (`@combilocas_publica_bot`)
- Comandos: `/hoy`, `/picks`, `/manana`, `/combis`, `/editar`, `/borrar`, `/pausa`, `/reanudar`, `/ayuda`.
- 60 min antes de cada post automático manda el borrador con ✅ Vale / ✏️ Cambiar / ❌ Cancelar
  (si no contesta, sale tal cual). Si el post lleva foto (combi de partido, boleto), el borrador va con la foto.
- Si le manda texto o foto, pregunta si lo sube; si es captura de bet365 → flujo de boleto.
- Si el bot se reinicia entre la foto y el botón, recupera la foto del propio chat; si no puede,
  dice «ese botón ya no vale, mándamelo otra vez». **Nunca se queda callado.**

### Vigilancia (para que nada falle en silencio)
- **Registro del bot del móvil**: `datos/asistente_log.txt` (cada mensaje, botón y error, se sube cada 3 min).
  Para ver lo que imprimió cualquier ejecución de GitHub: lanzar a mano «Leer registro de una ejecución» con su id
  → `datos/registro_ejecucion.txt`.
- **Vigilante** (en el asistente, proceso aparte del bucle): avisa al móvil si un post lleva >15 min
  sin salir o si el bucle de publicación no da señales en >35 min.
- **Avisos**: fallo al publicar en Telegram o Threads, verde de cualquier combi/escalera/boleto.
- **Revisión de cuotas**: 24 h antes, si la cuota del texto se desvía >10 % de la real de bet365 → aviso.

---

## 6 bis. Primeros pasos para una IA nueva
1. Leer este manual entero.
2. Clonar el repositorio `marcooshz1234-sudo/bot-futbol` (Python 3.12; para imágenes: `pip install playwright`
   + `python -m playwright install chromium`, ffmpeg; para leer boletos: Pillow + tesseract).
3. `python3 -m unittest discover -s tests -q` → tiene que dar OK.
4. Ver en GitHub → Actions que «Publicar en Telegram y redes» y «Asistente en el móvil» están en marcha.
5. Mirar qué sale hoy (`auto.json` + `cola.json`) antes de proponer nada.
6. Cualquier cambio: tests → `git pull --rebase` → commit → `git push` → comprobar que el bucle no lo pisa.
7. Antes de decir a Marcos que algo funciona: probarlo (simulación de la sección 7) y decir exactamente
   qué se ha probado y qué no.

## 7. Mantenimiento: cómo comprobar que todo va bien

1. **¿Está publicando?** Mirar `datos/bucle_log.txt` (última línea con hora reciente, UTC) y
   GitHub → Actions: «Publicar en Telegram y redes» tiene que estar siempre en marcha.
2. **¿Qué sale hoy?** En el bot del móvil `/hoy`, o leer `auto.json` + `cola.json` del día.
3. **¿Sale todo bien?** Cada post publicado tiene `enviado`/`mensaje_id` (Telegram) y `redes.threads`,
   `redes.instagram`. Los errores quedan en `errores_redes`; los de Telegram y Threads llegan como aviso.
4. **Tests** antes de subir cualquier cambio: `python3 -m unittest discover -s tests -q` → tiene que poner OK.
5. **Simulación sin publicar**: copiar el repo a una carpeta aparte, quitar el remoto
   (`git remote remove origin`), poner la red falsa (que responda «ok» a Telegram/Threads/Instagram)
   y adelantar el reloj 5 min cada vuelta durante 48 h ejecutando `publicar_telegram.main()`,
   `redes.main()`, `app_datos.main()`, `verdes_auto.main()`, `avisos.main()`. Así se ve qué saldría,
   cuándo y dónde sin publicar nada. (El 27/10 se hizo y salió todo bien.)
6. **Comprobación de normas** de lo programado: cuotas reales (`cuota_real_sel`), patas ≥1,25, 4–7 patas
   y cuota 7–10 en combis de partido, sin «menos de», sin +18, sin jugarbien, sin el nombre de Marcos.

### Cómo cambiar cosas sin romper nada
- Subir cambios con `git pull --rebase` + `git push`. El bucle escribe en `cola.json`, `auto.json`,
  `enviados*.json` y `datos/` constantemente: **si cambias `cola.json` a mano, hazlo justo después de un
  pull y súbelo al momento**; comprueba después que el cambio sigue ahí (el bucle no lo pisó).
- Para cambiar un post ya programado del bot: editar en `cola.json` o con el bot del móvil (✏️ Cambiar).
  Si cambia el texto, la imagen se rehace sola en ≤10 min (huella `.huella`).
- Para quitar un post: `"caducada": "quitada"` + nota. Nunca borrarlo del archivo si ya se publicó.
- Las horas, formatos y reglas de las combis están en `plantillas.py` y `combis_dia.py` (constantes arriba).

---

## 8. Errores que NO pueden volver a pasar (y por qué pasaron)

| Qué pasó | Por qué | Cómo se evita ahora |
|---|---|---|
| Un boleto aprobado por Marcos no se publicó y nadie avisó (26–27/10) | El asistente lo metía en `cola.json` a la vez que el bucle; el guardado chocaba y se perdía. Además, si el bot se reiniciaba, olvidaba la foto | El asistente publica él mismo y contesta «✅ Telegram ✅ Threads» o el error; recupera la foto tras reinicio; si un guardado falla, avisa |
| Se le dijo a Marcos que algo estaba funcionando sin haberlo probado | — | Regla: no decir «hecho» sin comprobarlo. Simular antes |
| Combi Dortmund–Werder anunciada a 2,26 que en bet365 pagaba ~1,80 (los seguidores lo notaron) | Se multiplicaron patas del mismo partido | Recorte de «Crear apuesta» por parejas + aviso si la cuota del texto no cuadra |
| Combis de partido de 7,46 y 7,65 que en realidad pagaban ~3,4–3,8 | Igual: patas muy relacionadas multiplicadas | Igual. Se quitaron |
| Una pata publicada a 1,53 había bajado a 1,35 | Cuota vieja | `cuotas_frescas.py` cada 5 min antes de publicar |
| Escalera con dinero en Instagram cuando la norma decía sin dinero | Las imágenes copiaban el texto | Instagram quita el dinero de todo salvo la escalera (decisión de Marcos) |
| Verdes que no se detectaban | Se leía el texto en vez de las selecciones guardadas | Cada combi guarda `sel` + `cuotas` |
| Imagen de Instagram con el texto viejo | El texto cambió y la imagen no | El bucle rehace imágenes desactualizadas cada 10 min |
| Combis todas iguales (4 patas a x7), demasiados «más de 2,5» y tiros totales | Búsqueda que solo miraba la cuota | Reglas de variedad (sección 4) |
| Picks de «menos de goles» que fallaron | — | Prohibidos |
| «Rayo gana alguna de las dos partes» y «Almería gana alguna de las dos partes» (Copa, 27/10) dados por verdes y la loca x7,21 publicada como VERDE | Los partidos fueron a la prórroga y el bot contaba los goles de la prórroga como 2ª parte | Todo se evalúa con el marcador del minuto 90 (`a_90()` en `picks.py`) |
| Posts subidos sin enseñárselos a Marcos | — | Siempre enseñar antes |
| 27/10 por la tarde el bucle estuvo parado ~40 min dos veces (un post salió 27 min tarde) | Al empezar cada tanda instalaba Chromium/ffmpeg y llegó a tardar 47 min; además la tanda se cortaba al pasar 65 min | La instalación va en segundo plano y el bucle empieza a publicar al momento. El vigilante del móvil avisó bien («el bucle no da señales») |
| `estado_redes.json` guardado con marcas de choque de git (26/10): `comprobar_redes.py` fallaba al leerlo y no avisaba si caducaban las claves de Meta | Choque al recuperar cambios locales en el bucle (`git stash pop`) | `reparar_json.py` se ejecuta tras cada pull y arregla cualquier JSON con marcas; `comprobar_redes.py` ya no se cae si el archivo está roto |
| Del 26 al 27/10 el bot del móvil no guardaba nada (cancelar, cambiar textos, pausa…) y nadie se enteró | `git add` con una ruta que no existía (`datos/comunidad_picks.json`) falla entero y no añade nada | El bot solo añade rutas que existen y, si no puede guardar, avisa. Además deja un registro de cada mensaje y botón en `datos/asistente_log.txt` (y el workflow «Leer registro de una ejecución» baja el registro de cualquier ejecución) |
| Falsa alarma «no salió a su hora» de dos combis quitadas a mano (27/10) | Se quitaron con `"caducada": true`, que significa «fallo» | Quitar siempre con `"caducada": "quitada"`; los avisos ya ignoran lo quitado, lo cancelado y lo que aún no le toca, y dicen la hora y el partido |

---

## 9. Lecciones de apuestas (de los resultados)
- Los «más de 2,5 goles» y «gol en la 1ª/2ª parte» fallan mucho en partidos cerrados.
- Varios picks del mismo partido caen juntos (si el partido sale raro, caen todos): evitar que muchas combis
  dependan del mismo partido.
- Las estadísticas prometen ~73 % y se acierta ~59 %: por eso se usa la probabilidad aprendida (`aprender.py`).
- Ligue 1 castigada; tiros de jugadores funcionan bien; córners de un equipo a 4+ fallan a menudo.
- El registro diario de lecciones está en `LECCIONES.md` (lo escribe el bot).

---

## 10. Pendiente / ideas
- App: «calendario de la semana» (elegido por Marcos, sin hacer).
- Afinar el recorte de «Crear apuesta» con más capturas reales de bet365 (cada captura con la cuota de
  cada pata y la que paga bet365 vale para ajustar `pareja()` en `combis_dia.py`).
- Más descargas de datos (11:15, 16:30, 23:45): propuesto, Marcos dijo que no por ahora.
- Canal de pago en Telegram cuando haya seguidores suficientes. App pública: todavía no.
- Facebook en pausa. TikTok descartado. Respuestas automáticas a comentarios: en pausa
  (la moderación sí borra comentarios con enlaces o publicidad).

---

## 11. Otro proyecto relacionado: la guía (tucanalconia)
Guía de pago sobre cómo montar un canal automático de Telegram/redes con IA. **No debe mencionar
combilocas ni apuestas.** Se trabaja en otro chat. Gmail: soporte.tucanalconia@gmail.com.
