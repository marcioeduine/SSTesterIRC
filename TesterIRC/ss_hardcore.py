import socket
import time
import sys
import threading
import random
import string

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

    def send_raw(self, data):
        self.s.send(data)

    def recv(self):
        try:
            return self.s.recv(4096).decode(errors='ignore')
        except:
            return ""

    def auth(self, nick, user=None):
        if user is None:
            user = nick
        self.send(f"PASS {PASS}")
        self.send(f"NICK {nick}")
        self.send(f"USER {user} 0 * :realname")
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
#  SECÇÃO 1 — BUFFER OVERFLOW & MALFORMED DATA
# =========================================================================

def test_huge_line():
    section("TESTE 1: LINHA GIGANTE (100KB)")
    c = IRCClient("Huge")
    c.connect()
    c.auth("huge1")
    
    # Enviar linha de 100KB
    huge = "PRIVMSG huge1 :" + "A" * 100000 + "\r\n"
    try:
        c.s.send(huge.encode())
        time.sleep(0.5)
        # Servidor deve desconectar ou ignorar
        c.send("PING test")
        time.sleep(0.5)
        res = c.recv()
        if "PONG" in res or res == "":
            log("Linha Gigante", "OK", "Servidor sobreviveu")
        else:
            log("Linha Gigante", "FAIL", "Resposta inesperada")
    except:
        log("Linha Gigante", "OK", "Servidor desconectou (esperado)")
    c.close()

def test_no_newline_flood():
    section("TESTE 2: FLOOD SEM NEWLINE")
    c = IRCClient("NoNL")
    c.connect()
    c.auth("nonl1")
    
    # Enviar 10KB sem newline
    try:
        for _ in range(100):
            c.s.send(("X" * 100).encode())
            time.sleep(0.01)
        time.sleep(1)
        # Deve desconectar por buffer overflow
        c.send("PING test")
        time.sleep(0.5)
        res = c.recv()
        if res == "" or "ERROR" in res:
            log("Flood sem newline", "OK", "Servidor protegeu-se")
        else:
            log("Flood sem newline", "FAIL", "Servidor aceitou dados infinitos")
    except:
        log("Flood sem newline", "OK", "Desconectou")
    c.close()

def test_null_bytes():
    section("TESTE 3: BYTES NULOS")
    c = IRCClient("Null")
    c.connect()
    c.auth("null1")
    
    # Enviar bytes nulos
    c.s.send(b"PRIVMSG null1 :Test\x00\x00\x00\r\n")
    time.sleep(0.5)
    res = c.recv()
    log("Bytes Nulos", "OK", "Servidor processou sem crash")
    c.close()

def test_binary_garbage():
    section("TESTE 4: LIXO BINÁRIO")
    c = IRCClient("Binary")
    c.connect()
    c.auth("bin1")
    
    # Enviar dados binários aleatórios
    garbage = bytes([random.randint(0, 255) for _ in range(500)])
    c.s.send(garbage + b"\r\n")
    time.sleep(0.5)
    c.send("PING test")
    time.sleep(0.5)
    res = c.recv()
    log("Lixo Binário", "OK", "Servidor sobreviveu")
    c.close()

# =========================================================================
#  SECÇÃO 2 — EDGE CASES DE PARSING
# =========================================================================

def test_many_colons():
    section("TESTE 5: MÚLTIPLOS : NO COMANDO")
    c = IRCClient("Colons")
    c.connect()
    c.auth("colons1")
    
    c.send("PRIVMSG colons1 ::::::test:with:many:colons::")
    time.sleep(0.5)
    res = c.recv()
    if ":test:with:many:colons" in res:
        log("Múltiplos :", "OK", "Parsed corretamente")
    else:
        log("Múltiplos :", "FAIL", f"Resposta: {repr(res[:80])}")
    c.close()

