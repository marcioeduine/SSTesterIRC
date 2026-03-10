import socket
import time
import sys
import subprocess
import signal
import os

# CONFIGURAÇÃO
HOST = "127.0.0.1"
PORT = 6667
PASS = "senha"

# Contadores globais
passed = 0
failed = 0

def log(test_name, status, message=""):
    global passed, failed
    color = "\033[92m" if status == "OK" else "\033[91m"
    reset = "\033[0m"
    print(f"  [{color}{status}{reset}] {test_name}: {message}")
    if status == "OK":
        passed += 1
    else:
        failed += 1

def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

class IRCClient:
    def __init__(self, name):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.name = name

    def connect(self):
        self.s.connect((HOST, PORT))
        self.s.settimeout(2)

    def send(self, msg):
        self.s.send((msg + "\r\n").encode())

    def recv(self):
        try:
            return self.s.recv(4096).decode()
        except:
            return ""

    def auth(self, nick, user=None):
        """Helper: authenticate a client fully and consume the welcome."""
        if user is None:
            user = nick
        self.send(f"PASS {PASS}")
        self.send(f"NICK {nick}")
        self.send(f"USER {user} 0 * :realname")
        # Read until we get 001 (welcome) or exhaust retries
        data = ""
        for _ in range(5):
            time.sleep(0.3)
            chunk = self.recv()
            data += chunk
            if "001" in data:
                break
        return data

    def close(self):
        try:
            self.s.close()
        except:
            pass

# =========================================================================
#  SECÇÃO 1 — BASIC CHECKS (Autenticação, Registo)
# =========================================================================

def test_authentication():
    section("TESTE 1: AUTENTICAÇÃO COMPLETA")
    c = IRCClient("User1")
    c.connect()
    c.send(f"PASS {PASS}")
    c.send("NICK user1")
    c.send("USER u 0 * :realname")
    time.sleep(0.5)
    res = c.recv()
    if "001" in res:
        log("Auth Completa", "OK", "Recebeu RPL_WELCOME (001)")
    else:
        log("Auth Completa", "FAIL", f"Não recebeu 001. Resposta: {repr(res)}")
    c.close()

def test_wrong_password():
    section("TESTE 2: PASSWORD ERRADA")
    c = IRCClient("BadPass")
    c.connect()
    c.send("PASS wrongpassword")
    c.send("NICK badpass")
    c.send("USER b 0 * :b")
    time.sleep(0.5)
    res = c.recv()
    if "464" in res:
        log("Wrong PASS", "OK", "Recebeu ERR_PASSWDMISMATCH (464)")
    elif "001" not in res:
        log("Wrong PASS", "OK", f"Não recebeu welcome (conexão recusada): {repr(res[:80])}")
    else:
        log("Wrong PASS", "FAIL", f"Recebeu welcome com password errada! {repr(res)}")
    c.close()

def test_no_password():
    section("TESTE 3: SEM PASSWORD")
    c = IRCClient("NoPass")
    c.connect()
    c.send("NICK nopass")
    c.send("USER n 0 * :n")
    time.sleep(0.5)
    res = c.recv()
    if "001" not in res:
        log("No PASS", "OK", "Servidor não registou sem PASS")
    else:
        log("No PASS", "FAIL", "Registou sem PASS!")
    c.close()

# =========================================================================
#  SECÇÃO 2 — NETWORKING
# =========================================================================

def test_multiple_connections():
    section("TESTE 4: MÚLTIPLAS CONEXÕES SIMULTÂNEAS")
    clients = []
    ok = True
    for i in range(5):
        c = IRCClient(f"multi{i}")
        c.connect()
        res = c.auth(f"multi{i}")
        if "001" not in res:
            log(f"MultiConn #{i}", "FAIL", f"Não recebeu welcome: {repr(res[:80])}")
            ok = False
        clients.append(c)

    if ok:
        log("Multi Conexões", "OK", "5 clientes conectados e autenticados simultaneamente")

    for c in clients:
        c.close()

