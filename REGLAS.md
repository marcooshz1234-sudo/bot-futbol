# REGLAS DE COMBILOCAS (la lista única)

> **Esta es LA lista.** Toda regla nueva o cambiada de Marcos se escribe AQUÍ (con fecha) y, si se puede comprobar
> en un post, también en `comprobar_post.py` + su test (`tests/test_comprobar_post.py`), en el mismo momento.
> Si dos reglas chocan, vale la más nueva (la vieja se tacha aquí con «~~»).
>
> 🤖 = la comprueba `comprobar_post.py` antes de publicar (si falla, el post NO sale) · ⚙️ = la hace el bot al generar
> · 👤 = de trabajo (la IA la tiene que cumplir; no se puede comprobar con código)
>
> **Antes de meter cualquier post a mano:** `python3 comprobar_post.py <id>` (o sin id: todo lo pendiente).

---

## 0. Para qué es cada red (16/11, Marcos) — manda sobre lo de abajo si choca
- **Threads e Instagram = COMBILOCAS de verdad, para captar gente que se vaya al Telegram.** Mucho volumen: todos los picks que gusten del día, combis con escudos, listas, GANADORES, y muchas combis locas (cuota 100, cuota 500…).
  - Formato: partidos sin foto → solo texto con emojis; un partido con 4-5 cosas → los 2 escudos; un pick solo → su foto.
  - **Nada de cuánto hemos acertado** (ni verdes, ni rojos, ni balances, ni como comentario), salvo un verde de **combi de cuota 5 o más** (17/11: antes 10; «Señores, acertamos tal»), comprobado bien antes de subirlo.
  - Lo que más importa medir es **la gente que te sigue desde cada post** (y los likes); las visualizaciones también, pero menos (rendimiento_redes.py).
  - **Contenido constante** (threads_locas.py): cada 30 min de 09:00 a 01:00 y cada hora de madrugada (de 21:00 a 23:30, con los partidos de MAÑANA: `-loca-th-noche-`, 16/11); combis x50/x100/x500/x1000, listas del día, tiros de jugadores habituales (sin esperar alineaciones). Nada de un pick suelto con explicación. Enlace del Telegram en el comentario 1 de cada 4.
  - **Combis con escudos (foto de los 2 escudos)**: entre 4 y 6 al día (no todos los partidos), unas 4 h antes; partidazo → 6-8 cosas, partido flojo → 3-4. Sin córners ni tarjetas, sin «gana X» junto a «X o empate».
  - **Días de Europa League / Conference (o 12+ partidos)**: más posts (cada 20 min de día, hasta 10 escudos).
  - Threads no deja más de 500 caracteres. La cuota, siempre como saldría en bet365 (crear apuesta en el mismo partido). Un pick, como mucho en 2 posts del día.
  - **Patas de 1,40 a 9** (el tope de 1,80 es solo para Telegram).
  - Si un cuotón entra pero algún jugador no jugó (anulado), el comentario lo dice tranquilo: «han entrado todas, X no jugó y la cuota baja un poco».
- **X = @combilocass (18/11, Marcos: «deberíamos empezar el canal de X»)**: lo mismo que Threads, cortado a 280 (emojis cuentan 2; si no cabe, sin la frase final / «(fem.)», y si aún no, hilo de 2). **Sin «@» delante de las cuotas** (en X «@1,80» es una mención). En la bio X no deja «✅». Cuenta nueva: empezar con 3-5 posts al día (pick, escalera, verdes, resumen) para que no la tome por spam. De momento lo sube Claude desde el Chrome de Marcos con su OK; Marcos quiere que sea automático y gratis (Buffer, por probar).
- **Telegram = lo serio (lo que luego se podrá vender).** La escalera: 1 pick (2 solo si hay uno muy fijo), explicada.
  - **Primero el buenos días y luego el contenido** (16/11): de 01:00 hasta el buenos días no sale nada nuevo (los verdes sí); lo que esperaba sale justo después.
  - **Siempre con explicación**: si un pick (también las copias de tipsters) va sin porqué, el bot le añade 1-3 razones (forma, tabla, rachas, qué se juega). Debajo de la foto el porqué se queda.
  - El buenos días ya **no lista lo que sale hoy** (salía solo la escalera).
