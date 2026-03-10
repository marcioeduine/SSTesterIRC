import socket
import time
import sys

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
#  RPL_* (Respostas de Sucesso - 001-399)
# =========================================================================

def test_001_welcome():
    section("RPL 001: RPL_WELCOME")
    c = IRCClient("Welcome")
    c.connect()
    c.send(f"PASS {PASS}")
    c.send("NICK welcome1")
    c.send("USER w 0 * :w")
    time.sleep(0.5)
    res = c.recv()
    if "001" in res and "Welcome" in res:
        log("001 RPL_WELCOME", "OK", "Welcome message enviada")
    else:
        log("001 RPL_WELCOME", "FAIL", f"Resposta: {repr(res[:80])}")
    c.close()

def test_002_yourhost():
    section("RPL 002: RPL_YOURHOST")
    c = IRCClient("YourHost")
    c.connect()
    res = c.auth("yourhost1")
    if "002" in res and "host" in res.lower():
        log("002 RPL_YOURHOST", "OK", "Host info enviada")
    else:
        log("002 RPL_YOURHOST", "FAIL", f"Resposta: {repr(res[:80])}")
    c.close()

def test_003_created():
    section("RPL 003: RPL_CREATED")
    c = IRCClient("Created")
    c.connect()
    res = c.auth("created1")
    if "003" in res and "created" in res.lower():
        log("003 RPL_CREATED", "OK", "Server creation info enviada")
    else:
        log("003 RPL_CREATED", "FAIL", f"Resposta: {repr(res[:80])}")
    c.close()

def test_004_myinfo():
    section("RPL 004: RPL_MYINFO")
    c = IRCClient("MyInfo")
    c.connect()
    res = c.auth("myinfo1")
    if "004" in res and "itkol" in res:
        log("004 RPL_MYINFO", "OK", "Server modes info enviada")
    else:
        log("004 RPL_MYINFO", "FAIL", f"Resposta: {repr(res[:80])}")
    c.close()

def test_221_umodeis():
    section("RPL 221: RPL_UMODEIS")
    c = IRCClient("UMode")
    c.connect()
    c.auth("umode1")
    c.send("MODE umode1")
    time.sleep(0.3)
    res = c.recv()
    if "221" in res:
        log("221 RPL_UMODEIS", "OK", "User mode resposta enviada")
    else:
        log("221 RPL_UMODEIS", "FAIL", f"Resposta: {repr(res[:80])}")
    c.close()

def test_324_channelmodeis():
    section("RPL 324: RPL_CHANNELMODEIS")
    c = IRCClient("ChanMode")
    c.connect()
    c.auth("chanmode1")
    c.send("JOIN #test324")
    time.sleep(0.3)
    c.recv()
    c.send("MODE #test324")
    time.sleep(0.3)
    res = c.recv()
    if "324" in res:
        log("324 RPL_CHANNELMODEIS", "OK", "Channel mode resposta enviada")
    else:
        log("324 RPL_CHANNELMODEIS", "FAIL", f"Resposta: {repr(res[:80])}")
    c.close()

def test_331_notopic():
    section("RPL 331: RPL_NOTOPIC")
    c = IRCClient("NoTopic")
    c.connect()
    c.auth("notopic1")
    c.send("JOIN #notopic")
    time.sleep(0.5)
    res = c.recv()
    if "331" in res and "No topic" in res:
        log("331 RPL_NOTOPIC", "OK", "No topic message enviada")
    else:
        log("331 RPL_NOTOPIC", "FAIL", f"Resposta: {repr(res[:80])}")
    c.close()

def test_332_topic():
    section("RPL 332: RPL_TOPIC")
    
    c1 = IRCClient("TopicKeeper")
    c2 = IRCClient("TopicJoiner")
    
    c1.connect()
    c1.auth("keeper1")
    c1.send("JOIN #topic332")
    time.sleep(0.3)
    c1.recv()
    
    c1.send("TOPIC #topic332 :Test Topic")
    time.sleep(0.3)
    c1.recv()
    
    c2.connect()
    c2.auth("joiner1")
    c2.send("JOIN #topic332")
    time.sleep(0.5)
    res = c2.recv()
    if "332" in res and "Test Topic" in res:
        log("332 RPL_TOPIC", "OK", "Topic mostrado no JOIN")
    else:
        log("332 RPL_TOPIC", "FAIL", f"Resposta: {repr(res[:80])}")
    c1.close()
    c2.close()