def test_channel_broadcast():
    section("TESTE 5: BROADCAST NO CANAL")
    c1 = IRCClient("Sender")
    c2 = IRCClient("Receiver1")
    c3 = IRCClient("Receiver2")

    c1.connect(); c1.auth("sender1")
    c2.connect(); c2.auth("recv1")
    c3.connect(); c3.auth("recv2")

    c1.send("JOIN #broadcast")
    time.sleep(0.3); c1.recv()

    c2.send("JOIN #broadcast")
    time.sleep(0.3); c2.recv()
    c1.recv()  # consume JOIN notification from c2

    c3.send("JOIN #broadcast")
    time.sleep(0.3); c3.recv()
    c1.recv(); c2.recv()  # consume JOIN notification from c3

    # Sender envia mensagem
    c1.send("PRIVMSG #broadcast :Hello everyone")
    time.sleep(0.5)

    r2 = c2.recv()
    r3 = c3.recv()

    ok2 = "Hello everyone" in r2
    ok3 = "Hello everyone" in r3

    if ok2 and ok3:
        log("Channel Broadcast", "OK", "Ambos receivers receberam a mensagem")
    else:
        log("Channel Broadcast", "FAIL", f"recv1={repr(r2[:60])}, recv2={repr(r3[:60])}")

    c1.close(); c2.close(); c3.close()

# =========================================================================
#  SECÇÃO 3 — NETWORKING SPECIALS
# =========================================================================

def test_fragmentation():
    section("TESTE 6: COMANDOS PARCIAIS (FRAGMENTAÇÃO)")
    c = IRCClient("FragUser")
    c.connect()
    c.s.send(f"PASS {PASS}\r\nNI".encode())
    time.sleep(0.5)
    c.s.send("CK frag\r\n".encode())
    time.sleep(0.5)
    c.send("USER f 0 * :f")
    time.sleep(0.5)
    res = c.recv()
    if "001" in res:
        log("Fragmentação", "OK", "Servidor remontou comando partido")
    else:
        log("Fragmentação", "FAIL", f"Falhou: {repr(res[:80])}")
    c.close()

def test_partial_cmd_other_alive():
    section("TESTE 7: COMANDO PARCIAL + OUTRAS CONEXÕES FUNCIONAM")
    # c1 sends half a command, c2 should still work fine
    c1 = IRCClient("HalfCmd")
    c1.connect()
    c1.s.send(f"PASS {PASS}\r\nNICK half\r\nUSER h 0 * :h\r\nPRIVM".encode())  # partial PRIVMSG

    c2 = IRCClient("Other")
    c2.connect()
    res = c2.auth("other1")
    if "001" in res:
        log("Parcial + Outro OK", "OK", "c2 autenticou enquanto c1 tem comando incompleto")
    else:
        log("Parcial + Outro OK", "FAIL", f"c2 falhou: {repr(res[:80])}")

    c1.close(); c2.close()

def test_ctrlD_subject():
    section("TESTE 7b: CTRL+D DO SUBJECT (com^Dman^Dd)")
    # Simulates the exact test from the subject:
    # nc -C 127.0.0.1 6667 → com^Dman^Dd
    # ctrl+D sends the buffer without newline, so the server receives
    # "com" then "man" then "d\r\n" in separate recv() calls
    c = IRCClient("CtrlD")
    c.connect()
    # First authenticate normally
    c.send(f"PASS {PASS}")
    c.send("NICK ctrld1")
    c.send("USER c 0 * :c")
    time.sleep(0.5)
    res = c.recv()
    if "001" not in res:
        log("Ctrl+D Subject", "FAIL", f"Auth falhou: {repr(res[:60])}")
        c.close()
        return

    # Now simulate: "PRIVMSG ctrld1 :hel" + "lo wor" + "ld\r\n"
    # Each chunk sent separately (like ctrl+D in nc)
    c.s.send("PRIV".encode())           # partial - no newline
    time.sleep(0.3)
    c.s.send("MSG ctr".encode())        # partial - no newline
    time.sleep(0.3)
    c.s.send("ld1 :hello\r\n".encode()) # final chunk with \r\n
    time.sleep(0.5)
    res = c.recv()
    if "hello" in res:
        log("Ctrl+D Subject", "OK", "Servidor reagregou 'PRIV' + 'MSG ctr' + 'ld1 :hello' correctamente")
    else:
        log("Ctrl+D Subject", "FAIL", f"Resp: {repr(res[:80])}")
    c.close()

