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
# SABİTLER VE KANALLAR
# ==========================================
WINTERFALL_ROL = "♱ 𝐖𝐢𝐧𝐭𝐞𝐫𝐟𝐚𝐥𝐥"
EKIP_ROL = "𝙒𝙞𝙣𝙩𝙚𝙧𝙛𝙖𝙡𝙡 𝙀𝙠𝙞𝙥"
TICKET_KATEGORI_ADI = "AÇIK TICKETLAR"

KANALLAR = {
    "girisCıkıs": "「🎈」giriş-çıkış",
    "galeriChat": "「📷」galeri-chat",
    "sohbet": "「💬」sohbet",
    "ekipDuyuru": "「📣」ekip-duyuru",
    "mesajLog": "mesaj-log",
    "rolLog": "rol-log",
    "moderasyonLog": "moderasyon-log",
    "sesLog": "ses-log"
}
YASAKLI_KELIMELER = ["küfür1", "küfür2"]
spamMap = {}

KIS_TEMASI = {
    "adi": "WinterFall Klasik Kış Frost",
    "renk": discord.Color.from_rgb(30, 61, 89),
    "emoji": "❄️",
    "footer": "WinterFall Ecosystem • Frost Edition"
}

# ==========================================
# 4. TİCKET SİSTEMİ
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
            discord.SelectOption(label="Kill Montage", description="Kill Montage gönderimi için.", emoji="📷"),
            discord.SelectOption(label="Ekip Alım", description="Ekibimize katılmak için başvuru yap.", emoji="📥"),
            discord.SelectOption(label="Merge", description="Sunucu birleşim / merge teklifleri için.", emoji="🔗")
        ]
        super().__init__(placeholder="Destek kategorisi seçin...", min_values=1, max_values=1, options=options, custom_id="ticket_select_menu")

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        secilen_kategori = self.values[0]
        guild = interaction.guild
        
        kategori = discord.utils.get(guild.categories, name=TICKET_KATEGORI_ADI)
        if not kategori:
            try:
                kategori = await guild.create_category(TICKET_KATEGORI_ADI)
            except Exception as e:
                logger.error(f"Kategori oluşturulamadı: {e}")

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
        }

        kategori_adi = f"ticket-{secilen_kategori.lower().replace(' ', '-')}-{interaction.user.name}"
        ticket_channel = await guild.create_text_channel(name=kategori_adi, category=kategori, overwrites=overwrites)

        if secilen_kategori == "Partnerlik":
            embed = discord.Embed(
                title="💖 Partnerlik Başvuru Talebi",
                description="Aramıza katılmak için şartları sağlayıp sunucu davetinizi bırakın.",
                color=discord.Color.from_rgb(255, 105, 180)
            )
            await interaction.followup.send(f"**{secilen_kategori}** için destek kanalınız oluşturuldu: {ticket_channel.mention}", ephemeral=True)
            await ticket_channel.send(embed=embed, view=TicketKapatView())
            await ticket_channel.send("Selam! Partnerlik şartlarımız şunlardır:\n1. Sunucunuz aktif olmalı.\n2. Davet linkini buraya bırakabilirsiniz.")
        elif secilen_kategori == "Kill Montage":
            embed = discord.Embed(
                title="📷 Kill Montage Gönderim Talebi",
                description="Montage videolarınızı veya çalışmalarınızı bu kanala iletebilirsiniz.",
                color=discord.Color.from_rgb(0, 200, 255)
            )
            await interaction.followup.send(f"**{secilen_kategori}** için kanalınız oluşturuldu: {ticket_channel.mention}", ephemeral=True)
            await ticket_channel.send(embed=embed, view=TicketKapatView())
            await ticket_channel.send("Lütfen kill montage video veya dosyalarınızı buraya yükleyin.")
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
# 5. BOT EVENTLERİ VE LOG SİSTEMLERİ
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
async def on_message_delete(message):
    if message.author.bot or not message.guild:
        return
    log_kanal = discord.utils.get(message.guild.text_channels, name=KANALLAR["mesajLog"])
    if log_kanal:
        embed = discord.Embed(title="🗑️ Mesaj Silindi", color=discord.Color.red(), timestamp=discord.utils.utcnow())
        embed.add_field(name="Yazan", value=f"{message.author} (`{message.author.id}`)", inline=False)
        embed.add_field(name="Kanal", value=message.channel.mention, inline=False)
        embed.add_field(name="İçerik", value=message.content or "[Medya/Dosya]", inline=False)
        try:
            await log_kanal.send(embed=embed)
        except Exception:
            pass

