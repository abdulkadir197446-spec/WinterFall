import discord
from discord.ext import commands
from discord import app_commands
import os
from flask import Flask
import threading
import sqlite3
import random
from datetime import timedelta
import logging
import asyncio

# ==========================================
# 0. DETAYLI LOGLAMA VE SİSTEM YAPILANDIRMASI
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("WinterFallBot")

# ==========================================
# 1. BOT INTENTS VE BAŞLANGIÇ AYARLARI
# ==========================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True
intents.guilds = True
intents.emojis = True
intents.bans = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ==========================================
# 2. RENDER 7/24 WEB SUNUCUSU (FLASK)
# ==========================================
app = Flask('')

@app.route('/')
def home():
    logger.info("Web sunucusuna ping atıldı (7/24 aktif tutma isteği).")
    return "WinterFall Pro AI Bot Aktif ve Çalışır Durumda!", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# ==========================================
# 3. VERİTABANI YÖNETİMİ
# ==========================================
def get_database_connection():
    try:
        connection = sqlite3.connect('winterfall_pro.db')
        return connection
    except sqlite3.Error as db_err:
        logger.error(f"SQLite bağlantı hatası: {db_err}")
        return None

def initialize_database_structure():
    conn = get_database_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS invites (
                    user_id INTEGER PRIMARY KEY,
                    invites_count INTEGER DEFAULT 0,
                    fake_count INTEGER DEFAULT 0,
                    leave_count INTEGER DEFAULT 0
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS partner_stats (
                    user_id INTEGER PRIMARY KEY,
                    real_partner INTEGER DEFAULT 0,
                    fake_partner INTEGER DEFAULT 0,
                    last_text TEXT DEFAULT ""
                )
            ''')
            conn.commit()
            logger.info("Veritabanı tabloları başarıyla oluşturuldu.")
        except sqlite3.Error as err:
            logger.error(f"Tablo oluşturma hatası: {err}")
        finally:
            conn.close()

initialize_database_structure()

# ==========================================
# SABİTLER, TEMALAR VE KANALLAR
# ==========================================
WINTERFALL_ROL = "♱ 𝐖𝐢𝐧𝐭𝐞𝐫𝐟𝐚𝐥𝐥"
EKIP_ROL = "𝙒𝙞𝙣𝙩𝙚𝙧𝙛𝙖𝙡𝙡 𝙀𝙠𝙞𝙥"
KANALLAR = {
    "girisCıkıs": "「🎈」giriş-çıkış",
    "galeriChat": "「📷」galeri-chat",
    "sohbet": "「💬」sohbet",
    "ekipDuyuru": "「📣」ekip-duyuru",
    "mesajLog": "mesaj-log",
    "modLog": "mod-log"
}
YASAKLI_KELIMELER = ["küfür1", "küfür2"]
spamMap = {}

TEMALAR = {
    "kış": {
        "adi": "WinterFall Klasik Kış Frost",
        "renk": discord.Color.from_rgb(30, 61, 89),
        "emoji": "❄️",
        "footer": "WinterFall Ecosystem • Frost Edition"
    },
    "nitro": {
        "adi": "Discord Nitro & Boost",
        "renk": discord.Color.from_rgb(114, 137, 218),
        "emoji": "💎",
        "footer": "WinterFall Ecosystem • Nitro Boost"
    },
    "altın": {
        "adi": "Özel Altın / VIP Elite",
        "renk": discord.Color.gold(),
        "emoji": "👑",
        "footer": "WinterFall Ecosystem • VIP Elite"
    },
    "siber": {
        "adi": "Cyberpunk / Neon Vibe",
        "renk": discord.Color.from_rgb(0, 255, 204),
        "emoji": "⚡",
        "footer": "WinterFall Ecosystem • Cyber Mode"
    }
}

# ==========================================
# 4. TİCKET SİSTEMİ (Seçim Menüsü ve Butonlar)
# ==========================================
class TicketKapatView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Ticket'ı Kapat", style=discord.ButtonStyle.danger, custom_id="ticket_kapat_btn")
    async def kapat_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Ticket kapatılıyor, 5 saniye içinde kanal silinecek...", ephemeral=True)
        await asyncio.sleep(5)
        try:
            await interaction.channel.delete()
        except:
            pass

class TicketSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Destek", description="Genel destek almak için.", emoji="🛠️"),
            discord.SelectOption(label="Partnerlik", description="Sunucu partnerliği için.", emoji="💖"),
            discord.SelectOption(label="Şikayet", description="Yetkili şikayeti veya öneri için.", emoji="⚠️"),
            discord.SelectOption(label="Ekip Alım", description="Ekibimize katılmak için başvuru yap.", emoji="📥"),
            discord.SelectOption(label="Merge", description="Sunucu birleşim / merge teklifleri için.", emoji="🔗")
        ]
        super().__init__(placeholder="Destek kategorisi seçin...", min_values=1, max_values=1, options=options, custom_id="ticket_select_menu")

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        secilen_kategori = self.values[0]
        guild = interaction.guild
        
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
        }

        kategori_adi = f"ticket-{secilen_kategori.lower().replace(' ', '-')}-{interaction.user.name}"
        ticket_channel = await guild.create_text_channel(name=kategori_adi, overwrites=overwrites)

        if secilen_kategori == "Partnerlik":
            embed = discord.Embed(
                title="💖 Partnerlik Başvuru Talebi",
                description="Aramıza katılmak için şartları sağlayıp sunucu davetinizi bırakın.",
                color=discord.Color.from_rgb(255, 105, 180)
            )
            await interaction.followup.send(f"**{secilen_kategori}** için destek kanalınız oluşturuldu: {ticket_channel.mention}", ephemeral=True)
            await ticket_channel.send(embed=embed, view=TicketKapatView())
            partnerlik_metni = (
                "Selam! Partnerlik şartlarımız şunlardır:\n"
                "1. Sunucunuz aktif olmalı.\n"
                "2. Davet linkini buraya bırakabilirsiniz."
            )
            await ticket_channel.send(partnerlik_metni)
        else:
            await interaction.followup.send(f"Destek kanalınız oluşturuldu: {ticket_channel.mention}", ephemeral=True)
            embed = discord.Embed(
                title=f"❄️ {secilen_kategori} Talebi",
                description=f"Değerli **{interaction.user.name}**, yetkililerimiz en kısa sürede sizinle ilgilenecektir.",
                color=discord.Color.blue()
            )
            await ticket_channel.send(embed=embed, view=TicketKapatView())

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())

# ==========================================
# 5. BOT EVENTLERİ VE KONTROL SİSTEMLERİ
# ==========================================
@bot.event
async def on_ready():
    logger.info(f'{bot.user.name} başarıyla giriş yaptı!')
    try:
        synced = await bot.tree.sync()
        logger.info(f"{len(synced)} adet slash komut senkronize edildi.")
    except Exception as e:
        logger.error(f"Komut senkronizasyon hatası: {e}")

@bot.event
async def on_member_join(member):
    try:
        channel = discord.utils.get(member.guild.text_channels, name=KANALLAR["girisCıkıs"])
        if channel:
            embed = discord.Embed(
                title='❄️ Yeni Savaşçı Katıldı! ❄️',
                description=f'Sunucuya hoş geldin **{member.name}**! Seninle beraber **{member.guild.member_count}** kişi olduk!',
                color=discord.Color.from_rgb(30, 61, 89)
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text='WinterFall Güvenlik ve Kar Sistemi', icon_url=member.guild.icon.url if member.guild.icon else None)
            embed.timestamp = discord.utils.utcnow()
            await channel.send(content=f"<@{member.id}>", embeds=[embed])
    except Exception as e:
        logger.error(f"Giriş event hatası: {e}")

@bot.event
async def on_member_remove(member):
    try:
        channel = discord.utils.get(member.guild.text_channels, name=KANALLAR["girisCıkıs"])
        if channel:
            embed = discord.Embed(
                title='❄️ Bir Savaşçı Ayrıldı ❄️',
                description=f'**{member.name}** aramızdan ayrıldı. Sensiz **{member.guild.member_count}** kişi kaldık. Güle güle!',
                color=discord.Color.from_rgb(139, 0, 0)
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text='WinterFall Veda Sistemi', icon_url=member.guild.icon.url if member.guild.icon else None)
            embed.timestamp = discord.utils.utcnow()
            await channel.send(embeds=[embed])
    except Exception as e:
        logger.error(f"Çıkış event hatası: {e}")

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        await bot.process_commands(message)
        return

    is_winterfall = any(r.name == WINTERFALL_ROL for r in message.author.roles)

    if message.channel.name == KANALLAR["ekipDuyuru"]:
        ekip_rol_obj = discord.utils.get(message.guild.roles, name=EKIP_ROL)
        if ekip_rol_obj:
            await message.channel.send(
                content=f"🔔 Hey **{ekip_rol_obj.name}** üyeleri! Ekip duyuru kanalına yeni bir bildiri düştü, hemen kontrol et!",
                embed=discord.Embed(
                    title='❄️ WinterFall Ekip Bildirisi',
                    description=f"**Yazan:** {message.author.mention}\n\n[Mesaja Gitmek İçin Tıkla]({message.url})",
                    color=discord.Color.from_rgb(0, 180, 216)
                )
            )

    if not is_winterfall:
        if message.channel.name == KANALLAR["galeriChat"] and len(message.attachments) == 0:
            await message.delete()
            try:
                await message.author.send(f"❄️ `{KANALLAR['galeriChat']}` kanalına yalnızca görsel/medya atabilirsin!")
            except:
                pass
            return

        if message.channel.name == KANALLAR["sohbet"] and message.content.startswith('/') and not message.content.startswith('/sunucu') and not message.content.startswith('/ai'):
            await message.delete()
            try:
                await message.author.send(f"❄️ Bu sohbet kanalında sadece `/sunucu` ve `/ai` komutları kullanılabilir!")
            except:
                pass
            return

    if not is_winterfall:
        mesaj_icerigi = message.content.lower()
        if any(kufur in mesaj_icerigi for kufur in YASAKLI_KELIMELER):
            await message.delete()
            uyari = await message.channel.send(f"⚠️ {message.author.mention} Küfür etmek yasak!")
            await asyncio.sleep(5)
            await uyari.delete()

            log_kanal = discord.utils.get(message.guild.text_channels, name=KANALLAR["mesajLog"])
            if log_kanal:
                log_embed = discord.Embed(title='❄️ WinterFall | Küfür Algılandı', color=discord.Color.from_rgb(255, 77, 77))
                log_embed.add_field(name='Yapılan (Kullanıcı)', value=f"{message.author} (`{message.author.id}`)", inline=True)
                log_embed.add_field(name='Kanal', value=f"{message.channel.mention}", inline=True)
                log_embed.add_field(name='Silinen Mesaj', value=message.content, inline=False)
                log_embed.timestamp = discord.utils.utcnow()
                await log_kanal.send(embed=log_embed)
            return

        user_id = message.author.id
        currentTime = asyncio.get_event_loop().time()
        userSpamData = spamMap.get(user_id, {"lastMessage": "", "count": 0, "time": 0})

        if userSpamData["lastMessage"] == message.content and (currentTime - userSpamData["time"]) < 5.0:
            userSpamData["count"] += 1
            userSpamData["time"] = currentTime
            spamMap[user_id] = userSpamData

            if userSpamData["count"] == 2:
                await message.channel.send(f"⚠️ <@{user_id}>, lütfen spam yapmayı kes! Bu 2. uyarın.")
            elif userSpamData["count"] >= 3:
                try:
                    await message.author.timeout(timedelta(minutes=10), reason="WinterFall Anti-Spam: Üst üste spam yapıldı.")
                    await message.channel.send(f"❄️ <@{user_id}> üst üste spam yaptığı için **10 dakika** süreyle susturuldu!")
                    spamMap[user_id] = {"lastMessage": "", "count": 0, "time": 0}
                except Exception as err:
                    logger.error(f"Timeout hatası: {err}")
        else:
            spamMap[user_id] = {"lastMessage": message.content, "count": 1, "time": currentTime}

    await bot.process_commands(message)

# ==========================================
# 6. MODERASYON, ÇEKİLİŞ PANELİ, TICKET VE AI KOMUTLARI
# ==========================================

@bot.tree.command(name="ticket-kur", description="Gelişmiş seçim menülü destek (ticket) panelini kurar.")
@app_commands.default_permissions(administrator=True)
async def ticket_kur(interaction: discord.Interaction):
    embed = discord.Embed(
        title="❄️ WinterFall Destek Sistemi",
        description="Aşağıdaki menüden açmak istediğiniz destek kategorisini seçin.",
        color=discord.Color.from_rgb(100, 150, 255)
    )
    await interaction.channel.send(embed=embed, view=TicketView())
    await interaction.response.send_message("Ticket paneli başarıyla kuruldu!", ephemeral=True)


# --- Çekiliş Modalı (Ödül ve Süre Girişi İçin) ---
class CekilisOlusturModal(discord.ui.Modal, title="🎁 WinterFall Çekiliş Oluşturucu"):
    odul = discord.ui.TextInput(
        label="Çekiliş Ödülü",
        placeholder="Örn: 1x Discord Nitro / 100K Nakit",
        required=True,
        max_length=100
    )
    sure = discord.ui.TextInput(
        label="Süre (Saat cinsinden)",
        placeholder="Örn: 24 (1 gün için)",
        default="24",
        required=True,
        max_length=3
    )

    def __init__(self, tema_key: str):
        super().__init__()
        self.tema_key = tema_key

    async def on_submit(self, interaction: discord.Interaction):
        try:
            sure_saat = int(self.sure.value)
        except ValueError:
            await interaction.response.send_message("❌ Süre kısmına geçerli bir sayı yazmalısın!", ephemeral=True)
            return

        secilen_tema = TEMALAR.get(self.tema_key, TEMALAR["kış"])
        bitis_zamani = discord.utils.utcnow() + timedelta(hours=sure_saat)

        embed = discord.Embed(
            title=f"{secilen_tema['emoji']} WinterFall Ödüllü Çekiliş Vakti!",
            description=(
                f"🎁 **Verilen Ödül:** `{self.odul.value}`\n"
                f"👑 **Düzenleyen:** {interaction.user.mention}\n"
                f"⏳ **Bitiş Süresi:** <t:{int(bitis_zamani.timestamp())}:R> (<t:{int(bitis_zamani.timestamp())}:F>)\n\n"
                f"Katılmak için aşağıdaki **🎉 Katıl** butonuna tıklaman yeterli!"
            ),
            color=secilen_tema['renk']
        )
        embed.set_footer(text=f"{secilen_tema['footer']} • Şansınız bol olsun!")

        class CekilisKatilView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=None)
                self.katilanlar = set()

            @discord.ui.button(label="🎉 Katıl (0)", style=discord.ButtonStyle.primary, custom_id="winterfall_cekilis_btn_v3")
            async def katil_btn(self, btn_interaction: discord.Interaction, button: discord.ui.Button):
                if btn_interaction.user.id in self.katilanlar:
                    self.katilanlar.remove(btn_interaction.user.id)
                    button.label = f"🎉 Katıl ({len(self.katilanlar)})"
                    await btn_interaction.response.send_message("❌ Çekilişten başarıyla ayrıldın!", ephemeral=True)
                else:
                    self.katilanlar.add(btn_interaction.user.id)
                    button.label = f"🎉 Katıl ({len(self.katilanlar)})"
                    await btn_interaction.response.send_message("✅ Çekilişe başarıyla katıldın! Şanslı isim sen olabilirsin.", ephemeral=True)
                await btn_interaction.message.edit(view=self)

        await interaction.channel.send(embed=embed, view=CekilisKatilView())
        await interaction.response.send_message(f"✅ **{secilen_tema['adi']}** temalı çekiliş paneli başarıyla yayına alındı!", ephemeral=True)


# --- Çekiliş Tema Seçim Paneli (View) ---
class CekilisTemaSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)

    @discord.ui.select(
        placeholder="Çekiliş temasını seçin...",
        min_values=1,
        max_values=1,
        options=[
            discord.SelectOption(label="Kış Klasik", value="kış", emoji="❄️", description="Klasik kış mavisi tasarımı."),
            discord.SelectOption(label="Discord Nitro & Boost", value="nitro", emoji="💎", description="Nitro ve takviye temalı özel çekiliş."),
            discord.SelectOption(label="Özel Altın / VIP", value="altın", emoji="👑", description="Altın sarısı VIP elite tasarımı."),
            discord.SelectOption(label="Cyberpunk / Neon", value="siber", emoji="⚡", description="Neon yeşil/mavi cyber teması.")
        ]
    )
    async def tema_secildi(self, interaction: discord.Interaction, select: discord.ui.Select):
        secilen_tema_key = select.values[0]
        # Temayı seçtikten sonra ödül ve süreyi girmek için modal ekranını açıyoruz
        await interaction.response.send_modal(CekilisOlusturModal(tema_key=secilen_tema_key))


@bot.tree.command(name="çekiliş", description="Görsel temalı interaktif çekiliş yönetim panelini açar.")
@app_commands.default_permissions(manage_guild=True)
async def cekilis_komutu(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎁 WinterFall Çekiliş Kontrol Paneli",
        description="Aşağıdaki menüden çekiliş için bir **tema** seçerek ödül ve süreyi belirleyebileceğin panele ulaşabilirsin.",
        color=discord.Color.from_rgb(30, 61, 89)
    )
    embed.set_footer(text="WinterFall Giveaway System • Panel", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
    
    await interaction.response.send_message(embed=embed, view=CekilisTemaSelectView(), ephemeral=True)


@bot.tree.command(name="sunucu", description="Sunucunun tüm detaylı istatistiklerini ve bilgilerini gösteren modern kart atar.")
async def sunucu_komutu(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild
    
    bot_sayisi = sum(1 for m in guild.members if m.bot)
    uye_sayisi = guild.member_count - bot_sayisi
    kanal_sayisi = len(guild.channels)
    rol_sayisi = len(guild.roles)
    
    embed = discord.Embed(
        title=f"🛡️ {guild.name} • Sunucu İstatistik ve Bilgi Merkezi",
        description="WinterFall ekosistem altyapısıyla korunan sunucumuza ait genel detaylar aşağıda listelenmiştir.",
        color=discord.Color.from_rgb(0, 150, 255)
    )
    
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    if guild.banner:
        embed.set_image(url=guild.banner.url)
        
    embed.add_field(name="👑 Sunucu Sahibi", value=guild.owner.mention if guild.owner else "Bilinmiyor", inline=True)
    embed.add_field(name="📅 Kuruluş Tarihi", value=f"<t:{int(guild.created_at.timestamp())}:D>", inline=True)
    embed.add_field(name="🌍 Sunucu Bölgesi", value=str(guild.preferred_locale).upper(), inline=True)
    
    embed.add_field(name="👥 Toplam Üye", value=f"Gerçek: **{uye_sayisi}**\nBot: **{bot_sayisi}**\nToplam: **{guild.member_count}**", inline=True)
    embed.add_field(name="📁 Kanal Bilgileri", value=f"Toplam Kanal: **{kanal_sayisi}**", inline=True)
    embed.add_field(name="🛡️ Rol ve Güvenlik", value=f"Rol Sayısı: **{rol_sayisi}**\nDoğrulama Seviyesi: **{guild.verification_level}**", inline=True)
    
    embed.set_footer(text=f"Sorgulayan: {interaction.user.name} • WinterFall Information Panel", icon_url=interaction.user.display_avatar.url)
    
    await interaction.channel.send(embed=embed)
    await interaction.followup.send("✅ Gelişmiş sunucu bilgi kartı kanala gönderildi.", ephemeral=True)


@bot.tree.command(name="ai", description="Yapay zeka asistanına soru sorar ve akıllı yanıt alır.")
@app_commands.describe(soru="Yapay zekaya yöneltmek istediğiniz soru veya mesaj")
async def ai_komutu(interaction: discord.Interaction, soru: str):
    await interaction.response.defer(thinking=True)
    
    soru_kucuk = soru.lower()
    
    if "nasılsın" in soru_kucuk or "naber" in soru_kucuk:
        yanit = "Harikayım! WinterFall sistemlerini senin için optimize ediyorum. Sana nasıl yardımcı olabilirim?"
    elif "merhaba" in soru_kucuk or "selam" in soru_kucuk:
        yanit = f"Selamlar {interaction.user.mention}! WinterFall yapay zeka asistanı hizmetinizde."
    elif "yardım" in soru_kucuk:
        yanit = "Sunucumuzda `/ticket-kur` ile destek açabilir, `/çekiliş` ile çekiliş paneli açabilir ya da `/sunucu` ile istatistikleri inceleyebilirsin."
    elif "winterfall" in soru_kucuk:
        yanit = "WinterFall; güvenlik, eğlence, yapay zeka ve gelişmiş moderasyon araçlarını barındıran üst düzey bir Discord ekosistemidir."
    else:
        akilli_cevaplar = [
            f"Analiz edildi: '{soru}' konusunu WinterFall veritabanı ve genel kurallar çerçevesinde inceliyorum.",
            f"Harika bir yaklaşım! '{soru}' hakkında topluluğumuzun sohbet kanallarında fikir alışverişi yapabilirsin.",
            f"Yapay zeka motoru girdini işledi: '{soru}' talebin için gerekli protokoller aktif durumda."
        ]
        yanit = random.choice(akilli_cevaplar)

    embed = discord.Embed(
        title="🤖 WinterFall AI Asistan Yanıtı",
        description=yanit,
        color=discord.Color.from_rgb(0, 210, 255)
    )
    embed.add_field(name="Sorulan Soru", value=soru, inline=False)
    embed.set_footer(text=f"Soran: {interaction.user.name} • WinterFall AI Engine", icon_url=interaction.user.display_avatar.url)
    
    await interaction.followup.send(embed=embed)


@bot.tree.command(name="ban", description="Belirtilen kullanıcıyı sunucudan yasaklar.")
@app_commands.default_permissions(ban_members=True)
async def ban_komutu(interaction: discord.Interaction, member: discord.Member, sebep: str = "Sebep belirtilmedi"):
    await interaction.response.defer(ephemeral=True)
    try:
        await member.ban(reason=sebep)
        await interaction.followup.send(f"✅ **{member.name}** başarıyla banlandı.", ephemeral=True)
        
        log_kanal = discord.utils.get(interaction.guild.text_channels, name=KANALLAR["modLog"])
        if log_kanal:
            embed = discord.Embed(title="❄️ WinterFall | Üye Banlandı", color=discord.Color.red())
            embed.add_field(name="🔨 İşlemi Yapan", value=f"{interaction.user} (`{interaction.user.id}`)", inline=False)
            embed.add_field(name="🎯 İşlem Yapılan", value=f"{member} (`{member.id}`)", inline=False)
            embed.add_field(name="Sebep", value=sebep, inline=False)
            embed.set_thumbnail(url=member.display_avatar.url)
            await log_kanal.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"❌ Ban işlemi gerçekleştirilemedi: {e}", ephemeral=True)


@bot.tree.command(name="kick", description="Belirtilen kullanıcıyı sunucudan atar.")
@app_commands.default_permissions(kick_members=True)
async def kick_komutu(interaction: discord.Interaction, member: discord.Member, sebep: str = "Sebep belirtilmedi"):
    await interaction.response.defer(ephemeral=True)
    try:
        await member.kick(reason=sebep)
        await interaction.followup.send(f"👢 **{member.name}** sunucudan atıldı.", ephemeral=True)
        
        log_kanal = discord.utils.get(interaction.guild.text_channels, name=KANALLAR["modLog"])
        if log_kanal:
            embed = discord.Embed(title="❄️ WinterFall | Üye Atıldı (Kick)", color=discord.Color.orange())
            embed.add_field(name="🔨 İşlemi Yapan", value=f"{interaction.user} (`{interaction.user.id}`)", inline=False)
            embed.add_field(name="🎯 İşlem Yapılan", value=f"{member} (`{member.id}`)", inline=False)
            embed.add_field(name="Sebep", value=sebep, inline=False)
            embed.set_thumbnail(url=member.display_avatar.url)
            await log_kanal.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"❌ Kick işlemi gerçekleştirilemedi: {e}", ephemeral=True)

# ==========================================
# 7. ANA ÇALIŞTIRMA
# ==========================================
if __name__ == "__main__":
    logger.info("WinterFall Bot servisleri başlatılıyor...")
    t = threading.Thread(target=run_flask, daemon=True)
    t.start()
    
    TOKEN = os.getenv("DISCORD_TOKEN")
    if TOKEN:
        bot.run(TOKEN)
    else:
        logger.critical("HATA: DISCORD_TOKEN bulunamadı! Render ortam değişkenlerine token'ı ekleyin.")