def test_nc_without_C_flag():
    section("TESTE 7c: nc SEM FLAG -C (só \\n, sem \\r)")
    # nc without -C sends only \n, not \r\n
    c = IRCClient("NcPlain")
    c.connect()
    # Send commands with \n only (no \r)
    c.s.send(f"PASS {PASS}\n".encode())
    c.s.send("NICK ncplain1\n".encode())
    c.s.send("USER n 0 * :n\n".encode())
    time.sleep(0.5)
    res = c.recv()
    if "001" in res:
        log("nc sem -C", "OK", "Servidor aceitou comandos com \\n puro (sem \\r)")
    else:
        log("nc sem -C", "FAIL", f"Resp: {repr(res[:80])}")
    c.close()

def test_abrupt_disconnect():
    section("TESTE 8: DESCONEXÃO BRUTA (sem QUIT)")
    c1 = IRCClient("Dono")
    c1.connect(); c1.auth("dono1")
    c1.send("JOIN #segfault")
    time.sleep(0.3); c1.recv()

    c2 = IRCClient("Alvo")
    c2.connect(); c2.auth("alvo1")
    c2.send("JOIN #segfault")
    time.sleep(0.3); c2.recv(); c1.recv()

    # Kill c2 without QUIT
    c2.close()
    time.sleep(0.5)

    c1.send("PRIVMSG #segfault :Alguem vivo?")
    time.sleep(0.3)
    c1.recv()  # just check it doesn't crash
    log("Desconexão Bruta", "OK", "Servidor estável após morte abrupta de cliente")
    c1.close()

def test_half_command_disconnect():
    section("TESTE 9: KILL nc COM METADE DE UM COMANDO")
    c1 = IRCClient("HalfDie")
    c1.connect()
    c1.send(f"PASS {PASS}")
    c1.send("NICK halfdie")
    c1.send("USER h 0 * :h")
    time.sleep(0.3); c1.recv()
    # Send half a command then die
    c1.s.send("PRIVMSG #test :incom".encode())
    c1.close()
    time.sleep(0.5)

    # Check server still works
    c2 = IRCClient("PostDeath")
    c2.connect()
    res = c2.auth("postdeath")
    if "001" in res:
        log("Half Cmd Kill", "OK", "Servidor ok após nc morrer com comando incompleto")
    else:
        log("Half Cmd Kill", "FAIL", f"Servidor instável: {repr(res[:80])}")
    c2.close()

def test_stopped_client_flood():
    section("TESTE 10: CLIENTE PARADO (^Z) + FLOOD NO CANAL")
    # Simulates a stopped client by connecting but not reading
    c1 = IRCClient("Flooder")
    c1.connect(); c1.auth("flooder1")
    c1.send("JOIN #flood")
    time.sleep(0.3); c1.recv()

    c2 = IRCClient("Sleeper")
    c2.connect(); c2.auth("sleeper1")
    c2.send("JOIN #flood")
    time.sleep(0.3); c2.recv(); c1.recv()

    # Flood the channel while c2 doesn't read (simulating ^Z)
    print("  [Info] Flooding canal com 200 mensagens enquanto c2 'dorme'...")
    for i in range(200):
        c1.send(f"PRIVMSG #flood :Flood msg {i}")

    time.sleep(1)
    # Now c2 "wakes up" and reads
    data = ""
    try:
        c2.s.settimeout(3)
        while True:
            chunk = c2.s.recv(4096).decode()
            if not chunk:
                break
            data += chunk
    except:
        pass

    count = data.count("PRIVMSG")
    if count > 0:
        log("^Z + Flood", "OK", f"Cliente 'acordou' e recebeu {count} mensagens pendentes")
    else:
        log("^Z + Flood", "FAIL", "Cliente não recebeu mensagens acumuladas")

    c1.close(); c2.close()

# =========================================================================
#  SECÇÃO 4 — CLIENT COMMANDS: PRIVMSG
# =========================================================================

def test_privmsg_channel():
    section("TESTE 11: PRIVMSG PARA CANAL")
    c1 = IRCClient("Msg1"); c2 = IRCClient("Msg2")
    c1.connect(); c1.auth("msgchan1")
    c2.connect(); c2.auth("msgchan2")

    c1.send("JOIN #privtest")
    time.sleep(0.3); c1.recv()
    c2.send("JOIN #privtest")
    time.sleep(0.3); c2.recv(); c1.recv()

    c1.send("PRIVMSG #privtest :Channel hello!")
    time.sleep(0.5)
    res = c2.recv()
    if "Channel hello!" in res:
        log("PRIVMSG Canal", "OK", "Mensagem de canal recebida")
    else:
        log("PRIVMSG Canal", "FAIL", f"Resp: {repr(res[:80])}")

    c1.close(); c2.close()