@bot.event
async def on_message_edit(before, after):
    if before.author.bot or not before.guild or before.content == after.content:
        return
    log_kanal = discord.utils.get(before.guild.text_channels, name=KANALLAR["mesajLog"])
    if log_kanal:
        embed = discord.Embed(title="✏️ Mesaj Düzenlendi", color=discord.Color.orange(), timestamp=discord.utils.utcnow())
        embed.add_field(name="Kullanıcı", value=f"{before.author} (`{before.author.id}`)", inline=False)
        embed.add_field(name="Kanal", value=before.channel.mention, inline=False)
        embed.add_field(name="Önceki", value=before.content or "[Boş]", inline=False)
        embed.add_field(name="Sonraki", value=after.content or "[Boş]", inline=False)
        try:
            await log_kanal.send(embed=embed)
        except Exception:
            pass

@bot.event
async def on_member_update(before, after):
    if before.roles != after.roles:
        log_kanal = discord.utils.get(before.guild.text_channels, name=KANALLAR["rolLog"])
        if log_kanal:
            eklenen = [r.mention for r in after.roles if r not in before.roles]
            cikarilan = [r.mention for r in before.roles if r not in after.roles]
            embed = discord.Embed(title="🏷️ Üye Rol Güncellendi", color=discord.Color.blue(), timestamp=discord.utils.utcnow())
            embed.add_field(name="Kullanıcı", value=f"{after.mention} (`{after.id}`)", inline=False)
            if eklenen:
                embed.add_field(name="Eklenen Roller", value=", ".join(eklenen), inline=False)
            if cikarilan:
                embed.add_field(name="Çıkarılan Roller", value=", ".join(cikarilan), inline=False)
            try:
                await log_kanal.send(embed=embed)
            except Exception:
                pass

@bot.event
async def on_guild_role_create(role):
    log_kanal = discord.utils.get(role.guild.text_channels, name=KANALLAR["rolLog"])
    if log_kanal:
        embed = discord.Embed(title="➕ Yeni Rol Oluşturuldu", color=discord.Color.green(), timestamp=discord.utils.utcnow())
        embed.add_field(name="Rol Adı", value=role.name, inline=False)
        try:
            await log_kanal.send(embed=embed)
        except Exception:
            pass

@bot.event
async def on_guild_role_delete(role):
    log_kanal = discord.utils.get(role.guild.text_channels, name=KANALLAR["rolLog"])
    if log_kanal:
        embed = discord.Embed(title="➖ Rol Silindi", color=discord.Color.red(), timestamp=discord.utils.utcnow())
        embed.add_field(name="Rol Adı", value=role.name, inline=False)
        try:
            await log_kanal.send(embed=embed)
        except Exception:
            pass

