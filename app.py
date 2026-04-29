from flask import Flask, request, Response, stream_with_context, redirect, jsonify
import requests
import sqlite3
import random
import os
import unicodedata
import re

app = Flask(__name__)
DB_PATH = "filmes.db"
CHUNK_SIZE = 1024 * 256 

# Agentes para Smart TV e Apps não darem erro
AGENTES = [
    "VLC/3.0.20 LibVLC/3.0.20",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "okhttp/4.12.0"
]

def limpar_texto(texto):
    if not texto: return ""
    # Remove acentos
    texto = ''.join(c for c in unicodedata.normalize('NFD', str(texto)) if unicodedata.category(c) != 'Mn')
    # Mantém apenas letras e números (remove parênteses do ano, pontos, etc)
    texto = re.sub(r'[^a-zA-Z0-9]', '', texto)
    return texto.lower().strip()

def executar_proxy(url_video):
    headers = {
        "User-Agent": random.choice(AGENTES),
        "Connection": "keep-alive",
        "Accept": "*/*"
    }
    range_header = request.headers.get("Range")
    if range_header: headers["Range"] = range_header

    try:
        r = requests.get(url_video, headers=headers, stream=True, timeout=(15, 300), allow_redirects=True)
        
        def generate():
            for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                if chunk: yield chunk

        resp = Response(stream_with_context(generate()), status=r.status_code)
        resp.headers["Content-Type"] = "video/mp4"
        resp.headers["Accept-Ranges"] = "bytes"
        resp.headers["Access-Control-Allow-Origin"] = "*"
        
        if 'Content-Length' in r.headers: resp.headers['Content-Length'] = r.headers['Content-Length']
        if 'Content-Range' in r.headers: resp.headers['Content-Range'] = r.headers['Content-Range']
        
        return resp
    except:
        return redirect(url_video)

@app.route("/buscar")
def buscar():
    titulo = request.args.get("titulo")
    if not titulo: return "Vazio", 400

    # Limpamos o título que vem do site (ex: "M3GAN (2022)" vira "m3gan2022")
    t_limpo = limpar_texto(titulo)
    # Criamos uma versão sem o ano para fallback (ex: "m3gan")
    t_sem_ano = re.sub(r'\d{4}$', '', t_limpo)

    print(f"🎯 Mestre, buscando no DB: {t_limpo} ou {t_sem_ano}")

    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            
            # BUSCA INTELIGENTE: Tenta o nome com ano, depois sem ano, depois por aproximação
            c.execute("""
                SELECT url FROM filmes 
                WHERE nome_busca = ? 
                OR nome_busca = ? 
                OR nome_busca LIKE ? 
                LIMIT 1
            """, (t_limpo, t_sem_ano, f"%{t_sem_ano}%"))
            
            res = c.fetchone()
            conn.close()
            
            if res:
                return executar_proxy(res[0])
        except Exception as e:
            print(f"Erro DB: {e}")

    # BACKUP VIP.TXT
    if os.path.exists("vips.txt"):
        with open("vips.txt", "r", encoding="utf-8", errors="ignore") as f:
            for linha in f:
                if "|" in linha:
                    nome, url = linha.split("|", 1)
                    n_vip = limpar_texto(nome)
                    if t_sem_ano in n_vip or n_vip in t_sem_ano:
                        return executar_proxy(url.strip())

    return "Filme não encontrado no DB", 404

@app.route("/")
def index():
    return "🚀 Motor v21 - Sincronizado com filmes.db!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