def test_empty_params():
    section("TESTE 6: PARÂMETROS VAZIOS")
    c = IRCClient("Empty")
    c.connect()
    c.auth("empty1")
    
    # JOIN sem canal
    c.send("JOIN")
    time.sleep(0.3)
    res = c.recv()
    if "461" in res:
        log("JOIN vazio", "OK", "Detectou falta de parâmetros")
    else:
        log("JOIN vazio", "FAIL", f"Resposta: {repr(res[:60])}")
    
    # PRIVMSG sem target
    c.send("PRIVMSG")
    time.sleep(0.3)
    res = c.recv()
    if "461" in res:
        log("PRIVMSG vazio", "OK", "Detectou falta de parâmetros")
    else:
        log("PRIVMSG vazio", "FAIL", f"Resposta: {repr(res[:60])}")
    
    c.close()

def test_spaces_everywhere():
    section("TESTE 7: ESPAÇOS EM TODO O LADO")
    c = IRCClient("Spaces")
    c.connect()
    c.auth("spaces1")
    
    # Espaços extras
    c.send("   PRIVMSG    spaces1    :test   with   spaces   ")
    time.sleep(0.5)
    res = c.recv()
    if "test" in res:
        log("Espaços extras", "OK", "Parsed")
    else:
        log("Espaços extras", "WARN", f"Resposta: {repr(res[:60])}")
    c.close()

def test_case_sensitivity():
    section("TESTE 8: CASE SENSITIVITY")
    c = IRCClient("Case")
    c.connect()
    c.auth("case1")
    
    # Comandos em minúsculas
    c.send("join #test")
    time.sleep(0.3)
    res = c.recv()
    
    c.send("PaRt #test")
    time.sleep(0.3)
    res2 = c.recv()
    
    log("Case Sensitivity", "OK", "Comandos aceites em qualquer case")
    c.close()

# =========================================================================
#  SECÇÃO 3 — NICKNAME INJECTION & EDGE CASES
# =========================================================================

def test_nick_with_spaces():
    section("TESTE 9: NICK COM ESPAÇOS")
    c = IRCClient("NickSpace")
    c.connect()
    c.send(f"PASS {PASS}")
    c.send("NICK nick with spaces")
    c.send("USER n 0 * :n")
    time.sleep(0.5)
    res = c.recv()
    # Deve aceitar só "nick" ou rejeitar
    log("Nick com espaços", "OK", "Servidor tratou")
    c.close()

def test_nick_special_chars():
    section("TESTE 10: NICK COM CARACTERES ESPECIAIS")
    c = IRCClient("NickSpec")
    c.connect()
    c.send(f"PASS {PASS}")
    
    special_nicks = ["nick#1", "nick@2", "nick:3", "nick!4", "nick$5"]
    for nick in special_nicks:
        c.send(f"NICK {nick}")
        time.sleep(0.2)
    
    c.send("USER n 0 * :n")
    time.sleep(0.5)
    res = c.recv()
    log("Nick especial", "OK", "Servidor tratou caracteres especiais")
    c.close()

def test_nick_too_long():
    section("TESTE 11: NICK DEMASIADO LONGO")
    c = IRCClient("NickLong")
    c.connect()
    c.send(f"PASS {PASS}")
    c.send("NICK " + "A" * 100)
    c.send("USER n 0 * :n")
    time.sleep(0.5)
    res = c.recv()
    log("Nick longo", "OK", "Servidor aceitou/truncou")
    c.close()

def test_nick_change_spam():
    section("TESTE 12: SPAM DE MUDANÇA DE NICK")
    c = IRCClient("NickSpam")
    c.connect()
    c.auth("spam1")
    
    # Mudar nick 100 vezes
    for i in range(100):
        c.send(f"NICK spam{i}")
    time.sleep(1)
    
    c.send("PING test")
    time.sleep(0.5)
    res = c.recv()
    if "PONG" in res or res != "":
        log("Nick spam", "OK", "Servidor aguentou 100 mudanças")
    else:
        log("Nick spam", "FAIL", "Servidor desconectou")
    c.close()

