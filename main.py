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
from groq import Groq  # Groq AI kütüphanesi
import pyttsx3  # gTTS yerine pyttsx3 (Sınırsız yerel TTS)

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
    return "WinterFall Bot 7/24 Aktif! (Slash Komutları ve Sınırsız Ses Sistemi Devrede)"

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

# Davetleri cache'lemek için sözlük
invite_cache = {}

# Yetkili Kontrol Fonksiyonu
def yetkili_mi_kontrol_etmek(author, guild):
    izinli_roller = ["❄ 𝙁𝙤𝙪𝙣𝙙𝙚𝙧", "❄ 𝙈𝙖𝙮𝙤𝙧", "❄𝘾𝙤-𝙈𝙖𝙮𝙤𝙧", "♱ 𝐖𝐢𝐧𝐭𝐞𝐫𝐟𝙖𝙡𝙡", "𝐖𝐢𝐧𝐭𝐞𝐫𝐟𝙖𝙡𝙡 Yönetim"]
    kullanici_rolleri = [role.name for role in author.roles]
    return author.id == guild.owner_id or any(r in kullanici_rolleri for r in izinli_roller)

# --- TICKET KATEGORİ KONTROLÜ (YZ İÇİN) ---
def is_ticket_channel(channel):
    return channel.category and channel.category.name == "AÇIK TICKETLAR"

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
        if isinstance(channel, discord.TextChannel) and channel.name.endswith(f"-{member.name.lower()}"):
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
        
        partner_metni = (
            f"{etiket_metni}\n\n"
            "📢 **Winterfall 𝐓𝐎𝐏𝐋𝐔𝐋𝐔𝐆̆𝐔 𝐍𝐄𝐃𝐈𝐑?**\n\n"
            "⚔️ 𝐀𝐤𝐭𝐢𝐟 & 𝐒𝐚𝐦𝐢𝐦𝐢 𝐄𝐤𝐢𝐩\n"
            "🛡️ 𝐒𝐚𝐯𝐚𝐬̧𝐥𝐚𝐫𝐝𝐚 𝐘𝐚𝐫𝐝𝐢𝐦 & 𝐃𝐞𝐬𝐭𝐞𝐤\n"
            "🔗 𝐌𝐞𝐫𝐠𝐞 𝐓𝐞𝐤𝐥𝐢𝐟𝐥𝐞𝐫𝐢𝐧𝐞 𝐀𝐜̧𝐢𝐠̆𝐢𝐳\n"
            "📥 𝐄𝐤𝐢𝐩 𝐀𝐥𝐢𝐦𝐥𝐚𝐫𝐢 𝐀𝐤𝐭𝐢𝐟\n"
            "🎮 𝐅𝐚𝐫𝐤𝐥𝐢 𝐎𝐲𝐮𝐧𝐥𝐚𝐫 – 𝐎𝐲𝐮𝐧 𝐀𝐫𝐤𝐚𝐝𝐚𝐬̧𝐢 𝐁𝐮𝐥𝐚𝐛𝐢𝐥𝐢𝐫𝐬𝐢𝐧𝐢𝐳\n"
            "🤝 𝐒𝐚𝐦𝐢𝐦𝐢 & 𝐃𝐨𝐬𝐭𝐚𝐧𝐞 𝐎𝐫𝐭𝐚𝐦\n\n"
            "🔥 Winterfall – 𝐁𝐢𝐫𝐥𝐢𝐤𝐭𝐞 𝐆𝐮̈𝐜̧𝐥𝐮̈𝐲𝐮̈𝐳!\n\n"
            "https://discord.gg/NgfQafxkDV"
        )
        await ticket_channel.send(partner_metni)
    else:
        embed = discord.Embed(
            title=f"🎫 {secilen_kategori} Talebi Açıldı",
            description=f"Merhaba {member.mention}, yetkililerimiz ve yapay zeka asistanımız en kısa sürede sizinle ilgilenecektir.\n\nDesteği kapatmak için aşağıdaki **Desteği Kapat** butonuna basabilirsiniz.",
            color=discord.Color.blue()
        )

        if form_verileri:
            for baslik, cevap in form_verileri.items():
                embed.add_field(name=f"📌 {baslik}", value=f"```\n{cevap}\n```", inline=False)

        await interaction.response.send_message(f"**{secilen_kategori}** için destek kanalınız oluşturuldu: {ticket_channel.mention}", ephemeral=True)
        await ticket_channel.send(content=etiket_metni, embed=embed, view=TicketKapatView())