def test_341_inviting():
    section("RPL 341: RPL_INVITING")
    c1 = IRCClient("Inviter")
    c2 = IRCClient("Invited")
    c1.connect(); c1.auth("inviter1")
    c2.connect(); c2.auth("invited1")
    
    c1.send("JOIN #invite341")
    time.sleep(0.3); c1.recv()
    
    c1.send("INVITE invited1 #invite341")
    time.sleep(0.3)
    res = c1.recv()
    if "341" in res:
        log("341 RPL_INVITING", "OK", "Invite confirmação enviada")
    else:
        log("341 RPL_INVITING", "FAIL", f"Resposta: {repr(res[:80])}")
    c1.close(); c2.close()

def test_353_namreply():
    section("RPL 353: RPL_NAMREPLY")
    c = IRCClient("Names")
    c.connect()
    c.auth("names1")
    c.send("JOIN #names353")
    time.sleep(0.5)
    res = c.recv()
    if "353" in res and "names1" in res:
        log("353 RPL_NAMREPLY", "OK", "Names list enviada")
    else:
        log("353 RPL_NAMREPLY", "FAIL", f"Resposta: {repr(res[:80])}")
    c.close()

def test_366_endofnames():
    section("RPL 366: RPL_ENDOFNAMES")
    c = IRCClient("EndNames")
    c.connect()
    c.auth("endnames1")
    c.send("JOIN #end366")
    time.sleep(0.5)
    res = c.recv()
    if "366" in res and "End of" in res:
        log("366 RPL_ENDOFNAMES", "OK", "End of NAMES enviado")
    else:
        log("366 RPL_ENDOFNAMES", "FAIL", f"Resposta: {repr(res[:80])}")
    c.close()

# =========================================================================
#  ERR_* (Erros - 400-599)
# =========================================================================

def test_401_nosuchnick():
    section("ERR 401: ERR_NOSUCHNICK")
    c = IRCClient("NoNick")
    c.connect()
    c.auth("nonick1")
    c.send("PRIVMSG naoexiste123 :test")
    time.sleep(0.3)
    res = c.recv()
    if "401" in res and "No such nick" in res:
        log("401 ERR_NOSUCHNICK", "OK", "Nick inexistente detectado")
    else:
        log("401 ERR_NOSUCHNICK", "FAIL", f"Resposta: {repr(res[:80])}")
    c.close()

def test_403_nosuchchannel():
    section("ERR 403: ERR_NOSUCHCHANNEL")
    c = IRCClient("NoChan")
    c.connect()
    c.auth("nochan1")
    c.send("MODE #naoexiste123")
    time.sleep(0.3)
    res = c.recv()
    if "403" in res and "No such channel" in res:
        log("403 ERR_NOSUCHCHANNEL", "OK", "Canal inexistente detectado")
    else:
        log("403 ERR_NOSUCHCHANNEL", "FAIL", f"Resposta: {repr(res[:80])}")
    c.close()

def test_404_cannotsendtochan():
    section("ERR 404: ERR_CANNOTSENDTOCHAN")
    c = IRCClient("CantSend")
    c.connect()
    c.auth("cantsend1")
    # Tentar enviar para canal onde não está
    c.send("PRIVMSG #naosouaqui :test")
    time.sleep(0.3)
    res = c.recv()
    if "404" in res or "403" in res:  # Ambos são válidos
        log("404 ERR_CANNOTSENDTOCHAN", "OK", "Send bloqueado (404 ou 403)")
    else:
        log("404 ERR_CANNOTSENDTOCHAN", "FAIL", f"Resposta: {repr(res[:80])}")
    c.close()

def test_409_noorigin():
    section("ERR 409: ERR_NOORIGIN")
    c = IRCClient("NoOrigin")
    c.connect()
    c.auth("noorigin1")
    c.send("PING")  # PING sem parâmetro
    time.sleep(0.3)
    res = c.recv()
    if "409" in res and "origin" in res.lower():
        log("409 ERR_NOORIGIN", "OK", "PING sem origem detectado")
    else:
        log("409 ERR_NOORIGIN", "FAIL", f"Resposta: {repr(res[:80])}")
    c.close()

def test_421_unknowncommand():
    section("ERR 421: ERR_UNKNOWNCOMMAND")
    c = IRCClient("Unknown")
    c.connect()
    c.auth("unknown1")
    c.send("COMANDOINVALIDO param1 param2")
    time.sleep(0.3)
    res = c.recv()
    if "421" in res and "Unknown command" in res:
        log("421 ERR_UNKNOWNCOMMAND", "OK", "Comando desconhecido detectado")
    else:
        log("421 ERR_UNKNOWNCOMMAND", "FAIL", f"Resposta: {repr(res[:80])}")
    c.close()

