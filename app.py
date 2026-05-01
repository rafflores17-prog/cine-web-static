import os
import re
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

M3U_URL = "https://github.com/StartStatic1/meus-apks/releases/download/V_backup/lista.m3u"

catalogo_filmes = []

# LIMPAR NOME (VERSÃO SEGURA)
def limpar(nome):
    nome = str(nome).lower()

    nome = re.sub(r'\(.*?\)', '', nome)
    nome = re.sub(r'\[.*?\]', '', nome)

    nome = nome.replace(":", "")
    nome = nome.replace("-", " ")
    nome = nome.replace(".", " ")

    return " ".join(nome.split())

# CARREGAR M3U
def carregar_arquivos():
    print("⏳ Carregando M3U...")

    try:
        r = requests.get(M3U_URL, timeout=60)
        linhas = r.text.splitlines()

        for i in range(len(linhas)):
            linha = linhas[i].strip()

            if linha.startswith("#EXTINF"):
                nome_sujo = linha.split(",")[-1].strip()
                nome_limpo = limpar(nome_sujo)

                if i + 1 < len(linhas):
                    link = linhas[i + 1].strip()

                    if "/movie/" in link:
                        catalogo_filmes.append({
                            "nome": nome_limpo,
                            "link": link
                        })

        print(f"✅ {len(catalogo_filmes)} filmes carregados")

    except Exception as e:
        print("❌ ERRO:", e)

carregar_arquivos()

# BUSCA SIMPLES (IGUAL HTML)
def buscar_filmes(titulo):
    resultados = []

    for filme in catalogo_filmes:
        if titulo in filme["nome"]:
            resultados.append(filme)

    return resultados

# ENDPOINT
@app.route("/buscar")
def buscar():
    titulo = request.args.get("titulo", "")
    titulo_limpo = limpar(titulo)

    if not titulo_limpo:
        return jsonify([])

    resultados = buscar_filmes(titulo_limpo)

    return jsonify(resultados[:10])  # limita 10

@app.route("/")
def index():
    return f"Motor Online OK - {len(catalogo_filmes)} filmes"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