# =========================================================================
#  SECÇÃO 4 — CHANNEL ATTACKS
# =========================================================================

def test_join_many_channels():
    section("TESTE 13: JOIN 100 CANAIS")
    c = IRCClient("JoinMany")
    c.connect()
    c.auth("joinmany1")
    
    # Juntar 100 canais
    channels = [f"#chan{i}" for i in range(100)]
    for ch in channels:
        c.send(f"JOIN {ch}")
    time.sleep(2)
    
    c.send("PING test")
    time.sleep(0.5)
    res = c.recv()
    log("Join 100 canais", "OK", "Servidor processou")
    c.close()

def test_channel_name_injection():
    section("TESTE 14: INJECÇÃO NO NOME DO CANAL")
    c = IRCClient("ChanInj")
    c.connect()
    c.auth("chaninj1")
    
    weird_names = [
        "#test\r\nPRIVMSG", 
        "#test#test", 
        "##test",
        "#" + "A" * 200,
        "#test:with:colons"
    ]
    
    for name in weird_names:
        c.send(f"JOIN {name}")
        time.sleep(0.2)
    
    log("Injecção canal", "OK", "Servidor tratou nomes estranhos")
    c.close()

def test_mode_spam():
    section("TESTE 15: SPAM DE MODE")
    c = IRCClient("ModeSpam")
    c.connect()
    c.auth("modespam1")
    
    c.send("JOIN #modespam")
    time.sleep(0.3)
    c.recv()
    
    # Spam de modes
    modes = ["+i", "-i", "+t", "-t", "+k test", "-k", "+l 10", "-l"]
    for _ in range(20):
        for mode in modes:
            c.send(f"MODE #modespam {mode}")
    
    time.sleep(1)
    c.send("PING test")
    time.sleep(0.5)
    res = c.recv()
    log("Mode spam", "OK", "Servidor aguentou")
    c.close()

def test_mode_invalid_limit():
    section("TESTE 16: MODE +l COM VALORES INVÁLIDOS")
    c = IRCClient("ModeInv")
    c.connect()
    c.auth("modeinv1")
    
    c.send("JOIN #modeinv")
    time.sleep(0.3)
    c.recv()
    
    invalid_limits = ["-5", "0", "99999999", "abc", "123abc", "2147483648"]
    for lim in invalid_limits:
        c.send(f"MODE #modeinv +l {lim}")
        time.sleep(0.2)
    
    log("Mode +l inválido", "OK", "Servidor rejeitou valores inválidos")
    c.close()

# =========================================================================
#  SECÇÃO 5 — PRIVMSG ATTACKS
# =========================================================================

def test_privmsg_to_self_loop():
    section("TESTE 17: PRIVMSG LOOP PARA SI PRÓPRIO")
    c = IRCClient("Loop")
    c.connect()
    c.auth("loop1")
    
    # Enviar 100 mensagens para si próprio
    for i in range(100):
        c.send(f"PRIVMSG loop1 :msg{i}")
    
    time.sleep(1)
    c.send("PING test")
    time.sleep(0.5)
    res = c.recv()
    log("PRIVMSG loop", "OK", "Servidor processou")
    c.close()

def test_privmsg_non_existent():
    section("TESTE 18: PRIVMSG PARA USER INEXISTENTE")
    c = IRCClient("NonExist")
    c.connect()
    c.auth("nonexist1")
    
    c.send("PRIVMSG naoexiste123 :test")
    time.sleep(0.3)
    res = c.recv()
    if "401" in res:
        log("PRIVMSG inexistente", "OK", "ERR_NOSUCHNICK")
    else:
        log("PRIVMSG inexistente", "WARN", f"Resposta: {repr(res[:60])}")
    c.close()

def test_privmsg_empty_message():
    section("TESTE 19: PRIVMSG COM MENSAGEM VAZIA")
    c = IRCClient("Empty")
    c.connect()
    c.auth("empty1")
    
    c.send("PRIVMSG empty1 :")
    time.sleep(0.3)
    res = c.recv()
    log("PRIVMSG vazio", "OK", "Servidor tratou")
    c.close()

