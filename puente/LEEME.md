# Puente (Mac)

Une **El Analista** (este repo), **El Bot Asesor** (Ollama `qwen3.5:9b` en el Mac) y **El Publicador** (cola de Telegram).

- Se instala con `Instalar puente.command` (en la carpeta `combis` del escritorio): doble clic.
- Funciona solo cada hora mientras el Mac esté encendido (launchd: `com.combilocas.puente`).
- Borradores: `~/Combilocas/Borradores/AAAA-MM-DD.md`. Marca `[x]` para publicar; puedes editar el texto.
- Registro: `~/Combilocas/puente.log`.
- Para lanzarlo al momento: `Puente ahora.command`.
- Si el Asesor está apagado o se inventa un número, se usa la frase del código.
