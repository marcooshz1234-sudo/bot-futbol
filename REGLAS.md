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

## 1. Cuotas
- 🤖 Un pick solo: **mínimo 1,35** (12/11: «nadie coge un 1,11»).
- 🤖 Cada pata de una combi: **mínimo 1,20** (12/11). Excepción: UNA pata de 1,15–1,20 si es gana/no pierde de un
  favorito de élite (España, Francia, Real Madrid…) en una combi de 1,50 o más; nunca para rellenar (12/11).
- 🤖 Combi total: mínimo 1,35.
- ⚙️ Las combis del bot: patas de 1,25 o más (`combis_dia.CUOTA_MIN_PATA`).
- 👤 **Nunca combis largas de patas regalo** (@1,05, @1,12…): el objetivo es estar al nivel de Pérez y TipsAnalistas (12/11).
- 👤 Todas las cuotas, de bet365. Si no se sabe la cuota, la selección no va.
- 🤖 **Combi de un partido: la cuota NO se multiplica.** Se publica con la cuota real del «Crear apuesta» que da Marcos (12/11).
- ⚙️ Cuotazas (errores de bet365 frente a Pinnacle): mínimo 1,40 (11/11).

## 2. Mercados
- 🤖 **Prohibidos en lo nuestro** (bot y Claude): más de 2,5 goles del partido (05/11), goles de la 1ª parte y «ambos marcan
  en la 1ª parte» (04/11), ganador al descanso / empate al descanso (07/11), **tarjetas totales del partido** (12/11:
  mejor por equipo), tiros totales del partido (05/11), fueras de juego (03/11), «menos de X», «no», «12 / sin empate»,
  paradas del portero (se miran a mano).
- 🤖 **Excepción:** las copias de canales de Telegram SÍ pueden llevar esos mercados («y más si lo dicen ellos», 12/11).
- 🤖 **Combis con escudos (de un partido): sin córners ni tarjetas** (01/11: córners 43 % y tarjetas 36 % de acierto en octubre).
- 👤 Se prefieren: «gana X» (con la promo «2 goles de ventaja»), doble oportunidad, «X marca 2 o más», ambos marcan,
  jugadores titulares fijos con cosas que suman (tiros, faltas), córners en combis de varios partidos.
- 👤 Mejor «ambos ven tarjeta» que «más de 4 tarjetas» (03/11).
- 👤 Todo se cierra a los 90 minutos: la prórroga no cuenta (27/10).

## 3. Lógica de una combi
- 🤖 **Nunca chocar**: dos posts del mismo partido tienen que poder ganar a la vez. Única excepción: la loca puede llevar
  un «o empate» aunque choque, pero no como costumbre (12/11).
- 🤖 **Máximo 2 posts con el mismo pronóstico** en el día (ganadores no cuenta; la cola a mano sí) (11/11).
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

## 4. Copias de canales de Telegram
- ⚙️ Se copian TODOS los canales de fútbol que seguimos (no NBA ni tenis), sin su nombre ni su boleto (12/11).
- ⚙️ Con la cuota de bet365 de ahora, no la suya. Sin cuota, no se sube.
- ⚙️ Si son picks bajos (< 1,35) o pocos, se juntan en una combi (hasta 4, de partidos distintos, ≥ 1,35); si no, tal cual.
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
- ⚙️ Solo: pick del día (1,50–1,70), escalera, una combi buena y las copias de canales (09/11 y 12/11).
- ⚙️ 9:30 buenos días con foto (3 que rotan) y lo que sale hoy; noche europea los días de Champions/EL/Conference;
  «en directo» al empezar un partido nuestro, de vez en cuando (uno cada 3 días como mucho, 12/11); ¡PLENO! si sale todo (12/11). No el balance de la noche.
- ⚙️ Fotos de la marca en escalera, pick del día y rojos; animación ¡VERDE! en verdes de cuota ≥ 3,00 (12/11). Sin muñeco.
- 👤 Nunca editar un post ya publicado (04/11): si falta algo, respuesta o post nuevo.
- ⚙️ Los posts de «solo Threads» no salen en Telegram (12/11).
- 👤 Nada de GIF de relleno, encuestas, concursos ni rankings (11/11).

## 7. Threads e Instagram
- ⚙️ Threads: texto con emojis; **foto solo en el pick del día y los ganadores** (12/11).
- ⚙️ Estilo Threads: cabecera en mayúsculas con 🔥⚽, ✅ en cada pata, «🎯 CUOTA … 💎», lo que se gana con 10 € y
  un cierre que cambia (12/11).
- ⚙️ Enlace de Telegram en el primer comentario de los posts principales y todos los verdes (12/11).
- ⚙️ El verde de una combi va como primer comentario de su post en Threads (12/11).
- ⚙️ Siempre lo que se gana con 10 €.
- ⚙️ Instagram: nunca dinero ni boletos en las imágenes (salvo la escalera).
- ⚙️ Logo de la competición en los posts de una sola competición o partido: máxima calidad, sin círculo blanco.
- ⚙️ Ganadores (plantilla oro): «WIN», nunca sin su foto.
- 👤 Más contenido de noche para el día siguiente; sobre las 00:30, siempre algo con escudos.

## 8. Verdes y rojos
- ⚙️ Los verdes llevan la cuota de la publicación. Solo salen cuando terminan los partidos (o 10 min en verde).
- ⚙️ Pata anulada (aplazado, jugador que no juega): se quita y la cuota se rehace, como paga bet365.
- ⚙️ **Verdes seguros salen solos** (12/11: «los acertados que los suba de una, ni pregunte, pero tiene que estar seguro»):
  todas las patas en verde y confirmadas, sin anuladas, con su cuota (≥ 1,35) y que no sea un boleto. Si hay cualquier
  duda, se le mandan a Marcos con el motivo y salen con su «✅ Publicar».
- ⚙️ **Varios verdes a la vez → un solo post con una foto** en Telegram e Instagram (12/11: «para que no haya tantas»).
  Cada verde espera 15 min por si cae otro. En Threads, cada uno sigue como comentario de su post.
- 👤 Rojos y cuotazas: solo con «✅ Publicar» de Marcos.
- 👤 Si la combi nunca se publicó (captura de Marcos), el verde no lleva «¿Quién la llevaba?».

- ⚙️ **Resumen de la noche (23:15): nunca los fallados** (13/11: «queda muy feo»). Solo cuántos picks en verde, los
  picks sueltos aparte («8 de 11 acertados») y los números solo si son buenos (≥ 60 %), con la lista de los verdes y
  su cuota. Con menos de 3 verdes, no sale.

## 9. Escalera
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