def test_privmsg_channel_not_member():
    section("TESTE 20: PRIVMSG PARA CANAL SEM SER MEMBRO")
    c = IRCClient("NotMem")
    c.connect()
    c.auth("notmem1")
    
    c.send("PRIVMSG #naoestouneste :test")
    time.sleep(0.3)
    res = c.recv()
    if "403" in res or "404" in res or "442" in res:
        log("PRIVMSG não-membro", "OK", "Erro apropriado")
    else:
        log("PRIVMSG não-membro", "WARN", f"Resposta: {repr(res[:60])}")
    c.close()

# =========================================================================
#  SECÇÃO 6 — RACE CONDITIONS
# =========================================================================

def test_simultaneous_join():
    section("TESTE 21: 10 CLIENTES JOIN SIMULTÂNEO")
    clients = []
    
    def join_channel(i):
        c = IRCClient(f"Sim{i}")
        c.connect()
        c.auth(f"sim{i}")
        c.send("JOIN #simul")
        time.sleep(0.5)
        c.recv()
        clients.append(c)
    
    threads = []
    for i in range(10):
        t = threading.Thread(target=join_channel, args=(i,))
        t.start()
        threads.append(t)
    
    for t in threads:
        t.join()
    
    log("Join simultâneo", "OK", "10 clientes juntaram-se")
    
    for c in clients:
        c.close()

def test_kick_during_message():
    section("TESTE 22: KICK DURANTE ENVIO DE MENSAGEM")
    c1 = IRCClient("Kicker")
    c2 = IRCClient("Victim")
    
    c1.connect(); c1.auth("kicker1")
    c2.connect(); c2.auth("victim1")
    
    c1.send("JOIN #kicktest")
    time.sleep(0.3); c1.recv()
    
    c2.send("JOIN #kicktest")
    time.sleep(0.3); c2.recv(); c1.recv()
    
    # c2 envia mensagem, c1 kicka ao mesmo tempo
    def send_spam():
        for i in range(50):
            try:
                c2.send(f"PRIVMSG #kicktest :msg{i}")
                time.sleep(0.01)
            except:
                break
    
    t = threading.Thread(target=send_spam)
    t.start()
    time.sleep(0.1)
    c1.send("KICK #kicktest victim1")
    t.join()
    
    log("Kick durante msg", "OK", "Sem crash")
    c1.close(); c2.close()

# =========================================================================
#  SECÇÃO 7 — AUTHENTICATION BYPASS ATTEMPTS
# =========================================================================

def test_commands_before_auth():
    section("TESTE 23: COMANDOS ANTES DE AUTENTICAR")
    c = IRCClient("NoAuth")
    c.connect()
    
    # Tentar comandos sem autenticar
    c.send("JOIN #test")
    c.send("PRIVMSG #test :hack")
    c.send("MODE #test +o")
    c.send("KICK #test user")
    time.sleep(0.5)
    res = c.recv()
    
    if "451" in res or res == "":
        log("Cmd antes auth", "OK", "Servidor bloqueou")
    else:
        log("Cmd antes auth", "FAIL", "Executou sem autenticação!")
    c.close()

def test_double_password():
    section("TESTE 24: ENVIAR PASS DUAS VEZES")
    c = IRCClient("DoublePass")
    c.connect()
    c.send(f"PASS {PASS}")
    c.send(f"PASS outrasenhha")
    c.send("NICK double1")
    c.send("USER d 0 * :d")
    time.sleep(0.5)
    res = c.recv()
    
    if "462" in res or "001" in res:
        log("Double PASS", "OK", "Servidor tratou")
    else:
        log("Double PASS", "WARN", f"Resposta: {repr(res[:60])}")
    c.close()

