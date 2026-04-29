from flask import Flask, request, Response, stream_with_context, redirect
import requests
import sqlite3
import random
import os
import unicodedata
import re
import datetime

app = Flask(__name__)

# =========================
# CONFIGURAÇÕES OTIMIZADAS
# =========================
LOG_FILE = "logs_erros.txt"
DB_PATH = "filmes.db"

TIMEOUT_CONNECT = 10
TIMEOUT_READ = 180

# Chunk de 256KB: O "Ponto Doce" para não crashar o Chrome nem o UC Browser
CHUNK_SIZE = 1024 * 256 

# Seus Agentes de Elite para enganar qualquer servidor
AGENTES = [
    "EPPIPROPLAYER/1.0.8 (Linux;Android 14) AndroidXMedia3/1.5.1",
    "purpleplayer/1.2.82",
    "Dalvik/2.1.0 (Linux; U; Android 14; 2312FPCA6G Build/UP1A.231005.007)",
    "VLC/3.0.4 LibVLC/3.0.4",
    "okhttp/4.12.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

def registrar_log(titulo, url, erro):
    try:
        agora = datetime.datetime.now()
        linha = f"\n{agora}\nFILME: {titulo}\nURL: {url}\nERRO: {erro}\n----------------------\n"
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(linha)
    except:
        pass

def limpar_texto(texto):
    if not texto: return ""
    texto = ''.join(c for c in unicodedata.normalize('NFD', str(texto)) if unicodedata.category(c) != 'Mn')
    texto = re.sub(r'[^a-zA-Z0-9\s]', ' ', texto)
    return re.sub(r'\s+', ' ', texto).strip().lower()

# =========================
# LEITOR DE TXT (VIP.TXT)
# =========================

def ler_txt_vip():
    acervo = {}
    caminho = "vips.txt"
    if os.path.exists(caminho):
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                for linha in f:
                    if "|" in linha:
                        nome, url = linha.split("|", 1)
                        # Limpa espaços e normaliza para a busca bater
                        acervo[limpar_texto(nome.strip())] = url.strip()
        except Exception as e:
            registrar_log("LER_VIP", caminho, str(e))
    return acervo

# =========================
# PROXY ULTRA ESTÁVEL (CORREÇÃO M3GAN)
# =========================

def executar_proxy(url_video, titulo):
    try:
        headers = {
            "User-Agent": random.choice(AGENTES),
            "Connection": "keep-alive",
            "Accept": "*/*"
        }

        range_header = request.headers.get("Range")
        if range_header:
            headers["Range"] = range_header

        r = requests.get(
            url_video,
            headers=headers,
            stream=True,
            timeout=(TIMEOUT_CONNECT, TIMEOUT_READ),
            allow_redirects=True
        )

        if r.status_code >= 400:
            registrar_log(titulo, url_video, f"HTTP {r.status_code}")
            return redirect(url_video)

        def generate():
            for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                if chunk:
                    yield chunk

        resp_headers = {
            "Content-Type": "video/mp4",
            "Accept-Ranges": "bytes",
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "no-cache",
            "X-Content-Type-Options": "nosniff"
        }

        if r.headers.get("Content-Length"):
            resp_headers["Content-Length"] = r.headers["Content-Length"]
        if r.headers.get("Content-Range"):
            resp_headers["Content-Range"] = r.headers["Content-Range"]

        return Response(
            stream_with_context(generate()),
            status=r.status_code,
            headers=resp_headers
        )

    except Exception as e:
        registrar_log(titulo, url_video, str(e))
        return redirect(url_video)

# =========================
# BUSCA DB OTIMIZADA
# =========================

def buscar_db(titulo_limpo):
    if not os.path.exists(DB_PATH):
        return None
    try:
        # Usamos o row_factory para ler melhor as colunas se precisar
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # 1. TENTA BUSCA EXATA (Para não trocar o 1 pelo 2)
        c.execute("SELECT url FROM filmes WHERE nome_busca = ? LIMIT 1", (titulo_limpo,))
        res = c.fetchone()
        
        # 2. SE NÃO ACHOU, TENTA BUSCA POR INÍCIO (Startswith)
        if not res:
            c.execute("SELECT url FROM filmes WHERE nome_busca LIKE ? LIMIT 1", (f"{titulo_limpo}%",))
            res = c.fetchone()
            
        conn.close()
        return res[0] if res else None
    except Exception as e:
        registrar_log(titulo_limpo, "ERRO_DB", str(e))
        return None

# =========================
# ROTA PRINCIPAL
# =========================

@app.route("/buscar")
def buscar():
    titulo = request.args.get("titulo")
    if not titulo:
        return "Título vazio", 400

    titulo_limpo = limpar_texto(titulo)
    print(f"🎯 Mestre, buscando no DB: {titulo_limpo}")

    # --- ORDEM DE PRIORIDADE ---
    
    # 1. BANCO DE DADOS (Seu foco total)
    url = buscar_db(titulo_limpo)
    
    # 2. VIP.TXT (Backup manual em segundo lugar)
    if not url:
        vips = ler_txt_vip()
        if titulo_limpo in vips:
            url = vips[titulo_limpo]
        else:
            # Tenta busca aproximada no VIP se não achou exata
            for nome, u in vips.items():
                if nome.startswith(titulo_limpo):
                    url = u
                    break

    if url:
        return executar_proxy(url, titulo)

    registrar_log(titulo, "Global", "Filme não encontrado em nenhuma fonte")
    return "Filme não encontrado", 404

@app.route("/")
def index():
    return "🚀 Motor Cine Mega v19 - Foco DB & VIP Ativo!"

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000))
    )
