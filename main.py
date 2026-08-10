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

# Prefix kaldırıldı, sadece slash komutları kullanılıyor
bot = commands.Bot(command_prefix="!", intents=intents)

# ==========================================
# 2. RENDER 7/24 WEB SUNUCUSU (FLASK)
# ==========================================
app = Flask('')

@app.route('/')
def home():
    logger.info("Web sunucusuna ping atıldı (7/24 aktif tutma isteği).")
    return "WinterFall Pro Bot Aktif ve Çalışır Durumda!", 200

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
# SABİTLER VE KANALLAR
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

# --- WinterFall Giriş / Çıkış Kart Sistemi ---
@bot.event
async def on_member_join(member):
    try:
        channel = discord.utils.get(member.guild.text_channels, name=KANALLAR["girisCıkıs"])
        if channel:
            embed = discord.Embed(
                title='❄️ Yeni Savaşçı Katıldı! ❄️',
                description=f'Sunucuya hoş geldin **{member.name}**! Seninle beraber **{member.guild.memberCount}** kişi olduk!',
                color=discord.Color.from_rgb(30, 61, 89)
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text='WinterFall Güvenlik ve Kar Sistemi', icon_url=member.guild.iconURL())
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
                description=f'**{member.name}** aramızdan ayrıldı. Sensiz **{member.guild.memberCount}** kişi kaldık. Güle güle!',
                color=discord.Color.from_rgb(139, 0, 0)
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text='WinterFall Veda Sistemi', icon_url=member.guild.iconURL())
            embed.timestamp = discord.utils.utcnow()
            await channel.send(embeds=[embed])
    except Exception as e:
        logger.error(f"Çıkış event hatası: {e}")

# --- Mesaj & Güvenlik Denetimi (Küfür, Spam, Kanal Filtreleri, Ekip Duyuru) ---
@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        await bot.process_commands(message)
        return

    is_winterfall = any(r.name == WINTERFALL_ROL for r in message.member.roles)

    # 1. Ekip Duyuru Sistemi
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

    # 2. Kanal Kısıtlamaları (Galeri Chat ve Sohbet)
    if not is_winterfall:
        if message.channel.name == KANALLAR["galeriChat"] and len(message.attachments) == 0:
            await message.delete()
            try:
                await message.author.send(f"❄️ `{KANALLAR['galeriChat']}` kanalına yalnızca görsel/medya atabilirsin!")
            except:
                pass
            return

        if message.channel.name == KANALLAR["sohbet"] and message.content.startswith('/') and not message.content.startswith('/sunucu'):
            await message.delete()
            try:
                await message.author.send(f"❄️ Bu sohbet kanalında sadece `/sunucu` komutu kullanılabilir!")
            except:
                pass
            return

    # 3. Küfür Engelleme (WinterFall Rolü Hariç)
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

        # 4. Anti-Spam / Flood Koruması
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
                    await message.member.timeout(timedelta(minutes=10), reason="WinterFall Anti-Spam: Üst üste spam yapıldı.")
                    await message.channel.send(f"❄️ <@{user_id}> üst üste spam yaptığı için **10 dakika** süreyle susturuldu!")
                    spamMap[user_id] = {"lastMessage": "", "count": 0, "time": 0}
                except Exception as err:
                    logger.error(f"Timeout hatası: {err}")
        else:
            spamMap[user_id] = {"lastMessage": message.content, "count": 1, "time": currentTime}

    await bot.process_commands(message)

# ==========================================
# 6. MODERASYON VE YÖNETİM SLASH KOMUTLARI
# ==========================================
@bot.tree.command(name="ticket-kur", description="Destek (Ticket) panelini kurar.")
@app_commands.default_permissions(administrator=True)
async def ticket_kur(interaction: discord.Interaction):
    embed = discord.Embed(
        title="❄️ WinterFall Destek Sistemi",
        description="Aşağıdaki menüden açmak istediğiniz destek kategorisini seçin.",
        color=discord.Color.from_rgb(100, 150, 255)
    )
    await interaction.channel.send(embed=embed, view=TicketView())
    await interaction.response.send_message("Ticket paneli başarıyla kuruldu!", ephemeral=True)

@bot.tree.command(name="çekiliş", description="Sunucuda katılımcı sayısı anlık güncellenen WinterFall temalı çekiliş başlatır.")
@app_commands.default_permissions(manage_guild=True)
async def cekilis_komutu(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    embed = discord.Embed(
        title="🎉 WinterFall Çekiliş Vakti!",
        description="Katılmak için aşağıdaki **🎉 Katıl** butonuna tıklayın!",
        color=discord.Color.gold()
    )
    embed.set_footer(text=f"Düzenleyen: {interaction.user.name}")
    
    class CekilisView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=None)
            self.katilanlar = set()

        @discord.ui.button(label="🎉 Katıl (0)", style=discord.ButtonStyle.primary, custom_id="winterfall_cekilis_btn")
        async def katil_btn(self, btn_interaction: discord.Interaction, button: discord.ui.Button):
            if btn_interaction.user.id in self.katilanlar:
                self.katilanlar.remove(btn_interaction.user.id)
                button.label = f"🎉 Katıl ({len(self.katilanlar)})"
                await btn_interaction.response.send_message("❌ Çekilişten ayrıldın!", ephemeral=True)
            else:
                self.katilanlar.add(btn_interaction.user.id)
                button.label = f"🎉 Katıl ({len(self.katilanlar)})"
                await btn_interaction.response.send_message("✅ Çekilişe başarıyla katıldın!", ephemeral=True)
            await btn_interaction.message.edit(view=self)

    await interaction.channel.send(embed=embed, view=CekilisView())
    await interaction.followup.send("✅ Çekiliş paneli gönderildi!", ephemeral=True)

@bot.tree.command(name="sunucu", description="Sunucunun adını ve detaylarını gösteren bilgi kartı atar.")
async def sunucu_komutu(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild
    embed = discord.Embed(
        title=f"🛡️ {guild.name} Sunucu Bilgileri",
        color=discord.Color.blurple()
    )
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.add_field(name="👑 Sunucu Sahibi", value=guild.owner.mention if guild.owner else "Bilinmiyor", inline=True)
    embed.add_field(name="👥 Toplam Üye", value=str(guild.member_count), inline=True)
    embed.add_field(name="📅 Kuruluş Tarihi", value=f"<t:{int(guild.created_at.timestamp())}:D>", inline=False)
    embed.set_footer(text="WinterFall Server Information")
    
    await interaction.channel.send(embed=embed)
    await interaction.followup.send("✅ Sunucu bilgi kartı gönderildi.", ephemeral=True)

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