def test_431_nonicknamegiven():
    section("ERR 431: ERR_NONICKNAMEGIVEN")
    c = IRCClient("NoNickGiven")
    c.connect()
    c.auth("nonickgiven1")
    c.send("NICK")  # NICK sem parâmetro
    time.sleep(0.3)
    res = c.recv()
    if "431" in res and "No nickname" in res:
        log("431 ERR_NONICKNAMEGIVEN", "OK", "NICK vazio detectado")
    else:
        log("431 ERR_NONICKNAMEGIVEN", "FAIL", f"Resposta: {repr(res[:80])}")
    c.close()

def test_433_nicknameinuse():
    section("ERR 433: ERR_NICKNAMEINUSE")
    c1 = IRCClient("User1")
    c2 = IRCClient("User2")
    c1.connect(); c1.auth("duplicate1")
    c2.connect()
    c2.send(f"PASS {PASS}")
    c2.send("NICK duplicate1")  # Mesmo nick
    c2.send("USER d 0 * :d")
    time.sleep(0.5)
    res = c2.recv()
    if "433" in res and "in use" in res.lower():
        log("433 ERR_NICKNAMEINUSE", "OK", "Nick duplicado detectado")
    else:
        log("433 ERR_NICKNAMEINUSE", "FAIL", f"Resposta: {repr(res[:80])}")
    c1.close(); c2.close()

def test_441_usernotinchannel():
    section("ERR 441: ERR_USERNOTINCHANNEL")
    c = IRCClient("NotInChan")
    c.connect()
    c.auth("notinchan1")
    c.send("JOIN #test441")
    time.sleep(0.3); c.recv()
    # Tentar kickar alguém que não está no canal
    c.send("KICK #test441 naoexiste")
    time.sleep(0.3)
    res = c.recv()
    if "441" in res and "aren't on" in res.lower():
        log("441 ERR_USERNOTINCHANNEL", "OK", "User não no canal detectado")
    else:
        log("441 ERR_USERNOTINCHANNEL", "FAIL", f"Resposta: {repr(res[:80])}")
    c.close()

def test_442_notonchannel():
    section("ERR 442: ERR_NOTONCHANNEL")
    c = IRCClient("NotOn")
    c.connect()
    c.auth("noton1")
    # Tentar PART de canal onde não está
    c.send("PART #naoestouneste")
    time.sleep(0.3)
    res = c.recv()
    if "442" in res or "403" in res:  # Ambos aceitáveis
        log("442 ERR_NOTONCHANNEL", "OK", "Not on channel detectado (442 ou 403)")
    else:
        log("442 ERR_NOTONCHANNEL", "FAIL", f"Resposta: {repr(res[:80])}")
    c.close()

def test_443_useronchannel():
    section("ERR 443: ERR_USERONCHANNEL")
    c = IRCClient("OnChan")
    c.connect()
    c.auth("onchan1")
    c.send("JOIN #test443")
    time.sleep(0.3); c.recv()
    # Tentar INVITE a si próprio
    c.send("INVITE onchan1 #test443")
    time.sleep(0.3)
    res = c.recv()
    if "443" in res and "already on" in res.lower():
        log("443 ERR_USERONCHANNEL", "OK", "User já no canal detectado")
    else:
        log("443 ERR_USERONCHANNEL", "FAIL", f"Resposta: {repr(res[:80])}")
    c.close()

def test_451_notregistered():
    section("ERR 451: ERR_NOTREGISTERED")
    c = IRCClient("NotReg")
    c.connect()
    # Tentar comando sem autenticar
    c.send("JOIN #test")
    time.sleep(0.3)
    res = c.recv()
    if "451" in res and "not registered" in res.lower():
        log("451 ERR_NOTREGISTERED", "OK", "Not registered detectado")
    else:
        log("451 ERR_NOTREGISTERED", "FAIL", f"Resposta: {repr(res[:80])}")
    c.close()

