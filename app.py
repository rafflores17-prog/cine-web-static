from flask import Flask, request, redirect
import sqlite3
import requests
import os

app = Flask(__name__)

# Servidores API de backup antigos
SERVIDORES_API = [
    {"nome": "Cinevexio", "host": "http://cinevexio.top:80", "user": "175473583", "pass": "643238922"},
    {"nome": "Stmax", "host": "http://stmax.top:80", "user": "lucas6043", "pass": "px2926br"}
]

def ler_arquivo_txt(caminho):
    """Lê um arquivo txt e transforma em dicionário"""
    acervo = {}
    if os.path.exists(caminho):
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                for linha in f:
                    if "|" in linha:
                        nome, url = linha.split("|", 1)
                        acervo[nome.strip().lower()] = url.strip()
        except Exception as e:
            print(f"Erro ao ler {caminho}: {e}")
    return acervo

# Carrega os dois arquivos separadamente na memória
ACERVO_VIP = ler_arquivo_txt("vips.txt")
ACERVO_GIGANTE = ler_arquivo_txt("filmes_site.txt")

@app.route("/buscar")
def buscar():
    titulo = request.args.get("titulo")
    if not titulo: return "Título vazio", 400
    
    titulo_limpo = titulo.strip().lower()

    # 🥇 1º PASSO: BUSCA NO SEU VIP (SUA CORREÇÃO É A LEI)
    for nome_vip, url_vip in ACERVO_VIP.items():
        if nome_vip in titulo_limpo or titulo_limpo in nome_vip:
            print(f"💎 ELITE VIP: Entregando {nome_vip}")
            return redirect(url_vip, code=302)

    # 🥈 2º PASSO: BUSCA NO NOVO ARQUIVO GIGANTE (filmes_site.txt)
    for nome_txt, url_txt in ACERVO_GIGANTE.items():
        if nome_txt in titulo_limpo or titulo_limpo in nome_txt:
            print(f"🚀 TXT GIGANTE: Entregando {nome_txt}")
            return redirect(url_txt, code=302)

    # 🥉 3º PASSO: BUSCA NO BANCO DE DADOS LOCAL (filmes.db)
    try:
        if os.path.exists('filmes.db'):
            conn = sqlite3.connect('filmes.db')
            c = conn.cursor()
            palavras = titulo_limpo.split()
            termo_base = palavras[0] if len(palavras) == 1 else " ".join(palavras[:2])
            c.execute("SELECT url FROM playlist WHERE nome LIKE ? LIMIT 1", (f"%{termo_base}%",))
            resultado = c.fetchone()
            conn.close()
            if resultado:
                print("💾 BANCO DE DADOS: Encontrado no SQLite")
                return redirect(resultado[0], code=302)
    except: pass

    # 🏅 4º PASSO: BUSCA NAS APIs EXTERNAS (Último recurso)
    for srv in SERVIDORES_API:
        try:
            url_api = f"{srv['host']}/player_api.php?username={srv['user']}&password={srv['pass']}&action=get_vod_streams"
            r = requests.get(url_api, timeout=4).json()
            for item in r:
                if titulo_limpo in item.get('name', '').lower():
                    v_url = f"{srv['host']}/movie/{srv['user']}/{srv['pass']}/{item.get('stream_id')}.mp4"
                    print("📡 API ANTIGA: Encontrado no backup")
                    return redirect(v_url, code=302)
        except: continue

    return "Filme não encontrado em nenhuma base", 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
