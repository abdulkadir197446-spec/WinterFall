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
logger = logging.getLogger("VlandiaBot")

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
    return "Vlandia Pro Bot Aktif ve Çalışır Durumda!", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# ==========================================
# 3. VERİTABANI YÖNETİMİ
# ==========================================
def get_database_connection():
    try:
        connection = sqlite3.connect('vlandia_pro.db')
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
                    user_id INTEGER,
                    guild_id INTEGER,
                    text_content TEXT,
                    PRIMARY KEY (user_id, guild_id, text_content)
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS partner_counts (
                    user_id INTEGER PRIMARY KEY,
                    real_partner INTEGER DEFAULT 0,
                    fake_partner INTEGER DEFAULT 0
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS giveaways (
                    message_id INTEGER PRIMARY KEY,
                    prize TEXT,
                    winners_count INTEGER,
                    end_time REAL,
                    host_id INTEGER,
                    participants TEXT,
                    ended INTEGER DEFAULT 0
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
# SABİTLER VE KANALLAR (Ateş ve Kırmızı Tema)
# ==========================================
MANUEL_ROLLER = ["♱ 𝐕𝐥𝐚𝐧𝐝𝐢𝐚", "Vlandia Yönetim", "🦁 𝙁𝙤𝙪𝙣𝙙𝙚𝙧"]
EKIP_ROL = "𝙑𝙡𝙖𝙣𝙙𝙞𝙖 𝙀𝙠𝙞𝙥"
TICKET_KATEGORI_ADI = "🔥 VLANDİA DESTEK"

# Sırasıyla alt rütbeden üst rütbeye doğru sıralanmış rank rolleri listesi
RANK_HIYERARSISI = [
    "🦁Denetleyici",
    "🦁Asistan",
    "🦁Asistan +",
    "🦁Moderatör",
    "🦁Moderatör +",
    "🦁Sorumlu",
    "🦁Baş Sorumlu"
]

KANALLAR = {
    "girisCıkıs": "「🎈」giriş-çıkış",
    "galeriChat": "「📷」galeri-chat",
    "sohbet": "「💬」sohbet",
    "ekipDuyuru": "「📣」ekip-duyuru",
    "mesajLog": "mesaj-log",
    "rolLog": "rol-log",
    "moderasyonLog": "moderasyon-log",
    "sesLog": "ses-log",
    "rankLog": "「📈」rankup-rankdown",
    "botKomut": "「💻」bot-komut",
    "partner": "「🤝」partner",
    "partnerSayac": "「⏳」partnerlik-sayaç",
    "cekilis": "「🎉」çekiliş"
}
YASAKLI_KELIMELER = ["küfür1", "küfür2"]

# Ateş ve Kırmızı Vlandia Teması
VLANDIA_TEMASI = {
    "adi": "Vlandia Ateş ve Kırmızı Tasarımı",
    "renk": discord.Color.from_rgb(220, 20, 60), # Ateş Kırmızısı / Crimson
    "emoji": "🔥",
    "footer": "🔥 Vlandia Empire • Fire Edition • Tüm Hakları Saklıdır"
}

# ==========================================
# 4. TİCKET SİSTEMİ
# ==========================================
class TicketKapatView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Ticket'ı Kapat", style=discord.ButtonStyle.danger, custom_id="ticket_kapat_btn_vlandia")
    async def kapat_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔥 Ticket kapatılıyor, 5 saniye içinde kanal imha edilecek...", ephemeral=True)
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
            discord.SelectOption(label="Ekip Alım", description="Vlandia kadrosuna dahil ol.", emoji="📥")
        ]
        super().__init__(placeholder="🔥 İşlem yapmak istediğin kategoriyi seç...", min_values=1, max_values=1, options=options, custom_id="ticket_select_menu_vlandia")

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

        kategori_adi = f"🔥│ticket-{secilen_kategori.lower().replace(' ', '-')}-{interaction.user.name}"
        ticket_channel = await guild.create_text_channel(name=kategori_adi, category=kategori, overwrites=overwrites)

        if secilen_kategori == "Partnerlik":
            embed = discord.Embed(
                title="💖 Partnerlik Başvuru Talebi",
                description="Aramıza katılmak için şartları sağlayıp sunucu davetinizi bırakın.",
                color=discord.Color.from_rgb(255, 69, 0)
            )
            embed.set_footer(text=VLANDIA_TEMASI['footer'])
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
                title=f"🔥 Vlandia | {secilen_kategori} Talebi",
                description=f"Değerli **{interaction.user.name}**, imparatorluk ekibimiz en kısa sürede seninle ilgilenecektir.",
                color=VLANDIA_TEMASI['renk']
            )
            embed.set_footer(text=VLANDIA_TEMASI['footer'])
            await interaction.followup.send(f"🔥 Destek kanalın oluşturuldu: {ticket_channel.mention}", ephemeral=True)
            await ticket_channel.send(embed=embed, view=TicketKapatView())

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())

