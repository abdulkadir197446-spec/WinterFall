import os
import threading
from flask import Flask
import discord
from discord.ext import commands

# --- Render İçin Web Sunucusu Kurulumu ---
app = Flask('')

@app.route('/')
def home():
    return "Bot aktif ve çalışıyor!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

# --- Discord Bot Kurulumu ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Bot başarıyla giriş yaptı: {bot.user.name} ({bot.user.id})')
    print('--------------------------------------------------')

@bot.command()
async def ping(ctx):
    await ctx.send(f'Pong! Gecikme süresi: {round(bot.latency * 1000)}ms')

# --- Başlatma İşlemleri ---
if __name__ == '__main__':
    # Web sunucusunu arka planda çalıştır
    server_thread = threading.Thread(target=run_flask)
    server_thread.start()
    
    # Tokenı Render Environment Variable (BOT_TOKEN) üzerinden güvenle al
    token = os.environ.get('BOT_TOKEN')
    if token:
        bot.run(token)
    else:
        print("HATA: BOT_TOKEN çevre değişkeni bulunamadı! Lütfen Render panelindeki Environment sekmesine ekleyin.")
