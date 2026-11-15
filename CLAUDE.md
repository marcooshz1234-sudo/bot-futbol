# CLAUDE.md · Léelo antes de hacer nada

Proyecto **@combilocas** de Marcos: bot de pronósticos de fútbol (Telegram, Threads, Instagram) en este repo.

## Al empezar CUALQUIER sesión (en este orden)
1. `git pull` y lee **`REGLAS.md`**: todas las normas de Marcos al día. Si algo choca con otra cosa, manda REGLAS.md.
2. **`MANUAL_PROYECTO.md`**: qué es cada pieza y cómo funciona.
3. El final de **`informes/bitacora/AAAA-MM.md`** (mes actual): lo que se ha hecho y lo pendiente de los últimos días.
4. Si el Mac de Marcos está enlazado: su bóveda de Obsidian «Combilocas» (iCloud) → `00 Inicio/Pendientes.md` y la
   última nota de `05 Diario/`. Es una copia para él; la verdad está en este repo.

## Cómo trabajar con Marcos (resumen; el detalle en REGLAS.md)
- Español, corto, con tablas; a menudo escribe desde el móvil.
- **Enseñar antes de subir**: nada nuevo se publica ni se cambia en el estilo sin que lo vea. Arreglos pequeños sí, con test.
- **«Arreglado» = no vuelve a pasar**: cada arreglo lleva su test en `tests/` y una línea en la bitácora.
- Nunca decir que algo está hecho sin comprobarlo. Nunca pedir, ver ni pegar tokens o contraseñas (las pone él).
- Nunca borrar publicaciones ni editar un post de Telegram ya publicado. bet365 solo lectura.
- Lo que Marcos tenga que abrir o hacer él, en su **Escritorio**.
- Antes de commit: `timeout 300 python3 -m unittest discover -s tests` y `node tests/test_panel.cjs`.
  Push: `for i in 1 2 3 4; do git pull -q --rebase --autostash -X theirs; git push -q && break; sleep 10; done`.

## Al acabar
Una línea por cambio en la bitácora del mes (qué y por qué) y, si es una norma nueva de Marcos, en `REGLAS.md`
(y su copia en el proyecto de claude.ai: `claude/REGLAS_NOVIEMBRE.md`).
