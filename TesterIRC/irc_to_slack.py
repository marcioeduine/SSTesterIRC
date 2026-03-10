#!/usr/bin/env python3

import socket
import requests
import time
import re
import threading

TOKENS = ["SLACK_TOKEN_REMOVED", "SLACK_TOKEN_REMOVED"]

IDS = ["C0AF7G2KABE", "#ss_irc"]

# ===== CONFIGURAÇÃO =====
IRC_SERVER = "localhost"
IRC_PORT = 6667
IRC_PASSWORD = "senha"
IRC_NICK = "SSBot"
IRC_CHANNELS = ["#ss_irc"]
SLACK_TOKEN = TOKENS[1]
SLACK_CHANNEL_ID = IDS[0]
SLACK_CHANNEL_NAME = "ss_irc"
# ========================

LAST_SLACK_TS = time.time()

def send_to_slack(message):
    """Envia mensagem do IRC para o Slack"""
    try:
        requests.post(
            'https://slack.com/api/chat.postMessage',
            headers={'Authorization': f'Bearer {SLACK_TOKEN}'},
            json={'channel': SLACK_CHANNEL_ID, 'text': message}
        )
    except Exception as e:
        print(f"Erro ao enviar para Slack: {e}")

def listen_slack(irc_socket):
    global LAST_SLACK_TS
    # Inicializa com o tempo actual menos um pequeno buffer
    LAST_SLACK_TS = str(time.time() - 10)
    print(f"📡 Monitorização activa em: {SLACK_CHANNEL_ID}")
    
    while True:
        try:
            response = requests.get(
                'https://slack.com/api/conversations.history',
                headers={'Authorization': f'Bearer {SLACK_TOKEN}'},
                params={
                    'channel': SLACK_CHANNEL_ID, 
                    'oldest': LAST_SLACK_TS,
                    'inclusive': False,
                    'limit': 10
                }
            )
            data = response.json()
            
            if data.get('ok'):
                messages = data.get('messages', [])
                for msg in reversed(messages):
                    msg_ts = msg['ts']
                    
                    # Filtro: tem de ser mensagem de texto e ter um utilizador humano
                    if 'text' in msg and 'user' in msg and 'bot_id' not in msg:
                        user = msg['user']
                        text = msg['text']
                        
                        # Envia para o IRC
                        irc_line = f"PRIVMSG {IRC_CHANNELS[0]} :[Slack] <{user}> {text}\r\n"
                        irc_socket.send(irc_line.encode())
                        print(f"➡️ [Slack -> IRC]: <{user}> {text}")
                    
                    # Actualiza o cursor para a próxima consulta
                    LAST_SLACK_TS = msg_ts
            else:
                error = data.get('error')
                print(f"❌ Erro na API do Slack: {error}")
                if error == 'not_in_channel':
                    print("💡 Convida o bot: /invite @Nome_Do_Bot")
                elif error == 'missing_scope':
                    print("💡 Reinstala a App após adicionar 'groups:history'.")

        except Exception as e:
            print(f"⚠️ Erro na Thread Slack: {e}")
        
        time.sleep(3)

def connect_irc():
    """Conecta ao servidor IRC"""
    irc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    irc.connect((IRC_SERVER, IRC_PORT))
    irc.send(f"PASS {IRC_PASSWORD}\r\n".encode())
    irc.send(f"NICK {IRC_NICK}\r\n".encode())
    irc.send(f"USER {IRC_NICK} 0 * :SS Slack Bot\r\n".encode())
    return irc

def main():
    print("🚀 A Iniciar Ponte Bidireccional IRC ↔ Slack...")
    irc = connect_irc()
    time.sleep(2)
    
    for channel in IRC_CHANNELS:
        irc.send(f"JOIN {channel}\r\n".encode())
        print(f"✅ Entrou no canal {channel}")

    # Inicia a thread que escuta o Slack
    slack_thread = threading.Thread(target=listen_slack, args=(irc,), daemon=True)
    slack_thread.start()

    print("📡 A monitorar ambas as plataformas... (Ctrl+C para parar)")
    
    buffer = ""
    while True:
        try:
            data = irc.recv(4096).decode('utf-8', errors='ignore')
            if not data: break
            buffer += data
            while '\r\n' in buffer:
                line, buffer = buffer.split('\r\n', 1)
                
                if line.startswith('PING'):
                    irc.send(f"PONG {line.split()[1]}\r\n".encode())
                    continue
                
                # Regex para capturar mensagens do IRC
                match = re.match(r':(.+?)!.+ PRIVMSG (#\S+) :(.+)', line)
                if match:
                    nick, channel, msg = match.groups()
                    # Ignora se a mensagem veio do próprio bot via prefixo [Slack]
                    if not msg.startswith("[Slack]"):
                        slack_msg = f"**[{channel}]** `{nick}`: {msg}"
                        print(f"⬅️ [IRC -> Slack]: {slack_msg}")
                        send_to_slack(slack_msg)
                        
        except KeyboardInterrupt:
            print("\n👋 A desligar...")
            break
        except Exception as e:
            print(f"❌ Erro IRC: {e}")
            time.sleep(5)
            irc = connect_irc()

if __name__ == "__main__":
    main()