# ==========================================
# 4.1 ÇEKİLİŞ SİSTEMİ VIEW & MODAL
# ==========================================
class GiveawayView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎉 Katıl (0)", style=discord.ButtonStyle.danger, custom_id="giveaway_katil_btn")
    async def katil_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        conn = get_database_connection()
        if not conn:
            await interaction.response.send_message("❌ Veritabanı bağlantı hatası!", ephemeral=True)
            return

        cursor = conn.cursor()
        cursor.execute("SELECT participants, ended FROM giveaways WHERE message_id = ?", (interaction.message.id,))
        row = cursor.fetchone()

        if not row:
            conn.close()
            await interaction.response.send_message("❌ Bu çekiliş veritabanında bulunamadı!", ephemeral=True)
            return

        participants_str, ended = row
        if ended == 1:
            conn.close()
            await interaction.response.send_message("❌ Bu çekiliş sona ermiştir!", ephemeral=True)
            return

        participants = participants_str.split(",") if participants_str else []
        user_id_str = str(interaction.user.id)

        if user_id_str in participants:
            participants.remove(user_id_str)
            msg = "🔥 Çekilişten başarıyla çıkış yaptın!"
        else:
            participants.append(user_id_str)
            msg = "🔥 Çekilişe başarıyla katıldın!"

        new_participants_str = ",".join(participants)
        cursor.execute("UPDATE giveaways SET participants = ? WHERE message_id = ?", (new_participants_str, interaction.message.id))
        conn.commit()
        conn.close()

        button.label = f"🎉 Katıl ({len(participants)})"
        try:
            await interaction.response.edit_message(view=self)
        except Exception:
            pass

        await interaction.followup.send(msg, ephemeral=True)

class GiveawayModal(discord.ui.Modal, title="🔥 Vlandia Çekiliş Paneli"):
    odul_input = discord.ui.TextInput(label="Ödül", placeholder="Örn: 1000 Robux / Nitro / VIP", required=True)
    kazanan_input = discord.ui.TextInput(label="Kaç Kişi Kazanacak?", placeholder="Örn: 1", required=True)
    sure_input = discord.ui.TextInput(label="Ne Zaman (Süre)?", placeholder="Örn: 1g, 2s, 30dk", required=True)
    aciklama_input = discord.ui.TextInput(label="Açıklama", placeholder="Çekiliş kuralları veya detaylar...", style=discord.TextStyle.paragraph, required=False)

    async def on_submit(self, interaction: discord.Interaction):
        odul = self.odul_input.value
        try:
            kazanan_sayisi = int(self.kazanan_input.value)
        except ValueError:
            await interaction.response.send_message("❌ Kazanan kişi sayısı bir sayı olmalıdır!", ephemeral=True)
            return

        sure_str = self.sure_input.value.strip().lower()
        aciklama = self.aciklama_input.value or "Ek açıklama belirtilmedi."

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
            await interaction.response.send_message("❌ Geçersiz süre formatı! Örn: 1g, 2s, 30dk", ephemeral=True)
            return

        end_timestamp = discord.utils.utcnow().timestamp() + toplam_saniye
        embed = discord.Embed(
            title=f"🔥 ÇEKİLİŞ: {odul}",
            description=f"**Açıklama:** {aciklama}\n\nAşağıdaki butona basarak alevler arasındaki çekilişe katılabilirsin!\n\n👑 **Kazanan Kişi Sayısı:** `{kazanan_sayisi}`\n⏳ **Bitiş:** <t:{int(end_timestamp)}:R> (<t:{int(end_timestamp)}:F>)\n👤 **Düzenleyen:** {interaction.user.mention}",
            color=VLANDIA_TEMASI['renk'],
            timestamp=discord.utils.utcnow()
        )
        embed.set_footer(text=VLANDIA_TEMASI['footer'])

        kanal = discord.utils.get(interaction.guild.text_channels, name=KANALLAR["cekilis"]) or interaction.channel
        view = GiveawayView()
        msg = await kanal.send(embed=embed, view=view)

        conn = get_database_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO giveaways (message_id, prize, winners_count, end_time, host_id, participants, ended) VALUES (?, ?, ?, ?, ?, ?, 0)",
                           (msg.id, odul, kazanan_sayisi, end_timestamp, interaction.user.id, ""))
            conn.commit()
            conn.close()

        await interaction.response.send_message(f"🔥 Çekiliş paneli başarıyla {kanal.mention} kanalında açıldı!", ephemeral=True)

