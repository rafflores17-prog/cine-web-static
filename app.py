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
    nome = re.sub(r'\b(19|20)\d{2}\b', '', nome)
    nome = re.sub(r"[\[\]\(\):.\-!]", " ", nome)
    return " ".join(nome.split()).strip()

def carregar_arquivos():
    global catalogo_filmes
    catalogo_filmes = {}
    print("⏳ Carregando listas na RAM...")
    
    # 1. Carrega o Manual Primeiro (Regra de Ouro)
    if os.path.exists(ARQUIVO_MANUAL):
        with open(ARQUIVO_MANUAL, "r", encoding="utf-8", errors="ignore") as f:
            for linha in f:
                if "|" in linha:
                    n, l = linha.split("|", 1)
                    catalogo_filmes[limpar(n)] = l.strip()

    # 2. Carrega as Listas M3U
    for url in LISTAS_M3U:
        try:
            r = requests.get(url, stream=True, timeout=60)
            linhas = [l.decode('utf-8', errors='ignore') for l in r.iter_lines() if l]
            for i in range(len(linhas)):
                if "#EXTINF" in linhas[i]:
                    n_limpo = limpar(linhas[i].split(",")[-1])
                    if i + 1 < len(linhas) and n_limpo not in catalogo_filmes:
                        link = linhas[i + 1].strip()
                        if "/movie/" in link:
                            catalogo_filmes[n_limpo] = link
        except: continue
    print(f"✅ Catálogo pronto: {len(catalogo_filmes)} filmes.")

carregar_arquivos()

def buscar_sniper(titulo_buscado):
    titulo_limpo = limpar(titulo_buscado)
    
    # 1. MATCH EXATO
    if titulo_limpo in catalogo_filmes:
        return catalogo_filmes[titulo_limpo]

    # 2. LÓGICA DO SEU BACKUP (Palavra-chave + Número)
    palavras = titulo_limpo.split()
    if palavras:
        primeira_palavra = palavras[0]
        for nome_cat, link in catalogo_filmes.items():
            if primeira_palavra in nome_cat:
                num_busca = re.search(r'\d+', titulo_limpo)
                num_cat = re.search(r'\d+', nome_cat)
                if num_busca and num_cat:
                    if num_busca.group() == num_cat.group():
                        return link
                elif not num_busca and not num_cat:
                    return link

    # 3. SIMILARIDADE (Ajustada para 0.6 para não falhar)
    melhor_link, maior_score = None, 0.0
    for nome_cat, link in catalogo_filmes.items():
        score = difflib.SequenceMatcher(None, titulo_limpo, nome_cat).ratio()
        if score > maior_score and score > 0.6:
            maior_score, melhor_link = score, link
    return melhor_link

@app.route("/buscar")
def buscar():
    titulo = request.args.get("titulo", "")
    link = buscar_sniper(titulo)
    if link:
        return redirect(link)
    return "Não encontrado", 404

@app.route("/")
def index():
    return f"Motor Cine Mega: {len(catalogo_filmes)} filmes", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