@bot.event
async def on_voice_state_update(member, before, after):
    guild = member.guild
    log_kanal = discord.utils.get(guild.text_channels, name=KANALLAR["sesLog"])

    if before.mute != after.mute or before.deaf != after.deaf:
        islem_yapan = "Bilinmiyor / Kendi İşlemi"
        try:
            await asyncio.sleep(0.5)
            async for entry in guild.audit_logs(limit=3, action=discord.AuditLogAction.member_update):
                if entry.target.id == member.id:
                    islem_yapan = f"{entry.user.mention} (`{entry.user.id}`)"
                    break
        except Exception as e:
            logger.error(f"Audit log okuma hatası: {e}")

        if log_kanal:
            embed = discord.Embed(timestamp=discord.utils.utcnow())
            embed.set_author(name=str(member), icon_url=member.display_avatar.url)
            
            if before.mute != after.mute:
                if after.mute:
                    embed.title = "🎙️ Ses Kanalında Susturuldu (Mute)"
                    embed.description = f"**İşlem Gören:** {member.mention} (`{member.id}`)\n**İşlemi Yapan:** {islem_yapan}"
                    embed.color = discord.Color.red()
                else:
                    embed.title = "🎙️ Ses Kanalında Susturması Kaldırıldı"
                    embed.description = f"**İşlem Gören:** {member.mention} (`{member.id}`)\n**İşlemi Yapan:** {islem_yapan}"
                    embed.color = discord.Color.green()
            
            elif before.deaf != after.deaf:
                if after.deaf:
                    embed.title = "🎧 Ses Kanalında Sağırlaştırıldı (Deafen)"
                    embed.description = f"**İşlem Gören:** {member.mention} (`{member.id}`)\n**İşlemi Yapan:** {islem_yapan}"
                    embed.color = discord.Color.red()
                else:
                    embed.title = "🎧 Ses Kanalında Sağırlaştırması Kaldırıldı"
                    embed.description = f"**İşlem Gören:** {member.mention} (`{member.id}`)\n**İşlemi Yapan:** {islem_yapan}"
                    embed.color = discord.Color.green()

            try:
                await log_kanal.send(embed=embed)
            except Exception:
                pass
        return

    if log_kanal:
        embed = discord.Embed(timestamp=discord.utils.utcnow())
        embed.set_author(name=str(member), icon_url=member.display_avatar.url)
        if before.channel is None and after.channel is not None:
            embed.title = "🔊 Ses Kanalına Katıldı"
            embed.description = f"{member.mention}, **{after.channel.name}** kanalına giriş yaptı."
            embed.color = discord.Color.green()
        elif before.channel is not None and after.channel is None:
            embed.title = "🔇 Ses Kanalından Ayrıldı"
            embed.description = f"{member.mention}, **{before.channel.name}** kanalından ayrıldı."
            embed.color = discord.Color.red()
        elif before.channel != after.channel:
            embed.title = "🔀 Ses Kanalı Değiştirdi"
            embed.description = f"{member.mention}, **{before.channel.name}** kanalından **{after.channel.name}** kanalına geçti."
            embed.color = discord.Color.orange()
        else:
            return
        try:
            await log_kanal.send(embed=embed)
        except Exception:
            pass

@bot.event
async def on_member_ban(guild, user):
    log_kanal = discord.utils.get(guild.text_channels, name=KANALLAR["moderasyonLog"])
    if log_kanal:
        embed = discord.Embed(title="🔨 Üye Banlandı", color=discord.Color.red(), timestamp=discord.utils.utcnow())
        embed.add_field(name="Kullanıcı", value=f"{user} (`{user.id}`)", inline=False)
        try:
            await log_kanal.send(embed=embed)
        except Exception:
            pass

@bot.event
async def on_member_unban(guild, user):
    log_kanal = discord.utils.get(guild.text_channels, name=KANALLAR["moderasyonLog"])
    if log_kanal:
        embed = discord.Embed(title="🔓 Üye Banı Kaldırıldı", color=discord.Color.green(), timestamp=discord.utils.utcnow())
        embed.add_field(name="Kullanıcı", value=f"{user} (`{user.id}`)", inline=False)
        try:
            await log_kanal.send(embed=embed)
        except Exception:
            pass

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        await bot.process_commands(message)
        return

    is_winterfall = any(r.name == WINTERFALL_ROL for r in message.author.roles)

    if message.channel.name == KANALLAR["ekipDuyuru"]:
        ekip_rol_obj = discord.utils.get(message.guild.roles, name=EKIP_ROL)
        if is_winterfall and ekip_rol_obj:
            dm_embed = discord.Embed(
                title='❄️ WinterFall Ekip Bildirisi',
                description=f"**Yazan:** {message.author.mention}\n\n[Mesaja Gitmek İçin Tıkla]({message.url})",
                color=discord.Color.from_rgb(0, 180, 216)
            )
            for member in message.guild.members:
                if not member.bot and any(r.name == EKIP_ROL for r in member.roles):
                    try:
                        await member.send(
                            content=f"🔔 Hey **{ekip_rol_obj.name}**! Ekip duyuru kanalına bakman gerekiyor.",
                            embed=dm_embed
                        )
                    except Exception:
                        pass

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

    bot.dispatch("custom_message", message)
    await bot.process_commands(message)

# ==========================================
# 6. KOMUTLAR
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

# Çekiliş katılımcılarını global olarak takip eden sözlük
cekilis_katilimlari = {}