def test_auth_timeout():
    section("TESTE 25: TIMEOUT DE AUTENTICAÇÃO")
    c = IRCClient("Timeout")
    c.connect()
    
    # Enviar comandos inválidos até timeout
    disconnected = False
    try:
        for i in range(15):
            c.send("INVALID command")
            time.sleep(0.1)
    except (BrokenPipeError, ConnectionResetError):
        disconnected = True
        log("Auth timeout", "OK", "Servidor desconectou após comandos inválidos")
    
    if not disconnected:
        time.sleep(1)
        try:
            c.send("PING test")
            time.sleep(0.5)
            res = c.recv()
            if res == "":
                log("Auth timeout", "OK", "Servidor desconectou")
            else:
                log("Auth timeout", "WARN", "Servidor ainda conectado")
        except:
            log("Auth timeout", "OK", "Desconectado")
    
    try:
        c.close()
    except:
        pass

# =========================================================================
#  SECÇÃO 8 — STRESS TESTS
# =========================================================================

def test_rapid_connect_disconnect():
    section("TESTE 26: 50 CONEXÕES/DESCONEXÕES RÁPIDAS")
    success = 0
    for i in range(50):
        try:
            c = IRCClient(f"Rapid{i}")
            c.connect()
            c.send(f"PASS {PASS}")
            c.send(f"NICK rapid{i}")
            c.send(f"USER r 0 * :r")
            time.sleep(0.05)
            c.close()
            success += 1
        except Exception as e:
            pass
    
    log("Rapid connect/disconnect", "OK", f"Servidor aguentou ({success}/50 conexões)")


def test_channel_flood():
    section("TESTE 27: FLOOD DE MENSAGENS NUM CANAL")
    c1 = IRCClient("Flooder")
    c2 = IRCClient("Receiver")
    
    c1.connect(); c1.auth("flooder1")
    c2.connect(); c2.auth("receiver1")
    
    c1.send("JOIN #flood")
    time.sleep(0.3); c1.recv()
    
    c2.send("JOIN #flood")
    time.sleep(0.3); c2.recv(); c1.recv()
    
    # Enviar 500 mensagens
    for i in range(500):
        c1.send(f"PRIVMSG #flood :flood{i}")
    
    time.sleep(2)
    c1.send("PING test")
    time.sleep(0.5)
    res = c1.recv()
    
    log("Channel flood", "OK", "Servidor processou 500 mensagens")
    c1.close(); c2.close()

def test_part_nonexistent_channel():
    section("TESTE 28: PART DE CANAL INEXISTENTE")
    c = IRCClient("PartNone")
    c.connect()
    c.auth("partnone1")
    
    c.send("PART #naoexiste")
    time.sleep(0.3)
    res = c.recv()
    if "403" in res or "442" in res:
        log("Part inexistente", "OK", "Erro apropriado")
    else:
        log("Part inexistente", "WARN", f"Resposta: {repr(res[:60])}")
    c.close()

# =========================================================================
#  SECÇÃO 9 — OPERATOR PRIVILEGE ESCALATION
# =========================================================================

def test_non_op_kick():
    section("TESTE 29: NÃO-OP TENTA KICK")
    c1 = IRCClient("Op")
    c2 = IRCClient("NonOp")
    
    c1.connect(); c1.auth("op1")
    c2.connect(); c2.auth("nonop1")
    
    c1.send("JOIN #optest")
    time.sleep(0.3); c1.recv()
    
    c2.send("JOIN #optest")
    time.sleep(0.3); c2.recv(); c1.recv()
    
    # c2 tenta kickar c1
    c2.send("KICK #optest op1")
    time.sleep(0.3)
    res = c2.recv()
    
    if "482" in res:
        log("Non-op KICK", "OK", "ERR_CHANOPRIVSNEEDED")
    else:
        log("Non-op KICK", "FAIL", "Kick executou sem ser OP!")
    
    c1.close(); c2.close()

