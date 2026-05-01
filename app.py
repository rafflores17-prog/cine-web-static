import os
import re
import requests
from flask import Flask, request, redirect

app = Flask(__name__)

# O SEU LINK DIRETO DO GITHUB RELEASES
M3U_URL = "https://github.com/StartStatic1/meus-apks/releases/download/V_backup/lista.m3u" 
ARQUIVO_MANUAL = "manual.txt" # Arquivo local para filmes manuais

catalogo_filmes = {}
catalogo_manual = {}

def limpar(nome):
    nome = re.sub(r"\[.*?\]", "", nome)
    nome = re.sub(r"\(.*?\)", "", nome)
    nome = nome.replace(".", " ")
    return nome.strip().lower()

def carregar_arquivos():
    # 1. Carrega os filmes manuais primeiro (Prioridade)
    if os.path.exists(ARQUIVO_MANUAL):
        print("⏳ Carregando filmes do backup manual...")
        with open(ARQUIVO_MANUAL, "r", encoding="utf-8", errors="ignore") as f:
            for linha in f:
                if "|" in linha:
                    nome_sujo, link = linha.split("|", 1)
                    catalogo_manual[limpar(nome_sujo)] = link.strip()
        print(f"✅ {len(catalogo_manual)} filmes manuais carregados!")

    # 2. Carrega a lista M3U de 60MB da Nuvem
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

# Executa as cargas assim que o Koyeb liga
carregar_arquivos()

@app.route("/buscar")
def buscar():
    titulo = request.args.get("titulo", "")
    titulo_limpo = limpar(titulo)
    
    if not titulo_limpo:
        return "Nenhum título enviado", 400

    # 1. Tenta achar no Backup Manual primeiro
    for nome_cat, link in catalogo_manual.items():
        if titulo_limpo in nome_cat or nome_cat in titulo_limpo:
            print(f"🎬 FILME MANUAL ENCONTRADO: {nome_cat}")
            return redirect(link)

    # 2. Tenta achar na Nuvem M3U
    for nome_cat, link in catalogo_filmes.items():
        if titulo_limpo in nome_cat or nome_cat in titulo_limpo:
            print(f"🎬 FILME M3U ENCONTRADO: {nome_cat}")
            return redirect(link)

    print(f"❌ NÃO LOCALIZADO: {titulo_limpo}")
    return "Filme não encontrado na lista.", 404

@app.route("/")
def index():
    return f"🎬 Motor Cine Mega Online! Manuais: {len(catalogo_manual)} | M3U: {len(catalogo_filmes)}", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