class CekilisKatilView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎉 Katıl (0)", style=discord.ButtonStyle.primary, custom_id="winterfall_cekilis_btn_v12")
    async def katil_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        msg_id = interaction.message.id
        
        if msg_id not in cekilis_katilimlari:
            cekilis_katilimlari[msg_id] = set()

        katilanlar_set = cekilis_katilimlari[msg_id]
        user_id = interaction.user.id

        if user_id in katilanlar_set:
            katilanlar_set.remove(user_id)
            await interaction.response.send_message("❌ Çekilişten başarıyla ayrıldın!", ephemeral=True)
        else:
            katilanlar_set.add(user_id)
            await interaction.response.send_message("✅ Çekilişe başarıyla katıldın!", ephemeral=True)

        button.label = f"🎉 Katıl ({len(katilanlar_set)})"

        if katilanlar_set:
            katilanlar_listesi = ", ".join([f"<@{uid}>" for uid in list(katilanlar_set)[:15]])
            if len(katilanlar_set) > 15:
                katilanlar_listesi += f" ve +{len(katilanlar_set) - 15} kişi daha..."
        else:
            katilanlar_listesi = "Henüz kimse katılmadı."

        eski_embed = interaction.message.embeds[0]
        
        embed_satirlari = eski_embed.description.split("\n")
        yeni_aciklama_parcalari = []
        
        for satir in embed_satirlari:
            if satir.startswith("👥 **Katılanlar"):
                break
            yeni_aciklama_parcalari.append(satir)
            
        yeni_aciklama = "\n".join(yeni_aciklama_parcalari) + f"\n👥 **Katılanlar ({len(katilanlar_set)}):**\n{katilanlar_listesi}"

        yeni_embed = discord.Embed(
            title=eski_embed.title,
            description=yeni_aciklama,
            color=KIS_TEMASI['renk']
        )
        yeni_embed.set_footer(text=eski_embed.footer.text)
        
        await interaction.message.edit(embed=yeni_embed, view=self)

