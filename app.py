import os
import time
import requests
from flask import Flask, jsonify, request, render_template

app = Flask(__name__, template_folder="templates")

# ==========================
# CONFIG
# ==========================

TIMEOUT = 10
CACHE_TTL = 300

cache = {}

# ==========================
# SERVIDORES (fallback)
# ==========================

SERVIDORES = [

    {
        "nome": "Serv99",
        "tipo": "api",
        "host": "http://serv99.xyz:8880",
        "user": "261491762",
        "pass": "2516895925"
    },

    {
        "nome": "Falcon",
        "tipo": "m3u",
        "url": "http://falcon12.top:80/get.php?username=175473583&password=643238922&type=m3u_plus&output=ts"
    },

    {
        "nome": "Dark1",
        "tipo": "m3u",
        "url": "http://d4rk.info:80/get.php?username=GLedsoonn777&password=PErtilee444&type=m3u_plus&output=ts"
    }

]

# ==========================
# CACHE
# ==========================

def get_cache(key):

    if key in cache:

        data, t = cache[key]

        if time.time() - t < CACHE_TTL:
            return data

        del cache[key]

    return None


def set_cache(key, data):

    cache[key] = (data, time.time())


# ==========================
# BUSCA COM FALLBACK
# ==========================

def buscar_filme(nome):

    key = f"busca:{nome}"

    cached = get_cache(key)

    if cached:
        return cached

    for srv in SERVIDORES:

        try:

            print("Tentando:", srv["nome"])

            if srv["tipo"] == "api":

                url = (
                    f"{srv['host']}/player_api.php"
                    f"?username={srv['user']}"
                    f"&password={srv['pass']}"
                    f"&action=get_vod_streams"
                )

                r = requests.get(url, timeout=TIMEOUT)

                if nome.lower() in r.text.lower():

                    set_cache(key, r.text)

                    return r.text

            elif srv["tipo"] == "m3u":

                r = requests.get(
                    srv["url"],
                    timeout=TIMEOUT
                )

                if nome.lower() in r.text.lower():

                    set_cache(key, r.text)

                    return r.text

        except Exception as e:

            print("Erro:", e)

            continue

    return None


# ==========================
# ROTAS DO SITE
# ==========================

@app.route("/")
def index():

    return render_template(
        "index.html"
    )


@app.route("/detalhe")
def detalhe():

    return render_template(
        "detalhe.html"
    )


# ==========================
# API
# ==========================

@app.route("/buscar")
def buscar():

    nome = request.args.get("nome")

    if not nome:

        return jsonify({
            "erro": "Informe ?nome=filme"
        })

    resultado = buscar_filme(nome)

    if resultado:

        return jsonify({
            "status": "ok"
        })

    return jsonify({
        "status": "nao_encontrado"
    )


@app.route("/health")
def health():

    return "OK"


# ==========================
# START (Koyeb)
# ==========================

if __name__ == "__main__":

    PORT = int(os.environ.get("PORT", 8000))

    app.run(
        host="0.0.0.0",
        port=PORT
    )