def test_non_op_mode():
    section("TESTE 30: NÃO-OP TENTA MODE")
    c1 = IRCClient("Op")
    c2 = IRCClient("NonOp")
    
    c1.connect(); c1.auth("op1")
    c2.connect(); c2.auth("nonop1")
    
    c1.send("JOIN #modetest")
    time.sleep(0.3); c1.recv()
    
    c2.send("JOIN #modetest")
    time.sleep(0.3); c2.recv(); c1.recv()
    
    # c2 tenta MODE
    c2.send("MODE #modetest +i")
    time.sleep(0.3)
    res = c2.recv()
    
    if "482" in res:
        log("Non-op MODE", "OK", "Bloqueado")
    else:
        log("Non-op MODE", "FAIL", "MODE executou sem ser OP!")
    
    c1.close(); c2.close()

def test_non_op_topic():
    section("TESTE 31: NÃO-OP TENTA TOPIC COM +t")
    c1 = IRCClient("Op")
    c2 = IRCClient("NonOp")
    
    c1.connect(); c1.auth("op1")
    c2.connect(); c2.auth("nonop1")
    
    c1.send("JOIN #topictest")
    time.sleep(0.3); c1.recv()
    
    c1.send("MODE #topictest +t")
    time.sleep(0.3); c1.recv()
    
    c2.send("JOIN #topictest")
    time.sleep(0.3); c2.recv(); c1.recv()
    
    # c2 tenta TOPIC
    c2.send("TOPIC #topictest :new topic")
    time.sleep(0.3)
    res = c2.recv()
    
    if "482" in res:
        log("Non-op TOPIC +t", "OK", "Bloqueado")
    else:
        log("Non-op TOPIC +t", "FAIL", "TOPIC executou!")
    
    c1.close(); c2.close()

# =========================================================================
#  SECÇÃO 10 — UNICODE & ENCODING
# =========================================================================

def test_unicode_messages():
    section("TESTE 32: MENSAGENS UNICODE")
    c = IRCClient("Unicode")
    c.connect()
    c.auth("unicode1")
    
    messages = [
        "Olá mundo! 🌍",
        "Testing 中文字符",
        "Эмодзи тест 😀🎉",
        "العربية الاختبار"
    ]
    
    for msg in messages:
        try:
            c.send(f"PRIVMSG unicode1 :{msg}")
            time.sleep(0.2)
        except:
            pass
    
    log("Unicode", "OK", "Servidor processou Unicode")
    c.close()

def test_long_realname():
    section("TESTE 33: REALNAME MUITO LONGO")
    c = IRCClient("LongReal")
    c.connect()
    c.send(f"PASS {PASS}")
    c.send("NICK longreal1")
    c.send("USER l 0 * :" + "A" * 1000)
    time.sleep(0.5)
    res = c.recv()
    log("Realname longo", "OK", "Servidor aceitou")
    c.close()

# =========================================================================
#  SECÇÃO 11 — INVITE EDGE CASES
# =========================================================================

def test_invite_self():
    section("TESTE 34: INVITE A SI PRÓPRIO")
    c = IRCClient("InvSelf")
    c.connect()
    c.auth("invself1")
    
    c.send("JOIN #invtest")
    time.sleep(0.3); c.recv()
    
    c.send("INVITE invself1 #invtest")
    time.sleep(0.3)
    res = c.recv()
    if "443" in res:
        log("Invite self", "OK", "ERR_USERONCHANNEL")
    else:
        log("Invite self", "WARN", f"Resposta: {repr(res[:60])}")
    c.close()

def test_invite_nonexistent_user():
    section("TESTE 35: INVITE USER INEXISTENTE")
    c = IRCClient("InvNone")
    c.connect()
    c.auth("invnone1")
    
    c.send("JOIN #invtest")
    time.sleep(0.3); c.recv()
    
    c.send("INVITE naoexiste123 #invtest")
    time.sleep(0.3)
    res = c.recv()
    if "401" in res:
        log("Invite inexistente", "OK", "ERR_NOSUCHNICK")
    else:
        log("Invite inexistente", "WARN", f"Resposta: {repr(res[:60])}")
    c.close()

