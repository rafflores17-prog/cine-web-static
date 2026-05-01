import os
import re
import requests
from flask import Flask, request, redirect

app = Flask(__name__)

M3U_URL = "https://github.com/StartStatic1/meus-apks/releases/download/V_backup/lista.m3u" 
ARQUIVO_MANUAL = "manual.txt" 

catalogo_filmes = {}
catalogo_manual = {}

def limpar(nome):
    nome = re.sub(r"\[.*?\]", "", nome)
    nome = re.sub(r"\(.*?\)", "", nome)
    nome = nome.replace(".", " ")
    return nome.strip().lower()

def carregar_arquivos():
    if os.path.exists(ARQUIVO_MANUAL):
        print("⏳ Carregando filmes do backup manual...")
        with open(ARQUIVO_MANUAL, "r", encoding="utf-8", errors="ignore") as f:
            for linha in f:
                if "|" in linha:
                    nome_sujo, link = linha.split("|", 1)
                    catalogo_manual[limpar(nome_sujo)] = link.strip()
        print(f"✅ {len(catalogo_manual)} filmes manuais carregados!")

    print("⏳ Iniciando carga da lista M3U da Nuvem...")
    try:
        r = requests.get(M3U_URL, stream=True, timeout=60)
        linhas = [linha.decode('utf-8', errors='ignore') for linha in r.iter_lines() if linha]
                
        for i in range(len(linhas)):
            linha = linhas[i].strip()
            if linha.startswith("#EXTINF"):
                nome_sujo = linha.split(",")[-1].strip()
                nome_limpo = limpar(nome_sujo)

                if i + 1 < len(linhas):
                    link = linhas[i + 1].strip()
                    if "/movie/" in link and link.endswith(".mp4"):
                        catalogo_filmes[nome_limpo] = link
                        
        print(f"✅ SUCESSO! {len(catalogo_filmes)} filmes da M3U na memória!")
    except Exception as e:
        print(f"❌ ERRO ao baixar lista M3U: {e}")

carregar_arquivos()

# 🎯 FUNÇÃO SNIPER: Acha o filme certo e ignora os errados
def encontrar_link_preciso(titulo_limpo, catalogo):
    # 1. MATCH EXATO (Ex: Buscou "american pie", achou "american pie")
    if titulo_limpo in catalogo:
        return catalogo[titulo_limpo], "Exato"
        
    # 2. COMEÇA COM (Ex: Buscou "american pie", achou "american pie dublado hd")
    for nome_cat, link in catalogo.items():
        if nome_cat.startswith(titulo_limpo):
            return link, "Começa com"

    # 3. MATCH PARCIAL SEGURO (Pega a palavra mais longa para não confundir)
    melhor_link = None
    tamanho_match = 0
    for nome_cat, link in catalogo.items():
        if len(nome_cat) > 3 and nome_cat in titulo_limpo:
            if len(nome_cat) > tamanho_match:
                melhor_link = link
                tamanho_match = len(nome_cat)
    
    if melhor_link:
        return melhor_link, "Contém"
        
    return None, None

@app.route("/buscar")
def buscar():
    titulo = request.args.get("titulo", "")
    titulo_limpo = limpar(titulo)
    
    if not titulo_limpo:
        return "Nenhum título enviado", 400

    # 1. Bate no MANUAL primeiro com a Lógica Sniper
    link, tipo = encontrar_link_preciso(titulo_limpo, catalogo_manual)
    if link:
        print(f"🎬 MANUAL ({tipo}): {titulo_limpo}")
        return redirect(link)

    # 2. Bate na M3U com a Lógica Sniper
    link, tipo = encontrar_link_preciso(titulo_limpo, catalogo_filmes)
    if link:
        print(f"🎬 M3U ({tipo}): {titulo_limpo}")
        return redirect(link)

    print(f"❌ NÃO LOCALIZADO: {titulo_limpo}")
    return "Filme não encontrado.", 404

@app.route("/")
def index():
    return f"🎬 Motor Cine Mega Online! Manuais: {len(catalogo_manual)} | M3U: {len(catalogo_filmes)}", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
