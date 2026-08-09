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
                embed.add_field(name=f"📌 {baslik}", value=f"```\n{cevap}\n```", inline=False)

        await interaction.response.send_message(f"**{secilen_kategori}** için destek kanalınız oluşturuldu: {ticket_channel.mention}", ephemeral=True)
        await ticket_channel.send(content=etiket_metni, embed=embed, view=TicketKapatView())

# --- TICKET MODALLARI ---
class EkipAlimFormu(discord.ui.Modal, title="Ekip Alım Başvuru Formu"):
    eski_ekip = discord.ui.TextInput(label="Eski ekibin?", placeholder="Örn: Vanguard", required=True)
    sunucu = discord.ui.TextInput(label="Hangi sunucuda oynuyorsun?", placeholder="Örn: CraftRise", required=True)
    oyun_ici_isim = discord.ui.TextInput(label="Oyun içi ismin ne?", placeholder="Örn: Steve", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await olustur_ticket_kanali(interaction, "Ekip Alım", {
            "Eski Ekibi": self.eski_ekip.value,
            "Oynadığı Sunucu": self.sunucu.value,
            "Oyun İçi İsmi": self.oyun_ici_isim.value
        })

class MergeFormu(discord.ui.Modal, title="Merge Başvuru Formu"):
    kim_kime = discord.ui.TextInput(label="Kim kime katılacak?", placeholder="Örn: X ekibi, Y ekibine katılacak.", style=discord.TextStyle.paragraph, required=True)
    ekip_ismi = discord.ui.TextInput(label="Ekip ismi?", placeholder="Örn: WinterFall", required=True)
    sunucular = discord.ui.TextInput(label="Hangi sunucularda oynuyorsunuz?", placeholder="Örn: CraftRise", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await olustur_ticket_kanali(interaction, "Merge", {
            "Kim Kime Katılacak": self.kim_kime.value,
            "Ekip İsmi": self.ekip_ismi.value,
            "Sunucular": self.sunucular.value
        })

class AllyFormu(discord.ui.Modal, title="Ally Başvuru Formu"):
    ekip_ismi = discord.ui.TextInput(label="Ekip ismi?", placeholder="Örn: WinterFall", required=True)
    sunucular = discord.ui.TextInput(label="Hangi sunucularda oynuyorsunuz?", placeholder="Örn: CraftRise", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await olustur_ticket_kanali(interaction, "Ally", {
            "Ekip İsmi": self.ekip_ismi.value,
            "Sunucular": self.sunucular.value
        })

class GenelDestekFormu(discord.ui.Modal, title="Genel Destek Formu"):
    sorun = discord.ui.TextInput(label="Sorun nedir?", placeholder="Yaşadığınız sorunu kısaca buraya yazın...", style=discord.TextStyle.paragraph, required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await olustur_ticket_kanali(interaction, "Genel Destek", {"Sorun": self.sorun.value})

class TicketSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Ekip Alım", emoji="👤"),
            discord.SelectOption(label="Merge", emoji="🔗"),
            discord.SelectOption(label="Partnerlik", emoji="💖"),
            discord.SelectOption(label="Ally", emoji="⚔️"),
            discord.SelectOption(label="Genel Destek", emoji="⚙️")
        ]
        super().__init__(placeholder="Seçim yap", min_values=1, max_values=1, options=options, custom_id="ticket_select_menu")

    async def callback(self, interaction: discord.Interaction):
        secilen = self.values[0]
        if secilen == "Ekip Alım": await interaction.response.send_modal(EkipAlimFormu())
        elif secilen == "Merge": await interaction.response.send_modal(MergeFormu())
        elif secilen == "Ally": await interaction.response.send_modal(AllyFormu())
        elif secilen == "Genel Destek": await interaction.response.send_modal(GenelDestekFormu())
        else: await olustur_ticket_kanali(interaction, secilen)

class TicketSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())

# --- ÇEKİLİŞ SİSTEMİ ---
def parse_time(time_str):
    time_str = time_str.lower().strip()
    if time_str.endswith('m'): return int(time_str[:-1]) * 60
    elif time_str.endswith('h'): return int(time_str[:-1]) * 3600
    elif time_str.endswith('d'): return int(time_str[:-1]) * 86400
    return int(time_str) * 60

class CekilisKatilView(discord.ui.View):
    def __init__(self, embed=None, mesaj=None):
        super().__init__(timeout=None)
        self.katilimcilar = set()
        self.embed = embed
        self.mesaj = mesaj

    @discord.ui.button(label="🎉 Katıl", style=discord.ButtonStyle.blurple, custom_id="cekilis_katil")
    async def katil(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in self.katilimcilar:
            self.katilimcilar.add(interaction.user.id)
            await interaction.response.send_message("🎉 Çekilişe başarıyla katıldın!", ephemeral=True)
        else:
            self.katilimcilar.remove(interaction.user.id)
            await interaction.response.send_message("Çekilişten ayrıldın.", ephemeral=True)
        
        if self.embed and self.mesaj:
            try:
                self.embed.set_field_at(0, name="📊 Katılımcı Sayısı", value=f"**{len(self.katilimcilar)}** kişi katıldı", inline=False)
                await self.mesaj.edit(embed=self.embed)
            except: pass

class CekilisModal(discord.ui.Modal, title="Çekiliş Oluştur"):
    sure = discord.ui.TextInput(label="Süre (Örn: 10m, 1h)", placeholder="10m")
    kazanan = discord.ui.TextInput(label="Kazanan Sayısı", placeholder="1")
    odul = discord.ui.TextInput(label="Ödül", placeholder="VIP")
    aciklama = discord.ui.TextInput(label="Açıklama", required=False, style=discord.TextStyle.paragraph)

    async def on_submit(self, interaction: discord.Interaction):
        saniye = parse_time(self.sure.value)
        timestamp = int(time.time() + saniye)
        embed = discord.Embed(title=f"🎉 {self.odul.value}", color=discord.Color.dark_theme())
        embed.add_field(name="📊 Katılımcı Sayısı", value="**0** kişi katıldı", inline=False)
        embed.description = f"Sona Erme: <t:{timestamp}:R>\nDüzenleyen: {interaction.user.mention}"
        
        await interaction.response.send_message("Çekiliş başlatıldı!", ephemeral=True)
        mesaj = await interaction.channel.send(content="🎉 **ÇEKİLİŞ BAŞLADI** 🎉", embed=embed)
        view = CekilisKatilView(embed, mesaj)
        await mesaj.edit(view=view)

        await asyncio.sleep(saniye)
        try: guncel_mesaj = await interaction.channel.fetch_message(mesaj.id)
        except: guncel_mesaj = mesaj

        katilimcilar_listesi = list(view.katilimcilar)
        if not katilimcilar_listesi:
            await guncel_mesaj.edit(content="🎉 **ÇEKİLİŞ BİTTİ (Katılım olmadı)** 🎉", view=None)
            return

        kazananlar = random.sample(katilimcilar_listesi, min(int(self.kazanan.value), len(katilimcilar_listesi)))
        kazananlar_mention = ", ".join([f"<@{uid}>" for uid in kazananlar])
        await guncel_mesaj.edit(content=f"🎉 **ÇEKİLİŞ BİTTİ** 🎉\nKazananlar: {kazananlar_mention}", view=None)
        await interaction.channel.send(f"Tebrikler {kazananlar_mention}! **{self.odul.value}** kazandınız!")

class CekilisSetupView(discord.ui.View):
    @discord.ui.button(label="Çekilişi Ayarla", style=discord.ButtonStyle.green)
    async def ayarla(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not yetkili_mi_kontrol_etmek(interaction.user, interaction.guild):
            await interaction.response.send_message("❌ Yetkin yok!", ephemeral=True)
            return
        await interaction.response.send_modal(CekilisModal())

# ==========================================
# SLASH KOMUTLARI
# ==========================================

@bot.tree.command(name="sunucu", description="Sunucu bilgisi gösterir.")
async def sunucu(interaction: discord.Interaction):
    guild = interaction.guild
    
    # Kanal türlerini sayma
    yazi_kanali = len(guild.text_channels)
    ses_kanali = len(guild.voice_channels)
    kategori_sayisi = len(guild.categories)
    
    # Oluşturulma tarihi timestamp formatı (Discord'un yerel zaman damgası)
     kuruldu_timestamp = int(guild.created_at.timestamp())

    embed = discord.Embed(
        title=f"❄️ {guild.name} | Sunucu Bilgileri",
        color=discord.Color.dark_theme()
    )
    
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
        
    embed.add_field(name="👑 Sunucu Sahibi", value=guild.owner.mention if guild.owner else "Bulunamadı", inline=False)
    embed.add_field(name="🆔 Sunucu ID", value=str(guild.id), inline=False)
    embed.add_field(name="📅 Oluşturulma Tarihi", value=f"<t:{kuruldu_timestamp}:D> (<t:{kuruldu_timestamp}:R>)", inline=False)
    embed.add_field(name="📜 Kanal Sayısı", value=f"[{guild.channels.__len__()}]\n{yazi_kanali} Yazı | {ses_kanali} Ses | {kategori_sayisi} Kategori", inline=False)
    embed.add_field(name="👤 Üye Sayısı", value=str(guild.member_count), inline=False)
    embed.add_field(name="🌹 Rol Sayısı", value=str(len(guild.roles)), inline=False)
    embed.add_field(name="🟣 Boost sayısı", value=str(guild.premium_subscription_count), inline=False)

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="i", description="Davet istatistikleri.")
@app_commands.describe(member="İstatistiklerine bakılacak üye")
async def invite_bak(interaction: discord.Interaction, member: discord.Member = None):
    hedef = member or interaction.user
    conn = sqlite3.connect('davetler.db')
    cursor = conn.cursor()
    cursor.execute('SELECT joins, lefts, fakes, rejoins FROM davet_loglari WHERE user_id = ?', (hedef.id,))
    row = cursor.fetchone()
    conn.close()
    
    joins, lefts, fakes, rejoins = (row if row else (0, 0, 0, 0))

    embed = discord.Embed(title="Invite log", color=discord.Color.dark_theme())
    embed.description = f"≫ {hedef.mention} has **{joins}** invites"
    
    if hedef.avatar:
        embed.set_thumbnail(url=hedef.avatar.url)
    else:
        embed.set_thumbnail(url=hedef.default_avatar.url)

    embed.add_field(name="Joins", value=str(joins), inline=False)
    embed.add_field(name="Left", value=str(lefts), inline=False)
    embed.add_field(name="Fake", value=str(fakes), inline=False)
    embed.add_field(name="Rejoins", value=f"{rejoins} (7d)", inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="ireset", description="Davetleri sıfırlar.")
async def invite_reset(interaction: discord.Interaction):
    if not yetkili_mi_kontrol_etmek(interaction.user, interaction.guild):
        await interaction.response.send_message("❌ Yetkin yok!", ephemeral=True)
        return
    conn = sqlite3.connect('davetler.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM davet_loglari')
    conn.commit()
    conn.close()
    await interaction.response.send_message("🔄 Davetler sıfırlandı!", ephemeral=True)

@bot.tree.command(name="bağlan", description="Bot ses kanalına girer.")
async def baglan(interaction: discord.Interaction):
    if not yetkili_mi_kontrol_etmek(interaction.user, interaction.guild):
        await interaction.response.send_message("❌ Yetkin yok!", ephemeral=True)
        return
    if not interaction.user.voice:
        await interaction.response.send_message("❌ Ses kanalında olmalısın!", ephemeral=True)
        return
    channel = interaction.user.voice.channel
    if interaction.guild.voice_client:
        await interaction.guild.voice_client.move_to(channel)
    else:
        await channel.connect(self_deaf=True)
    await interaction.response.send_message(f"🔊 Kanala bağlandım: **{channel.name}**", ephemeral=True)

@bot.tree.command(name="ayrıl", description="Bot sesten çıkar.")
async def ayril(interaction: discord.Interaction):
    if not yetkili_mi_kontrol_etmek(interaction.user, interaction.guild):
        await interaction.response.send_message("❌ Yetkin yok!", ephemeral=True)
        return
    if interaction.guild.voice_client:
        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message("👋 Sesten ayrıldım.", ephemeral=True)
    else:
        await interaction.response.send_message("❌ Seste değilim!", ephemeral=True)

@bot.tree.command(name="konuş", description="Metni sesli okur.")
@app_commands.describe(mesaj="Okunacak yazı")
async def konus(interaction: discord.Interaction, mesaj: str):
    if not yetkili_mi_kontrol_etmek(interaction.user, interaction.guild):
        await interaction.response.send_message("❌ Yetkin yok!", ephemeral=True)
        return
    if not interaction.guild.voice_client:
        await interaction.response.send_message("❌ Önce botu sese sok! (`/bağlan`)", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    try:
        dosya_adi = f"ses_{int(time.time())}.mp3"
        tts = gTTS(text=mesaj, lang='tr')
        tts.save(dosya_adi)

        voice_client = interaction.guild.voice_client
        if voice_client.is_playing(): voice_client.stop()

        voice_client.play(discord.FFmpegPCMAudio(dosya_adi))
        await interaction.followup.send(r'🗣️ Okunuyor: *"' + mesaj + r'"*', ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Hata: {e}", ephemeral=True)

@bot.tree.command(name="mute", description="Üyeyi metin kanallarında susturur.")
@app_commands.describe(member="Susturulacak üye", sebep="Sebep")
async def mute(interaction: discord.Interaction, member: discord.Member, sebep: str = "Belirtilmedi"):
    if not yetkili_mi_kontrol_etmek(interaction.user, interaction.guild):
        await interaction.response.send_message("❌ Bu komutu sadece yetkililer kullanabilir!", ephemeral=True)
        return
    try:
        sure = discord.utils.utcnow() + discord.timedelta(hours=1)
        await member.timeout(sure, reason=sebep)
        await interaction.response.send_message(f"🔇 **{member.display_name}** susturuldu! Sebep: *{sebep}*", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Hata: {e}", ephemeral=True)

@bot.tree.command(name="ban", description="Üyeyi sunucudan yasaklar.")
@app_commands.describe(member="Yasaklanacak üye", sebep="Sebep")
async def ban(interaction: discord.Interaction, member: discord.Member, sebep: str = "Belirtilmedi"):
    if not yetkili_mi_kontrol_etmek(interaction.user, interaction.guild):
        await interaction.response.send_message("❌ Bu komutu sadece yetkililer kullanabilir!", ephemeral=True)
        return
    try:
        await member.ban(reason=sebep)
        await interaction.response.send_message(f"🔨 **{member.display_name}** yasaklandı! Sebep: *{sebep}*", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Hata: {e}", ephemeral=True)

@bot.tree.command(name="sesat", description="Üyeyi ses kanalından atar.")
@app_commands.describe(member="Atılacak üye")
async def sesat(interaction: discord.Interaction, member: discord.Member):
    if not yetkili_mi_kontrol_etmek(interaction.user, interaction.guild):
        await interaction.response.send_message("❌ Bu komutu sadece yetkililer kullanabilir!", ephemeral=True)
        return
    if not member.voice:
        await interaction.response.send_message(f"❌ **{member.display_name}** seste değil!", ephemeral=True)
        return
    try:
        await member.move_to(None)
        await interaction.response.send_message(f"🥾 **{member.display_name}** sesten atıldı!", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Hata: {e}", ephemeral=True)

@bot.tree.command(name="kilitle", description="Bulunulan kanalı üyeler için kilitler veya açar.")
@app_commands.describe(durum="Açmak için 'ac', kapatmak için 'kapat' yazın.")
@app_commands.choices(durum=[
    app_commands.Choice(name="Kapat (Kilitle)", value="kapat"),
    app_commands.Choice(name="Aç (Kilidi Kaldır)", value="ac")
])
async def kilitle(interaction: discord.Interaction, durum: str):
    if not yetkili_mi_kontrol_etmek(interaction.user, interaction.guild):
        await interaction.response.send_message("❌ Bu komutu sadece yetkililer kullanabilir!", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    channel = interaction.channel
    default_role = interaction.guild.default_role

    try:
        if durum == "kapat":
            await channel.set_permissions(default_role, send_messages=False)
            await channel.send("🔒 **Bu kanal yetkililer tarafından kilitlendi!** Üyeler mesaj gönderemez.")
            await interaction.followup.send("✅ Kanal üyeler için kilitlendi (Yetkililer yazabilir).", ephemeral=True)
        elif durum == "ac":
            await channel.set_permissions(default_role, send_messages=None)
            await channel.send("🔓 **Kanalın kilidi açıldı!** Tekrar mesaj yazabilirsiniz.")
            await interaction.followup.send("✅ Kanalın kilidi açıldı.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ İşlem sırasında bir hata oluştu: {e}", ephemeral=True)

@bot.tree.command(name="ticket_kur", description="Ticket menüsü kurar.")
async def ticket_kur(interaction: discord.Interaction):
    if not yetkili_mi_kontrol_etmek(interaction.user, interaction.guild):
        await interaction.response.send_message("❌ Yetkin yok!", ephemeral=True)
        return
    embed = discord.Embed(title="Bilet Oluştur", description="Ticket açmak için menüyü kullanın.", color=discord.Color.green())
    await interaction.channel.send(embed=embed, view=TicketSelectView())
    await interaction.response.send_message("✅ Kuruldu.", ephemeral=True)

@bot.tree.command(name="çekiliş", description="Çekiliş başlatır.")
async def cekilis(interaction: discord.Interaction):
    if not yetkili_mi_kontrol_etmek(interaction.user, interaction.guild):
        await interaction.response.send_message("❌ Yetkin yok!", ephemeral=True)
        return
    await interaction.response.send_message("Çekilişi ayarlayın.", view=CekilisSetupView(), ephemeral=True)

@bot.tree.command(name="sil", description="Mesaj siler.")
@app_commands.describe(miktar="Silinecek sayı (1-100)")
async def sil(interaction: discord.Interaction, miktar: int):
    if not yetkili_mi_kontrol_etmek(interaction.user, interaction.guild):
        await interaction.response.send_message("❌ Yetkin yok!", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=miktar)
    await interaction.followup.send(f"🧹 **{len(deleted)}** mesaj silindi.", ephemeral=True)

# --- DAVET OLAYLARI ---
@bot.event
async def on_member_join(member):
    try:
        for invite in await member.guild.invites():
            if member.id in invite_cache and invite_cache[member.id] < invite.uses:
                inviter = invite.inviter
                if inviter:
                    conn = sqlite3.connect('davetler.db')
                    cursor = conn.cursor()
                    cursor.execute('SELECT joins FROM davet_loglari WHERE user_id = ?', (inviter.id,))
                    if cursor.fetchone():
                        cursor.execute('UPDATE davet_loglari SET joins = joins + 1 WHERE user_id = ?', (inviter.id,))
                    else:
                        cursor.execute('INSERT INTO davet_loglari (user_id, joins) VALUES (?, 1)', (inviter.id,))
                    conn.commit()
                    conn.close()
                break
    except: pass

@bot.event
async def on_member_remove(member):
    try:
        conn = sqlite3.connect('davetler.db')
        cursor = conn.cursor()
        cursor.execute('UPDATE davet_loglari SET lefts = lefts + 1 WHERE user_id = ?', (member.id,))
        conn.commit()
        conn.close()
    except: pass

# --- MESAJ YÖNETİMİ (AI SADECE TICKET'TA) ---
@bot.event
async def on_message(message):
    if message.author.bot: return

    if is_ticket_channel(message.channel):
        async with message.channel.typing():
            yanit = await ai_yanit_uret(message.content)
            await message.reply(yanit)
        return

    await bot.process_commands(message)

@bot.event
async def on_ready():
    bot.add_view(TicketSelectView())
    bot.add_view(CekilisKatilView())
    bot.add_view(TicketKapatView())
    try: await bot.tree.sync()
    except: pass
    print(f'Bot aktif ve hazır: {bot.user.name}')

if __name__ == '__main__':
    threading.Thread(target=run_flask).start()
    token = os.environ.get('BOT_TOKEN')
    if token: bot.run(token)
    else: print("HATA: BOT_TOKEN bulunamadı!")