- 🤖 **Picks y copias de Telegram, SIEMPRE con su foto de banderas/escudos** (16/11, Marcos: «programalo todo bien»; Islandia –1,5 salió solo en texto y lo borró). La racha de «3 fotos seguidas → texto» ya no vale para picks ni copias; si el pick no se entiende, la foto lleva al menos las banderas del partido; y si aun así no hay foto, el post NO sale y avisa por privado.
- 👤 **Telegram, serio y profesional** (16/11, Marcos: «tenemos que ir con más cuidado de lo que subimos»; «me lo enseñas primero»): todo lo que Claude meta a mano en Telegram se le enseña ANTES y sale solo con su OK (en la cola con `requiere_ok` hasta que diga).
- 👤 **Boletos de Marcos en Threads, con su captura** (16/11, Marcos: «en Threads sube la captura en todas»; «recorta el dinero, en las muy locas déjalo»). Si la captura deja ver el dinero, el texto usa **la misma apuesta y lo mismo que paga la captura** (p. ej. «1€ → 176€», no «10€ → 1.636€»); nunca una cuota distinta de la de la foto. El estilo automático no toca los boletos (la CUOTA salía dos veces).
- Un **pick suelto** (o copia de tipster de una pata) es solo para Telegram, nunca Threads/Instagram.
- **Copias de los canales (16/11, Marcos: «coge las que te gusten… fallar lo menos posible»; «que pese más el % de acierto de cada tipster»)**: ya no se copia todo. Nota = 40 % lo que ve bet365 + 60 % el acierto del tipster (suavizado: con pocos picks cuenta como 50 %) + 0,10 si lo dan 2 canales; se copia con nota ≥ 0,55. Nunca algo que bet365 vea por debajo del 33 %, ni a favor de un equipo que no se juega nada contra uno que sí. Siempre con su porqué. **El motivo del analista, siempre con otras palabras** (nunca su texto tal cual; si no hay uno reescrito, el bot pone sus propias razones) (16/11 10:53). **De 1,80 para arriba solo los tipsters buenos (≥ 70 % de acierto suavizado: INSIDER, Lafiebredelpick, MAX ANALISTA)** (16/11 10:41; el acierto suma todas las formas del nombre del canal, con y sin emojis). **Tipster Pérez, favorito: sus picks se copian siempre** (sin nota ni tope de 1,80; solo se frena lo que bet365 ve por debajo del 33 % o a favor de quien no se juega nada) (16/11, Marcos: «me gusta mucho»).

- 🎯 **Picks de Telegram: lo más probable de TODOS los mercados, sin ser monótonos** (16/11, Marcos: «quiero que salga lo más probable… más de 2,5 goles si lo ves muy probable… que no sea monótono, aunque el gana o gana o empata me gusta»). Resultado, goles, córners, jugadores… **Tarjetas: las nuestras nunca; solo copiadas de un canal que acierte bastante** (tipster bueno, ≥ 70 %) (17/11: «van fatal… solo que lo suba si es de un canal que acierte bastante»; comprobar_post.pick_tarjetas_tg las para). Lo prohibido en las combis (más de 2,5 goles, tarjetas del partido) vale aquí solo con prob. ≥ 70 %; el resto de prohibidos (1ª parte, menos de, tiros del partido…), no. Los dos picks del día de tipos distintos (salvo el último plan B del mínimo diario) y lo que salió los 3 días antes resta un poco (el «gana», la mitad). La promo «2 goles de ventaja» no se escribe en los posts (el verde ya cuenta el 2-0).
- 🎯 **Más picks si hay cuotas buenas** (16/11, Marcos: «si hay más cuotas buenas, que las meta también, y si son de diferente mercado, mejor»; los repetidos pueden salir): hasta 2 picks más en Telegram (12:30 y 16:30, `pick-seguro-3/4`), solo con cuota 1,50-1,70 y prob. ≥ 62 % (sin plan B), sin chocar con lo de hoy; se prefiere un mercado que no haya salido ese día.
- 📊 **Resumen semanal por privado** (16/11, Marcos): domingo 22:00, acierto de los picks de Telegram por tipo y de las copias; ⚠️ si un tipo baja del 55 % → Marcos decide si se le sube el listón (resumen_semanal.py).

