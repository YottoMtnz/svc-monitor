#!/usr/bin/env python3
"""Service monitor B. Usa Telegram Bot HTTP API."""
import time, random, os
import requests

BOT_TOKEN = os.environ.get('TOKEN_B', '')
API = f'https://api.telegram.org/bot{BOT_TOKEN}'
CANAL_PRINCIPAL = -1003980747672
ADMINS = [6161812537, 0]

solicitudes = {}
offset = 0

def api(method, **params):
    try:
        r = requests.post(f'{API}/{method}', json=params, timeout=30)
        return r.json()
    except Exception as e:
        print(f'API error {method}: {e}')
        return {}

def send(chat_id, text):
    return api('sendMessage', chat_id=chat_id, text=text)

def edit(chat_id, msg_id, text):
    if msg_id:
        api('editMessageText', chat_id=chat_id, message_id=msg_id, text=text)

def handle_start_game(chat_id, user, game_id):
    codigo = str(random.randint(100000, 999999))
    solicitudes[chat_id] = {'game_id': game_id, 'codigo': codigo}
    send(chat_id, "🔒 Solicitud recibida\n\nSe requiere un Código de Autorización.\nPor favor, introduce el Código aquí:")
    username = user.get('username') or user.get('first_name', '?')
    alerta = (f"🔔 NUEVA SOLICITUD\n\n👤 Usuario: @{username} (ID: {user['id']})\n🎮 ID: {game_id}\n🔑 Código: {codigo}")
    for admin_id in ADMINS:
        if admin_id != 0:
            try: send(admin_id, alerta)
            except Exception as e: print(f'Error admin {admin_id}: {e}')

def tiene_media(result_msg):
    """True si el mensaje tiene cualquier tipo de archivo (doc, foto, video, audio)."""
    if not result_msg: return False
    for campo in ('document', 'photo', 'video', 'audio', 'voice', 'video_note', 'animation'):
        if campo in result_msg:
            return True
    return False

def es_delimitador(result_msg):
    """True si es texto puro sin ningún archivo (marca fin del juego)."""
    if not result_msg: return True
    if tiene_media(result_msg): return False
    # Texto sin media = delimitador
    return True

def handle_codigo(chat_id, texto):
    if chat_id not in solicitudes: return
    datos = solicitudes[chat_id]
    if texto.strip() == datos['codigo']:
        del solicitudes[chat_id]
        game_id = datos['game_id']
        msg = send(chat_id, "✅ ¡Código verificado! Procesando...")
        msg_id = (msg.get('result') or {}).get('message_id')
        copiados = 0
        current = game_id
        r = api('copyMessage', chat_id=chat_id, from_chat_id=CANAL_PRINCIPAL, message_id=current)
        if not r.get('ok'):
            edit(chat_id, msg_id, "❌ No encontrado.")
            return
        copiados += 1; current += 1
        for _ in range(60):
            r = api('copyMessage', chat_id=chat_id, from_chat_id=CANAL_PRINCIPAL, message_id=current)
            if not r.get('ok'): break
            result_msg = r.get('result', {})
            if es_delimitador(result_msg):
                try:
                    api('deleteMessage', chat_id=chat_id, message_id=result_msg.get('message_id'))
                except: pass
                break
            copiados += 1; current += 1
            time.sleep(0.5)
        if copiados <= 1:
            edit(chat_id, msg_id, "❌ Sin archivos.")
            return
        edit(chat_id, msg_id, f"📦 Enviadas {copiados-1} partes...")
        time.sleep(1)
        send(chat_id, "✅ ¡Listo!")
    else:
        send(chat_id, "❌ Código incorrecto.")

def main():
    global offset
    if not BOT_TOKEN:
        print("ERROR: TOKEN_B no configurado")
        return
    print("Bot B iniciado.")
    while True:
        try:
            d = api('getUpdates', offset=offset, timeout=25)
            for u in d.get('result', []):
                offset = u['update_id'] + 1
                msg = u.get('message')
                if not msg or msg.get('chat', {}).get('type') != 'private': continue
                chat_id = msg['chat']['id']
                texto = msg.get('text', '')
                user = msg.get('from', {})
                if texto.startswith('/start game_'):
                    try: handle_start_game(chat_id, user, int(texto.split('game_')[1].split()[0]))
                    except ValueError: pass
                elif texto == '/start':
                    send(chat_id, "Hola. Usa los enlaces del canal para solicitar.")
                elif not texto.startswith('/'):
                    handle_codigo(chat_id, texto)
        except Exception as e:
            print(f'[AVISO] {e}. Reintentando...')
            time.sleep(10)

if __name__ == '__main__':
    main()