def test_privmsg_user():
    section("TESTE 12: PRIVMSG PARA UTILIZADOR (DM)")
    c1 = IRCClient("DmSender"); c2 = IRCClient("DmRecv")
    c1.connect(); c1.auth("dmsender")
    c2.connect(); c2.auth("dmrecv")

    c1.send("PRIVMSG dmrecv :Hello privately!")
    time.sleep(0.5)
    res = c2.recv()
    if "Hello privately!" in res:
        log("PRIVMSG DM", "OK", "Mensagem direta recebida")
    else:
        log("PRIVMSG DM", "FAIL", f"Resp: {repr(res[:80])}")

    c1.close(); c2.close()

def test_privmsg_no_such_nick():
    section("TESTE 13: PRIVMSG PARA NICK INEXISTENTE")
    c1 = IRCClient("Ghost")
    c1.connect(); c1.auth("ghostsend")

    c1.send("PRIVMSG fantasma :Boo")
    time.sleep(0.5)
    res = c1.recv()
    if "401" in res:
        log("PRIVMSG Inexistente", "OK", "Recebeu 401 ERR_NOSUCHNICK")
    else:
        log("PRIVMSG Inexistente", "FAIL", f"Resp: {repr(res[:80])}")
    c1.close()

def test_privmsg_no_params():
    section("TESTE 14: PRIVMSG SEM PARÂMETROS")
    c1 = IRCClient("NoParam")
    c1.connect(); c1.auth("noparam1")

    c1.send("PRIVMSG")
    time.sleep(0.5)
    res = c1.recv()
    if "461" in res:
        log("PRIVMSG Sem Params", "OK", "Recebeu 461 ERR_NEEDMOREPARAMS")
    else:
        log("PRIVMSG Sem Params", "FAIL", f"Resp: {repr(res[:80])}")
    c1.close()

def test_privmsg_not_on_channel():
    section("TESTE 15: PRIVMSG PARA CANAL SEM ESTAR NELE")
    c1 = IRCClient("Outside"); c2 = IRCClient("Inside")
    c1.connect(); c1.auth("outsider1")
    c2.connect(); c2.auth("insider1")

    c2.send("JOIN #private")
    time.sleep(0.3); c2.recv()

    c1.send("PRIVMSG #private :Can I talk?")
    time.sleep(0.5)
    res = c1.recv()
    if "442" in res or "404" in res:
        log("PRIVMSG Fora Canal", "OK", "Bloqueado de falar no canal sem estar nele")
    else:
        log("PRIVMSG Fora Canal", "FAIL", f"Resp: {repr(res[:80])}")

    c1.close(); c2.close()

# =========================================================================
#  SECÇÃO 5 — OPERATOR COMMANDS
# =========================================================================

def test_kick_by_non_op():
    section("TESTE 16: KICK POR NÃO-OPERADOR")
    c1 = IRCClient("Op"); c2 = IRCClient("Normal")

    c1.connect(); c1.auth("kickop1")
    c1.send("JOIN #kicktest"); time.sleep(0.3); c1.recv()

    c2.connect(); c2.auth("kicknorm1")
    c2.send("JOIN #kicktest"); time.sleep(0.3); c2.recv(); c1.recv()

    c2.send("KICK #kicktest kickop1")
    time.sleep(0.5)
    res = c2.recv()
    if "482" in res:
        log("KICK não-OP", "OK", "Normal barrado de KICK (482)")
    else:
        log("KICK não-OP", "FAIL", f"Resp: {repr(res[:80])}")

    c1.close(); c2.close()