# ==========================================
# 5. BOT EVENTLERİ VE OTOMATİK SİSTEMLER
# ==========================================
@bot.event
async def on_ready():
    logger.info(f'{bot.user.name} başarıyla giriş yaptı!')
    bot.add_view(TicketView())
    bot.add_view(GiveawayView())
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
                title='🔥 BİR SAVAŞÇI ALEVLERİN ARASINDAN KATILDI! 🔥',
                description=f'Vlandia sancağı altına hoş geldin **{member.name}**!\nSeninle beraber imparatorluğumuz **{member.guild.member_count}** kişiye ulaştı!',
                color=VLANDIA_TEMASI['renk']
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text=VLANDIA_TEMASI['footer'], icon_url=member.guild.icon.url if member.guild.icon else None)
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
                title='🔥 BİR SAVAŞÇI FIRTINAYA YENİK DÜŞTÜ 🔥',
                description=f'**{member.name}** aramızdan ayrıldı. Geriye **{member.guild.member_count}** kişi kaldık.',
                color=discord.Color.from_rgb(139, 0, 0)
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text=VLANDIA_TEMASI['footer'], icon_url=member.guild.icon.url if member.guild.icon else None)
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
        embed = discord.Embed(title="🔥🗑️ Vlandia İmparatorluğu | Mesaj Silindi", color=discord.Color.red(), timestamp=discord.utils.utcnow())
        embed.add_field(name="Yapan / Sayan", value=f"{message.author} (`{message.author.id}`)", inline=False)
        embed.add_field(name="Kanal", value=message.channel.mention, inline=False)
        embed.add_field(name="İçerik", value=message.content or "[Medya/Dosya]", inline=False)
        embed.set_footer(text=VLANDIA_TEMASI['footer'])
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
        embed = discord.Embed(title="🔥✏️ Vlandia İmparatorluğu | Mesaj Düzenlendi", color=discord.Color.orange(), timestamp=discord.utils.utcnow())
        embed.add_field(name="Yapan / Kullanıcı", value=f"{before.author} (`{before.author.id}`)", inline=False)
        embed.add_field(name="Kanal", value=before.channel.mention, inline=False)
        embed.add_field(name="Eski Hali", value=before.content or "[Boş]", inline=False)
        embed.add_field(name="Yeni Hali", value=after.content or "[Boş]", inline=False)
        embed.set_footer(text=VLANDIA_TEMASI['footer'])
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
            embed = discord.Embed(title="🔥🏷️ Rol Güncellendi", color=VLANDIA_TEMASI['renk'], timestamp=discord.utils.utcnow())
            embed.add_field(name="Yapılan (Kullanıcı)", value=f"{after.mention} (`{after.id}`)", inline=False)
            if eklenen:
                embed.add_field(name="Eklenen Roller", value=", ".join(eklenen), inline=False)
            if cikarilan:
                embed.add_field(name="Alınan Roller", value=", ".join(cikarilan), inline=False)
            embed.set_footer(text=VLANDIA_TEMASI['footer'])
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

    embed = discord.Embed(color=VLANDIA_TEMASI['renk'], timestamp=discord.utils.utcnow())
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
                    embed.title = "🔥🎙️ Krallık Ses Durumu Değişti"
                    embed.description = f"**Yapan:** {yapan}\n**Yapılan:** {member.mention} kullanıcısı {durum}."
                elif before.deaf != after.deaf:
                    durum = "sağırlaştırıldı" if after.deaf else "sağırlaştırılması kaldırıldı"
                    embed.title = "🔥🎧 Krallık Kulaklık Durumu Değişti"
                    embed.description = f"**Yapan:** {yapan}\n**Yapılan:** {member.mention} kullanıcısı {durum}."
            elif before.channel is not None and after.channel is None:
                async for entry in guild.audit_logs(limit=3, action=discord.AuditLogAction.member_move):
                    if entry.target.id == member.id:
                        yapan = f"{entry.user.mention} (`{entry.user.id}`)"
                        break
                embed.title = "🔥👢 Ses Kanalından Atıldı / Ayrıldı"
                embed.description = f"**Yapan:** {yapan}\n**Yapılan:** {member.mention} kullanıcısı **{before.channel.name}** kanalından uzaklaştırıldı/çıktı."
            else:
                return
        else:
            if before.channel is None and after.channel is not None:
                embed.title = "🔥🔊 Ses Kanalına Giriş Yapıldı"
                embed.description = f"**Yapan / Yapılan:** {member.mention}\n**Kanal:** **{after.channel.name}**"
            elif before.channel is not None and after.channel is None:
                embed.title = "🔥🔇 Ses Kanalından Çıkıldı"
                embed.description = f"**Yapan / Yapılan:** {member.mention}\n**Kanal:** **{before.channel.name}**"
            elif before.channel is not None and after.channel is not None:
                async for entry in guild.audit_logs(limit=3, action=discord.AuditLogAction.member_move):
                    if entry.target.id == member.id:
                        yapan = f"{entry.user.mention} (`{entry.user.id}`)"
                        break
                embed.title = "🔥🔀 Ses Kanalı Değiştirildi / Taşındı"
                embed.description = f"**Yapan:** {yapan}\n**Yapılan:** {member.mention} taşındı.\n**Eski Kanal:** **{before.channel.name}** ➡️ **Yeni Kanal:** **{after.channel.name}**"
            else:
                return

        embed.set_footer(text=VLANDIA_TEMASI['footer'])
        await log_kanal.send(embed=embed)
    except Exception as e:
        logger.error(f"Ses log hatası: {e}")

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        await bot.process_commands(message)
        return

    # PARTNER SİSTEMİ KONTROLÜ
    if message.channel.name == KANALLAR["partner"]:
        conn = get_database_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id FROM partner_stats WHERE guild_id = ? AND text_content = ?", (message.guild.id, message.content.strip()))
            existing = cursor.fetchone()
            
            cursor.execute("SELECT real_partner, fake_partner FROM partner_counts WHERE user_id = ?", (message.author.id,))
            p_row = cursor.fetchone()
            if not p_row:
                cursor.execute("INSERT INTO partner_counts (user_id, real_partner, fake_partner) VALUES (?, 0, 0)", (message.author.id,))
                real_count, fake_count = 0, 0
            else:
                real_count, fake_count = p_row

            log_kanal = discord.utils.get(message.guild.text_channels, name=KANALLAR["partnerSayac"])

            if existing:
                fake_count += 1
                cursor.execute("UPDATE partner_counts SET fake_partner = ? WHERE user_id = ?", (fake_count, message.author.id))
                conn.commit()
                conn.close()

                if log_kanal:
                    embed = discord.Embed(
                        title="⚠️ Sahte (Fake) Partner Algılandı!",
                        description=f"**Yetkili:** {message.author.mention} (`{message.author.id}`)\n**Durum:** Bu partnerlik metni daha önce kullanılmış!\n**Toplam Sahte:** `{fake_count}`",
                        color=discord.Color.red(),
                        timestamp=discord.utils.utcnow()
                    )
                    embed.set_footer(text=VLANDIA_TEMASI['footer'])
                    try:
                        await log_kanal.send(embed=embed)
                    except:
                        pass
            else:
                cursor.execute("INSERT INTO partner_stats (user_id, guild_id, text_content) VALUES (?, ?, ?)", (message.author.id, message.guild.id, message.content.strip()))
                real_count += 1
                cursor.execute("UPDATE partner_counts SET real_partner = ? WHERE user_id = ?", (real_count, message.author.id))
                conn.commit()
                conn.close()

                if log_kanal:
                    embed = discord.Embed(
                        title="🤝 Başarılı Partnerlik Kaydı!",
                        description=f"**Yetkili:** {message.author.mention} (`{message.author.id}`)\n**Kaçıncı Partnerlik:** `#{real_count}`\n**Durum:** Başarıyla onaylandı ve işlendi!",
                        color=discord.Color.green(),
                        timestamp=discord.utils.utcnow()
                    )
                    embed.set_footer(text=VLANDIA_TEMASI['footer'])
                    try:
                        await log_kanal.send(embed=embed)
                    except:
                        pass

    mesaj_icerigi = message.content.lower()
    if any(kufur in mesaj_icerigi for kufur in YASAKLI_KELIMELER):
        try:
            await message.delete()
            await message.channel.send(f"🔥 {message.author.mention}, küfür ettiğin için otomatik **rankdown** uygulandı!", delete_after=5)
            
            rank_log_kanal = discord.utils.get(message.guild.text_channels, name=KANALLAR["rankLog"])
            if rank_log_kanal:
                log_embed = discord.Embed(
                    title="🔥📉 Otomatik Rankdown (Ceza) Uygulandı",
                    description=f"**Kullanıcı:** {message.author.mention} (`{message.author.id}`)\n**Sebep:** Küfür / Yasaklı Kelime Kullanımı\n**Kanal:** {message.channel.mention}",
                    color=discord.Color.red(),
                    timestamp=discord.utils.utcnow()
                )
                log_embed.set_footer(text=VLANDIA_TEMASI['footer'])
                await rank_log_kanal.send(embed=log_embed)
        except Exception as e:
            logger.error(f"Küfür engelleme ve log hatası: {e}")

    is_vlandia = any(r.name == "♱ 𝐕𝐥𝐚𝐧𝐝𝐢𝐚" for r in message.author.roles)

    if message.channel.name == KANALLAR["ekipDuyuru"]:
        ekip_rol_obj = discord.utils.get(message.guild.roles, name=EKIP_ROL)
        if is_vlandia and ekip_rol_obj:
            dm_embed = discord.Embed(
                title='🔥 VLANDİA İMPARATORLUK BİLDİRİSİ',
                description=f"**Yayan Savaşçı:** {message.author.mention}\n\n[Mesaja Gitmek İçin Tıkla]({message.url})",
                color=VLANDIA_TEMASI['renk']
            )
            dm_embed.set_footer(text=VLANDIA_TEMASI['footer'])
            for member in message.guild.members:
                if not member.bot and any(r.name == EKIP_ROL for r in member.roles):
                    try:
                        await member.send(content=f"🔥 Hey **{ekip_rol_obj.name}**! Duyuru kanalına göz at.", embed=dm_embed)
                    except Exception:
                        pass

    if not is_vlandia:
        if message.channel.name == KANALLAR["galeriChat"] and len(message.attachments) == 0:
            await message.delete()
            try:
                await message.author.send("🔥 Bu kanala yalnızca görsel veya medya dosyaları atabilirsin!")
            except:
                pass
            return

    await bot.process_commands(message)