## 1. Cuotas
- 🤖 Un pick solo: **mínimo 1,35** (12/11: «nadie coge un 1,11»).
- 🤖 Cada pata de una combi: **mínimo 1,20** (12/11). Excepción: UNA pata de 1,15–1,20 si es gana/no pierde de un
  favorito de élite (España, Francia, Real Madrid…) en una combi de 1,50 o más; nunca para rellenar (12/11).
- 🤖 Combi total: mínimo 1,35.
- 🤖 **Cada pata, máximo 1,80** (13/11: «vamos a hacer los picks más seguros»). En lo nuestro (combis, picks,
  escalera); no en las copias de canales, ganadores ni marcadores exactos. **La de 1 € a 500 € tampoco: patas grandes, sin
  límite, dentro de la lógica** (14/11, Marcos). Las listas de picks sí llevan el límite. Los boletos de Marcos (su combinada de bet365) tampoco (14/11).
- ⚙️ **Cuotazas: hasta 2,20 y solo de 9:00 a 23:00** (13/11: la de Andorra–Gibraltar @3,25 a las 3 de la mañana).
- ⚙️ Las combis del bot: patas de 1,25 o más (`combis_dia.CUOTA_MIN_PATA`).
- 👤 **Nunca combis largas de patas regalo** (@1,05, @1,12…): el objetivo es estar al nivel de Pérez y TipsAnalistas (12/11).
- 👤 Todas las cuotas, de bet365. Si no se sabe la cuota, la selección no va.
- 👤 **Calculadora del «Crear apuesta»** (13/11): `python3 crear_apuesta.py <id>`. Nunca estimaciones a ojo. Cada cuota
  real que da Marcos se guarda sola (datos/crear_medidas.json) y el bot aprende de ella.
- 🤖 **Combi de un partido: la cuota NO se multiplica.** Sale con la cuota de la calculadora (`crear_apuesta.py`) y «aprox.»; si Marcos da la real antes de salir, manda la suya (15/11: las 3 de escudos del domingo no salieron esperando su cuota). (plantillas.cuota_crear + test_crear_calculadora_post)
- ⚙️ **Nunca el mismo post dos veces en la misma red** (15/11: Madrid CFF y Finlandia ×2 en Telegram, Bélgica–Italia ×3 en Threads). Para volver a subir uno, el original va a `borrados.json` o el nuevo lleva «repuesto_de». (comprobar_post.duplicado)
- ⚙️ Cuotazas (errores de bet365 frente a Pinnacle): mínimo 1,40 (11/11).

## 2. Mercados
- 🤖 **Prohibidos en lo nuestro** (bot y Claude): más de 2,5 goles del partido (05/11), goles de la 1ª parte y «ambos marcan
  en la 1ª parte» (04/11), ganador al descanso / empate al descanso (07/11), **tarjetas totales del partido** (12/11:
  mejor por equipo), tiros totales del partido (05/11), fueras de juego (03/11), «menos de X», «no», «12 / sin empate»,
  paradas del portero (se miran a mano).
- 🤖 **Excepción:** las copias de canales de Telegram SÍ pueden llevar esos mercados («y más si lo dicen ellos», 12/11). Y el pick suelto de Telegram, más de 2,5 goles y tarjetas del partido si son muy probables (16/11, ver §0).
- 🤖 **Combis con escudos (de un partido): sin córners ni tarjetas** (01/11: córners 43 % y tarjetas 36 % de acierto en octubre).
- 👤 Se prefieren: «gana X» (con la promo «2 goles de ventaja»), doble oportunidad, «X marca 2 o más», ambos marcan,
  jugadores titulares fijos con cosas que suman (tiros, faltas), córners en combis de varios partidos.
- 👤 Mejor «ambos ven tarjeta» que «más de 4 tarjetas» (03/11).
- 🤖 Todo se cierra a los 90 minutos: la prórroga no cuenta (27/10, `picks.a_90()`).
- ⚙️ Jugador cambiado: cuenta lo que haga el que entra («Sustituto+» de bet365, 01/11).
- ⚙️ Variedad en cada combi: tipos de mercado distintos; en las de varios partidos, una pata por partido.

