from flask import Flask, request, Response, stream_with_context, redirect
import requests
import sqlite3
import random
import os
import unicodedata
import re
import datetime
import difflib # 🤖 A Mente do Robô de Busca

app = Flask(__name__)

# =========================
# CONFIG
# =========================
LOG_FILE = "logs_erros.txt"

AGENTES_VIP = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "okhttp/4.12.0",
    "VLC/3.0.4 LibVLC/3.0.4",
    "Dalvik/2.1.0 (Linux; U; Android 14)"
]

SERVIDORES_API = [
    {"nome": "Mnba", "host": "http://mnba.shop:80", "user": "danicamara", "pass": "acg2010v"},
    {"nome": "Dnsrot", "host": "http://play.dnsrot.vip:80", "user": "sheilalima11", "pass": "s6dfkck1jlq"},
    {"nome": "Kmediaplay", "host": "http://kmediaplay.click:80", "user": "Indio1432", "pass": "indio1433"}
]

API_CACHE = {}

# =========================
# LIMPAR TEXTO
# =========================
def limpar_texto(texto):
    if not texto: return ""
    texto = ''.join(c for c in unicodedata.normalize('NFD', str(texto)) if unicodedata.category(c) != 'Mn')
    texto = re.sub(r'[^a-zA-Z0-9\s]', ' ', texto)
    return re.sub(r'\s+', ' ', texto).strip().lower()

# =========================
# LOG ERROS
# =========================
def registrar_log(titulo, url, erro):
    try:
        agora = datetime.datetime.now()
        linha = f"\n[{agora}]\nFILME: {titulo}\nURL: {url}\nERRO: {erro}\n----------------------\n"
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(linha)
    except: pass

# =========================
# CARREGAR TXT
# =========================
def ler_txt(caminho):
    acervo = {}
    if os.path.exists(caminho):
        with open(caminho, "r", encoding="utf-8") as f:
            for linha in f:
                if "|" in linha:
                    n, u = linha.split("|", 1)
                    acervo[limpar_texto(n)] = u.strip()
    return acervo

print("Carregando listas para a RAM...")
VIP_CACHE = ler_txt("vips.txt")
GIGANTE_CACHE = ler_txt("filmes_site.txt")
print("Listas carregadas com sucesso.")

# =========================
# ROBÔ DE BUSCA INTELIGENTE (Fim do Bug das Trilogias)
# =========================
def similaridade(a, b):
    # Dá uma nota de 0.0 a 1.0 para o quanto os textos são iguais
    return difflib.SequenceMatcher(None, a, b).ratio()

def busca_inteligente(t_limpo, acervo):
    # 1. Se existir o nome exato, ganha imediatamente (Nota 100%)
    if t_limpo in acervo:
        return acervo[t_limpo]

    melhor_url = None
    maior_nota = 0.0

    # 2. Varredura com Robô: Avalia quem tem a maior nota de semelhança
    for nome_db, url in acervo.items():
        if t_limpo in nome_db:
            nota = similaridade(t_limpo, nome_db)
            # Penaliza filmes que tenham números a mais se a busca não tiver
            if re.search(r'\d', nome_db) and not re.search(r'\d', t_limpo):
                nota -= 0.15 

            if nota > maior_nota:
                maior_nota = nota
                melhor_url = url

    # Só aceita se a nota for alta (evita puxar lixo)
    if maior_nota >= 0.70:
        return melhor_url

    return None

# =========================
# O VIGIA E PROXY
# =========================
def executar_proxy(url_video, titulo):
    agente = random.choice(AGENTES_VIP)
    headers = {
        "User-Agent": agente,
        "Connection": "keep-alive"
    }
    range_header = request.headers.get("Range")
    if range_header: headers["Range"] = range_header

    try:
        # O Vigia faz o pedido
        r = requests.get(url_video, headers=headers, stream=True, timeout=(5, 60), allow_redirects=True)
        
        # 🚨 VIGIA EM AÇÃO: Se der erro ou se o IPTV mandar HTML em vez de vídeo, ele REJEITA!
        content_type = r.headers.get("Content-Type", "").lower()
        if r.status_code >= 400 or 'text' in content_type or 'html' in content_type:
            registrar_log(titulo, url_video, f"Vigia Bloqueou: Status {r.status_code} ou não é vídeo ({content_type})")
            r.close()
            return None # Retorna None para o motor testar o próximo link!

        def generate():
            # Chunk de 256KB para não engasgar o player do browser
            for chunk in r.iter_content(chunk_size=256 * 1024):
                if chunk: yield chunk

        resp_headers = {
            "Accept-Ranges": "bytes",
            "Access-Control-Allow-Origin": "*",
            "Content-Type": "video/mp4", # Força a ser vídeo
            "Cache-Control": "no-cache",
            "X-Content-Type-Options": "nosniff"
        }
        
        if 'Content-Range' in r.headers: resp_headers['Content-Range'] = r.headers['Content-Range']
        if 'Content-Length' in r.headers: resp_headers['Content-Length'] = r.headers['Content-Length']

        return Response(stream_with_context(generate()), status=r.status_code, headers=resp_headers)

    except Exception as e:
        registrar_log(titulo, url_video, f"Queda de Conexão: {str(e)}")
        return None

