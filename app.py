import os
import re
import requests
import difflib
from flask import Flask, request, redirect

app = Flask(__name__)

LISTAS_M3U = [
    "https://github.com/StartStatic1/meus-apks/releases/download/V_backup/lista.m3u",
    "https://github.com/StartStatic1/meus-apks/releases/download/V_BACKUP2/lista2.m3u"
]
ARQUIVO_MANUAL = "manual.txt"
catalogo_filmes = {}

def limpar(nome):
    nome = str(nome).lower()
    nome = re.sub(r'\bii\b', '2', nome).replace('parte ii', '2')
    nome = re.sub(r'\biii\b', '3', nome).replace('parte iii', '3')
    nome = re.sub(r'\b(walt disney|disney|pixar|marvel|fhd|4k|dublado|legendado)\b', '', nome)
    nome = re.sub(r"[\[\]\(\):.\-!]", " ", nome)
    return " ".join(nome.split()).strip()

def carregar_tudo():
    global catalogo_filmes
    catalogo_filmes = {}
    for url in LISTAS_M3U:
        try:
            r = requests.get(url, stream=True, timeout=60)
            linhas = [l.decode('utf-8', errors='ignore') for l in r.iter_lines() if l]
            for i in range(len(linhas)):
                linha = linhas[i].strip()
                if linha.startswith("#EXTINF"):
                    nome_limpo = limpar(linha.split(",")[-1].strip())
                    if i + 1 < len(linhas):
                        link = linhas[i + 1].strip()
                        if "/movie/" in link:
                            catalogo_filmes[nome_limpo] = link
        except: continue

    if os.path.exists(ARQUIVO_MANUAL):
        with open(ARQUIVO_MANUAL, "r", encoding="utf-8", errors="ignore") as f:
            for linha in f:
                if "|" in linha:
                    # O .strip() aqui remove os espaços antes e depois da barra!
                    partes = linha.split("|")
                    nome_manual = limpar(partes[0].strip())
                    link_manual = partes[1].strip()
                    catalogo_filmes[nome_manual] = link_manual
    print(f"✅ Catálogo Cine Mega: {len(catalogo_filmes)} filmes.")

carregar_tudo()

@app.route("/buscar")
def buscar():
    titulo = request.args.get("titulo", "")
    titulo_limpo = limpar(titulo)
    
    # 1. Busca Direta (Manual ou Exata)
    if titulo_limpo in catalogo_filmes:
        return redirect(catalogo_filmes[titulo_limpo])

    # 2. Busca Sniper (Franquias)
    num_busca = re.search(r'\d+', titulo_limpo)
    num_busca = num_busca.group() if num_busca else None
    melhor_link, maior_score = None, 0.0

    for nome_cat, link in catalogo_filmes.items():
        num_cat = re.search(r'\d+', nome_cat)
        num_cat = num_cat.group() if num_cat else None
        if num_busca != num_cat: continue

        score = difflib.SequenceMatcher(None, titulo_limpo, nome_cat).ratio()
        if titulo_limpo in nome_cat: score += 0.2 # Lógica do seu HTML

        if score > maior_score and score > 0.45:
            maior_score, melhor_link = score, link

    if melhor_link: return redirect(melhor_link)
    return "Não encontrado", 404

@app.route("/")
def index():
    return f"Motor Ativo: {len(catalogo_filmes)} filmes", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