## 3. Lógica de una combi
- 🤖 **Nunca chocar**: dos posts del mismo partido tienen que poder ganar a la vez. Única excepción: la loca puede llevar
  un «o empate» aunque choque, pero no como costumbre (12/11).
- 🤖 **Máximo 2 posts con el mismo pronóstico** en el día (ganadores no cuenta; la cola a mano sí) (11/11).
- 🤖 **«Que gane un equipo» (gana, gana una parte, hándicap, doble oportunidad…) como mucho en 2 posts del día por equipo** (13/11: Suiza iba en 4 posts y un 0-0 tumbó los 4). Córners, tarjetas, jugadores y goles no cuentan para esto; las combis con escudos, el estrella y los ganadores tampoco. Los posts del día NO tienen límite. (combis_dia.equipo_de + test_fallos_13nov)
- 🤖 **Partidos de selecciones con pocos goles esperados (el «más de 2,5» paga más de 1,90): nada de «más goles»** («X marca» sí) (13/11: Liechtenstein 0-1 y Luxemburgo 0-1).
- 🤖 **En día bueno, una sola combi: la del día** (ni multi ni loca). Marcos: «una combi al día tiene que haber; el resto lo puedes cambiar» (13/11).
- 🤖 En la misma combi no van juntos «ambos marcan» y «X marca» (31/10).
- 🤖 Ni «marca el local» y «marca el visitante», ni «X o empate» y que le marque el rival (02/11).
- 🤖 Combis de varios partidos: **en orden de hora** (02/11) y **de un solo día** (si falla uno se cae todo el finde).
- 🤖 Nada a favor de un equipo al que le falta su estrella (prensa), salvo que siga siendo favorito claro (≤ 1,35) (12/11).
- 🤖 Partido aplazado, bloqueado o ya jugado: no se publica.
- ⚙️ **Días buenos: solo partidos buenos** (12/11). Si el día tiene 4 o más partidos buenos (Champions, Europa League,
  Conference, Nations League, Mundial/Eurocopa y clasificaciones, las 5 grandes ligas, Champions femenina, o un grande
  aunque sea de Copa), todo lo nuestro sale solo de esos: nada de Segunda, Copa de equipos pequeños ni ligas femeninas.
  Los días flojos, como siempre. Las copias de canales de Telegram no cambian. 👤 Los posts a mano, igual.
- 👤 Construir sobre el escenario que se espera del partido (que pasen cosas), con datos que lo confirmen.
- 👤 Contexto siempre: clasificación, forma, jugadores clave y sus bajas, calendario europeo, nivel de la liga.
- 👤 Antes de las alineaciones, solo jugadores fijísimos; al salir los onces, se rehacen las patas de jugadores (05/11).
- ⚙️ Combis con escudos: 4–5 patas, cuota 5–7 (01/11). Loca: lo mejor de cada partido, 1–2 cosas. Larga: ~10 patas,
  solo «quién gana».

- 🎯 **Qué se juega cada equipo** (16/11, Marcos): antes de un pick se mira la clasificación (que_se_juegan.py): si puede quedar primero, clasificarse o descender según gane, empate o pierda (desempate UEFA: cara a cara primero). Nunca «gana X» si X no se juega nada y su rival sí. Las patas del que se lo juega (goles, tiros, córners, jugadores) suben un poco y las del que no, bajan. Vale para la Nations, la Champions y las ligas.
- 16/11 (Marcos): la tarjeta de GANADORES nunca cortada; si son muchas filas, mejor sin foto.

