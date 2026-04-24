from flask import Flask, render_template, request, redirect
import requests
import random
import re

app = Flask(__name__)

NOME_SITE = "Cine Mega"
TMDB_API_KEY = "c90fb79a2f7d756a49bee848bce5f413"
IMG = "https://image.tmdb.org/t/p/w500"
BG = "https://image.tmdb.org/t/p/original"

SERVIDORES = [
    {"host": "http://serv99.xyz:8880", "user": "261491762", "pass": "2516895925"},
    {"host": "http://stmax.top:80", "user": "lucas6043", "pass": "px2926br"},
    {"host": "http://koquwz.com:80", "user": "471204", "pass": "epp4Jx"},
    {"host": "http://koquwz.com:80", "user": "douglas20102010", "pass": "Ss12345678"},
    {"host": "http://techon.one:80", "user": "003008", "pass": "440144634"},
    {"host": "http://sventank.com:80", "user": "123456", "pass": "654321"}
]

# ROTA SECRETA PARA ENGANAR O CHROME
@app.route("/stream/<int:srv_idx>/<int:stream_id>.mp4")
def proxy_stream(srv_idx, stream_id):
    srv = SERVIDORES[srv_idx]
    # O link real nunca sai do Python, o navegador só vê o seu domínio
    link_real = f"{srv['host']}/movie/{srv['user']}/{srv['pass']}/{stream_id}.mp4"
    return redirect(link_real)

def buscar_no_iptv(titulo_filme):
    titulo_busca = re.sub(r'[^\w\s]', '', titulo_filme).lower().strip()
    for idx, srv in enumerate(SERVIDORES):
        url_api = f"{srv['host']}/player_api.php?username={srv['user']}&password={srv['pass']}&action=get_vod_streams"
        try:
            r = requests.get(url_api, timeout=5)
            for item in r.json():
                nome_iptv = re.sub(r'[^\w\s]', '', item.get('name', '')).lower()
                if titulo_busca == nome_iptv or (titulo_busca in nome_iptv and len(nome_iptv) < len(titulo_busca) + 12):
                    # Retornamos o link do NOSSO site para o player interno
                    return f"/stream/{idx}/{item.get('stream_id')}.mp4", f"{srv['host']}/movie/{srv['user']}/{srv['pass']}/{item.get('stream_id')}.mp4"
        except: continue
    return None, None

@app.route("/")
def home():
    res = requests.get(f"https://api.themoviedb.org/3/movie/popular?api_key={TMDB_API_KEY}&language=pt-BR").json().get("results", [])
    random.shuffle(res)
    return render_template("index.html", filmes=res[:20], img=IMG, nome_site=NOME_SITE)

@app.route("/filme/<int:id>")
def filme(id):
    f_data = requests.get(f"https://api.themoviedb.org/3/movie/{id}?api_key={TMDB_API_KEY}&language=pt-BR").json()
    link_interno, link_real = buscar_no_iptv(f_data.get('title', ''))
    videos = requests.get(f"https://api.themoviedb.org/3/movie/{id}/videos?api_key={TMDB_API_KEY}&language=pt-BR").json().get("results", [])
    trailer = next((v['key'] for v in videos if v['type'] == 'Trailer'), None)
    return render_template("detalhes.html", filme=f_data, img=IMG, bg=BG, trailer=trailer, play_interno=link_interno, play_real=link_real, nome_site=NOME_SITE)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
