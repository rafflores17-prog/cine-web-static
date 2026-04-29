import os
import random
import requests
import unicodedata
import re
from flask import Flask, request, Response, stream_with_context, redirect

app = Flask(__name__)

# FONTES QUERIDINHAS
FONTES = {
    "1": {"host": "http://serv99.xyz:8880", "user": "1764371", "pass": "2419902"},
    "2": {"host": "http://nxpanelxr51.info", "user": "sandroalvares2", "pass": "T9er2T"}
}

def limpar_busca(txt):
    if not txt: return ""
    # Remove anos, exclamações e símbolos para busca ampla
    txt = re.sub(r'\(\d{4}\)', '', str(txt))
    txt = ''.join(c for c in unicodedata.normalize('NFD', txt) if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]', '', txt.lower())

@app.route("/play")
def play():
    titulo = request.args.get("titulo")
    fonte_id = request.args.get("fonte", "1")
    
    if not titulo: return "Vazio", 400
    
    alvo = limpar_busca(titulo)
    srv = FONTES.get(fonte_id)
    if not srv: return "Fonte OFF", 404

    print(f"🎬 Buscando: {alvo} na Fonte {fonte_id}")

    try:
        url_api = f"{srv['host']}/player_api.php?username={srv['user']}&password={srv['pass']}&action=get_vod_streams"
        r = requests.get(url_api, timeout=5)
        dados = r.json()
        
        for item in dados:
            nome_api = limpar_busca(item.get('name', ''))
            # Busca flexível: se o nome bater parcialmente, ele manda o play
            if alvo in nome_api or nome_api in alvo:
                v_url = f"{srv['host']}/movie/{srv['user']}/{srv['pass']}/{item.get('stream_id')}.mp4"
                print(f"✅ Sucesso: {item.get('name')}")
                
                # REDIRECT DIRETO: É o único jeito de não travar a CPU e rodar American Pie
                return redirect(v_url)
    except Exception as e:
        print(f"❌ Erro na busca: {e}")
    
    return "Nao achou", 404

@app.route("/")
def index():
    return "Cine Mega v47 Online"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, threaded=True)