## 4. Copias de canales de Telegram
- ⚙️ Se copian TODOS los canales de fútbol que seguimos (no NBA ni tenis), sin su nombre ni su boleto (12/11).
- 👤 **Baloncesto y tenis (13/11):** se leen y se guardan (datos/tipsters_raw.json), pero NUNCA se suben al canal ni a redes. Solo se le dan a Marcos cuando los pida («solo cuando te los pida me los das, nada de subirlos al canal»).
- ⚙️ Con la cuota de bet365 de ahora, no la suya. Sin cuota, no se sube.
- ⚙️ Si son picks bajos (< 1,35) o pocos, se juntan en una combi (hasta 4, de partidos distintos, ≥ 1,35); si no, tal cual.
- 🤖 **Nunca nombres de otras casas ni notas internas** en lo publicado («MyMatch», «pata de su…») (13/11).
- ⚙️ Un post de un canal se copia una sola vez. Su «Crear apuesta» va en UNA línea con su cuota; nunca partido en patas
  (con la misma cuota en cada pata salía una cuota falsa, 13/11).
- ⚙️ Combinada suya a la que le falta una pata (por las reglas): fuera entera. «Crear apuesta»: con su cuota y el verde a mano.
- ⚙️ No se copia lo que choca, lo que ya va en 2 posts ni lo que va a favor de un equipo sin su estrella.

## 5. Textos
- 🤖 Nunca «seguro», «asegurado», «sin riesgo» (12/11).
- 🤖 Nunca el nombre de Marcos. Nunca «jugarbien.es» ni «+18 | Juega responsable» (27/10). Nunca «Solo queda rezar».
- 🤖 En Telegram nunca «@combilocas» (lleva a otro canal, 05/11).
- 🤖 «Combina máximo 2 o 3» solo con 5 picks o más; «Coged los picks que más os gusten» solo en combis de 10+.
- ⚙️ No repetitivo: frases de apertura y de cierre variadas; el cierre no en todos los posts (12/11).
- ⚙️ Stake solo cuando no es 2 (12/11).
- 👤 Nombre completo del jugador y su equipo (05/11). Nombres de equipos y selecciones en español.
- 👤 Escribir como los canales de Telegram que sigue, no como un bot (09/11).

## 6. Telegram (canal gratis)
- 🤖 **Toda combi de Telegram, con su foto de escudos/banderas** (18/11, Marcos: «algún pick de hoy también ha salido sin escudo»: la combi del miércoles y la de las favoritas salieron solo en texto). La racha de «3 fotos → texto» ya no vale para combis; sin foto, no sale (tarjeta_tg + publicar_telegram; test_combis_tg_con_escudos).
- ⚙️ Solo: pick del día (1,50–1,70), escalera, una combi buena y las copias de canales (09/11 y 12/11).
- ⚙️ 9:30 buenos días con foto (3 que rotan) y lo que sale hoy; noche europea los días de Champions/EL/Conference;
  «en directo» al empezar un partido nuestro, de vez en cuando (uno cada 3 días como mucho, 12/11); ¡PLENO! si sale todo (12/11). No el balance de la noche.
- ⚙️ Fotos de la marca en escalera, pick del día y rojos; animación ¡VERDE! en verdes de cuota ≥ 3,00 (12/11). Sin muñeco.
- 👤 Nunca editar un post ya publicado (04/11): si falta algo, respuesta o post nuevo.
- ⚙️ Los posts de «solo Threads» no salen en Telegram (12/11).
- 🤖 **Más fotos, menos texto (13/11):** copias de tipsters, picks, cuotazas y combis de varios partidos salen con tarjeta (banderas/escudos, apuesta corta, cuota y hora) y debajo solo la entrada, las patas y la cuota. Sin argumento ni «Sin argumento: solo el pick». El pick va escrito en la foto (Crear apuesta: una fila por condición), con el logo de la competición (logos grandes de football-logos.cc/paladarnegro, letras en blanco) y el escudo del club o la bandera de la selección (13/11). Pero no siempre: tras 3 posts seguidos con foto, el siguiente va en texto («que el canal no esté solo con fotos»). (tarjeta_tg.py + test_tarjeta_tg)
- 👤 Nada de GIF de relleno, encuestas, concursos ni rankings (11/11).

## 7. Threads e Instagram
- ⚙️ Threads: sin etiqueta de tema (26/10: con ella se veía 3–10 veces menos); texto con emojis; **foto solo en el pick del día y los ganadores** (12/11). Y los boletos de Marcos, siempre con su captura (14/11: sin ella no se entienden).
- ⚙️ Estilo Threads: cabecera en mayúsculas con 🔥⚽, ✅ en cada pata, «🎯 CUOTA … 💎», lo que se gana con 10 € y
  un cierre que cambia (12/11).