def test_461_needmoreparams():
    section("ERR 461: ERR_NEEDMOREPARAMS")
    c = IRCClient("NeedMore")
    c.connect()
    c.auth("needmore1")
    # Comandos sem parâmetros suficientes
    tests = [
        ("JOIN", "JOIN sem parâmetro"),
        ("PRIVMSG", "PRIVMSG sem target"),
        ("MODE #test", "MODE sem modo"),
        ("KICK #test", "KICK sem user"),
        ("INVITE", "INVITE sem parâmetros"),
        ("TOPIC", "TOPIC sem canal")
    ]
    
    for cmd, desc in tests:
        c.send(cmd)
        time.sleep(0.2)
    
    time.sleep(0.5)
    res = c.recv()
    if res.count("461") >= 3:  # Pelo menos 3 erros 461
        log("461 ERR_NEEDMOREPARAMS", "OK", f"Detectou múltiplos comandos incompletos ({res.count('461')})")
    else:
        log("461 ERR_NEEDMOREPARAMS", "FAIL", f"Apenas {res.count('461')} erros 461")
    c.close()

def test_462_alreadyregistred():
    section("ERR 462: ERR_ALREADYREGISTRED")
    c = IRCClient("AlreadyReg")
    c.connect()
    c.send(f"PASS {PASS}")
    c.send("NICK alreadyreg1")
    c.send("USER a 0 * :a")
    time.sleep(0.5)
    c.recv()
    # Tentar registar novamente
    c.send(f"PASS {PASS}")
    time.sleep(0.3)
    res = c.recv()
    if "462" in res and "may not reregister" in res.lower():
        log("462 ERR_ALREADYREGISTRED", "OK", "Re-registro bloqueado")
    else:
        log("462 ERR_ALREADYREGISTRED", "FAIL", f"Resposta: {repr(res[:80])}")
    c.close()

def test_464_passwdmismatch():
    section("ERR 464: ERR_PASSWDMISMATCH")
    c = IRCClient("BadPass")
    c.connect()
    c.send("PASS senhaerrada123")
    c.send("NICK badpass1")
    c.send("USER b 0 * :b")
    time.sleep(0.5)
    res = c.recv()
    if "464" in res and "incorrect" in res.lower():
        log("464 ERR_PASSWDMISMATCH", "OK", "Password errada detectada")
    else:
        log("464 ERR_PASSWDMISMATCH", "FAIL", f"Resposta: {repr(res[:80])}")
    c.close()

def test_471_channelisfull():
    section("ERR 471: ERR_CHANNELISFULL")
    c1 = IRCClient("Op")
    c2 = IRCClient("Limit1")
    c3 = IRCClient("Blocked")
    
    c1.connect(); c1.auth("op471")
    c1.send("JOIN #full471")
    time.sleep(0.3); c1.recv()
    c1.send("MODE #full471 +l 2")  # Limite de 2
    time.sleep(0.3); c1.recv()
    
    c2.connect(); c2.auth("limit1_471")
    c2.send("JOIN #full471")
    time.sleep(0.3); c2.recv(); c1.recv()
    
    c3.connect(); c3.auth("blocked471")
    c3.send("JOIN #full471")
    time.sleep(0.5)
    res = c3.recv()
    
    if "471" in res and "full" in res.lower():
        log("471 ERR_CHANNELISFULL", "OK", "Canal cheio detectado")
    else:
        log("471 ERR_CHANNELISFULL", "FAIL", f"Resposta: {repr(res[:80])}")
    c1.close(); c2.close(); c3.close()

def test_473_inviteonlychan():
    section("ERR 473: ERR_INVITEONLYCHAN")
    c1 = IRCClient("OpInv")
    c2 = IRCClient("BlockedInv")
    
    c1.connect(); c1.auth("opinv473")
    c1.send("JOIN #invite473")
    time.sleep(0.3); c1.recv()
    c1.send("MODE #invite473 +i")  # Invite only
    time.sleep(0.3); c1.recv()
    
    c2.connect(); c2.auth("blocked473")
    c2.send("JOIN #invite473")
    time.sleep(0.5)
    res = c2.recv()
    
    if "473" in res and "invite" in res.lower():
        log("473 ERR_INVITEONLYCHAN", "OK", "Invite-only bloqueou")
    else:
        log("473 ERR_INVITEONLYCHAN", "FAIL", f"Resposta: {repr(res[:80])}")
    c1.close(); c2.close()