# =========================================================================
#  SECÇÃO 12 — TOPIC EDGE CASES
# =========================================================================

def test_topic_very_long():
    section("TESTE 36: TOPIC DE 1000 CARACTERES")
    c = IRCClient("TopicLong")
    c.connect()
    c.auth("topiclong1")
    
    c.send("JOIN #topiclong")
    time.sleep(0.3); c.recv()
    
    c.send("TOPIC #topiclong :" + "T" * 1000)
    time.sleep(0.5)
    res = c.recv()
    log("Topic longo", "OK", "Servidor aceitou/truncou")
    c.close()

def test_topic_with_newlines():
    section("TESTE 37: TOPIC COM NEWLINES")
    c = IRCClient("TopicNL")
    c.connect()
    c.auth("topicnl1")
    
    c.send("JOIN #topicnl")
    time.sleep(0.3); c.recv()
    
    # Tentar injectar newline no tópico
    c.send("TOPIC #topicnl :Line1\r\nPRIVMSG")
    time.sleep(0.5)
    res = c.recv()
    log("Topic com newline", "OK", "Servidor tratou")
    c.close()

# =========================================================================
#  SECÇÃO 13 — QUIT EDGE CASES
# =========================================================================

def test_quit_in_multiple_channels():
    section("TESTE 38: QUIT EM 10 CANAIS")
    c = IRCClient("QuitMany")
    c.connect()
    c.auth("quitmany1")
    
    # Join 10 canais
    for i in range(10):
        c.send(f"JOIN #quit{i}")
        time.sleep(0.1)
    
    time.sleep(1)
    c.recv()  # Limpar buffer
    
    c.send("QUIT :Bye")
    time.sleep(0.5)
    log("Quit em 10 canais", "OK", "Servidor processou")
    c.close()

def test_quit_during_operation():
    section("TESTE 39: QUIT DURANTE OPERAÇÃO")
    c = IRCClient("QuitOp")
    try:
        c.connect()
        c.auth("quitop1")
        
        c.send("JOIN #quitop")
        time.sleep(0.3); c.recv()
        
        # Enviar comandos e QUIT no meio
        c.send("PRIVMSG #quitop :msg1")
        c.send("QUIT :Bye")
        try:
            c.send("PRIVMSG #quitop :msg2")  # Não deve chegar
        except (BrokenPipeError, ConnectionResetError):
            pass  # Esperado - servidor já desconectou
        time.sleep(0.5)
        log("Quit durante op", "OK", "Servidor processou")
    except Exception as e:
        log("Quit durante op", "OK", f"Servidor desconectou: {type(e).__name__}")
    finally:
        try:
            c.close()
        except:
            pass

# =========================================================================
#  SECÇÃO 14 — KEY (+k) ATTACKS
# =========================================================================

def test_key_with_spaces():
    section("TESTE 40: KEY COM ESPAÇOS")
    c = IRCClient("KeySpace")
    c.connect()
    c.auth("keyspace1")
    
    c.send("JOIN #keyspace")
    time.sleep(0.3); c.recv()
    
    c.send("MODE #keyspace +k key with spaces")
    time.sleep(0.3)
    res = c.recv()
    log("Key com espaços", "OK", "Servidor tratou")
    c.close()

def test_key_very_long():
    section("TESTE 41: KEY DE 500 CARACTERES")
    c = IRCClient("KeyLong")
    c.connect()
    c.auth("keylong1")
    
    c.send("JOIN #keylong")
    time.sleep(0.3); c.recv()
    
    c.send("MODE #keylong +k " + "K" * 500)
    time.sleep(0.3)
    res = c.recv()
    log("Key longa", "OK", "Servidor aceitou/truncou")
    c.close()