# --- TICKET MODALLARI ---
class EkipAlimFormu(discord.ui.Modal, title="Ekip Alım Başvuru Formu"):
    eski_ekip = discord.ui.TextInput(label="Eski ekibin?", placeholder="Örn: Vanguard", style=discord.TextStyle.short, required=True)
    sunucu = discord.ui.TextInput(label="Hangi sunucuda oynuyorsun?", placeholder="Örn: CraftRise", style=discord.TextStyle.short, required=True)
    oyun_ici_isim = discord.ui.TextInput(label="Oyun içi ismin ne?", placeholder="Örn: Steve", style=discord.TextStyle.short, required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await olustur_ticket_kanali(interaction, "Ekip Alım", {
            "Eski Ekibi": self.eski_ekip.value,
            "Oynadığı Sunucu": self.sunucu.value,
            "Oyun İçi İsmi": self.oyun_ici_isim.value
        })

class MergeFormu(discord.ui.Modal, title="Merge Başvuru Formu"):
    kim_kime = discord.ui.TextInput(label="Kim kime katılacak?", placeholder="Örn: X ekibi, Y ekibine katılacak.", style=discord.TextStyle.paragraph, required=True)
    ekip_ismi = discord.ui.TextInput(label="Ekip ismi?", placeholder="Örn: WinterFall", style=discord.TextStyle.short, required=True)
    sunucular = discord.ui.TextInput(label="Hangi sunucularda oynuyorsunuz?", placeholder="Örn: CraftRise, SonOyuncu", style=discord.TextStyle.short, required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await olustur_ticket_kanali(interaction, "Merge", {
            "Kim Kime Katılacak": self.kim_kime.value,
            "Ekip İsmi": self.ekip_ismi.value,
            "Sunucular": self.sunucular.value
        })

class AllyFormu(discord.ui.Modal, title="Ally Başvuru Formu"):
    ekip_ismi = discord.ui.TextInput(label="Ekip ismi?", placeholder="Örn: WinterFall", style=discord.TextStyle.short, required=True)
    sunucular = discord.ui.TextInput(label="Hangi sunucularda oynuyorsunuz?", placeholder="Örn: CraftRise, SonOyuncu", style=discord.TextStyle.short, required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await olustur_ticket_kanali(interaction, "Ally", {
            "Ekip İsmi": self.ekip_ismi.value,
            "Sunucular": self.sunucular.value
        })

class GenelDestekFormu(discord.ui.Modal, title="Genel Destek Formu"):
    sorun = discord.ui.TextInput(label="Sorun nedir?", placeholder="Yaşadığınız sorunu kısaca buraya yazın...", style=discord.TextStyle.paragraph, required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await olustur_ticket_kanali(interaction, "Genel Destek", {
            "Sorun": self.sorun.value
        })

# --- AÇILIR MENÜ ---
class TicketSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Ekip Alım", emoji="👤", description="Ekip başvurusu için form doldurun."),
            discord.SelectOption(label="Merge", emoji="🔗", description="Merge işlemleri için form doldurun."),
            discord.SelectOption(label="Partnerlik", emoji="💖", description="Partnerlik görüşmeleri için ticket açar."),
            discord.SelectOption(label="Ally", emoji="⚔️", description="Müttefiklik (Ally) için form doldurun."),
            discord.SelectOption(label="Genel Destek", emoji="⚙️", description="Bir sorun bildirmek için form doldurun.")
        ]
        super().__init__(placeholder="Seçim yap", min_values=1, max_values=1, options=options, custom_id="ticket_select_menu")

    async def callback(self, interaction: discord.Interaction):
        secilen_kategori = self.values[0]

        if secilen_kategori == "Ekip Alım":
            await interaction.response.send_modal(EkipAlimFormu())
        elif secilen_kategori == "Merge":
            await interaction.response.send_modal(MergeFormu())
        elif secilen_kategori == "Ally":
            await interaction.response.send_modal(AllyFormu())
        elif secilen_kategori == "Genel Destek":
            await interaction.response.send_modal(GenelDestekFormu())
        else:
            await olustur_ticket_kanali(interaction, secilen_kategori)

class TicketSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())

# --- ÇEKİLİŞ SİSTEMİ ---
def parse_time(time_str):
    time_str = time_str.lower().strip()
    if time_str.endswith('m'):
        return int(time_str[:-1]) * 60
    elif time_str.endswith('h'):
        return int(time_str[:-1]) * 3600
    elif time_str.endswith('d'):
        return int(time_str[:-1]) * 86400
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
            except:
                pass

class CekilisModal(discord.ui.Modal, title="Çekiliş Oluştur"):
    sure = discord.ui.TextInput(label="Süre (Örn: 10m, 1h, 1d)", placeholder="Örn: 10m", style=discord.TextStyle.short)
    kazanan = discord.ui.TextInput(label="Kazanan Sayısı", placeholder="1", style=discord.TextStyle.short)
    odul = discord.ui.TextInput(label="Ödül", placeholder="Örn: VIP Üyelik", style=discord.TextStyle.short)
    aciklama = discord.ui.TextInput(label="Açıklama (İsteğe Bağlı)", placeholder="Şartlar vs.", style=discord.TextStyle.paragraph, required=False)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            saniye = parse_time(self.sure.value)
            kazanan_sayisi = int(self.kazanan.value)
        except:
            await interaction.response.send_message("❌ Hatalı süre veya kazanan sayısı girdiniz!", ephemeral=True)
            return

        timestamp = int(time.time() + saniye)

        embed = discord.Embed(title=f"🎉 {self.odul.value}", color=discord.Color.dark_theme())
        embed.add_field(name="📊 Katılımcı Sayısı", value="**0** kişi katıldı", inline=False)
        
        if self.aciklama.value:
            embed.description = f"{self.aciklama.value}\n\n**Sona Erme:** <t:{timestamp}:R>\n**Düzenleyen:** {interaction.user.mention}\n**Kazanan Sayısı:** {kazanan_sayisi}"
        else:
            embed.description = f"**Sona Erme:** <t:{timestamp}:R>\n**Düzenleyen:** {interaction.user.mention}\n**Kazanan Sayısı:** {kazanan_sayisi}"
        
        await interaction.response.send_message("Çekiliş başarıyla başlatıldı!", ephemeral=True)
        mesaj = await interaction.channel.send(content="🎉 **ÇEKİLİŞ BAŞLADI** 🎉", embed=embed)

        view = CekilisKatilView(embed, mesaj)
        await mesaj.edit(view=view)

        await asyncio.sleep(saniye)

        try:
            guncel_mesaj = await interaction.channel.fetch_message(mesaj.id)
        except:
            guncel_mesaj = mesaj

        katilimcilar_listesi = list(view.katilimcilar)

        if len(katilimcilar_listesi) == 0:
            sonuc_embed = discord.Embed(title=f"🎉 {self.odul.value}", description=f"Yeterli katılım olmadığı için çekiliş iptal edildi.\n\n**Düzenleyen:** {interaction.user.mention}", color=discord.Color.red())
            await guncel_mesaj.edit(content="🎉 **ÇEKİLİŞ BİTTİ** 🎉", embed=sonuc_embed, view=None)
            return

        kazananlar_id = random.sample(katilimcilar_listesi, min(kazanan_sayisi, len(katilimcilar_listesi)))
        kazananlar_mention = ", ".join([f"<@{uid}>" for uid in kazananlar_id])

        sonuc_embed = discord.Embed(title=f"🎉 {self.odul.value}", color=discord.Color.dark_theme())
        if self.aciklama.value:
            sonuc_embed.description = f"{self.aciklama.value}\n\nSona Erdi: <t:{timestamp}:f>\nDüzenleyen: {interaction.user.mention}\nKatılım: **{len(katilimcilar_listesi)}**\nKazananlar: {kazananlar_mention}"
        else:
            sonuc_embed.description = f"Sona Erdi: <t:{timestamp}:f>\nDüzenleyen: {interaction.user.mention}\nKatılım: **{len(katilimcilar_listesi)}**\nKazananlar: {kazananlar_mention}"

        await guncel_mesaj.edit(content="🎉 **ÇEKİLİŞ BİTTİ** 🎉", embed=sonuc_embed, view=None)
        await interaction.channel.send(f"Tebrikler {kazananlar_mention}! **{self.odul.value}** kazandınız!")

class CekilisSetupView(discord.ui.View):
    @discord.ui.button(label="Çekilişi Ayarla", style=discord.ButtonStyle.green)
    async def ayarla(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not yetkili_mi_kontrol_etmek(interaction.user, interaction.guild):
            await interaction.response.send_message("❌ Bu butonu kullanmaya yetkin yok!", ephemeral=True)
            return

        await interaction.response.send_modal(CekilisModal())

# ==========================================
# BÜTÜN SLASH KOMUTLARI
# ==========================================

@bot.tree.command(name="sunucu", description="Sunucu hakkında detaylı bilgi gösterir.")
async def sunucu(interaction: discord.Interaction):
    guild = interaction.guild
    yazi_kanali = len(guild.text_channels)
    ses_kanali = len(guild.voice_channels)
    kategori_sayisi = len(guild.categories)
    toplam_kanal = len(guild.channels)
    kurulus_tarihi = guild.created_at.strftime("%d/%m/%Y")
    
    embed = discord.Embed(
        title=f"{guild.name} | Sunucu Bilgileri",
        description=(
            f"👑 **Sunucu Sahibi**\n{guild.owner.mention}\n\n"
            f"🆔 **Sunucu ID**\n{guild.id}\n\n"
            f"📅 **Oluşturulma Tarihi**\n{kurulus_tarihi}\n\n"
            f"📜 **Kanal Sayısı** [{toplam_kanal}]\n"
            f"{yazi_kanali} Yazı | {ses_kanali} Ses | {kategori_sayisi} Kategori\n\n"
            f"👥 **Üye Sayısı**\n{guild.member_count:,}\n\n"
            f"🌹 **Rol Sayısı**\n{len(guild.roles)}\n\n"
            f"🟣 **Boost sayısı**\n{guild.premium_subscription_count}"
        ),
        color=discord.Color.dark_embed()
    )
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.set_footer(text=f"Requested by {interaction.user.name} • bugün saat {datetime.now().strftime('%H:%M')}")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="i", description="Kullanıcının davet istatistiklerini gösterir.")
@app_commands.describe(member="Davetlerine bakılacak üye (İsteğe bağlı)")
async def invite_bak(interaction: discord.Interaction, member: discord.Member = None):
    hedef = member or interaction.user
    try:
        conn = sqlite3.connect('davetler.db')
        cursor = conn.cursor()
        cursor.execute('SELECT joins, lefts, fakes, rejoins FROM davet_loglari WHERE user_id = ?', (hedef.id,))
        row = cursor.fetchone()
        conn.close()

        joins = row[0] if row else 0
        lefts = row[1] if row else 0
        fakes = row[2] if row else 0
        rejoins = row[3] if row else 0

        embed = discord.Embed(
            title="Invite log",
            description=f"≫ {hedef.mention} has **{joins}** invites",
            color=discord.Color.blurple()
        )
        
        embed.add_field(name="Joins", value=str(joins), inline=False)
        embed.add_field(name="Left", value=str(lefts), inline=False)
        embed.add_field(name="Fake", value=str(fakes), inline=False)
        embed.add_field(name="Rejoins", value=f"{rejoins} (7d)", inline=False)
        
        if hedef.display_avatar:
            embed.set_thumbnail(url=hedef.display_avatar.url)
            
        embed.set_footer(text=f"Requested by {interaction.user.name} • bugün saat {datetime.now().strftime('%H:%M')}")
        
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ Davet bilgileri okunurken hata oluştu: {e}", ephemeral=True)

@bot.tree.command(name="ireset", description="Tüm davet istatistiklerini sıfırlar (Yalnızca yetkili).")
async def invite_reset(interaction: discord.Interaction):
    if not yetkili_mi_kontrol_etmek(interaction.user, interaction.guild):
        await interaction.response.send_message("❌ Bu komutu sadece yetkililer kullanabilir!", ephemeral=True)
        return

    try:
        conn = sqlite3.connect('davetler.db')
        cursor = conn.cursor()
        cursor.execute('DELETE FROM davet_loglari')
        conn.commit()
        conn.close()
        await interaction.response.send_message("🔄 Sunucudaki tüm davet istatistikleri ve logları başarıyla sıfırlandı!", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Davetler sıfırlanırken hata oluştu: {e}", ephemeral=True)

@bot.tree.command(name="bağlan", description="Botun ses kanalında kalıcı/sınırsız kalmasını sağlar (Yalnızca yetkili).")
async def baglan(interaction: discord.Interaction):
    if not yetkili_mi_kontrol_etmek(interaction.user, interaction.guild):
        await interaction.response.send_message("❌ Bu komutu sadece yetkililer kullanabilir!", ephemeral=True)
        return

    if not interaction.user.voice:
        await interaction.response.send_message("❌ Önce bir ses kanalına girmelisin!", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    try:
        channel = interaction.user.voice.channel
        if interaction.guild.voice_client:
            await interaction.guild.voice_client.move_to(channel)
        else:
            await channel.connect(self_deaf=True)
        await interaction.followup.send(f"🔊 Ses kanalına katıldım ve kalıcı olarak sabitlendim: **{channel.name}**", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Ses kanalına bağlanırken hata oluştu: {e}", ephemeral=True)

@bot.tree.command(name="ayrıl", description="Botun ses kanalından çıkmasını sağlar (Yalnızca yetkili).")
async def ayril(interaction: discord.Interaction):
    if not yetkili_mi_kontrol_etmek(interaction.user, interaction.guild):
        await interaction.response.send_message("❌ Bu komutu sadece yetkililer kullanabilir!", ephemeral=True)
        return

    if interaction.guild.voice_client:
        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message("👋 Ses kanalından ayrıldım.", ephemeral=True)
    else:
        await interaction.response.send_message("❌ Zaten bir ses kanalında değilim!", ephemeral=True)

@bot.tree.command(name="konuş", description="Botun ses kanalında metni sesli okumasını sağlar (pyttsx3 - Sınırsız).")
@app_commands.describe(mesaj="Botun sesli olarak söylemesini istediğin yazı")
async def konus(interaction: discord.Interaction, mesaj: str):
    if not yetkili_mi_kontrol_etmek(interaction.user, interaction.guild):
        await interaction.response.send_message("❌ Bu komutu sadece yetkililer kullanabilir!", ephemeral=True)
        return

    if not interaction.guild.voice_client:
        await interaction.response.send_message("❌ Önce botu bir ses kanalına sokmalısın! (`/bağlan`)", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    try:
        engine = pyttsx3.init()
        engine.save_to_file(mesaj, 'ses.mp3')
        engine.runAndWait()

        voice_client = interaction.guild.voice_client
        if voice_client.is_playing():
            voice_client.stop()

        audio_source = discord.FFmpegPCMAudio('ses.mp3')
        voice_client.play(audio_source)

        await interaction.followup.send(f"🗣️ Sesli okunuyor: *\"{mesaj}\*", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Sesli okuma sırasında hata oluştu: {e}", ephemeral=True)

@bot.tree.command(name="ticket_kur", description="Ticket menüsünü kurar (Yalnızca yetkili).")
async def ticket_kur(interaction: discord.Interaction):
    if not yetkili_mi_kontrol_etmek(interaction.user, interaction.guild):
        await interaction.response.send_message("❌ Bu komutu sadece yetkililer kullanabilir!", ephemeral=True)
        return
        
    embed = discord.Embed(
        title="Bilet Oluştur",
        description="Ticket açmak için aşağıdaki **Seçim yap** menüsünden uygun kategoriyi seçin.",
        color=discord.Color.green()
    )
    await interaction.channel.send(embed=embed, view=TicketSelectView())
    await interaction.response.send_message("✅ Ticket menüsü başarıyla kuruldu.", ephemeral=True)

@bot.tree.command(name="çekiliş", description="Yeni bir çekiliş başlatır (Yalnızca yetkili).")
async def cekilis(interaction: discord.Interaction):
    if not yetkili_mi_kontrol_etmek(interaction.user, interaction.guild):
        await interaction.response.send_message("❌ Bu komutu sadece yetkililer kullanabilir!", ephemeral=True)
        return
        
    await interaction.response.send_message("Çekiliş detaylarını girmek için aşağıdaki butona tıklayın.", view=CekilisSetupView(), ephemeral=True)

@bot.tree.command(name="sil", description="Belirtilen miktarda mesajı siler (Yalnızca yetkili).")
@app_commands.describe(miktar="Silinecek mesaj sayısı (1-100)")
async def sil(interaction: discord.Interaction, miktar: int):
    if not yetkili_mi_kontrol_etmek(interaction.user, interaction.guild):
        await interaction.response.send_message("❌ Bu komutu sadece yetkililer kullanabilir!", ephemeral=True)
        return
        
    if miktar <= 0 or miktar > 100:
        await interaction.response.send_message("❌ Lütfen 1 ile 100 arasında bir sayı girin.", ephemeral=True)
        return
        
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=miktar)
    await interaction.followup.send(f"🧹 **{len(deleted)}** adet mesaj başarıyla silindi.", ephemeral=True)

# --- DAVET SİSTEMİ OLAYLARI ---
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
                    row = cursor.fetchone()
                    if row:
                        cursor.execute('UPDATE davet_loglari SET joins = joins + 1 WHERE user_id = ?', (inviter.id,))
                    else:
                        cursor.execute('INSERT INTO davet_loglari (user_id, joins) VALUES (?, 1)', (inviter.id,))
                    conn.commit()
                    conn.close()
                break
        for invite in await member.guild.invites():
            invite_cache[invite.code] = invite.uses
    except Exception as e:
        print(f"Join davet hatası: {e}")

@bot.event
async def on_member_remove(member):
    try:
        conn = sqlite3.connect('davetler.db')
        cursor = conn.cursor()
        cursor.execute('UPDATE davet_loglari SET lefts = lefts + 1 WHERE user_id = ?', (member.id,))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Remove davet hatası: {e}")

# --- GROQ AI YANIT ÜRETME FONKSİYONU ---
async def ai_yanit_uret(metin):
    try:
        chat_completion = ai_client.chat.completions.create(
            messages=[{"role": "user", "content": metin}],
            model="llama-3.1-8b-instant",
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"❌ Yapay zeka yanıt verirken bir hata oluştu: {e}"

# --- BOT OLAYLARI & YAPAY ZEKA / KANAL SİSTEMİ ---
@bot.event
async def on_ready():
    bot.add_view(TicketSelectView())
    bot.add_view(CekilisKatilView())
    bot.add_view(TicketKapatView())
    
    try:
        synced = await bot.tree.sync()
        print(f"Slash komutları senkronize edildi: {len(synced)} komut aktif.")
    except Exception as e:
        print(f"Komut senkronizasyon hatası: {e}")
    
    for guild in bot.guilds:
        try:
            for invite in await guild.invites():
                invite_cache[invite.code] = invite.uses
        except:
            pass

    print(f'Bot başarıyla giriş yaptı: {bot.user.name}')
    await bot.change_presence(activity=discord.Game(name="/sunucu | WinterFall"))

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if bot.user.mentioned_in(message) or is_ticket_channel(message.channel):
        temiz_mesaj = message.content.replace(f"<@{bot.user.id}>", "").strip()
        if temiz_mesaj:
            async with message.channel.typing():
                cevap = await ai_yanit_uret(temiz_mesaj)
                await message.reply(cevap)
        return

    icerik = message.content.lower()
    if ("kanal" in icerik or "kanalı" in icerik) and ("oluş" in icerik or "aç" in icerik):
        if yetkili_mi_kontrol_etmek(message.author, message.guild):
            temiz_isim = message.content.replace("oluşturur musun", "").replace("oluştur", "").replace("açarmısın", "").replace("açır mısın", "").replace("aç", "").replace("adında", "").replace("isimli", "").replace("kanal", "").replace("kanalı", "").replace("kur", "").strip()
            
            if not temiz_isim:
                temiz_isim = "yeni-kanal"

            try:
                if "ses" in icerik:
                    yeni_kanal = await message.guild.create_voice_channel(name=temiz_isim)
                    await message.reply(f"✅ Hemen oluşturuyorum! Ses kanalınız açıldı: **{yeni_kanal.name}**")
                else:
                    yeni_kanal = await message.guild.create_text_channel(name=temiz_isim)
                    await message.reply(f"✅ Hemen oluşturuyorum! Yazı kanalınız açıldı: {yeni_kanal.mention}")
            except Exception as e:
                await message.reply(f"❌ Kanal oluşturulurken hata oluştu: {e}")
            return

# --- BAŞLATMA ---
if __name__ == '__main__':
    server_thread = threading.Thread(target=run_flask)
    server_thread.start()
    
    token = os.environ.get('BOT_TOKEN')
    if token:
        bot.run(token)
    else:
        print("HATA: BOT_TOKEN bulunamadı!")
