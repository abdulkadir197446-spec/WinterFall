import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print('Bot başarıyla bağlandı!')
    print(f'Giriş yapılan kullanıcı: {bot.user}')

print("Bot başlatılıyor...")
bot.run('MTUyNzIzMTY3NTEyODQ4Mzk3MQ.G8F0BB.vtjE6Hf-0EkijAmsKGWb0X5SFhR5pAlo6ZtuIc')
