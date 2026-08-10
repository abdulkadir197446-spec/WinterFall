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
MANUEL_ROLLER = ["♱ 𝐖𝐢𝐧𝐭𝐞𝐫𝐟𝐚𝐥𝐥", "Winterfall Yönetim", "❄ 𝙁𝙤𝙪𝙣𝙙𝙚𝙧"]
EKIP_ROL = "𝙒𝙞𝙣𝐭𝐞𝙧𝙛𝙖𝙡𝙡 𝙀𝙠𝙞𝙥"
TICKET_KATEGORI_ADI = "❄️ WINTERFALL DESTEK"

KANALLAR = {
    "girisCıkıs": "「🎈」giriş-çıkış",
    "galeriChat": "「📷」galeri-chat",
    "sohbet": "「💬」sohbet",
    "ekipDuyuru": "「📣」ekip-duyuru",
    "mesajLog": "mesaj-log",
    "rolLog": "rol-log",
    "moderasyonLog": "moderasyon-log",
    "sesLog": "ses-log",
    "rankLog": "「📈」rankup-rankdown"
}
YASAKLI_KELIMELER = ["küfür1", "küfür2"]

KIS_TEMASI = {
    "adi": "WinterFall Buzul Frost Tasarımı",
    "renk": discord.Color.from_rgb(15, 76, 129),
    "emoji": "❄️",
    "footer": "❄️ WinterFall Ecosystem • Frost Edition • Tüm Hakları Saklıdır"
}

# ==========================================
# 4. TİCKET SİSTEMİ
# ==========================================
class TicketKapatView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Ticket'ı Kapat", style=discord.ButtonStyle.danger, custom_id="ticket_kapat_btn_frost")
    async def kapat_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("❄️ Ticket kapatılıyor, 5 saniye içinde kanal imha edilecek...", ephemeral=True)
        await asyncio.sleep(5)
        try:
            await interaction.channel.delete()
        except:
            pass

class TicketSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Destek", description="Genel yardıma mı ihtiyacın var? Tıkla.", emoji="🛠️"),
            discord.SelectOption(label="Partnerlik", description="Sunucu ortaklığı ve partnerlik işlemleri.", emoji="💖"),
            discord.SelectOption(label="Şikayet", description="Yetkili şikayeti veya öneri için.", emoji="⚠️"),
            discord.SelectOption(label="Kill Montage", description="Kill montage videolarını buraya ilet.", emoji="📷"),
            discord.SelectOption(label="Ekip Alım", description="WinterFall kadrosuna dahil ol.", emoji="📥")
        ]
        super().__init__(placeholder="❄️ İşlem yapmak istediğin kategoriyi seç...", min_values=1, max_values=1, options=options, custom_id="ticket_select_menu_frost")

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

        kategori_adi = f"❄️│ticket-{secilen_kategori.lower().replace(' ', '-')}-{interaction.user.name}"
        ticket_channel = await guild.create_text_channel(name=kategori_adi, category=kategori, overwrites=overwrites)

        if secilen_kategori == "Partnerlik":
            embed = discord.Embed(
                title="💖 Partnerlik Başvuru Talebi",
                description="Aramıza katılmak için şartları sağlayıp sunucu davetinizi bırakın.",
                color=discord.Color.from_rgb(255, 105, 180)
            )
            embed.set_footer(text=KIS_TEMASI['footer'])
            await interaction.followup.send(f"**{secilen_kategori}** için destek kanalınız oluşturuldu: {ticket_channel.mention}", ephemeral=True)
            await ticket_channel.send(embed=embed, view=TicketKapatView())
            partnerlik_metni = (
                "Selam! Partnerlik şartlarımız şunlardır:\n"
                "1. Sunucunuz aktif olmalı.\n"
                "2. Davet linkini buraya bırakabilirsiniz."
            )
            await ticket_channel.send(partnerlik_metni)
        else:
            embed = discord.Embed(
                title=f"❄️ WinterFall | {secilen_kategori} Talebi",
                description=f"Değerli **{interaction.user.name}**, kış ekibimiz en kısa sürede seninle ilgilenecektir.",
                color=KIS_TEMASI['renk']
            )
            embed.set_footer(text=KIS_TEMASI['footer'])
            await interaction.followup.send(f"❄️ Destek kanalın oluşturuldu: {ticket_channel.mention}", ephemeral=True)
            await ticket_channel.send(embed=embed, view=TicketKapatView())

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())

