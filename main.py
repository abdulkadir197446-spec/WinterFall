import os
import asyncio
import threading
import random
import sqlite3
import time
from datetime import datetime, timezone
from flask import Flask
import discord
from discord import app_commands
from discord.ext import commands
from groq import Groq
from gtts import gTTS

# --- Groq AI Kurulumu ---
ai_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# --- Veritabanı (SQLite) Kurulumu (Davetler İçin) ---
def veritabani_kur():
    conn = sqlite3.connect('davetler.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS davet_loglari (
            user_id INTEGER PRIMARY KEY,
            joins INTEGER DEFAULT 0,
            lefts INTEGER DEFAULT 0,
            fakes INTEGER DEFAULT 0,
            rejoins INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

veritabani_kur()

# --- Render İçin Web Sunucusu (7/24 Aktiflik İçin) ---
app = Flask('')

@app.route('/')
def home():
    return "WinterFall Bot 7/24 Aktif! (Tüm Sistemler Devrede)"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

# --- Discord Bot Kurulumu ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True
intents.guilds = True
intents.invites = True

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

invite_cache = {}

# Yetkili Kontrol Fonksiyonu
def yetkili_mi_kontrol_etmek(author, guild):
    izinli_roller = ["❄ 𝙁𝙤𝙪𝙣𝙙𝙚𝙧", "❄ 𝙈𝙖𝙮𝙤𝙧", "❄𝘾𝙤-𝙈𝙖𝙮𝙤𝙧", "♱ 𝐖𝐢𝐧𝐭𝐞𝙧𝐟𝙖𝙡𝙡", "𝐖𝐢𝐧𝐭𝐞𝙧𝐟𝙖𝙡𝙡 Yönetim"]
    kullanici_rolleri = [role.name for role in author.roles]
    return author.id == guild.owner_id or any(r in kullanici_rolleri for r in izinli_roller)

# AI Sadece Ticket Kanalında Çalışsın Diye Kontrol
def is_ticket_channel(channel):
    return channel.category and channel.category.name == "AÇIK TICKETLAR"

# --- AI YANIT ÜRETİCİ (Sadece Ticket İçin) ---
async def ai_yanit_uret(metin):
    try:
        sistem_mesaji = (
            "Sen WinterFall sunucusunun ticket ve destek asistanısın. "
            "Sadece ticket kanallarında destek veriyorsun. "
            "Cevap verirken asla /mute, /ban, /sesat, /çekiliş gibi bot komutlarını metin içinde geçirme, "
            "sadece kullanıcının sorununa doğal ve yardımcı cevaplar ver."
        )
        completion = ai_client.chat.completions.create(
            messages=[
                {"role": "system", "content": sistem_mesaji},
                {"role": "user", "content": metin}
            ], 
            model="llama-3.1-8b-instant"
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"❌ AI Hatası: {e}"

# --- TICKET KAPATMA BUTONU ---
class TicketKapatView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Desteği Kapat", style=discord.ButtonStyle.red, custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        kullanici_rolleri = [role.name for role in interaction.user.roles]
        yetkili_mi = interaction.user.id == interaction.guild.owner_id or "Ticket Yetkili" in kullanici_rolleri

        if not yetkili_mi:
            await interaction.response.send_message("❌ Desteği sadece **Ticket Yetkili** rolüne sahip kişiler kapatabilir!", ephemeral=True)
            return

        await interaction.response.send_message("Destek kanalı kapatılıyor...", ephemeral=True)
        await asyncio.sleep(2)
        try:
            await interaction.channel.delete()
        except Exception as e:
            print(f"Kanal silinirken hata oluştu: {e}")

# --- ORTAK TICKET OLUŞTURMA FONKSİYONU ---
async def olustur_ticket_kanali(interaction: discord.Interaction, secilen_kategori: str, form_verileri: dict = None):
    guild = interaction.guild
    member = interaction.user

    for channel in guild.channels:
        if isinstance(channel, discord.TextChannel) and channel.name.endswith(f"-{member.name.lower()}" ):
            await interaction.response.send_message(f"❌ Zaten açık bir destek talebiniz bulunuyor: {channel.mention}", ephemeral=True)
            return

    kategori_adi = "AÇIK TICKETLAR"
    category = discord.utils.get(guild.categories, name=kategori_adi)
    if not category:
        category = await guild.create_category(kategori_adi)

    ticket_yetkili_rol = discord.utils.get(guild.roles, name="Ticket Yetkili")

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        member: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }

    if ticket_yetkili_rol:
        overwrites[ticket_yetkili_rol] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

    kanal_adi = f"{secilen_kategori.lower().replace(' ', '-')}-{member.name.lower()}"

    ticket_channel = await guild.create_text_channel(
        name=kanal_adi,
        category=category,
        overwrites=overwrites
    )

    if ticket_yetkili_rol:
        etiket_metni = f"{member.mention} {ticket_yetkili_rol.mention}"
    else:
        etiket_metni = f"{member.mention} @Ticket Yetkili"

    if secilen_kategori == "Partnerlik":
        embed = discord.Embed(
            title="💖 Partnerlik Başvuru Talebi",
            description="Aramıza katılmak için sunucuya gelip ticket açmanız yeterli",
            color=discord.Color.from_rgb(255, 105, 180)
        )
        await interaction.response.send_message(f"**{secilen_kategori}** için destek kanalınız oluşturuldu: {ticket_channel.mention}", ephemeral=True)
        await ticket_channel.send(embed=embed, view=TicketKapatView())
        await ticket_channel.send(f"{etiket_metni}\n\nhttps://discord.gg/NgfQafxkDV")
    else:
        embed = discord.Embed(
            title=f"🎫 {secilen_kategori} Talebi Açıldı",
            description=f"Merhaba {member.mention}, yetkililerimiz ve yapay zeka asistanımız en kısa sürede sizinle ilgilenecektir.",
            color=discord.Color.blue()
        )

        if form_verileri:
            for baslik, cevap in form_verileri.items():
                embed.add_field(name=f"📌 {baslik}", value=f"```\n{cevap}\n
