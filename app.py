from flask import Flask, request, Response, stream_with_context, redirect
import requests
import sqlite3
import random
import os
import unicodedata
import re

app = Flask(__name__)
DB_PATH = "filmes.db"

# CHUNK MENOR = CPU BAIXO. 128KB é perfeito para streaming sem travar o servidor.
CHUNK_SIZE = 1024 * 128 

AGENTES = [
    "VLC/3.0.20 LibVLC/3.0.20",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "okhttp/4.12.0"
]

def extrair_letras(txt):
    if not txt: return ""
    txt = ''.join(c for c in unicodedata.normalize('NFD', str(txt)) if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]', '', txt.lower()) # Mantemos números para diferenciar o 1 do 2!

def executar_proxy(url_video):
    headers = {
        "User-Agent": random.choice(AGENTES),
        "Connection": "keep-alive",
        "Range": request.headers.get("Range", "bytes=0-")
    }

    try:
        # Timeout curto na conexão para não prender o CPU
        r = requests.get(url_video, headers=headers, stream=True, timeout=(5, 300), allow_redirects=True)
        
        def generate():
            try:
                for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                    if chunk: yield chunk
            except:
                pass # Se a conexão quebrar, ele apenas para de enviar em vez de dar erro 500

        resp = Response(stream_with_context(generate()), status=r.status_code)
        resp.headers["Content-Type"] = "video/mp4"
        resp.headers["Accept-Ranges"] = "bytes"
        resp.headers["Access-Control-Allow-Origin"] = "*"
        if 'Content-Range' in r.headers: resp.headers['Content-Range'] = r.headers['Content-Range']
        if 'Content-Length' in r.headers: resp.headers['Content-Length'] = r.headers['Content-Length']
        
        return resp
    except:
        return redirect(url_video)

@app.route("/buscar")
def buscar():
    titulo = request.args.get("titulo")
    if not titulo: return "Vazio", 400

    # Agora limpamos mantendo os números para não confundir as franquias
    alvo = extrair_letras(titulo)
    print(f"🔎 Buscando: {alvo}")

    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT url, nome FROM filmes")
            todos = c.fetchall()
            conn.close()

            # BUSCA DE PRECISÃO:
            # 1. Tenta achar exatamente o que foi pedido (Nome + Ano/Número)
            for url_db, nome_db in todos:
                if alvo == extrair_letras(nome_db):
                    return executar_proxy(url_db)
            
            # 2. Se não achou exato, tenta o que começa com (StartsWith)
            for url_db, nome_db in todos:
                if extrair_letras(nome_db).startswith(alvo):
                    return executar_proxy(url_db)
                    
        except: pass

    # Backup VIP.txt (Mesma lógica de precisão)
    if os.path.exists("vips.txt"):
        with open("vips.txt", "r", encoding="utf-8", errors="ignore") as f:
            for linha in f:
                if "|" in linha:
                    nome_vip, url_vip = linha.split("|", 1)
                    if alvo == extrair_letras(nome_vip):
                        return executar_proxy(url_vip.strip())

    return "Nao encontrado", 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
