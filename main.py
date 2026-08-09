import os
import asyncio
import threading
import discord
from discord.ext import commands
from flask import Flask
from google import genai

# --- Gemini AI Kurulumu ---
ai_client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# --- Flask 7/24 ---
app = Flask('')
@app.route('/')
def home(): return "WinterFall Bot 7/24 Aktif!"
def run_flask(): app.run(host='0.0.0.0', port=8080)

# --- Discord Bot Kurulumu ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# --- YARDIMCI FONKSİYONLAR ---
def is_ticket_channel(channel):
    """Kanalın 'AÇIK TICKETLAR' kategorisinde olup olmadığını kontrol eder."""
    return channel.category and channel.category.name == "AÇIK TICKETLAR"

# --- BOT OLAYLARI (MESAJ DİNLEYİCİ) ---
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # 1. YZ SİSTEMİ: 
    # A) Etiketlenirse HER YERDE cevap verir.
    # B) 'AÇIK TICKETLAR' kategorisindeyse ETİKETLEMEDEN cevap verir.
    if bot.user.mentioned_in(message) or is_ticket_channel(message.channel):
        temiz_mesaj = message.content.replace(f"<@{bot.user.id}>", "").strip()
        if temiz_mesaj:
            async with message.channel.typing():
                try:
                    # Gemini 2.0 Flash modeli kullanılıyor
                    response = ai_client.models.generate_content(
                        model='gemini-2.0-flash', 
                        contents=temiz_mesaj
                    )
                    await message.reply(response.text)
                except Exception as e:
                    await message.reply(f"❌ Yapay zeka asistanı şu an yanıt veremiyor: {e}")
        return

    # 2. DOĞAL DİLLE KANAL AÇMA (Yetkililer için)
    if ("kanal" in message.content.lower()) and ("aç" in message.content.lower() or "oluş" in message.content.lower()):
        # Burada yetkili kontrol fonksiyonunu çağırabilirsin
        isim = message.content.lower().replace("kanal", "").replace("aç", "").replace("oluştur", "").strip() or "yeni-kanal"
        if "ses" in message.content.lower():
            await message.guild.create_voice_channel(name=isim)
        else:
            await message.guild.create_text_channel(name=isim)
        await message.reply(f"✅ **{isim}** başarıyla oluşturuldu.")
        return

    await bot.process_commands(message)

# --- BAŞLATMA ---
if __name__ == '__main__':
    threading.Thread(target=run_flask).start()
    token = os.environ.get('BOT_TOKEN')
    if token:
        bot.run(token)
    else:
        print("HATA: BOT_TOKEN bulunamadı!")