- ⚙️ Enlace de Telegram en el primer comentario de los posts principales y todos los verdes (12/11).
- ⚙️ El verde de una combi va como primer comentario de su post en Threads (12/11).
- ⚙️ Siempre lo que se gana con 10 €.
- ⚙️ Instagram: nunca dinero ni boletos en las imágenes (salvo la escalera).
- ⚙️ Logo de la competición en los posts de una sola competición o partido: máxima calidad, sin círculo blanco.
- ⚙️ Ganadores (plantilla «estadio» con el logo CL): «WIN», nunca sin su foto (se rehace si cambian los equipos).
- 👤 Más contenido de noche para el día siguiente; sobre las 00:30, siempre algo con escudos.

## 8. Verdes y rojos
- ⚙️ **Acierto de Threads → comentario en ese mismo post (18/11, Marcos: «cuando aciertes una de threads lo vas a poner en el comentario de la misma publicación»):** todas, también listas y cuotas bajas; sale solo, sin esperar al OK (redes.verde_en_su_hilo, verdes_auto; test_threads_verde_comentario). Con jugador que no juega: «han entrado todas, X no jugó y baja un poco».
- ⚙️ Los verdes llevan la cuota de la publicación. Solo salen cuando terminan los partidos (o 10 min en verde).
- 🤖 **Los verdes, siempre con las banderas o escudos de cada partido** (17/11: la escalera Dinamarca–Noruega salió sin ellas; fotos.insignias) 18/11 (Marcos: «siempre revisa eso»): un verde sin foto ya no sale en ninguna red (comprobar_post.verde_sin_escudos; test_verde_con_escudos).
- ⚙️ Pata anulada (aplazado, jugador que no juega): se quita y la cuota se rehace, como paga bet365.
- ⚙️ **El aviso de «¡VERDE!» solo para verdes de verdad (13/11):** un post que se para para enseñárselo a Marcos le llega como «⏸️ Post en espera», nunca como verde (asistente.py + test_aviso_espera).
- ⚙️ **Verdes seguros salen solos** (12/11: «los acertados que los suba de una, ni pregunte, pero tiene que estar seguro»):
  todas las patas en verde y confirmadas, sin anuladas, con su cuota (≥ 1,35) y que no sea un boleto. Si hay cualquier
  duda, se le mandan a Marcos con el motivo y salen con su «✅ Publicar».
- ⚙️ **Verdes de Telegram: uno a uno, cada 10 min entre ellos** (17/11: «que suba ya las que se van acertando una a una
  cada 10 min»; antes, 12/11, iban juntos en un post). Ya no esperan 15 min a juntarse (verdes_auto.escalonar).
- ⚙️ **Threads: solo verdes de combis de x5 o más** (17/11), también las locas (centenaria, duelo, tapados…), no listas
  ni ganadores. Si llevan varias patas del mismo partido, pasan por su «✅ Publicar».
- 👤 Rojos y cuotazas: solo con «✅ Publicar» de Marcos.
- 👤 Si la combi nunca se publicó (captura de Marcos), el verde no lleva «¿Quién la llevaba?».

- ⚙️ **Resumen de la noche (23:15): los fallados salen, pero sin ❌** (13/11: «que no se vea tan mal»). Todo como
  «28 de 41 picks en verde», los picks sueltos aparte («8 de 11»), el % solo si es bueno (≥ 60 %), sin «lo peor», y la
  lista de los verdes con su cuota. Igual en el «📊 Historial: 4 de 6 en verde · +4 %» de los picks.

## 9. Escalera
- ⚙️ Empieza con 20 € y cada día juega lo ganado (7 días). Verde → sube un escalón; rojo → vuelve al día 1.
- ⚙️ Todos los días hay escalera, sin excepción (29/10). Opción A (≈ x2), sin descanso ni 1ª/2ª parte.
- ⚙️ Si a las 30 h falta el resultado de una pata, esperar y avisar (no darla por anulada) (11/11).