# ==========================================
# 6. KOMUTLAR
# ==========================================
@bot.tree.command(name="partnersayaç", description="Kullanıcının yaptığı gerçek ve sahte partner sayılarını gösterir.")
@app_commands.describe(member="İstatistiklerine bakılacak yetkili")
async def partnersayaç_komutu(interaction: discord.Interaction, member: discord.Member = None):
    if interaction.channel.name != KANALLAR["botKomut"]:
        await interaction.response.send_message(f"❌ Bu komut yalnızca <#{discord.utils.get(interaction.guild.text_channels, name=KANALLAR['botKomut']).id if discord.utils.get(interaction.guild.text_channels, name=KANALLAR['botKomut']) else 0}> kanalında kullanılabilir!", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    target = member or interaction.user
    conn = get_database_connection()
    real_p, fake_p = 0, 0
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT real_partner, fake_partner FROM partner_counts WHERE user_id = ?", (target.id,))
        row = cursor.fetchone()
        if row:
            real_p, fake_p = row
        conn.close()

    embed = discord.Embed(title=f"🔥 Partner Raporu • {target.name}", color=VLANDIA_TEMASI['renk'])
    embed.set_thumbnail(url=target.display_avatar.url)
    embed.add_field(name="🤝 Gerçek Partner", value=f"**{real_p}** adet", inline=True)
    embed.add_field(name="⚠️ Sahte (Fake) Partner", value=f"**{fake_p}** adet", inline=True)
    embed.set_footer(text=VLANDIA_TEMASI['footer'])
    await interaction.followup.send(embed=embed, ephemeral=True)

@bot.tree.command(name="rankup", description="Bir kullanıcının mevcut rütbesini bir üst rütbeye yükseltir.")
@app_commands.describe(member="Rütbesi yükseltilecek oyuncu")
async def rankup_komutu(interaction: discord.Interaction, member: discord.Member):
    if interaction.channel.name != KANALLAR["rankLog"]:
        await interaction.response.send_message(f"❌ Bu komut yalnızca <#{discord.utils.get(interaction.guild.text_channels, name=KANALLAR['rankLog']).id if discord.utils.get(interaction.guild.text_channels, name=KANALLAR['rankLog']) else 0}> kanalında kullanılabilir!", ephemeral=True)
        return

    has_vlandia_role = any(r.name == "♱ 𝐕𝐥𝐚𝐧𝐝𝐢𝐚" for r in interaction.user.roles)
    if not has_vlandia_role and not interaction.user.bot:
        await interaction.response.send_message("❌ Bu komutu kullanabilmek için **♱ 𝐕𝐥𝐚𝐧𝐝𝐢𝐚** rolüne sahip olmalısın!", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    # Kullanıcının üstünde olduğu rank rollerini bul
    kullanici_ranklari = [r for r in member.roles if r.name in RANK_HIYERARSISI]
    
    if not kullanici_ranklari:
        # Hiç rankı yoksa listedeki ilk rankı (en düşük) verelim
        hedef_rol_adi = RANK_HIYERARSISI[0]
        hedef_rol = discord.utils.get(interaction.guild.roles, name=hedef_rol_adi)
        if not hedef_rol:
            await interaction.followup.send(f"❌ Sunucuda **{hedef_rol_adi}** isimli rol bulunamadı!", ephemeral=True)
            return
        
        await member.add_roles(hedef_rol)
        await interaction.followup.send(f"🔥 {member.mention} hiç ranka sahip olmadığı için ilk rütbe olan **{hedef_rol.name}** verildi.", ephemeral=True)
    else:
        # Kullanıcının mevcut en yüksek rankını hiyerarşide bul
        en_yuksek_mevcut = max(kullanici_ranklari, key=lambda r: RANK_HIYERARSISI.index(r.name))
        mevcut_index = RANK_HIYERARSISI.index(en_yuksek_mevcut.name)

        if mevcut_index + 1 >= len(RANK_HIYERARSISI):
            await interaction.followup.send(f"❌ {member.mention} zaten en yüksek rütbede (**{en_yuksek_mevcut.name}**), daha fazla yükseltilemez!", ephemeral=True)
            return

        yeni_rol_adi = RANK_HIYERARSISI[mevcut_index + 1]
        yeni_rol = discord.utils.get(interaction.guild.roles, name=yeni_rol_adi)
        if not yeni_rol:
            await interaction.followup.send(f"❌ Sunucuda **{yeni_rol_adi}** isimli rol bulunamadı!", ephemeral=True)
            return

        try:
            await member.remove_roles(en_yuksek_mevcut)
            await member.add_roles(yeni_rol)
            await interaction.followup.send(f"🔥 {member.mention} başarıyla **{en_yuksek_mevcut.name}** rütbesinden **{yeni_rol.name}** rütbesine yükseltildi (Rankup).", ephemeral=True)
            
            rank_log_kanal = discord.utils.get(interaction.guild.text_channels, name=KANALLAR["rankLog"])
            if rank_log_kanal:
                log_embed = discord.Embed(
                    title="🔥📈 Otomatik Hiyerarşik Rankup Gerçekleşti",
                    description=f"**Kullanıcı:** {member.mention} (`{member.id}`)\n**Eski Rol:** {en_yuksek_mevcut.name}\n**Yeni Rol:** **{yeni_rol.name}**\n**Yetkili:** {interaction.user.mention}",
                    color=VLANDIA_TEMASI['renk'],
                    timestamp=discord.utils.utcnow()
                )
                log_embed.set_footer(text=VLANDIA_TEMASI['footer'])
                await rank_log_kanal.send(embed=log_embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Rol güncellenirken hata oluştu: {e}", ephemeral=True)

@bot.tree.command(name="rankdown", description="Bir kullanıcının mevcut rütbesini bir alt rütbeye düşürür.")
@app_commands.describe(member="Rütbesi düşürülecek oyuncu")
async def rankdown_komutu(interaction: discord.Interaction, member: discord.Member):
    if interaction.channel.name != KANALLAR["rankLog"]:
        await interaction.response.send_message(f"❌ Bu komut yalnızca <#{discord.utils.get(interaction.guild.text_channels, name=KANALLAR['rankLog']).id if discord.utils.get(interaction.guild.text_channels, name=KANALLAR['rankLog']) else 0}> kanalında kullanılabilir!", ephemeral=True)
        return

    has_vlandia_role = any(r.name == "♱ 𝐕𝐥𝐚𝐧𝐝𝐢𝐚" for r in interaction.user.roles)
    if not has_vlandia_role and not interaction.user.bot:
        await interaction.response.send_message("❌ Bu komutu kullanabilmek için **♱ 𝐕𝐥𝐚𝐧𝐝𝐢𝐚** rolüne sahip olmalısın!", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    kullanici_ranklari = [r for r in member.roles if r.name in RANK_HIYERARSISI]
    
    if not kullanici_ranklari:
        await interaction.followup.send(f"❌ {member.mention} üzerinde düşürülebilecek herhangi bir rank rolü bulunmuyor!", ephemeral=True)
        return

    en_yuksek_mevcut = max(kullanici_ranklari, key=lambda r: RANK_HIYERARSISI.index(r.name))
    mevcut_index = RANK_HIYERARSISI.index(en_yuksek_mevcut.name)

    if mevcut_index - 1 < 0:
        await interaction.followup.send(f"❌ {member.mention} zaten en düşük rütbede (**{en_yuksek_mevcut.name}**), daha fazla düşürülemez!", ephemeral=True)
        return

    yeni_rol_adi = RANK_HIYERARSISI[mevcut_index - 1]
    yeni_rol = discord.utils.get(interaction.guild.roles, name=yeni_rol_adi)
    if not yeni_rol:
        await interaction.followup.send(f"❌ Sunucuda **{yeni_rol_adi}** isimli rol bulunamadı!", ephemeral=True)
        return

    try:
        await member.remove_roles(en_yuksek_mevcut)
        await member.add_roles(yeni_rol)
        await interaction.followup.send(f"🔥 {member.mention} adlı kullanıcının rütbesi **{en_yuksek_mevcut.name}** seviyesinden **{yeni_rol.name}** seviyesine düşürüldü (Rankdown).", ephemeral=True)
        
        rank_log_kanal = discord.utils.get(interaction.guild.text_channels, name=KANALLAR["rankLog"])
        if rank_log_kanal:
            log_embed = discord.Embed(
                title="🔥📉 Otomatik Hiyerarşik Rankdown Gerçekleşti",
                description=f"**Kullanıcı:** {member.mention} (`{member.id}`)\n**Eski Rol:** {en_yuksek_mevcut.name}\n**Yeni Rol:** **{yeni_rol.name}**\n**Yetkili:** {interaction.user.mention}",
                color=discord.Color.red(),
                timestamp=discord.utils.utcnow()
            )
            log_embed.set_footer(text=VLANDIA_TEMASI['footer'])
            await rank_log_kanal.send(embed=log_embed)
    except Exception as e:
        await interaction.followup.send(f"❌ Rol güncellenirken hata oluştu: {e}", ephemeral=True)

@bot.tree.command(name="ticket-kur", description="Vlandia tarzı destek panelini kurar.")
@app_commands.default_permissions(administrator=True)
async def ticket_kur(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🔥 VLANDİA DESTEK MERKEZİ",
        description="Aşağıdaki imparatorluk menüsünü kullanarak ihtiyacına uygun destek talebini oluşturabilirsin.",
        color=VLANDIA_TEMASI['renk']
    )
    embed.set_footer(text=VLANDIA_TEMASI['footer'])
    await interaction.channel.send(embed=embed, view=TicketView())
    await interaction.response.send_message("🔥 Destek paneli başarıyla yerleştirildi!", ephemeral=True)

@bot.tree.command(name="çekiliş", description="Ödül, kazanan sayısı, süre ve açıklama girebileceğiniz çekiliş panelini açar.")
@app_commands.default_permissions(manage_guild=True)
async def cekilis_komutu(interaction: discord.Interaction):
    await interaction.response.send_modal(GiveawayModal())

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
        await interaction.followup.send("❌ Geçersiz süre formatı!", ephemeral=True)
        return

    delta = timedelta(seconds=toplam_saniye)
    try:
        await member.timeout(delta, reason=sebep)
        await interaction.followup.send(f"🔥 {member.mention} kullanıcısına **{sure}** süreyle zamanaşımı uygulandı.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Hata: {e}", ephemeral=True)

@bot.tree.command(name="sesat", description="Bir kullanıcıyı bulunduğu ses kanalından atar.")
@app_commands.describe(member="Sesten atılacak kullanıcı")
@app_commands.default_permissions(move_members=True)
async def sesat_komutu(interaction: discord.Interaction, member: discord.Member):
    await interaction.response.defer(ephemeral=True)
    if not member.voice or not member.voice.channel:
        await interaction.followup.send("❌ Bu kullanıcı seste değil!", ephemeral=True)
        return
    try:
        await member.move_to(None)
        await interaction.followup.send(f"🔥 {member.mention} sesten atıldı.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Hata: {e}", ephemeral=True)

@bot.tree.command(name="kilitle", description="Bulunduğunuz metin kanalını kilitler/açar.")
@app_commands.default_permissions(manage_channels=True)
async def kilitle_komutu(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    channel = interaction.channel
    overwrite = channel.overwrites_for(interaction.guild.default_role)
    overwrite.send_messages = False if overwrite.send_messages is not False else None
    try:
        await channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
        await interaction.followup.send("🔥 Kanal kilit durumu değiştirildi.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Hata: {e}", ephemeral=True)

@bot.tree.command(name="ireset", description="Sunucudaki tüm davet verilerini sıfırlar.")
@app_commands.default_permissions(administrator=True)
async def ireset_komutu(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    conn = get_database_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM invites")
        conn.commit()
        conn.close()
        await interaction.followup.send("🔥 Davetler sıfırlandı!", ephemeral=True)

@bot.tree.command(name="invite", description="Davet istatistiklerini gösterir.")
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

    embed = discord.Embed(title=f"🔥 Davet Raporu • {target.name}", color=VLANDIA_TEMASI['renk'])
    embed.add_field(name="📥 Gerçek", value=str(inv_count))
    embed.add_field(name="⚠️ Sahte", value=str(fake_count))
    await interaction.followup.send(embed=embed, ephemeral=True)

@bot.tree.command(name="sunucu", description="Sunucu istatistiklerini gösterir.")
async def sunucu_komutu(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild
    embed = discord.Embed(title=f"🔥 {guild.name} İstatistikleri", color=VLANDIA_TEMASI['renk'])
    embed.add_field(name="Üye Sayısı", value=str(guild.member_count))
    await interaction.followup.send(embed=embed, ephemeral=True)

@bot.tree.command(name="ai", description="Vlandia AI.")
async def ai_komutu(interaction: discord.Interaction, soru: str):
    await interaction.response.send_message(f"🔥 **Soru:** {soru}\n🤖 Aktif.", ephemeral=True)

@bot.tree.command(name="sil", description="Mesaj siler.")
@app_commands.default_permissions(manage_messages=True)
async def sil_komutu(interaction: discord.Interaction, miktar: int):
    await interaction.response.defer(ephemeral=True)
    await interaction.channel.purge(limit=miktar)
    await interaction.followup.send(f"🔥 {miktar} mesaj silindi.", ephemeral=True)

@bot.tree.command(name="ban", description="Banlar.")
@app_commands.default_permissions(ban_members=True)
async def ban_komutu(interaction: discord.Interaction, member: discord.Member, sebep: str = "Yok"):
    await member.ban(reason=sebep)
    await interaction.response.send_message(f"🔥 {member.name} banlandı.", ephemeral=True)

@bot.tree.command(name="kick", description="Atar.")
@app_commands.default_permissions(kick_members=True)
async def kick_komutu(interaction: discord.Interaction, member: discord.Member, sebep: str = "Yok"):
    await member.kick(reason=sebep)
    await interaction.response.send_message(f"🔥 {member.name} atıldı.", ephemeral=True)

# ==========================================
# 7. ÇALIŞTIRMA
# ==========================================
if __name__ == "__main__":
    logger.info("Vlandia Bot servisleri başlatılıyor...")
    t = threading.Thread(target=run_flask, daemon=True)
    t.start()
    
    TOKEN = os.getenv("DISCORD_TOKEN")
    if TOKEN:
        bot.run(TOKEN)
    else:
        logger.critical("HATA: DISCORD_TOKEN bulunamadı!")
