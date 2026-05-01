import os
import re
import requests
from flask import Flask, request, redirect

app = Flask(__name__)

# 🔗 O SEU LINK DIRETO DO GITHUB RELEASES
M3U_URL = "https://github.com/StartStatic1/meus-apks/releases/download/V_backup/lista.m3u" 

# Dicionário na memória RAM para busca instantânea
catalogo_filmes = {}

def limpar(nome):
    nome = re.sub(r"\[.*?\]", "", nome)
    nome = re.sub(r"\(.*?\)", "", nome)
    nome = nome.replace(".", " ")
    return nome.strip().lower()

def carregar_lista_da_nuvem():
    print("⏳ Iniciando carga da lista M3U de 60MB da Nuvem...")
    try:
        # Baixa o arquivo de 60MB
        r = requests.get(M3U_URL, stream=True, timeout=60)
        
        # Lê linha por linha para não travar a memória
        linhas = [linha.decode('utf-8', errors='ignore') for linha in r.iter_lines() if linha]
                
        for i in range(len(linhas)):
            linha = linhas[i].strip()
            if linha.startswith("#EXTINF"):
                nome_sujo = linha.split(",")[-1].strip()
                nome_limpo = limpar(nome_sujo)

                if i + 1 < len(linhas):
                    link = linhas[i + 1].strip()
                    # Filtra apenas os filmes mp4
                    if "/movie/" in link and link.endswith(".mp4"):
                        catalogo_filmes[nome_limpo] = link
                        
        print(f"✅ SUCESSO! {len(catalogo_filmes)} filmes carregados na memória!")
    except Exception as e:
        print(f"❌ ERRO ao baixar lista: {e}")

# Executa a carga assim que o Koyeb liga o motor
carregar_lista_da_nuvem()

@app.route("/buscar")
def buscar():
    titulo = request.args.get("titulo", "")
    titulo_limpo = limpar(titulo)
    
    if not titulo_limpo:
        return "Nenhum título enviado", 400

    # Busca super rápida na memória
    for nome_cat, link in catalogo_filmes.items():
        if titulo_limpo in nome_cat or nome_cat in titulo_limpo:
            print(f"🎬 FILME ENCONTRADO: {nome_cat}")
            return redirect(link)

    print(f"❌ NÃO LOCALIZADO: {titulo_limpo}")
    return "Filme não encontrado na lista M3U.", 404

# 🟢 ROTA DE HEALTH CHECK (Isso resolve o erro "Unhealthy" do Koyeb)
@app.route("/")
def index():
    return f"🎬 Motor Cine Mega M3U Online! Filmes indexados: {len(catalogo_filmes)}", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
