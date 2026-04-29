from flask import Flask, request, Response, stream_with_context, redirect
import requests
import sqlite3
import random
import os
import unicodedata
import re

app = Flask(__name__)
DB_PATH = "filmes.db"
CHUNK_SIZE = 1024 * 32 

SERVIDORES_API = [
    {"host": "http://newoneblue.site:80", "user": "58257413", "pass": "19193442"},
    {"host": "http://9thgen.skin:80", "user": "11974034383", "pass": "eduardo0102"},
    {"host": "http://zerohop.sbs:80", "user": "65989464", "pass": "29348534"},
    {"host": "http://zerohop.sbs:80", "user": "8051528", "pass": "2363328"},
    {"host": "http://dnmxelk01.top:80", "user": "881101381017", "pass": "896811296068"}
]

AGENTES_VIP = [
    "EPPIPROPLAYER/1.0.8 (Linux;Android 14) AndroidXMedia3/1.5.1",
    "purpleplayer/1.2.82",
    "Dalvik/2.1.0 (Linux; U; Android 14; 2312FPCA6G Build/UP1A.231005.007)",
    "VLC/3.0.4 LibVLC/3.0.4",
    "okhttp/4.12.0"
]

def limpar(txt):
    if not txt: return ""
    txt = ''.join(c for c in unicodedata.normalize('NFD', str(txt)) if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]', '', txt.lower())

def executar_proxy(url_video):
    # Se for link pesado, joga direto pro player
    if any(x in url_video.lower() for x in ["archive.org", "googlevideo", "blogspot"]):
        return redirect(url_video)

    headers = {
        "User-Agent": random.choice(AGENTES_VIP),
        "Range": request.headers.get("Range", "bytes=0-")
    }

    try:
        r = requests.get(url_video, headers=headers, stream=True, timeout=(5, 120), allow_redirects=True)
        
        # Se o link estiver quebrado ou barrado, não fica "rodando", ele tenta o próximo link
        if r.status_code >= 400:
            return None

        def generate():
            try:
                for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                    if chunk: yield chunk
            except: pass
            finally: r.close()

        resp = Response(stream_with_context(generate()), status=r.status_code)
        resp.headers["Content-Type"] = "video/mp4"
        resp.headers["Accept-Ranges"] = "bytes"
        resp.headers["Access-Control-Allow-Origin"] = "*"
        return resp
    except:
        return None

@app.route("/buscar")
def buscar():
    titulo = request.args.get("titulo")
    if not titulo: return "Vazio", 400

    alvo = limpar(titulo)
    print(f"🔎 Analisando todas as fontes para: {alvo}")

    links_encontrados = []

    # 1. PEGA DO VIP E FILMES_SITE.TXT
    for arq in ["vips.txt", "filmes_site.txt"]:
        if os.path.exists(arq):
            with open(arq, "r", encoding="utf-8", errors="ignore") as f:
                for linha in f:
                    if "|" in linha:
                        n, u = linha.split("|", 1)
                        if alvo in limpar(n):
                            links_encontrados.append(u.strip())

    # 2. PEGA DO BANCO DE DADOS
    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT url FROM filmes WHERE nome_busca LIKE ?", (f'%{alvo}%',))
            for row in c.fetchall():
                links_encontrados.append(row[0])
            conn.close()
        except: pass

    # 3. VARRE TODAS AS APIs E JUNTA OS LINKS
    for srv in SERVIDORES_API:
        try:
            url_api = f"{srv['host']}/player_api.php?username={srv['user']}&password={srv['pass']}&action=get_vod_streams"
            r = requests.get(url_api, timeout=3).json()
            for item in r:
                if alvo in limpar(item.get('name', '')):
                    v_url = f"{srv['host']}/movie/{srv['user']}/{srv['pass']}/{item.get('stream_id')}.mp4"
                    links_encontrados.append(v_url)
        except: continue

    # ==========================================
    # HORA DA VERDADE: TESTAR QUAL LINK RESPONDE
    # ==========================================
    if not links_encontrados:
        return "Nenhum link encontrado em nenhuma fonte", 404

    print(f"📊 Encontrei {len(links_encontrados)} links. Testando o melhor...")

    # Tenta rodar cada link encontrado até um funcionar
    for url in links_encontrados:
        resultado = executar_proxy(url)
        if resultado:
            return resultado

    # Se todos falharem no proxy, tenta o redirect do último achado como última esperança
    return redirect(links_encontrados[0])

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, threaded=True)