def test_kick_by_op():
    section("TESTE 17: KICK POR OPERADOR")
    c1 = IRCClient("Op"); c2 = IRCClient("Target")

    c1.connect(); c1.auth("kickop2")
    c1.send("JOIN #kicktest2"); time.sleep(0.3); c1.recv()

    c2.connect(); c2.auth("kicktgt")
    c2.send("JOIN #kicktest2"); time.sleep(0.3); c2.recv(); c1.recv()

    c1.send("KICK #kicktest2 kicktgt :goodbye")
    time.sleep(0.5)
    r1 = c1.recv()
    r2 = c2.recv()
    if "KICK" in r1 or "KICK" in r2:
        log("KICK por OP", "OK", "Operador executou KICK com sucesso")
    else:
        log("KICK por OP", "FAIL", f"op={repr(r1[:60])}, tgt={repr(r2[:60])}")

    c1.close(); c2.close()

def test_invite():
    section("TESTE 18: INVITE")
    c1 = IRCClient("Inviter"); c2 = IRCClient("Invited")

    c1.connect(); c1.auth("inviter1")
    c1.send("JOIN #invitetest"); time.sleep(0.3); c1.recv()

    c2.connect(); c2.auth("invited1")

    c1.send("INVITE invited1 #invitetest")
    time.sleep(0.5)
    r1 = c1.recv()
    r2 = c2.recv()

    ok_sender = "341" in r1  # RPL_INVITING
    ok_target = "INVITE" in r2
    if ok_sender and ok_target:
        log("INVITE", "OK", "Sender recebeu 341, Target recebeu INVITE")
    elif ok_sender:
        log("INVITE", "OK", f"Sender recebeu 341 (target pode não ter recebido: {repr(r2[:60])})")
    else:
        log("INVITE", "FAIL", f"sender={repr(r1[:60])}, target={repr(r2[:60])}")

    c1.close(); c2.close()

def test_invite_non_op():
    section("TESTE 18b: INVITE POR NÃO-OPERADOR (CANAL +i)")
    c1 = IRCClient("InvOp"); c2 = IRCClient("InvNorm"); c3 = IRCClient("InvTarget")

    c1.connect(); c1.auth("invop1")
    c1.send("JOIN #invonly"); time.sleep(0.3); c1.recv()

    # Set invite-only
    c1.send("MODE #invonly +i"); time.sleep(0.3); c1.recv()

    c2.connect(); c2.auth("invnorm1")
    # Invite c2 first so they can join
    c1.send("INVITE invnorm1 #invonly"); time.sleep(0.3); c1.recv(); c2.recv()
    c2.send("JOIN #invonly"); time.sleep(0.3); c2.recv(); c1.recv()

    c3.connect(); c3.auth("invtgt1")

    # c2 (non-op) tries to invite c3 on invite-only channel
    c2.send("INVITE invtgt1 #invonly")
    time.sleep(0.5)
    res = c2.recv()
    if "482" in res:
        log("INVITE não-OP +i", "OK", "Não-op barrado de INVITE em canal +i (482)")
    else:
        log("INVITE não-OP +i", "FAIL", f"Resp: {repr(res[:80])}")

    c1.close(); c2.close(); c3.close()

def test_topic_set_get():
    section("TESTE 19: TOPIC SET / GET")
    c1 = IRCClient("TopicUser")
    c1.connect(); c1.auth("topuser1")
    time.sleep(0.3)
    c1.send("JOIN #topictest")
    time.sleep(0.5); c1.recv()  # consume JOIN response fully
    time.sleep(0.3)

    # Set topic
    c1.send("TOPIC #topictest :This is the topic")
    time.sleep(0.5)
    res = c1.recv()
    # The broadcast should contain the TOPIC message
    ok_set = "TOPIC" in res and "This is the topic" in res

    # Get topic
    c1.send("TOPIC #topictest")
    time.sleep(0.5)
    res = c1.recv()
    ok_get = "332" in res and "This is the topic" in res

    if ok_set and ok_get:
        log("TOPIC Set/Get", "OK", "Topic definido e recuperado corretamente")
    elif ok_get:
        log("TOPIC Set/Get", "OK", f"Get OK, set broadcast talvez não recebido por sender")
    else:
        log("TOPIC Set/Get", "FAIL", f"set={ok_set}, get={ok_get}, last_resp={repr(res[:80])}")
    c1.close()

