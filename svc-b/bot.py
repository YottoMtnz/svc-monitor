#!/usr/bin/env python3
"""Service monitor B. Usa Telegram Bot HTTP API."""
import time, random, os
import requests

BOT_TOKEN = os.environ.get('TOKEN_B', '')
API = f'https://api.telegram.org/bot{BOT_TOKEN}'
CANAL_PRINCIPAL = -1003980747672
ADMINS = [6161812537, 0]

solicitudes = {}  # chat_id -> {codigo: game_id}
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
    if chat_id not in solicitudes:
        solicitudes[chat_id] = {}
    solicitudes[chat_id][codigo] = game_id
    send(chat_id, "🔒 Solicitud recibida\n\nSe requiere un Código de Autorización.\nPor favor, introduce el Código aquí:")
    username = user.get('username') or user.get('first_name', '?')
    alerta = (f"🔔 NUEVA SOLICITUD\n\n👤 Usuario: @{username} (ID: {user['id']})\n🎮 ID: {game_id}\n🔑 Código: {codigo}")
    for admin_id in ADMINS:
        if admin_id != 0:
            try: send(admin_id, alerta)
            except Exception as e: print(f'Error admin {admin_id}: {e}')

def es_documento(result_msg):
    """Verifica si el mensaje copiado es un documento (parte del juego)."""
    if not result_msg: return False
    # Si tiene documento, es parte del juego
    if 'document' in result_msg: return True
    # Si tiene texto pero no documento, es delimitador -> parar
    if 'text' in result_msg or 'caption' in result_msg:
        # Los documentos pueden tener caption, pero el mensaje original del juego
        # también puede ser texto. El original paraba en texto sin documento.
        return 'document' in result_msg
    return False

def handle_codigo(chat_id, texto):
    if chat_id not in solicitudes: return
    codigo_ingresado = texto.strip()
    if codigo_ingresado not in solicitudes[chat_id]: 
        # Código no coincide con ninguna solicitud pendiente
        return
    game_id = solicitudes[chat_id].pop(codigo_ingresado)
    if not solicitudes[chat_id]:
        del solicitudes[chat_id]
    
    msg = send(chat_id, "✅ ¡Código verificado! Procesando...")
    msg_id = (msg.get('result') or {}).get('message_id')
    
    archivos = []
    current = game_id
    # Copiar el mensaje inicial
    r = api('copyMessage', chat_id=chat_id, from_chat_id=CANAL_PRINCIPAL, message_id=current)
    if not r.get('ok'):
        edit(chat_id, msg_id, "❌ No encontrado.")
        return
    result_msg = r.get('result', {})
    archivos.append(current)
    current += 1
    
    # Seguir copiando mientras sean documentos (parar en texto delimitador)
    for _ in range(60):
        r = api('copyMessage', chat_id=chat_id, from_chat_id=CANAL_PRINCIPAL, message_id=current)
        if not r.get('ok'):
            break
        result_msg = r.get('result', {})
        # Si es texto sin documento, es delimitador -> parar (lógica original)
        if not es_documento(result_msg):
            # Borrar el mensaje delimitador que acabamos de copiar por error
            try:
                api('deleteMessage', chat_id=chat_id, message_id=result_msg.get('message_id'))
            except: pass
            break
        archivos.append(current)
        current += 1
        time.sleep(0.5)
    
    if len(archivos) <= 0:
        edit(chat_id, msg_id, "❌ Sin archivos.")
        return
    edit(chat_id, msg_id, f"📦 Enviadas {len(archivos)} partes...")
    time.sleep(1)
    send(chat_id, "✅ ¡Listo!")

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