def test_475_badchannelkey():
    section("ERR 475: ERR_BADCHANNELKEY")
    c1 = IRCClient("OpKey")
    c2 = IRCClient("BadKey")
    
    c1.connect(); c1.auth("opkey475")
    c1.send("JOIN #key475")
    time.sleep(0.3); c1.recv()
    c1.send("MODE #key475 +k secretpassword")
    time.sleep(0.3); c1.recv()
    
    c2.connect(); c2.auth("badkey475")
    c2.send("JOIN #key475 wrongpassword")
    time.sleep(0.5)
    res = c2.recv()
    
    if "475" in res and "key" in res.lower():
        log("475 ERR_BADCHANNELKEY", "OK", "Key errada detectada")
    else:
        log("475 ERR_BADCHANNELKEY", "FAIL", f"Resposta: {repr(res[:80])}")
    c1.close(); c2.close()

def test_482_chanoprivsneeded():
    section("ERR 482: ERR_CHANOPRIVSNEEDED")
    c1 = IRCClient("Op482")
    c2 = IRCClient("NonOp482")
    
    c1.connect(); c1.auth("op482")
    c2.connect(); c2.auth("nonop482")
    
    c1.send("JOIN #priv482")
    time.sleep(0.3); c1.recv()
    
    c2.send("JOIN #priv482")
    time.sleep(0.3); c2.recv(); c1.recv()
    
    # c2 tenta MODE sem ser OP
    c2.send("MODE #priv482 +i")
    time.sleep(0.3)
    res = c2.recv()
    
    if "482" in res and "operator" in res.lower():
        log("482 ERR_CHANOPRIVSNEEDED", "OK", "Privilégio de OP requerido")
    else:
        log("482 ERR_CHANOPRIVSNEEDED", "FAIL", f"Resposta: {repr(res[:80])}")
    c1.close(); c2.close()

# =========================================================================
#  MAIN
# =========================================================================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("  🔍 TESTES DE CÓDIGOS IRC - RPL_* e ERR_*")
    print("="*60)
    
    tests = [
        # RPL_* (Sucessos)
        ("test_001_welcome", test_001_welcome),
        ("test_002_yourhost", test_002_yourhost),
        ("test_003_created", test_003_created),
        ("test_004_myinfo", test_004_myinfo),
        ("test_221_umodeis", test_221_umodeis),
        ("test_324_channelmodeis", test_324_channelmodeis),
        ("test_331_notopic", test_331_notopic),
        ("test_332_topic", test_332_topic),
        ("test_341_inviting", test_341_inviting),
        ("test_353_namreply", test_353_namreply),
        ("test_366_endofnames", test_366_endofnames),
        
        # ERR_* (Erros)
        ("test_401_nosuchnick", test_401_nosuchnick),
        ("test_403_nosuchchannel", test_403_nosuchchannel),
        ("test_404_cannotsendtochan", test_404_cannotsendtochan),
        ("test_409_noorigin", test_409_noorigin),
        ("test_421_unknowncommand", test_421_unknowncommand),
        ("test_431_nonicknamegiven", test_431_nonicknamegiven),
        ("test_433_nicknameinuse", test_433_nicknameinuse),
        ("test_441_usernotinchannel", test_441_usernotinchannel),
        ("test_442_notonchannel", test_442_notonchannel),
        ("test_443_useronchannel", test_443_useronchannel),
        ("test_451_notregistered", test_451_notregistered),
        ("test_461_needmoreparams", test_461_needmoreparams),
        ("test_462_alreadyregistred", test_462_alreadyregistred),
        ("test_464_passwdmismatch", test_464_passwdmismatch),
        ("test_471_channelisfull", test_471_channelisfull),
        ("test_473_inviteonlychan", test_473_inviteonlychan),
        ("test_475_badchannelkey", test_475_badchannelkey),
        ("test_482_chanoprivsneeded", test_482_chanoprivsneeded),
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
    
    # Resumo final
    total = passed + failed
    print(f"\n{'='*60}")
    print(f"  RESULTADO FINAL: {passed}/{total} códigos testados")
    if failed == 0:
        print(f"  \033[92m✅ TODOS OS CÓDIGOS IRC FUNCIONAM!\033[0m")
    elif failed < 3:
        print(f"  \033[93m⚠️  {failed} código(s) falharam\033[0m")
    else:
        print(f"  \033[91m❌ {failed} código(s) falharam\033[0m")
    print(f"{'='*60}")
    
    print(f"\n📋 CÓDIGOS IRC TESTADOS:")
    print(f"   RPL_* (Sucessos): 001-004, 221, 324, 331-332, 341, 353, 366")
    print(f"   ERR_* (Erros):    401, 403-404, 409, 421, 431, 433, 441-443,")
    print(f"                     451, 461-462, 464, 471, 473, 475, 482")