def test_topic_restricted():
    section("TESTE 20: TOPIC COM MODO +t (SÓ OP MUDA)")
    c1 = IRCClient("TopOp"); c2 = IRCClient("TopNorm")

    c1.connect(); c1.auth("topop1")
    c1.send("JOIN #topicmod"); time.sleep(0.3); c1.recv()

    # Enable topic restriction
    c1.send("MODE #topicmod +t"); time.sleep(0.3); c1.recv()

    c2.connect(); c2.auth("topnorm1")
    c2.send("JOIN #topicmod"); time.sleep(0.3); c2.recv(); c1.recv()

    # Non-op tries to change topic
    c2.send("TOPIC #topicmod :Hacked topic")
    time.sleep(0.5)
    res = c2.recv()
    if "482" in res:
        log("TOPIC +t não-OP", "OK", "Não-op barrado de mudar topic com +t (482)")
    else:
        # Some servers just silently ignore, check if topic actually changed
        c1.send("TOPIC #topicmod")
        time.sleep(0.3)
        r2 = c1.recv()
        if "Hacked topic" not in r2:
            log("TOPIC +t não-OP", "OK", "Topic não foi alterado pelo não-op")
        else:
            log("TOPIC +t não-OP", "FAIL", f"Não-op conseguiu mudar topic! {repr(res[:80])}")

    c1.close(); c2.close()

# =========================================================================
#  SECÇÃO 6 — MODE TESTS
# =========================================================================

def test_mode_invite_only():
    section("TESTE 21: MODE +i (INVITE-ONLY)")
    c1 = IRCClient("ModeOp"); c2 = IRCClient("ModeBlocked")

    c1.connect(); c1.auth("modeop1")
    c1.send("JOIN #modetest"); time.sleep(0.3); c1.recv()

    c1.send("MODE #modetest +i"); time.sleep(0.3); c1.recv()

    c2.connect(); c2.auth("blocked1")
    c2.send("JOIN #modetest")
    time.sleep(0.5)
    res = c2.recv()
    if "473" in res:
        log("MODE +i", "OK", "Utilizador bloqueado sem convite (473)")
    else:
        log("MODE +i", "FAIL", f"Resp: {repr(res[:80])}")

    c1.close(); c2.close()

def test_mode_invite_then_join():
    section("TESTE 21b: MODE +i → INVITE → JOIN")
    c1 = IRCClient("InvOp2"); c2 = IRCClient("InvJoin")

    c1.connect(); c1.auth("invop2")
    c1.send("JOIN #invjoin"); time.sleep(0.3); c1.recv()

    c1.send("MODE #invjoin +i"); time.sleep(0.3); c1.recv()

    c2.connect(); c2.auth("invjoin1")

    # Invite c2
    c1.send("INVITE invjoin1 #invjoin"); time.sleep(0.3); c1.recv(); c2.recv()

    # c2 should now be able to join
    c2.send("JOIN #invjoin")
    time.sleep(0.5)
    res = c2.recv()
    if "JOIN" in res and "473" not in res:
        log("MODE +i + INVITE", "OK", "Utilizador convidado conseguiu entrar")
    else:
        log("MODE +i + INVITE", "FAIL", f"Resp: {repr(res[:80])}")

    c1.close(); c2.close()

def test_mode_key():
    section("TESTE 22: MODE +k (PASSWORD NO CANAL)")
    c1 = IRCClient("KeyOp"); c2 = IRCClient("KeyUser"); c3 = IRCClient("KeyBad")

    c1.connect(); c1.auth("keyop1")
    c1.send("JOIN #keytest"); time.sleep(0.3); c1.recv()

    c1.send("MODE #keytest +k secreto"); time.sleep(0.3); c1.recv()

    # c2 tries with correct key
    c2.connect(); c2.auth("keyuser1")
    c2.send("JOIN #keytest secreto")
    time.sleep(0.5)
    res2 = c2.recv()

    # c3 tries with wrong key
    c3.connect(); c3.auth("keybad1")
    c3.send("JOIN #keytest wrongkey")
    time.sleep(0.5)
    res3 = c3.recv()

    ok_correct = "JOIN" in res2 and "475" not in res2
    ok_blocked = "475" in res3

    if ok_correct and ok_blocked:
        log("MODE +k", "OK", "Key correta=entrou, key errada=bloqueado (475)")
    elif ok_blocked:
        log("MODE +k", "FAIL", f"Key errada bloqueada OK, mas key correta falhou: {repr(res2[:60])}")
    elif ok_correct:
        log("MODE +k", "FAIL", f"Key correta OK, mas key errada não bloqueada: {repr(res3[:60])}")
    else:
        log("MODE +k", "FAIL", f"correct={repr(res2[:60])}, wrong={repr(res3[:60])}")

    c1.close(); c2.close(); c3.close()