class CekilisOlusturModal(discord.ui.Modal, title="🎁 WinterFall Çekiliş Oluşturucu"):
    odul = discord.ui.TextInput(
        label="Çekiliş Ödülü",
        placeholder="Örn: 1x Discord Nitro / 100K Nakit",
        required=True,
        max_length=100
    )
    kazanan_sayisi = discord.ui.TextInput(
        label="Kazanan Kişi Sayısı",
        placeholder="Örn: 1 (Kaç kişiye çıkacak?)",
        default="1",
        required=True,
        max_length=2
    )
    sure = discord.ui.TextInput(
        label="Süre (dk: d, saat: s, gün: g)",
        placeholder="Örn: 30d (dakika) veya 2g (gün)",
        default="24s",
        required=True,
        max_length=10
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            kazanan_adet = int(self.kazanan_sayisi.value)
        except ValueError:
            await interaction.response.send_message("❌ Kazanan kısmına geçerli bir sayı yazmalısın!", ephemeral=True)
            return

        sure_str = self.sure.value.strip().lower()
        toplam_saniye = 0
        try:
            if sure_str.endswith('d'):
                toplam_saniye = int(sure_str[:-1]) * 60
            elif sure_str.endswith('g'):
                toplam_saniye = int(sure_str[:-1]) * 24 * 3600
            elif sure_str.endswith('s'):
                toplam_saniye = int(sure_str[:-1]) * 3600
            else:
                toplam_saniye = int(sure_str) * 3600
        except ValueError:
            await interaction.response.send_message("❌ Süre formatı hatalı! Örn: `30d`, `24s` veya `2g` kullanın.", ephemeral=True)
            return

        bitis_zamani = discord.utils.utcnow() + timedelta(seconds=toplam_saniye)

        embed = discord.Embed(
            title=f"{KIS_TEMASI['emoji']} WinterFall Ödüllü Çekiliş Vakti!",
            description=(
                f"🎁 **Verilen Ödül:** `{self.odul.value}`\n"
                f"👥 **Kazanan Kişi Sayısı:** `{kazanan_adet}` Asil\n"
                f"👑 **Düzenleyen:** {interaction.user.mention}\n"
                f"⏳ **Bitiş Süresi:** <t:{int(bitis_zamani.timestamp())}:R> (<t:{int(bitis_zamani.timestamp())}:F>)\n\n"
                f"👥 **Katılanlar (0):**\nHenüz kimse katılmadı."
            ),
            color=KIS_TEMASI['renk']
        )
        embed.set_footer(text=f"{KIS_TEMASI['footer']} • Şansınız bol olsun!")

        await interaction.channel.send(embed=embed, view=CekilisKatilView())
        await interaction.response.send_message(f"✅ Çekiliş paneli kuruldu!", ephemeral=True)

@bot.tree.command(name="çekiliş", description="Kış temalı interaktif çekiliş oluşturma panelini açar.")
@app_commands.default_permissions(manage_guild=True)
async def cekilis_komutu(interaction: discord.Interaction):
    await interaction.response.send_modal(CekilisOlusturModal())

@bot.tree.command(name="sil", description="Belirtilen miktarda mesajı siler.")
@app_commands.describe(miktar="Silinecek mesaj sayısı (1 - 100 arası)")
@app_commands.default_permissions(manage_messages=True)
async def sil_komutu(interaction: discord.Interaction, miktar: int):
    await interaction.response.defer(ephemeral=True)
    if miktar < 1 or miktar > 100:
        await interaction.followup.send("❌ Lütfen **1 ile 100** arasında bir sayı belirtin.", ephemeral=True)
        return

    try:
        silinenler = await interaction.channel.purge(limit=miktar)
        await interaction.followup.send(f"🧹 Başarıyla **{len(silinenler)}** adet mesaj silindi.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Hata: {e}", ephemeral=True)

@bot.tree.command(name="sunucu", description="Sunucu istatistiklerini gösterir.")
async def sunucu_komutu(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild
    bot_sayisi = sum(1 for m in guild.members if m.bot)
    uye_sayisi = guild.member_count - bot_sayisi
    
    embed = discord.Embed(
        title=f"🛡️ {guild.name} • İstatistikler",
        color=discord.Color.from_rgb(0, 150, 255)
    )
    embed.add_field(name="👑 Sunucu Sahibi", value=guild.owner.mention if guild.owner else "Bilinmiyor", inline=True)
    embed.add_field(name="👥 Toplam Üye", value=f"Gerçek: **{uye_sayisi}**\nBot: **{bot_sayisi}**", inline=True)
    await interaction.channel.send(embed=embed)
    await interaction.followup.send("✅ Bilgi kartı gönderildi.", ephemeral=True)

@bot.tree.command(name="ai", description="Yapay zeka asistanına soru sorar.")
@app_commands.describe(soru="Sorulacak soru")
async def ai_komutu(interaction: discord.Interaction, soru: str):
    await interaction.response.defer(thinking=True)
    yanit = f"Analiz edildi: '{soru}' konusunu inceliyorum. WinterFall yapay zeka modülü aktif."
    embed = discord.Embed(title="🤖 WinterFall AI", description=yanit, color=discord.Color.blue())
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="ban", description="Kullanıcıyı yasaklar.")
@app_commands.default_permissions(ban_members=True)
async def ban_komutu(interaction: discord.Interaction, member: discord.Member, sebep: str = "Sebep belirtilmedi"):
    await interaction.response.defer(ephemeral=True)
    try:
        await member.ban(reason=sebep)
        await interaction.followup.send(f"✅ {member.name} banlandı.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Hata: {e}", ephemeral=True)

@bot.tree.command(name="kick", description="Kullanıcıyı atar.")
@app_commands.default_permissions(kick_members=True)
async def kick_komutu(interaction: discord.Interaction, member: discord.Member, sebep: str = "Sebep belirtilmedi"):
    await interaction.response.defer(ephemeral=True)
    try:
        await member.kick(reason=sebep)
        await interaction.followup.send(f"👢 {member.name} atıldı.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Hata: {e}", ephemeral=True)

# ==========================================
# 7. ANA ÇALIŞTIRMA
# ==========================================
if __name__ == "__main__":
    logger.info("WinterFall Bot servisleri başlatılıyor...")
    t = threading.Thread(target=run_flask, daemon=True)
    t.start()
    
    TOKEN = os.environ.get("DISCORD_TOKEN")
    if TOKEN:
        bot.run(TOKEN)
    else:
        logger.critical("HATA: DISCORD_TOKEN bulunamadı!")
