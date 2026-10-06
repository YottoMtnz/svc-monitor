import asyncio
import random
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError

import os
API_ID = int(os.environ.get('TG_API_ID', '26515897'))
API_HASH = os.environ.get('TG_API_HASH', 'e0c12dceb88a371cc12d7ba9fddc0320')
BOT_TOKEN = os.environ.get('TOKEN_B', '')

CANAL_PRINCIPAL = -1003980747672

# 🔐 Lista de IDs de administradores autorizados.
ADMINS = [6161812537, 0] 

bot = TelegramClient('bot_session', API_ID, API_HASH)

solicitudes_pendientes = {}

@bot.on(events.NewMessage(pattern=r'/start game_(\d+)', func=lambda e: e.is_private))
async def handler_solicitud(event):
    user_id = event.sender_id
    game_id = int(event.pattern_match.group(1))
    
    codigo_secreto = str(random.randint(100000, 999999))
    
    solicitudes_pendientes[user_id] = {
        'game_id': game_id,
        'codigo': codigo_secreto
    }
    
    await event.respond(
        "🔒 Solicitud de juego recibida\n\n"
        "Solicite el codigo de descarga necesario al Administrador.\n"
        "Por favor, introduce el Código aquí para liberar tu descarga:"
    )
    
    # 🚨 Notificar a TODOS los administradores en la lista
    username_usuario = event.sender.username or event.sender.first_name
    alerta_admin = (
        f"🔔 NUEVA SOLICITUD DE DESCARGA\n\n"
        f"👤 Usuario: @{username_usuario} (ID: {user_id})\n"
        f"🎮 ID del Juego: {game_id}\n"
        f"🔑 Código: {codigo_secreto}"
    )
    
    for admin_id in ADMINS:
        if admin_id != 0:
            try:
                await bot.send_message(admin_id, alerta_admin)
            except Exception as e:
                print(f"No pude enviar alerta al admin {admin_id}: {e}")

@bot.on(events.NewMessage(func=lambda e: e.is_private and not e.text.startswith('/')))
async def verificar_codigo(event):
    user_id = event.sender_id
    texto_usuario = event.raw_text.strip()
    
    if user_id in solicitudes_pendientes:
        datos_solicitud = solicitudes_pendientes[user_id]
        codigo_correcto = datos_solicitud['codigo']
        game_id = datos_solicitud['game_id']
        
        if texto_usuario == codigo_correcto:
            del solicitudes_pendientes[user_id]
            
            msg_estado = await event.respond("✅ ¡Código verificado con éxito! Liberando descarga...")
            
            try:
                archivos_a_enviar = []
                current_id = game_id
                buscando = True
                
                while buscando:
                    ids_a_buscar = list(range(current_id, current_id + 40))
                    mensajes_obtenidos = await bot.get_messages(CANAL_PRINCIPAL, ids=ids_a_buscar)
                    
                    mensajes_validos = [m for m in mensajes_obtenidos if m]
                    if not mensajes_validos:
                        break

                    for msg in mensajes_validos:
                        if msg.id == game_id:
                            archivos_a_enviar.append(msg)
                            continue
                            
                        if msg.text and not msg.document and msg.id != game_id:
                            buscando = False
                            break
                            
                        if msg.document:
                            archivos_a_enviar.append(msg)
                            
                    current_id += 40

                if len(archivos_a_enviar) <= 1:
                    await msg_estado.edit("❌ Encontré el post, peor no veo archivos debajo de él.")
                    return

                total_partes = len(archivos_a_enviar) - 1
                await msg_estado.edit(f"📦 Enviando las {total_partes} partes del juego...")
                
                for msg in archivos_a_enviar:
                    await bot.send_message(event.chat_id, msg)
                await asyncio.sleep(2) 
                    
                await event.respond("🎮 ¡Todo listo! Disfruta del Juego.")
                
            except Exception as e:
                await msg_estado.edit(f"⚠️ Ocurrió un error técnico: {str(e)}")
                
        else:
            await event.respond("❌ Código incorrecto. Inténtalo de nuevo.")
    else:
        pass

@bot.on(events.NewMessage(pattern='/start$', func=lambda e: e.is_private))
async def start_normal(event):
    await event.respond("¡Hola! Por favor, usa los enlaces del canal de catálogo para solicitar un juego.")

async def main():
    print("Bot de Seguridad OTP iniciado. Esperando solicitudes...")
    while True:
        try:
            await bot.start(bot_token=BOT_TOKEN)
            await bot.run_until_disconnected()
        except (ConnectionError, OSError, Exception) as e:
            # Capturamos cualquier error de red o de desconexión y lo hacemos paciente
            print(f"\n[AVISO] Sin conexión a internet o error de red ({e}). Reintentando en 10 segundos...")
            await asyncio.sleep(10)

if __name__ == '__main__':
    asyncio.run(main())