"""
10/11 (Marcos): lo ejecutas TÚ UNA VEZ en tu ordenador para conectar el lector de canales con tu cuenta de Telegram.
Nadie más ve la clave: la pegas tú en GitHub. Pasos:

  1) En la Terminal:   pip3 install telethon
  2) Luego:            python3 sesion_telegram.py
  3) Te pide api_id y api_hash (de my.telegram.org), tu teléfono y el código que te llega a Telegram
     (y tu contraseña de verificación en dos pasos, si la tienes).
  4) Al final imprime una línea larga (la «sesión»). Cópiala y pégala en GitHub como secreto TG_SESSION.
     NO se la mandes a nadie: con ella se puede leer tu Telegram.
"""
from telethon.sessions import StringSession
from telethon.sync import TelegramClient

api_id = int(input("api_id: ").strip())
api_hash = input("api_hash: ").strip()
with TelegramClient(StringSession(), api_id, api_hash) as cliente:
    print("\nConectado como:", cliente.get_me().first_name)
    print("\nCopia esta línea entera y pégala en GitHub (secreto TG_SESSION):\n")
    print(cliente.session.save())
