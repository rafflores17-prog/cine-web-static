import os
import re
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

M3U_URL = "https://github.com/StartStatic1/meus-apks/releases/download/V_backup/lista.m3u"

catalogo_filmes = []

# LIMPAR NOME
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

# BUSCA INTELIGENTE (SEM ERRAR)
def buscar_filmes(titulo):
    resultados = []

    palavras_busca = titulo.split()

    for filme in catalogo_filmes:
        nome = filme["nome"]

        # match direto
        if titulo in nome:
            resultados.append(filme)
            continue

        # match por palavras
        palavras_nome = nome.split()
        iguais = sum(1 for p in palavras_busca if p in palavras_nome)

        if iguais >= max(1, len(palavras_busca)//2):
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

    # fallback (evita vir vazio)
    if not resultados:
        resultados = catalogo_filmes[:5]

    return jsonify(resultados[:10])

@app.route("/")
def index():
    return f"Motor OK - {len(catalogo_filmes)} filmes"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
