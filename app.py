from flask import Flask, request, Response, stream_with_context, redirect
import requests
import sqlite3
import random
import os
import unicodedata
import re

app = Flask(__name__)
DB_PATH = "filmes.db"
CHUNK_SIZE = 1024 * 64 

# LISTA DE FONTES COM ID (Para você escolher no seu painel)
SERVIDORES_API = [
    {"id": "0", "nome": "BlueOne", "host": "http://newoneblue.site:80", "user": "58257413", "pass": "19193442"},
    {"id": "1", "nome": "9thGen", "host": "http://9thgen.skin:80", "user": "11974034383", "pass": "eduardo0102"},
    {"id": "2", "nome": "ZeroHop_1", "host": "http://zerohop.sbs:80", "user": "65989464", "pass": "29348534"},
    {"id": "3", "nome": "ZeroHop_2", "host": "http://zerohop.sbs:80", "user": "8051528", "pass": "2363328"},
    {"id": "4", "nome": "Dnmx", "host": "http://dnmxelk01.top:80", "user": "881101381017", "pass": "896811296068"}
]

AGENTES_VIP = [
    "EPPIPROPLAYER/1.0.8 (Linux;Android 14)",
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
    # Redirect para economizar CPU em links conhecidos
    if any(x in url_video.lower() for x in [":80", "archive.org", "googlevideo"]):
        return redirect(url_video)

    headers = {
        "User-Agent": random.choice(AGENTES_VIP),
        "Range": request.headers.get("Range", "bytes=0-")
    }

    try:
        r = requests.get(url_video, headers=headers, stream=True, timeout=(5, 300), allow_redirects=True)
        if r.status_code >= 400: return redirect(url_video)

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
        return redirect(url_video)

@app.route("/buscar")
def buscar():
    titulo = request.args.get("titulo")
    fonte_id = request.args.get("fonte") # Novo parâmetro manual
    
    if not titulo: return "Vazio", 400
    alvo = limpar(titulo)

    # 1. PRIORIDADE SEMPRE: SEUS ARQUIVOS (vips.txt / filmes.db)
    # Se ele achar no seu banco, ele nem gasta API
    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT url FROM filmes WHERE nome_busca LIKE ? LIMIT 1", (f'%{alvo}%',))
            res = c.fetchone()
            conn.close()
            if res: 
                print(f"✅ Achado no Banco Local: {alvo}")
                return executar_proxy(res[0])
        except: pass

    # 2. SELEÇÃO MANUAL DE API
    # Se você passar &fonte=ID, ele vai direto nela
    srv = next((s for s in SERVIDORES_API if s['id'] == fonte_id), None)
    
    if srv:
        print(f"🚀 Rodando Fonte Manual [{srv['nome']}]: {alvo}")
        try:
            url_api = f"{srv['host']}/player_api.php?username={srv['user']}&password={srv['pass']}&action=get_vod_streams"
            r = requests.get(url_api, timeout=5).json()
            for item in r:
                if alvo in limpar(item.get('name', '')):
                    v_url = f"{srv['host']}/movie/{srv['user']}/{srv['pass']}/{item.get('stream_id')}.mp4"
                    return executar_proxy(v_url)
        except:
            return "Erro na fonte selecionada", 500
    else:
        # Se não escolher fonte, ele tenta a primeira por padrão para não dar erro
        print(f"⚠️ Nenhuma fonte manual válida. Tentando busca geral...")
        # Aqui você pode manter a lógica de tentar todas uma por uma (serial)
        # ou apenas retornar erro pedindo para escolher a fonte.

    return "Filme não encontrado na fonte selecionada", 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, threaded=True)
