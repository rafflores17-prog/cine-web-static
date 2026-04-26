from flask import Flask, render_template, request, send_from_directory, jsonify, Response, stream_with_context
import requests
import re
import os
import random
import sqlite3
import glob
from urllib.parse import quote

app = Flask(__name__)

# Configurações TMDB
TMDB_API_KEY = "c90fb79a2f7d756a49bee848bce5f413"
IMG = "https://image.tmdb.org/t/p/w500"
BG = "https://image.tmdb.org/t/p/original"

# 🚀 AGENTES VIP DO SEU BACKUP (OS QUE FUNCIONAM!)
AGENTES_VIP = [
    "EPPIPROPLAYER/1.0.8 (Linux;Android 14) AndroidXMedia3/1.5.1",
    "purpleplayer/1.2.82",
    "Dalvik/2.1.0 (Linux; U; Android 14; 2312FPCA6G Build/UP1A.231005.007)",
    "Dart/3.11 (dart:io)"
]

# ================================
# PROXY REVISADO (FORÇA BRUTA)
# ================================
@app.route("/proxy")
def proxy_video():
    url = request.args.get("url")
    user_agent_custom = request.args.get("user_agent")
    
    if not url: return "URL vazia", 400

    try:
        # Usa o agente do seu backup ou sorteia um VIP
        agente = user_agent_custom if user_agent_custom else random.choice(AGENTES_VIP)
        
        headers = {
            "User-Agent": agente,
            "Accept": "*/*",
            "Connection": "keep-alive",
            "Referer": "http://iptv.com" # Referer fixo para enganar o servidor
        }

        # Repassa o Range (essencial para o Chrome não crashar e poder avançar o filme)
        range_header = request.headers.get('Range', None)
        if range_header: headers['Range'] = range_header

        r = requests.get(url, headers=headers, stream=True, timeout=(5, 30), allow_redirects=True, verify=False)

        def generate():
            try:
                for chunk in r.iter_content(chunk_size=1024 * 128):
                    if chunk: yield chunk
            finally: r.close()

        # 🛡️ CABEÇALHOS QUE LIBERAM O CHOME E UC BROWSER
        resp_headers = {
            "Accept-Ranges": "bytes",
            "Access-Control-Allow-Origin": "*", # LIBERA O CHROME!
            "Cache-Control": "no-store",
            "Connection": "keep-alive"
        }
        
        if 'Content-Range' in r.headers: resp_headers['Content-Range'] = r.headers['Content-Range']
        if 'Content-Length' in r.headers: resp_headers['Content-Length'] = r.headers['Content-Length']

        return Response(
            stream_with_context(generate()),
            status=r.status_code,
            content_type=r.headers.get("Content-Type", "video/mp4"),
            headers=resp_headers
        )
    except Exception as e:
        return f"Erro Proxy: {e}", 500

# ================================
# BUSCA MULTI-BANCO (DATA1...DATA12)
# ================================
def buscar_filme(titulo):
    try:
        # Limpeza do título (estratégia do seu backup)
        titulo_limpo = re.sub(r'[^\w\s]', '', titulo).lower().strip()
        # Pega as duas primeiras palavras para busca assertiva
        palavras = titulo_limpo.split()
        termo = " ".join(palavras[:2]) if len(palavras) > 1 else palavras[0]

        # 🔍 Escaneia todos os bancos data*.db
        bancos = glob.glob("data*.db")
        for db_nome in sorted(bancos):
            try:
                conn = sqlite3.connect(db_nome)
                c = conn.cursor()
                # Busca que prioriza o nome mais curto (evita lixo)
                c.execute("SELECT url FROM playlist WHERE nome LIKE ? ORDER BY LENGTH(nome) ASC LIMIT 1", (f"%{termo}%",))
                res = c.fetchone()
                conn.close()
                if res:
                    agente = random.choice(AGENTES_VIP)
                    # Codifica a URL corretamente para o Proxy
                    return f"/proxy?url={quote(res[0], safe='')}&user_agent={quote(agente)}"
            except: continue
        
        # 🌐 FALLBACK API (Se não achar nos 12 bancos)
        # (Sua lista de servidores aqui...)
    except: pass
    return None

# ================================
# ROTAS PADRÃO (HOME E DETALHES)
# ================================
@app.route("/")
def home():
    q = request.args.get("q")
    url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&language=pt-BR&query={q}" if q else f"https://api.themoviedb.org/3/movie/popular?api_key={TMDB_API_KEY}&language=pt-BR"
    try: res = requests.get(url, timeout=10).json().get("results", [])
    except: res = []
    return render_template("index.html", filmes=res[:20], img=IMG, nome_site="Cine Mega")

@app.route("/filme/<int:id>")
def detalhes(id):
    try:
        data = requests.get(f"https://api.themoviedb.org/3/movie/{id}?api_key={TMDB_API_KEY}&language=pt-BR&append_to_response=videos", timeout=10).json()
        play_link = buscar_filme(data.get('title', ''))
        trailer = next((v['key'] for v in data.get('videos', {}).get('results', []) if v['type'] == 'Trailer'), None)
        return render_template("detalhes.html", filme=data, img=IMG, bg=BG, play_link=play_link, trailer_key=trailer)
    except: return "Erro", 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