## 10. Trabajo con Marcos
- 👤 Hablar siempre en español, corto y con tablas.
- 👤 **Nunca decir que algo está hecho y funcionando sin comprobarlo de verdad.** Revisar los datos al 100 % antes de decirlos.
- 👤 **Nunca cambiar nada (bot, app, posts) sin enseñárselo antes** o sin que lo pida.
- 👤 Ninguna IA pide, ve, copia ni pega tokens o contraseñas: las pone Marcos.
- 👤 Nunca borrar publicaciones de forma permanente. bet365: solo mirar.
- 👤 «Arreglado» = que no vuelva a pasar: con test.
- 👤 Con muchas cosas que decidir: preguntar con opciones.
- 👤 Todo cambio, a la bitácora (`informes/bitacora/AAAA-MM.md`).
- 🤖 **App «Mis combis» y widget de la pantalla de bloqueo: solo las combis que pasa Marcos** (16/11, Marcos: «quiero que ahí solo se vean las que yo te paso»): las de sus capturas/notas de bet365 (origen «Marcos…»); las que propone Claude o el bot no salen (mis_datos.es_suya).
- ⚙️ **Resumen de la noche: los fallados salen en «😤 Se nos escaparon», con un dato del partido** (16/11, Marcos): el marcador, y si el pick era de tiros/córners/tarjetas, cuánto hubo; en las combis, la pata que la tumbó. Sin ❌ (13/11).
- ⚙️ **Resumen de la noche con FOTO** (18/11, Marcos): lista de los verdes con banderas, «x/y», lo que se gana con 10 € a cada pick, ¡PLENO! si es todo; debajo texto corto y los fallos con su dato.
- ⚙️ **El resumen de la noche nunca sale solo: llega a Marcos y sale con su «✅ Publicar»** (17/11: salió solo con fallos).
- 🤖 **El resumen de la noche (Telegram) cuenta SOLO lo que salió en Telegram** (16/11, Marcos: «5 de 33… has mezclado todas las redes»): nada de locas ni boletos de Threads; y el resumen no sale en Threads (§0). (resumen_dia.en_telegram + test)
- ⚙️ **Combi muy gorda que se cae por UNA → se sube a Threads** (16/11, Marcos: «si alguna muy gorda falla por uno, se sube»): cuota ≥ 30, todas las demás en verde y los partidos acabados; «😱 SE NOS ESCAPÓ POR UNA» con la que falló. Pasa por su «✅ Publicar» (verdes_auto.casi_por_una). No listas, ni ganadores, ni boletos.
- 🤖 **Telegram: como mucho 2 picks de tarjetas al día** (17/11, Marcos: «ya hay dos picks de tarjetas hoy, ya no subas ninguno así»). El tercero no sale (comprobar_post.tarjetas_tg).
- 🤖 **Lo que mete Claude en Telegram, siempre con su «sel»** (17/11: «Gana Corea» salió sin ella, el bot no lo siguió y su verde no salía; Marcos: «mira tú bien lo que se ha subido al canal»). Sin sel no sale (comprobar_post.sin_sel_claude). Y cada noche, repasar post a post lo enviado a Telegram contra lo que sigue el bot.
- ⚙️ **Avisos al privado: SOLO de Telegram** (18/11, Marcos: «nunca los leo… en Telegram sí todo perfecto»). Nada de Threads/Instagram, spam, noticias, lecciones ni la revisión de las 9:00 (privado.py, ajuste «avisos_solo_telegram»). Los verdes de Threads con dudas ya no piden «✅ Publicar»: no salen.
- 👤 **Varios picks del mismo partido en Telegram, sin tope** (16/11, Marcos: «si las cosas son buenas no pasa nada»; le gustaron los 3 de Alemania–Países Bajos). No proponer límite por partido.
- 👤 **Navegador (su Chrome, Threads, Telegram web): solo lo de hoy** (16/11, Marcos: «estás mirando 4 días atrás… me quedo sin crédito»). Nada de scripts que bajen solos ni bucles de scroll: una lectura de la pantalla, como mucho 2-3 desplazamientos, y parar en cuanto aparezca un post de ayer. Si Marcos dice «para», no queda nada en marcha: cerrar la pestaña.

