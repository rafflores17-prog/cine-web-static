import os
import re
import requests
import difflib
from flask import Flask, request, redirect

app = Flask(__name__)

# LINKS DAS LISTAS
LISTAS_M3U = [
    "https://github.com/StartStatic1/meus-apks/releases/download/V_backup/lista.m3u",
    "https://github.com/StartStatic1/meus-apks/releases/download/V_BACKUP2/lista2.m3u"
]

ARQUIVO_MANUAL = "manual.txt"
catalogo_filmes = {}

def limpar(nome):
    nome = str(nome).lower()
    # Tradução de numeração
    nome = re.sub(r'\bii\b', '2', nome).replace('parte ii', '2')
    nome = re.sub(r'\biii\b', '3', nome).replace('parte iii', '3')
    # Limpeza de lixo e tags
    nome = re.sub(r'\b(walt disney|disney|pixar|marvel|apresenta|coleção|fhd|4k|dublado|legendado|hdtv|sd|720p|1080p)\b', '', nome)
    nome = re.sub(r'\b(19|20)\d{2}\b', '', nome) # Remove anos
    nome = re.sub(r"[\[\]\(\):.\-!]", " ", nome) # Remove pontuação inclusive "!"
    return " ".join(nome.split()).strip()

def carregar_tudo():
    global catalogo_filmes
    catalogo_filmes = {}
    print("⏳ Carregando listas na RAM...")
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
    
    # MANUAL SOBRESCREVE TUDO
    if os.path.exists(ARQUIVO_MANUAL):
        with open(ARQUIVO_MANUAL, "r", encoding="utf-8", errors="ignore") as f:
            for linha in f:
                if "|" in linha:
                    n, l = linha.split("|", 1)
                    catalogo_filmes[limpar(n)] = l.strip()
    print(f"✅ Catálogo pronto com {len(catalogo_filmes)} itens.")

carregar_tudo()

def buscar_sniper(titulo_buscado):
    titulo_limpo = limpar(titulo_buscado)
    
    # 1. Tenta Match Exato
    if titulo_limpo in catalogo_filmes:
        return catalogo_filmes[titulo_limpo]

    num_busca = re.search(r'\d+', titulo_limpo)
    num_busca = num_busca.group() if num_busca else None

    melhor_link = None
    maior_score = 0.0

    for nome_cat, link in catalogo_filmes.items():
        # Trava de Franquia (Obrigatória)
        num_cat = re.search(r'\d+', nome_cat)
        num_cat = num_cat.group() if num_cat else None
        if num_busca != num_cat:
            continue

        # Calcula Similaridade
        score = difflib.SequenceMatcher(None, titulo_limpo, nome_cat).ratio()
        
        # Bônus se o nome buscado estiver contido no nome do catálogo (Lógica do seu HTML)
        if titulo_limpo in nome_cat or nome_cat in titulo_limpo:
            score += 0.2

        if score > maior_score:
            maior_score = score
            melhor_link = link

    # Se o score for minimamente aceitável (igual sites profissionais), ele solta o play
    return melhor_link if maior_score > 0.45 else None

@app.route("/buscar")
def buscar():
    titulo = request.args.get("titulo", "")
    if not titulo: return "Erro", 400
    
    link = buscar_sniper(titulo)
    if link:
        print(f"🎬 PLAY: {titulo}")
        return redirect(link)
    
    print(f"❌ NÃO LOCALIZADO: {titulo}")
    return "Não encontrado", 404

@app.route("/")
def index():
    return f"Motor Cine Mega: {len(catalogo_filmes)} filmes ativos.", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