# =========================
# BUSCAS (DB E API)
# =========================
def buscar_no_db(t_limpo):
    try:
        if not os.path.exists("filmes.db"): return None
        conn = sqlite3.connect("filmes.db")
        c = conn.cursor()
        
        # Tenta o nome exato primeiro
        c.execute("SELECT url FROM playlist WHERE search_name = ? LIMIT 1", (t_limpo,))
        res = c.fetchone()
        
        # Se não achar, usa o robô (LIKE)
        if not res:
            c.execute("SELECT url FROM playlist WHERE search_name LIKE ? LIMIT 1", (f"{t_limpo} %",))
            res = c.fetchone()
            
        conn.close()
        if res: return res[0]
    except Exception as e:
        registrar_log(t_limpo, "DB Local", str(e))
    return None

def buscar_nas_apis(t_limpo):
    for srv in SERVIDORES_API:
        try:
            if srv["nome"] not in API_CACHE:
                url_api = f"{srv['host']}/player_api.php?username={srv['user']}&password={srv['pass']}&action=get_vod_streams"
                API_CACHE[srv["nome"]] = requests.get(url_api, timeout=5).json()

            dados = API_CACHE[srv["nome"]]
            
            # Aplica a mente do robô nas APIs também!
            melhor_url = None
            maior_nota = 0.0

            for item in dados:
                nome_api = limpar_texto(item.get("name", ""))
                if t_limpo in nome_api:
                    nota = similaridade(t_limpo, nome_api)
                    if re.search(r'\d', nome_api) and not re.search(r'\d', t_limpo):
                        nota -= 0.15 
                        
                    if nota > maior_nota:
                        maior_nota = nota
                        melhor_url = f"{srv['host']}/movie/{srv['user']}/{srv['pass']}/{item.get('stream_id')}.mp4"

            if maior_nota >= 0.70 and melhor_url:
                return melhor_url

        except Exception as e:
            registrar_log(t_limpo, f"API {srv['nome']}", str(e))
    return None

# =========================
# ROTA PRINCIPAL
# =========================
@app.route("/buscar")
def buscar():
    titulo = request.args.get("titulo")
    if not titulo: return "Título vazio", 400
    
    t_limpo = limpar_texto(titulo)
    print(f"🔎 O Robô está buscando: {t_limpo}")

    # Lista de prioridades do Vigia
    fontes = [
        ("VIP", lambda: busca_inteligente(t_limpo, VIP_CACHE)),
        ("DB", lambda: buscar_no_db(t_limpo)),
        ("API", lambda: buscar_nas_apis(t_limpo)),
        ("GIGANTE", lambda: busca_inteligente(t_limpo, GIGANTE_CACHE))
    ]

    # O Vigia testa cada fonte
    for nome_fonte, funcao_busca in fontes:
        url_encontrada = funcao_busca()
        
        if url_encontrada:
            print(f"✅ Encontrado em {nome_fonte}, o Vigia está a testar a qualidade...")
            resp = executar_proxy(url_encontrada, titulo)
            
            # Se a resposta existir, o Vigia aprovou! Se não, o loop continua e tenta a próxima fonte.
            if resp:
                print(f"🚀 Filme Aprovado e a rodar!")
                return resp
            else:
                print(f"❌ Vigia Bloqueou link do {nome_fonte} (Quebrado). Tentando próximo...")

    registrar_log(titulo, "Todas as Fontes", "O Vigia testou todos os links encontrados e todos estavam mortos, ou o filme não existe.")
    return "Filme não encontrado ou todos os links estão offline", 404

# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