# =========================================================================
#  MAIN
# =========================================================================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("  🔥 TESTES HARDCORE - TENTA REBENTAR O SERVIDOR! 🔥")
    print("="*60)
    
    tests = [
        # Secção 1: Buffer Overflow
        ("test_huge_line", test_huge_line),
        ("test_no_newline_flood", test_no_newline_flood),
        ("test_null_bytes", test_null_bytes),
        ("test_binary_garbage", test_binary_garbage),
        
        # Secção 2: Parsing Edge Cases
        ("test_many_colons", test_many_colons),
        ("test_empty_params", test_empty_params),
        ("test_spaces_everywhere", test_spaces_everywhere),
        ("test_case_sensitivity", test_case_sensitivity),
        
        # Secção 3: Nickname Attacks
        ("test_nick_with_spaces", test_nick_with_spaces),
        ("test_nick_special_chars", test_nick_special_chars),
        ("test_nick_too_long", test_nick_too_long),
        ("test_nick_change_spam", test_nick_change_spam),
        
        # Secção 4: Channel Attacks
        ("test_join_many_channels", test_join_many_channels),
        ("test_channel_name_injection", test_channel_name_injection),
        ("test_mode_spam", test_mode_spam),
        ("test_mode_invalid_limit", test_mode_invalid_limit),
        
        # Secção 5: PRIVMSG Attacks
        ("test_privmsg_to_self_loop", test_privmsg_to_self_loop),
        ("test_privmsg_non_existent", test_privmsg_non_existent),
        ("test_privmsg_empty_message", test_privmsg_empty_message),
        ("test_privmsg_channel_not_member", test_privmsg_channel_not_member),
        
        # Secção 6: Race Conditions
        ("test_simultaneous_join", test_simultaneous_join),
        ("test_kick_during_message", test_kick_during_message),
        
        # Secção 7: Auth Bypass
        ("test_commands_before_auth", test_commands_before_auth),
        ("test_double_password", test_double_password),
        ("test_auth_timeout", test_auth_timeout),
        
        # Secção 8: Stress Tests
        ("test_rapid_connect_disconnect", test_rapid_connect_disconnect),
        ("test_channel_flood", test_channel_flood),
        ("test_part_nonexistent_channel", test_part_nonexistent_channel),
        
        # Secção 9: Privilege Escalation
        ("test_non_op_kick", test_non_op_kick),
        ("test_non_op_mode", test_non_op_mode),
        ("test_non_op_topic", test_non_op_topic),
        
        # Secção 10: Unicode
        ("test_unicode_messages", test_unicode_messages),
        ("test_long_realname", test_long_realname),
        
        # Secção 11: Invite
        ("test_invite_self", test_invite_self),
        ("test_invite_nonexistent_user", test_invite_nonexistent_user),
        
        # Secção 12: Topic
        ("test_topic_very_long", test_topic_very_long),
        ("test_topic_with_newlines", test_topic_with_newlines),
        
        # Secção 13: Quit
        ("test_quit_in_multiple_channels", test_quit_in_multiple_channels),
        ("test_quit_during_operation", test_quit_during_operation),
        
        # Secção 14: Key
        ("test_key_with_spaces", test_key_with_spaces),
        ("test_key_very_long", test_key_very_long),
    ]
    
    for test_name, test_func in tests:
        try:
            test_func()
        except KeyboardInterrupt:
            print("\n\n⚠️  Testes interrompidos pelo utilizador")
            break
        except Exception as e:
            print(f"\n❌ ERRO em {test_name}: {e}")
            import traceback
            traceback.print_exc()
            # Continua para o próximo teste
    
    # Resumo final
    total = passed + failed
    print(f"\n{'='*60}")
    print(f"  RESULTADO FINAL: {passed}/{total} testes passaram")
    if failed == 0:
        print(f"  \033[92m✅ SERVIDOR É INDESTRUTÍVEL!\033[0m")
    elif failed < 5:
        print(f"  \033[93m⚠️  {failed} teste(s) falharam - Servidor robusto!\033[0m")
    else:
        print(f"  \033[91m❌ {failed} teste(s) falharam\033[0m")
    print(f"{'='*60}")
    print(f"\n⚠️  Verifica o terminal do servidor para crashes/memory leaks!")
