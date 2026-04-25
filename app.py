import os
import time
import requests
from flask import Flask, jsonify, request, send_from_directory
from threading import Lock

app = Flask(__name__, static_folder="static")

# =============================
# CONFIG
# =============================

TIMEOUT = 10
CACHE_TTL = 300

cache = {}
lock = Lock()

# =============================
# SERVIDORES
# =============================

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
    },

    {
        "nome": "Dark2",
        "tipo": "m3u",
        "url": "http://d4rk.info:80/get.php?username=21998570202&password=Asd7920&type=m3u_plus&output=ts"
    },

    {
        "nome": "Techon",
        "tipo": "api",
        "host": "http://techon.one:80",
        "user": "",
        "pass": ""
    },

    {
        "nome": "Stmax",
        "tipo": "api",
        "host": "http://stmax.top:80",
        "user": "",
        "pass": ""
    }

]

# =============================
# CACHE
# =============================

def get_cache(key):

    with lock:

        if key in cache:

            data, t = cache[key]

            if time.time() - t < CACHE_TTL:
                return data

            del cache[key]

    return None


def set_cache(key, data):

    with lock:
        cache[key] = (data, time.time())


# =============================
# BUSCA
# =============================

def buscar_filme(nome):

    key = f"busca:{nome}"

    cached = get_cache(key)

    if cached:
        return cached

    for srv in SERVIDORES:

        try:

            print("Tentando:", srv["nome"])

            if srv["tipo"] == "api":

                if not srv["user"]:
                    continue

                url = (
                    f"{srv['host']}/player_api.php"
                    f"?username={srv['user']}"
                    f"&password={srv['pass']}"
                    f"&action=get_vod_streams"
                )

                r = requests.get(
                    url,
                    timeout=TIMEOUT
                )

                if r.status_code != 200:
                    continue

                if nome.lower() in r.text.lower():

                    set_cache(key, r.text)

                    return r.text

            elif srv["tipo"] == "m3u":

                r = requests.get(
                    srv["url"],
                    timeout=TIMEOUT
                )

                if r.status_code != 200:
                    continue

                if nome.lower() in r.text.lower():

                    set_cache(key, r.text)

                    return r.text

        except Exception as e:

            print("Erro:", e)

            continue

    return None


# =============================
# ROTAS DO SITE
# =============================

@app.route("/")
def index():

    return send_from_directory(
        "static",
        "index.html"
    )


@app.route("/detalhe")
def detalhe():

    return send_from_directory(
        "static",
        "detalhe.html"
    )


# =============================
# API
# =============================

@app.route("/buscar")
def buscar():

    nome = request.args.get("nome")

    if not nome:

        return jsonify({

            "erro": "Informe ?nome=filme"

        }), 400

    resultado = buscar_filme(nome)

    if resultado:

        return jsonify({

            "status": "ok"

        })

    return jsonify({

        "status": "nao_encontrado"

    })


@app.route("/health")
def health():

    return "OK", 200


# =============================
# START
# =============================

if __name__ == "__main__":

    PORT = int(
        os.environ.get(
            "PORT",
            8000
        )
    )

    app.run(
        host="0.0.0.0",
        port=PORT
    )