# ==========================================
# 5. BOT EVENTLERİ VE OTOMATİK SİSTEMLER
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
                title='❄️ YENİ BİR BUZ SAVAŞÇISI KATILDI! ❄️',
                description=f'Sunucumuza hoş geldin **{member.name}**!\nSeninle beraber buz krallığımız **{member.guild.member_count}** kişiye ulaştı!',
                color=KIS_TEMASI['renk']
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text=KIS_TEMASI['footer'], icon_url=member.guild.icon.url if member.guild.icon else None)
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
                title='❄️ BİR SAVAŞÇI FIRTINAYA YENİK DÜŞTÜ ❄️',
                description=f'**{member.name}** aramızdan ayrıldı. Geriye **{member.guild.member_count}** kişi kaldık.',
                color=discord.Color.from_rgb(180, 40, 40)
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text=KIS_TEMASI['footer'], icon_url=member.guild.icon.url if member.guild.icon else None)
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
        embed = discord.Embed(title="❄️🗑️ Buz Krallığı | Mesaj Silindi", color=discord.Color.red(), timestamp=discord.utils.utcnow())
        embed.add_field(name="Yapan / Sayan", value=f"{message.author} (`{message.author.id}`)", inline=False)
        embed.add_field(name="Kanal", value=message.channel.mention, inline=False)
        embed.add_field(name="İçerik", value=message.content or "[Medya/Dosya]", inline=False)
        embed.set_footer(text=KIS_TEMASI['footer'])
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
        embed = discord.Embed(title="❄️✏️ Buz Krallığı | Mesaj Düzenlendi", color=discord.Color.orange(), timestamp=discord.utils.utcnow())
        embed.add_field(name="Yapan / Kullanıcı", value=f"{before.author} (`{before.author.id}`)", inline=False)
        embed.add_field(name="Kanal", value=before.channel.mention, inline=False)
        embed.add_field(name="Eski Hali", value=before.content or "[Boş]", inline=False)
        embed.add_field(name="Yeni Hali", value=after.content or "[Boş]", inline=False)
        embed.set_footer(text=KIS_TEMASI['footer'])
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
            embed = discord.Embed(title="❄️🏷️ Rol Güncellendi", color=KIS_TEMASI['renk'], timestamp=discord.utils.utcnow())
            embed.add_field(name="Yapılan (Kullanıcı)", value=f"{after.mention} (`{after.id}`)", inline=False)
            if eklenen:
                embed.add_field(name="Eklenen Roller", value=", ".join(eklenen), inline=False)
            if cikarilan:
                embed.add_field(name="Alınan Roller", value=", ".join(cikarilan), inline=False)
            embed.set_footer(text=KIS_TEMASI['footer'])
            try:
                await log_kanal.send(embed=embed)
            except Exception:
                pass