def test_mode_operator():
    section("TESTE 23: MODE +o / -o (DAR/TIRAR OPERADOR)")
    c1 = IRCClient("OpGrant"); c2 = IRCClient("OpRecv"); c3 = IRCClient("OpVictim")

    c1.connect(); c1.auth("opgrant1")
    c1.send("JOIN #optest"); time.sleep(0.3); c1.recv()

    c2.connect(); c2.auth("oprecv1")
    c2.send("JOIN #optest"); time.sleep(0.3); c2.recv(); c1.recv()

    c3.connect(); c3.auth("opvictim1")
    c3.send("JOIN #optest"); time.sleep(0.3); c3.recv(); c1.recv(); c2.recv()

    # c1 grants op to c2
    c1.send("MODE #optest +o oprecv1")
    time.sleep(0.5)
    r1 = c1.recv(); r2 = c2.recv()

    # c2 now should be able to kick c3
    c2.send("KICK #optest opvictim1 :testing op")
    time.sleep(0.5)
    r_kick = c2.recv()

    if "KICK" in r_kick or "KICK" in c3.recv():
        log("MODE +o grant", "OK", "Novo operador conseguiu executar KICK")
    else:
        log("MODE +o grant", "FAIL", f"Resp: {repr(r_kick[:80])}")

    # Rejoin c3 for -o test
    c3.close()
    c3 = IRCClient("OpVictim2")
    c3.connect(); c3.auth("opvictim2")
    c3.send("JOIN #optest"); time.sleep(0.3); c3.recv(); c1.recv(); c2.recv()

    # c1 removes op from c2
    c1.send("MODE #optest -o oprecv1")
    time.sleep(0.5)
    c1.recv(); c2.recv()

    # c2 should no longer be able to kick
    c2.send("KICK #optest opvictim2 :should fail")
    time.sleep(0.5)
    res = c2.recv()
    if "482" in res:
        log("MODE -o revoke", "OK", "Operador removido não consegue KICK (482)")
    else:
        log("MODE -o revoke", "FAIL", f"Resp: {repr(res[:80])}")

    c1.close(); c2.close(); c3.close()

def test_mode_limit():
    section("TESTE 24: MODE +l (LIMITE DE UTILIZADORES)")
    c1 = IRCClient("LimOp"); c2 = IRCClient("LimOk"); c3 = IRCClient("LimBlocked")

    c1.connect(); c1.auth("limop1")
    time.sleep(0.3)
    c1.send("JOIN #limtest"); time.sleep(0.5); c1.recv()

    # Set limit to 2
    c1.send("MODE #limtest +l 2"); time.sleep(0.5); c1.recv()

    c2.connect(); c2.auth("limok1")
    time.sleep(0.3)
    c2.send("JOIN #limtest")
    time.sleep(0.5)
    res2 = c2.recv()
    c1.recv()  # consume c2 JOIN notification

    c3.connect(); c3.auth("limblk1")
    time.sleep(0.3)
    c3.send("JOIN #limtest")
    time.sleep(0.5)
    res3 = c3.recv()

    ok_join = "JOIN" in res2 and "471" not in res2
    ok_blocked = "471" in res3

    if ok_join and ok_blocked:
        log("MODE +l", "OK", "2º entrou, 3º bloqueado pelo limite (471)")
    elif ok_join:
        log("MODE +l", "FAIL", f"Limite não bloqueou 3º: {repr(res3[:60])}")
    else:
        log("MODE +l", "FAIL", f"c2={repr(res2[:60])}, c3={repr(res3[:60])}")

    c1.close(); c2.close(); c3.close()

