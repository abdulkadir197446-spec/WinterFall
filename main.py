from flask import Flask
from threading import Thread
import discord
from discord.ext import commands

# Render'ın açık kalması için web sunucusu
app = Flask('')

@app.route('/')
def home():
    return "Bot aktif!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

keep_alive()

# Bot Kodların
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print('Bot başarıyla bağlandı!')
    print(f'Giriş yapılan kullanıcı: {bot.user}')

print("Bot başlatılıyor...")
bot.run('MTUyNzIzMTY3NTEyODQ4Mzk3MQ.G8F0BB.vtjE6HF-0EkijAmsKGWb0X5SFhR5pA1o6ZtuIc')