@bot.event
async def on_voice_state_update(member, before, after):
    guild = member.guild
    log_kanal = discord.utils.get(guild.text_channels, name=KANALLAR["sesLog"])
    if not log_kanal:
        return

    embed = discord.Embed(color=KIS_TEMASI['renk'], timestamp=discord.utils.utcnow())
    embed.set_author(name=str(member), icon_url=member.display_avatar.url)
    
    yapan = "Bilinmiyor / Kendi İşlemi"
    
    try:
        if before.channel == after.channel:
            if before.mute != after.mute or before.deaf != after.deaf:
                async for entry in guild.audit_logs(limit=3, action=discord.AuditLogAction.member_update):
                    if entry.target.id == member.id:
                        yapan = f"{entry.user.mention} (`{entry.user.id}`)"
                        break
                
                if before.mute != after.mute:
                    durum = "susturuldu" if after.mute else "susturması kaldırıldı"
                    embed.title = "❄️🎙️ Sunucu Ses Durumu Değişti"
                    embed.description = f"**Yapan:** {yapan}\n**Yapılan:** {member.mention} kullanıcısı {durum}."
                elif before.deaf != after.deaf:
                    durum = "sağırlaştırıldı" if after.deaf else "sağırlaştırılması kaldırıldı"
                    embed.title = "❄️🎧 Sunucu Kulaklık Durumu Değişti"
                    embed.description = f"**Yapan:** {yapan}\n**Yapılan:** {member.mention} kullanıcısı {durum}."
            
            elif before.channel is not None and after.channel is None:
                async for entry in guild.audit_logs(limit=3, action=discord.AuditLogAction.member_move):
                    if entry.target.id == member.id:
                        yapan = f"{entry.user.mention} (`{entry.user.id}`)"
                        break
                embed.title = "❄️👢 Ses Kanalından Atıldı / Ayrıldı"
                embed.description = f"**Yapan:** {yapan}\n**Yapılan:** {member.mention} kullanıcısı **{before.channel.name}** kanalından uzaklaştırıldı/çıktı."
            else:
                return
        else:
            if before.channel is None and after.channel is not None:
                embed.title = "❄️🔊 Ses Kanalına Giriş Yapıldı"
                embed.description = f"**Yapan / Yapılan:** {member.mention}\n**Kanal:** **{after.channel.name}**"
            elif before.channel is not None and after.channel is None:
                embed.title = "❄️🔇 Ses Kanalından Çıkıldı"
                embed.description = f"**Yapan / Yapılan:** {member.mention}\n**Kanal:** **{before.channel.name}**"
            elif before.channel is not None and after.channel is not None:
                async for entry in guild.audit_logs(limit=3, action=discord.AuditLogAction.member_move):
                    if entry.target.id == member.id:
                        yapan = f"{entry.user.mention} (`{entry.user.id}`)"
                        break
                embed.title = "❄️🔀 Ses Kanalı Değiştirildi / Taşındı"
                embed.description = f"**Yapan:** {yapan}\n**Yapılan:** {member.mention} taşındı.\n**Eski Kanal:** **{before.channel.name}** ➡️ **Yeni Kanal:** **{after.channel.name}**"
            else:
                return

        embed.set_footer(text=KIS_TEMASI['footer'])
        await log_kanal.send(embed=embed)
    except Exception as e:
        logger.error(f"Ses log hatası: {e}")

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        await bot.process_commands(message)
        return

    mesaj_icerigi = message.content.lower()
    if any(kufur in mesaj_icerigi for kufur in YASAKLI_KELIMELER):
        try:
            await message.delete()
            await message.channel.send(f"❄️ {message.author.mention}, küfür ettiğin için otomatik **rankdown** uygulandı!", delete_after=5)
            
            rank_log_kanal = discord.utils.get(message.guild.text_channels, name=KANALLAR["rankLog"])
            if rank_log_kanal:
                log_embed = discord.Embed(
                    title="❄️📉 Otomatik Rankdown (Ceza) Uygulandı",
                    description=f"**Kullanıcı:** {message.author.mention} (`{message.author.id}`)\n**Sebep:** Küfür / Yasaklı Kelime Kullanımı\n**Kanal:** {message.channel.mention}",
                    color=discord.Color.red(),
                    timestamp=discord.utils.utcnow()
                )
                log_embed.set_footer(text=KIS_TEMASI['footer'])
                await rank_log_kanal.send(embed=log_embed)
        except Exception as e:
            logger.error(f"Küfür engelleme ve log hatası: {e}")

    is_winterfall = any(r.name == "♱ 𝐖𝐢𝐧𝐭𝐞𝐫𝐟𝐚𝐥𝐥" for r in message.author.roles)

    if message.channel.name == KANALLAR["ekipDuyuru"]:
        ekip_rol_obj = discord.utils.get(message.guild.roles, name=EKIP_ROL)
        if is_winterfall and ekip_rol_obj:
            dm_embed = discord.Embed(
                title='❄️ WINTERFALL EKİP BİLDİRİSİ',
                description=f"**Yayan Savaşçı:** {message.author.mention}\n\n[Mesaja Gitmek İçin Tıkla]({message.url})",
                color=KIS_TEMASI['renk']
            )
            dm_embed.set_footer(text=KIS_TEMASI['footer'])
            for member in message.guild.members:
                if not member.bot and any(r.name == EKIP_ROL for r in member.roles):
                    try:
                        await member.send(content=f"❄️ Hey **{ekip_rol_obj.name}**! Duyuru kanalına göz at.", embed=dm_embed)
                    except Exception:
                        pass

    if not is_winterfall:
        if message.channel.name == KANALLAR["galeriChat"] and len(message.attachments) == 0:
            await message.delete()
            try:
                await message.author.send("❄️ Bu kanala yalnızca görsel veya medya dosyaları atabilirsin!")
            except:
                pass
            return

    bot.dispatch("custom_message", message)
    await bot.process_commands(message)