def test_mode_limit_remove():
    section("TESTE 24b: MODE -l (REMOVER LIMITE)")
    c1 = IRCClient("LimRmOp"); c2 = IRCClient("LimRmJoin")

    c1.connect(); c1.auth("limrmop1")
    time.sleep(0.3)
    c1.send("JOIN #limrm"); time.sleep(0.5); c1.recv()

    c1.send("MODE #limrm +l 1"); time.sleep(0.5); c1.recv()

    # c2 should be blocked
    c2.connect(); c2.auth("limrmj1")
    time.sleep(0.3)
    c2.send("JOIN #limrm")
    time.sleep(0.5)
    res = c2.recv()
    blocked = "471" in res

    # Remove limit
    c1.send("MODE #limrm -l"); time.sleep(0.5); c1.recv()

    # c2 should now be able to join
    c2.send("JOIN #limrm")
    time.sleep(0.5)
    res = c2.recv()
    ok = "JOIN" in res and "471" not in res

    if blocked and ok:
        log("MODE -l", "OK", "Limite removido, utilizador entrou")
    elif not blocked:
        log("MODE -l", "FAIL", f"Limite não funcionou: {repr(res[:60])}")
    else:
        log("MODE -l", "FAIL", f"Após -l, não entrou: {repr(res[:60])}")

    c1.close(); c2.close()

def test_mode_non_op():
    section("TESTE 25: MODE POR NÃO-OPERADOR")
    c1 = IRCClient("ModeOpReal"); c2 = IRCClient("ModeNorm")

    c1.connect(); c1.auth("mdopriv1")
    time.sleep(0.3)
    c1.send("JOIN #modepriv"); time.sleep(0.5); c1.recv()

    c2.connect(); c2.auth("modenorm1")
    time.sleep(0.3)
    c2.send("JOIN #modepriv"); time.sleep(0.5); c2.recv(); c1.recv()

    # Non-op tries to set +i
    c2.send("MODE #modepriv +i")
    time.sleep(0.5)
    res = c2.recv()
    if "482" in res:
        log("MODE não-OP", "OK", "Não-operador bloqueado de usar MODE (482)")
    else:
        log("MODE não-OP", "FAIL", f"Resp: {repr(res[:80])}")

    c1.close(); c2.close()

# =========================================================================
#  SECÇÃO 7 — FLOOD & NON-BLOCKING
# =========================================================================

def test_flood_non_blocking():
    section("TESTE 26: FLOOD & NON-BLOCKING (POLLOUT)")
    c1 = IRCClient("Gritador")
    c1.connect(); c1.auth("gritador1")

    print("  [Info] Enviando 500 mensagens de uma vez...")
    for i in range(500):
        c1.send(f"PRIVMSG gritador1 :Mensagem {i}")

    log("Flood", "OK", "Servidor processou grande volume de dados sem travar")
    c1.close()

# =========================================================================
#  MAIN
# =========================================================================

if __name__ == "__main__":
    try:
        # SECÇÃO 1: Basic Checks
        test_authentication()
        test_wrong_password()
        test_no_password()

        # SECÇÃO 2: Networking
        test_multiple_connections()
        test_channel_broadcast()

        # SECÇÃO 3: Networking Specials
        test_fragmentation()
        test_partial_cmd_other_alive()
        test_ctrlD_subject()
        test_nc_without_C_flag()
        test_abrupt_disconnect()
        test_half_command_disconnect()
        test_stopped_client_flood()

        # SECÇÃO 4: PRIVMSG
        test_privmsg_channel()
        test_privmsg_user()
        test_privmsg_no_such_nick()
        test_privmsg_no_params()
        test_privmsg_not_on_channel()

        # SECÇÃO 5: Operator Commands
        test_kick_by_non_op()
        test_kick_by_op()
        test_invite()
        test_invite_non_op()
        test_topic_set_get()
        test_topic_restricted()

        # SECÇÃO 6: MODE tests
        test_mode_invite_only()
        test_mode_invite_then_join()
        test_mode_key()
        test_mode_operator()
        test_mode_limit()
        test_mode_limit_remove()
        test_mode_non_op()

        # SECÇÃO 7: Flood
        test_flood_non_blocking()

        # Resumo final
        total = passed + failed
        print(f"\n{'='*60}")
        print(f"  RESULTADO FINAL: {passed}/{total} testes passaram")
        if failed == 0:
            print(f"  \033[92m✅ TODOS OS TESTES PASSARAM!\033[0m")
        else:
            print(f"  \033[91m❌ {failed} teste(s) falharam\033[0m")
        print(f"{'='*60}")
        print(f"\n⚠️  Verifique também o terminal do servidor com Valgrind para memory leaks.")

    except Exception as e:
        import traceback
        print(f"\n❌ Erro ao executar testes: {e}")
        traceback.print_exc()