- 🎯 **Combinada personal de Marcos, una cada día** (14/11, anunciado en el canal). A las 10:00 el bot le propone «Crear apuesta» por Telegram; él la monta en bet365 y manda la captura: sale como «MI COMBINADA PERSONAL DE HOY», sin dinero en la foto ni su nombre. Fuera de las reglas de nuestras combis (1,80, mercados, repetidos).

- 📊 **Resumen de la noche: el «Quién gana» no cuenta** (15/11, Marcos). Solo los picks y combis que subimos; las filas de ganadores ni se suman.

- 🇪🇸 **Todo en español y sin «el» delante de un país** (15/11, Marcos: «El Belarus o el Albania no puede ser»). nombres.espanol() corrige todo texto antes de salir (Telegram, Threads, imágenes, tarjetas) y comprobar_post bloquea lo que se cuele (regla «idioma»).

- 🧠 **Cada argumento tiene que apoyar el pick** (15/11, Marcos: «cómo va a poner que Bielorrusia marca y abajo que los dos llegan cansados»). Cansancio/rotaciones solo del rival; nada neutro ni en contra.

- 15/11 (Marcos): las copias de canales salen SIEMPRE con bandera o escudo en Telegram y Threads (foto VS de los dos escudos) y con el porqué entero.
- 15/11 (Marcos): si en una pasada llegan 2-3 picks nuevos de canales (partidos distintos, sin chocar, @1,35 o más), salen JUNTOS en una combi en vez de sueltos. Un pick que ya salió suelto NUNCA se mete en una combi.
- 15/11 (Marcos): pedir compartir el canal solo muy de vez en cuando: en el post de varios verdes, como mucho 1 vez cada 4 días.
- 15/11 (Marcos): «INFORMACIÓN TOP» (info_top.py): solo con una crisis real (virus, plaga de bajas, impagos, once alternativo) contada por 2+ medios con el equipo en el titular; pick a favor del rival; con escudos; NUNCA sale sola: se manda a Marcos con las fuentes y sale con «✅ Publicar». Máx. 1 cada 3 días.
- 15/11 (Marcos): Threads con foto en casi todo (escudos si es de un partido, si no la de Instagram); solo texto cuando el post tiene más de 4 cosas (patas/picks/filas). Más emojis en el texto de Threads: ninguna línea sin emoji.
- 15/11 (Marcos): dos combis largas del canal al día, NO como «mi combinada» (combis_personales.py), solo Threads e Instagram (NUNCA Telegram): A a las 11:30 y B a las 12:30, con los partidos desde las 13:00 repartidos entre las dos (no comparten partido), 6-12 patas de quién gana / ambos marcan / ambos reciben tarjeta, hasta @120 aprox.
- 15/11 (Marcos): en Threads cada pick lleva un emoji que tenga que ver con él (⚽ ambos marcan/marca, 🏆 gana, 🟨 tarjetas, 🎯 tiros, 🚩 córners, 🛡️ o empate, 🔥 más de X goles, 🅰️ asistencia; la bandera si es una selección). Nunca solo ✅.
- 15/11 (Marcos, foto «TIPS PREMIUM»): las combis largas diarias van en lista «➡️ 🇫🇷 Francia — Over 2.5»: bandera + país/equipo en español y el mercado a la derecha tal cual (Win, BTTS, Over 1.5, Over 2.5, X1, X2). En «gana», solo «Win».
- 15/11 (Marcos): los picks que los canales suben solo en FOTO (boletos) también se leen: OCR gratis (tesseract) y el mismo filtro que el texto. Mercados raros del boleto (remates, córners, tarjetas, hándicap…) no se copian solos: los mira Claude.
- 15/11 (Marcos): la primera frase de un post nunca se repite con los últimos posts del día («Este nos encanta para hoy» salió 3 veces seguidas).
- 15/11 (Marcos): un pick suelto (una sola cosa) SIEMPRE con los escudos/banderas, también en Threads (fallo: la foto se buscaba por el id del post y no la encontraba; ahora por su ruta).
- 15/11 (Marcos: «el escudo arriba»): en Threads la foto sale debajo del texto, así que los picks sueltos van con texto corto (solo el pick) y el porqué en el primer comentario («porque_threads»).