# ==========================================
# 6. KOMUTLAR (RANKUP, RANKDOWN, TICKET & DİĞERLERİ)
# ==========================================
@bot.tree.command(name="rankup", description="Bir kullanıcıya manuel rankup verir ve rank-log kanalına kaydeder.")
@app_commands.describe(member="Rankup verilecek kullanıcı", rol="Verilecek yeni rol")
@app_commands.default_permissions(manage_roles=True)
async def rankup_komutu(interaction: discord.Interaction, member: discord.Member, rol: discord.Role):
    # Sadece KANALLAR["rankLog"] isimli kanalda kullanılmasına izin verilir
    if interaction.channel.name != KANALLAR["rankLog"]:
        await interaction.response.send_message(f"❌ Bu komut yalnızca <#{discord.utils.get(interaction.guild.text_channels, name=KANALLAR['rankLog']).id if discord.utils.get(interaction.guild.text_channels, name=KANALLAR['rankLog']) else 0}> kanalında kullanılabilir!", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    try:
        await member.add_roles(rol)
        await interaction.followup.send(f"❄️ {member.mention} adlı kullanıcıya başarıyla **{rol.name}** verildi (Rankup).", ephemeral=True)
        
        rank_log_kanal = discord.utils.get(interaction.guild.text_channels, name=KANALLAR["rankLog"])
        if rank_log_kanal:
            log_embed = discord.Embed(
                title="❄️📈 Manuel Rankup Gerçekleşti",
                description=f"**Kullanıcı:** {member.mention} (`{member.id}`)\n**Verilen Rol:** **{rol.name}**\n**Yetkili:** {interaction.user.mention}",
                color=KIS_TEMASI['renk'],
                timestamp=discord.utils.utcnow()
            )
            log_embed.set_footer(text=KIS_TEMASI['footer'])
            await rank_log_kanal.send(embed=log_embed)
    except Exception as e:
        await interaction.followup.send(f"❌ Rol verilirken hata oluştu: {e}", ephemeral=True)

@bot.tree.command(name="rankdown", description="Bir kullanıcının rankını düşürür ve rank-log kanalına kaydeder.")
@app_commands.describe(member="Rankdown uygulanacak kullanıcı", rol="Alınacak rol")
@app_commands.default_permissions(manage_roles=True)
async def rankdown_komutu(interaction: discord.Interaction, member: discord.Member, rol: discord.Role):
    # Sadece KANALLAR["rankLog"] isimli kanalda kullanılmasına izin verilir
    if interaction.channel.name != KANALLAR["rankLog"]:
        await interaction.response.send_message(f"❌ Bu komut yalnızca <#{discord.utils.get(interaction.guild.text_channels, name=KANALLAR['rankLog']).id if discord.utils.get(interaction.guild.text_channels, name=KANALLAR['rankLog']) else 0}> kanalında kullanılabilir!", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    try:
        await member.remove_roles(rol)
        await interaction.followup.send(f"❄️ {member.mention} adlı kullanıcıdan **{rol.name}** alındı (Rankdown).", ephemeral=True)
        
        rank_log_kanal = discord.utils.get(interaction.guild.text_channels, name=KANALLAR["rankLog"])
        if rank_log_kanal:
            log_embed = discord.Embed(
                title="❄️📉 Manuel Rankdown Gerçekleşti",
                description=f"**Kullanıcı:** {member.mention} (`{member.id}`)\n**Alınan Rol:** **{rol.name}**\n**Yetkili:** {interaction.user.mention}",
                color=discord.Color.red(),
                timestamp=discord.utils.utcnow()
            )
            log_embed.set_footer(text=KIS_TEMASI['footer'])
            await rank_log_kanal.send(embed=log_embed)
    except Exception as e:
        await interaction.followup.send(f"❌ Rol alınırken hata oluştu: {e}", ephemeral=True)

@bot.tree.command(name="ticket-kur", description="WinterFall tarzı destek panelini kurar.")
@app_commands.default_permissions(administrator=True)
async def ticket_kur(interaction: discord.Interaction):
    embed = discord.Embed(
        title="❄️ WINTERFALL DESTEK MERKEZİ",
        description="Aşağıdaki buzdan menüyü kullanarak ihtiyacına uygun destek talebini oluşturabilirsin.",
        color=KIS_TEMASI['renk']
    )
    embed.set_footer(text=KIS_TEMASI['footer'])
    await interaction.channel.send(embed=embed, view=TicketView())
    await interaction.response.send_message("❄️ Destek paneli başarıyla yerleştirildi!", ephemeral=True)

cekilis_katilimlari = {}

class CekilisKatilView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎉 Katıl (0)", style=discord.ButtonStyle.primary, custom_id="winterfall_cekilis_frost_v3")
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
            if satir.startswith("### 👥 Katılanlar") or satir.startswith("👥 **Katılanlar"):
                break
            yeni_aciklama_parcalari.append(satir)
            
        yeni_aciklama = "\n".join(yeni_aciklama_parcalari) + f"\n\n### 👥 Katılanlar ({len(katilanlar_set)}):\n{katilanlar_listesi}"
        yeni_embed = discord.Embed(title=eski_embed.title, description=yeni_aciklama, color=KIS_TEMASI['renk'])
        yeni_embed.set_footer(text=eski_embed.footer.text)
        await interaction.message.edit(embed=yeni_embed, view=self)

class CekilisOlusturModal(discord.ui.Modal, title="❄️ WinterFall Ödüllü Çekiliş"):
    odul = discord.ui.TextInput(label="Çekiliş Ödülü", placeholder="Örn: 1x Discord Nitro", required=True, max_length=100)
    aciklama = discord.ui.TextInput(label="Açıklama / Kurallar", placeholder="Örn: Sunucumuzda aktif kalmak zorunludur.", style=discord.TextStyle.paragraph, required=False, max_length=300)
    kazanan_sayisi = discord.ui.TextInput(label="Kazanan Sayısı", placeholder="1", default="1", required=True, max_length=2)
    sure = discord.ui.TextInput(label="Süre (örn: 30d, 24s, 2g)", placeholder="24s", default="24s", required=True, max_length=10)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            kazanan_adet = int(self.kazanan_sayisi.value)
        except ValueError:
            await interaction.response.send_message("❌ Geçerli bir kazanan sayısı girin!", ephemeral=True)
            return

        sure_str = self.sure.value.strip().lower()
        toplam_saniye = 3600
        try:
            if sure_str.endswith('d'):
                toplam_saniye = int(sure_str[:-1]) * 60
            elif sure_str.endswith('g'):
                toplam_saniye = int(sure_str[:-1]) * 24 * 3600
            elif sure_str.endswith('s'):
                toplam_saniye = int(sure_str[:-1]) * 3600
        except ValueError:
            toplam_saniye = 86400

        bitis_zamani = discord.utils.utcnow() + timedelta(seconds=toplam_saniye)
        aciklama_metni = f"📝 **Açıklama:** {self.aciklama.value}\n" if self.aciklama.value else ""

        embed = discord.Embed(
            title=f"❄️ WINTERFALL ÖDÜLLÜ ÇEKİLİŞ",
            description=(
                f"### 🎁 Ödül: `{self.odul.value}`\n"
                f"{aciklama_metni}"
                f"### 👑 Kazanan: `{kazanan_adet}` Kişi\n"
                f"**Düzenleyen:** {interaction.user.mention}\n"
                f"**Bitiş:** <t:{int(bitis_zamani.timestamp())}:R> (<t:{int(bitis_zamani.timestamp())}:F>)\n\n"
                f"### 👥 Katılanlar (0):\nHenüz kimse katılmadı."
            ),
            color=KIS_TEMASI['renk']
        )
        embed.set_footer(text=KIS_TEMASI['footer'])
        await interaction.channel.send(embed=embed, view=CekilisKatilView())
        await interaction.response.send_message("❄️ Çekiliş başarıyla fırtınaya salındı!", ephemeral=True)

@bot.tree.command(name="çekiliş", description="Buz temalı çekiliş paneli açar.")
@app_commands.default_permissions(manage_guild=True)
async def cekilis_komutu(interaction: discord.Interaction):
    await interaction.response.send_modal(CekilisOlusturModal())

@bot.tree.command(name="zamanaşımı", description="Bir kullanıcıya belirttiğiniz süre kadar zamanaşımı (timeout) atar.")
@app_commands.describe(member="Zamanaşımı uygulanacak savaşçı", sure="Süre (Örn: 1g, 2s, 30dk)", sebep="Zamanaşımı sebebi")
@app_commands.default_permissions(moderate_members=True)
async def zamanaşımı_komutu(interaction: discord.Interaction, member: discord.Member, sure: str, sebep: str = "Sebep belirtilmedi"):
    await interaction.response.defer(ephemeral=True)
    sure_str = sure.strip().lower()
    toplam_saniye = 0
    try:
        if sure_str.endswith('dk'):
            toplam_saniye = int(sure_str[:-2]) * 60
        elif sure_str.endswith('s'):
            toplam_saniye = int(sure_str[:-1]) * 3600
        elif sure_str.endswith('g'):
            toplam_saniye = int(sure_str[:-1]) * 24 * 3600
        else:
            toplam_saniye = int(sure_str) * 60
    except ValueError:
        await interaction.followup.send("❌ Geçersiz süre formatı! Örn: `1g`, `2s`, `30dk`", ephemeral=True)
        return

    delta = timedelta(seconds=toplam_saniye)
    try:
        await member.timeout(delta, reason=sebep)
        await interaction.followup.send(f"❄️ {member.mention} kullanıcısına **{sure}** süreyle zamanaşımı uygulandı.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Zamanaşımı uygulanamadı: {e}", ephemeral=True)

@bot.tree.command(name="sesat", description="Bir kullanıcıyı bulunduğu ses kanalından atar.")
@app_commands.describe(member="Sesten atılacak kullanıcı")
@app_commands.default_permissions(move_members=True)
async def sesat_komutu(interaction: discord.Interaction, member: discord.Member):
    await interaction.response.defer(ephemeral=True)
    if not member.voice or not member.voice.channel:
        await interaction.followup.send("❌ Bu kullanıcı herhangi bir ses kanalında değil!", ephemeral=True)
        return
    try:
        await member.move_to(None)
        await interaction.followup.send(f"❄️ {member.mention} başarıyla ses kanalından dışarı atıldı.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Hata oluştu: {e}", ephemeral=True)

@bot.tree.command(name="kilitle", description="Bulunduğunuz metin kanalını mesaj gönderimine kilitler/açar.")
@app_commands.default_permissions(manage_channels=True)
async def kilitle_komutu(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    channel = interaction.channel
    overwrite = channel.overwrites_for(interaction.guild.default_role)
    
    if overwrite.send_messages is False:
        overwrite.send_messages = None
        durum = "açıldı"
    else:
        overwrite.send_messages = False
        durum = "kilitlendi"

    try:
        await channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
        await interaction.followup.send(f"❄️ Bu kanal mesaj gönderimine karşı başarıyla **{durum}**.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Kanal kilitlenirken hata oluştu: {e}", ephemeral=True)

@bot.tree.command(name="ireset", description="Sunucudaki tüm davet verilerini sıfırlar.")
@app_commands.default_permissions(administrator=True)
async def ireset_komutu(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    conn = get_database_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM invites")
            conn.commit()
            conn.close()
            await interaction.followup.send("❄️ Veritabanındaki tüm davet istatistikleri başarıyla sıfırlandı!", ephemeral=True)
        except Exception as e:
            conn.close()
            await interaction.followup.send(f"❌ Sıfırlama hatası: {e}", ephemeral=True)
    else:
        await interaction.followup.send("❌ Veritabanı bağlantısı kurulamadı!", ephemeral=True)

@bot.tree.command(name="invite", description="Sunucuya kaç kişi çektiğinizi ve sahte davet sayılarınızı gösterir.")
@app_commands.describe(member="İstatistiklerine bakılacak kullanıcı")
async def invite_komutu(interaction: discord.Interaction, member: discord.Member = None):
    await interaction.response.defer(ephemeral=True)
    target = member or interaction.user
    conn = get_database_connection()
    inv_count, fake_count, leave_count = 0, 0, 0
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT invites_count, fake_count, leave_count FROM invites WHERE user_id = ?", (target.id,))
        row = cursor.fetchone()
        if row:
            inv_count, fake_count, leave_count = row
        conn.close()

    embed = discord.Embed(title=f"❄️ Davet Raporu • {target.name}", color=KIS_TEMASI['renk'])
    embed.set_thumbnail(url=target.display_avatar.url)
    embed.add_field(name="📥 Gerçek Davet", value=f"**{inv_count}** kişi", inline=True)
    embed.add_field(name="⚠️ Sahte Davet", value=f"**{fake_count}** kişi", inline=True)
    embed.add_field(name="📤 Ayrılan", value=f"**{leave_count}** kişi", inline=True)
    embed.set_footer(text=KIS_TEMASI['footer'])
    await interaction.followup.send(embed=embed, ephemeral=True)

@bot.tree.command(name="sunucu", description="Sunucunun gelişmiş detaylı buzul istatistiklerini gösterir.")
async def sunucu_komutu(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild
    bot_sayisi = sum(1 for m in guild.members if m.bot)
    uye_sayisi = guild.member_count - bot_sayisi
    text_kanallari = len(guild.text_channels)
    ses_kanallari = len(guild.voice_channels)
    kategoriler = len(guild.categories)
    roller = len(guild.roles)
    boost_sayisi = guild.premium_subscription_count
    boost_seviyesi = guild.premium_tier

    embed = discord.Embed(title=f"❄️ {guild.name} • Gelişmiş Buzul İstatistikleri", color=KIS_TEMASI['renk'])
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.add_field(name="👑 Krallık Lideri", value=guild.owner.mention if guild.owner else "Bilinmiyor", inline=False)
    embed.add_field(name="👥 Savaşçı Dağılımı", value=f"Gerçek Üye: **{uye_sayisi}**\nBot Sayısı: **{bot_sayisi}**\nToplam: **{guild.member_count}**", inline=True)
    embed.add_field(name="📁 Kanal Bilgileri", value=f"Metin: **{text_kanallari}**\nSes: **{ses_kanallari}**\nKategori: **{kategoriler}**", inline=True)
    embed.add_field(name="🚀 Takviye (Boost)", value=f"Seviye: **{boost_seviyesi}**\nToplam Takviye: **{boost_sayisi}**", inline=True)
    embed.add_field(name="🛡️ Rol Sayısı", value=f"**{roller}** adet rol", inline=True)
    embed.set_footer(text=KIS_TEMASI['footer'])
    await interaction.channel.send(embed=embed)
    await interaction.followup.send("❄️ Detaylı sunucu kartı kanala gönderildi.", ephemeral=True)

@bot.tree.command(name="ai", description="WinterFall yapay zeka asistanı.")
@app_commands.describe(soru="Yapay zekaya sorulacak soru")
async def ai_komutu(interaction: discord.Interaction, soru: str):
    await interaction.response.defer(thinking=True)
    embed = discord.Embed(
        title="❄️ WinterFall AI Asistanı",
        description=f"**Soru:** {soru}\n\n🤖 *Buzul ağları üzerinden analiz edildi: Sistemler stabil ve aktif.*",
        color=KIS_TEMASI['renk']
    )
    embed.set_footer(text=KIS_TEMASI['footer'])
    await interaction.followup.send(embed=embed)

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
        await interaction.followup.send(f"❄️ Başarıyla **{len(silinenler)}** adet mesaj buz edildi (silindi).", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Hata: {e}", ephemeral=True)

@bot.tree.command(name="ban", description="Kullanıcıyı yasaklar.")
@app_commands.default_permissions(ban_members=True)
async def ban_komutu(interaction: discord.Interaction, member: discord.Member, sebep: str = "Sebep belirtilmedi"):
    await interaction.response.defer(ephemeral=True)
    try:
        await member.ban(reason=sebep)
        await interaction.followup.send(f"❄️ {member.name} krallıktan kalıcı olarak banlandı.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Hata: {e}", ephemeral=True)

@bot.tree.command(name="kick", description="Kullanıcıyı atar.")
@app_commands.default_permissions(kick_members=True)
async def kick_komutu(interaction: discord.Interaction, member: discord.Member, sebep: str = "Sebep belirtilmedi"):
    await interaction.response.defer(ephemeral=True)
    try:
        await member.kick(reason=sebep)
        await interaction.followup.send(f"❄️ {member.name} sunucudan dışarı atıldı.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Hata: {e}", ephemeral=True)

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
        logger.critical("HATA: DISCORD_TOKEN bulunamadı!")
