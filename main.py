import discord
from discord.ext import commands
from discord import app_commands
import os
from flask import Flask
import threading
import sqlite3
import random
from gtts import gTTS
import os.path
from datetime import timedelta
import logging
import asyncio
import sys

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
intents.integrations = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ==========================================
# 2. RENDER 7/24 WEB SUNUCUSU (FLASK)
# ==========================================
app = Flask(__name__)

@app.route('/')
def home_route():
    logger.info("Web sunucusuna ping atıldı (7/24 aktif tutma isteği).")
    return "WinterFall Pro Bot Aktif ve Çalışır Durumda!", 200

@app.route('/health')
def health_check():
    return {"status": "online", "bot": str(bot.user)}, 200

def start_flask_server():
    port = int(os.environ.get("PORT", 8080))
    try:
        app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
    except Exception as server_error:
        logger.error(f"Flask sunucusu başlatılırken kritik hata oluştu: {server_error}")

# ==========================================
# 3. VERİTABANI YÖNETİMİ VE TABLO KURULUMLARI
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
                CREATE TABLE IF NOT EXISTS user_ranks (
                    user_id INTEGER PRIMARY KEY,
                    rank_level INTEGER DEFAULT 1,
                    experience_points INTEGER DEFAULT 0
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS guild_log_settings (
                    guild_id INTEGER PRIMARY KEY,
                    mod_log_id INTEGER,
                    message_log_id INTEGER,
                    voice_log_id INTEGER
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
            logger.info("Veritabanı tabloları başarıyla oluşturuldu ve doğrulandı.")
        except sqlite3.Error as err:
            logger.error(f"Tablo oluşturma sırasında hata: {err}")
        finally:
            conn.close()

initialize_database_structure()

# ==========================================
# 4. TİCKET SİSTEMİ (BUTONLAR, MENÜLER VE SORULAR)
# ==========================================
class TicketView(discord.ui.View):
    def __init__(self, ticket_sahibi_id: int):
        super().__init__(timeout=None)
        self.ticket_sahibi_id = ticket_sahibi_id

    @discord.ui.button(label="🙋‍♂️ Bileti Üstlen", style=discord.ButtonStyle.success, custom_id="persistent_ticket_ustlen_btn")
    async def ustlen_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Yetkili rolü kontrolü (Sadece Ticket Yetkili veya Yönetici basabilir)
        yetkili_rol = discord.utils.get(interaction.guild.roles, name="Ticket Yetkili")
        if yetkili_rol not in interaction.user.roles and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Bu bileti sadece **Ticket Yetkili** rolüne sahip olanlar üstlenebilir!", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=False)
        try:
            guild = interaction.guild
            kanal = interaction.channel
            ustlenen = interaction.user

            ticket_sahibi = guild.get_member(self.ticket_sahibi_id)
            if not ticket_sahibi:
                try:
                    ticket_sahibi = await guild.fetch_member(self.ticket_sahibi_id)
                except:
                    ticket_sahibi = None

            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
            }

            if ticket_sahibi:
                overwrites[ticket_sahibi] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
            
            overwrites[ustlenen] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

            await kanal.edit(overwrites=overwrites, reason=f"Bilet {ustlenen.name} tarafından üstlenildi.")

            embed = discord.Embed(
                title="🙋‍♂️ Bilet Üstlenildi",
                description=f"Bu bilet **{ustlenen.mention}** tarafından üstlenilmiştir!\nArtık bu kanala sadece bilet sahibi ve üstlenen yetkili mesaj yazabilir.",
                color=discord.Color.green()
            )
            embed.set_footer(text="WinterFall Ticket Management")
            
            await kanal.send(embed=embed)
        except Exception as e:
            logger.error(f"Bileti üstlenme hatası: {e}")
            await interaction.followup.send("❌ Bilet üstlenilirken bir hata oluştu.", ephemeral=True)

    @discord.ui.button(label="🔒 Desteği Kapat", style=discord.ButtonStyle.danger, custom_id="persistent_ticket_kapat_btn")
    async def kapat_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            kapatan_kullanici = interaction.user
            logger.info(f"{kapatan_kullanici} ({kapatan_kullanici.id}) tarafından {interaction.channel.name} adlı ticket kapatıldı.")
            
            await interaction.response.send_message(f"⚠️ Ticket **{kapatan_kullanici.name}** tarafından kapatılıyor, kanal 5 saniye içinde silinecektir...", ephemeral=False)
            await asyncio.sleep(5)
            await interaction.channel.delete(reason=f"Ticket {kapatan_kullanici.name} tarafından kapatıldı.")
        except Exception as e:
            logger.error(f"Ticket kapatma işleminde hata: {e}")

class TicketSelectMenu(discord.ui.Select):
    def __init__(self):
        options_list = [
            discord.SelectOption(label="Ekip Alım", description="Ekibimize katılmak için başvuru yap.", emoji="📥"),
            discord.SelectOption(label="Merge", description="Sunucu birleşim / merge teklifleri için.", emoji="🔗"),
            discord.SelectOption(label="Partnerlik", description="Sunucu partnerlik başvurusu yapmak için.", emoji="💖"),
            discord.SelectOption(label="Ally", description="Ally (Müttefik) olmak için başvuru.", emoji="🤝"),
            discord.SelectOption(label="Genel Destek", description="Genel teknik veya sunucu yardımı almak için.", emoji="🛠️")
        ]
        super().__init__(placeholder="Destek kategorisi seçin...", min_values=1, max_values=1, options=options_list, custom_id="persistent_ticket_select_menu")

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            secilen_kategori = self.values[0]
            guild = interaction.guild
            
            overwrites_map = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
                guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
            }

            hedef_kategori_nesnesi = discord.utils.get(guild.categories, name="AÇIK TICKETLAR")
            channel_name = f"ticket-{secilen_kategori.lower().replace(' ', '-')}-{interaction.user.name}"
            
            ticket_channel = await guild.create_text_channel(
                name=channel_name, 
                overwrites=overwrites_map, 
                category=hedef_kategori_nesnesi
            )

            yetkili_rol_obj = discord.utils.get(guild.roles, name="Ticket Yetkili")
            yetkili_etiket_metni = yetkili_rol_obj.mention if yetkili_rol_obj else "@Ticket Yetkili"
            birlesik_etiket = f"{interaction.user.mention} {yetkili_etiket_metni}"

            view_nesnesi = TicketView(ticket_sahibi_id=interaction.user.id)

            if secilen_kategori == "Ekip Alım":
                embed_obj = discord.Embed(
                    title="📥 Ekip Alım Başvuru Talebi",
                    description="Ekibimize katılmak istiyorsan harika! Lütfen aşağıdaki soruları yanıtla:",
                    color=discord.Color.from_rgb(0, 200, 255)
                )
                embed_obj.add_field(name="Sorular", value="1. Eski ekibin neresi?\n2. Oyun içi ismin?\n3. Hangi sunucularda oynuyorsun?", inline=False)
                embed_obj.set_footer(text="WinterFall Ekip Alım Sistemleri")
                await interaction.followup.send(f"Destek kanalınız oluşturuldu: {ticket_channel.mention}", ephemeral=True)
                await ticket_channel.send(content=birlesik_etiket, embed=embed_obj, view=view_nesnesi)

            elif secilen_kategori == "Merge":
                embed_obj = discord.Embed(
                    title="🔗 Merge (Birleşim) Teklif Talebi",
                    description="Sunucu birleşim teklifiniz için teşekkürler. Lütfen aşağıdaki bilgileri sağlayın:",
                    color=discord.Color.from_rgb(150, 50, 250)
                )
                embed_obj.add_field(name="Sorular", value="1. Kim kime katılcak?\n2. Sunucunuzun üye sayısı ve aktifliği nedir?\n3. Hangi sunucularda oynuyorsun?", inline=False)
                embed_obj.set_footer(text="WinterFall Merge Systems")
                await interaction.followup.send(f"Destek kanalınız oluşturuldu: {ticket_channel.mention}", ephemeral=True)
                await ticket_channel.send(content=birlesik_etiket, embed=embed_obj, view=view_nesnesi)

            elif secilen_kategori == "Partnerlik":
                embed_obj = discord.Embed(
                    title="💖 Partnerlik Başvuru Talebi",
                    description="Aramıza katılmak için sunucuya gelip ticket açmanız yeterli.",
                    color=discord.Color.from_rgb(255, 105, 180)
                )
                embed_obj.add_field(name="Talep Eden", value=interaction.user.mention, inline=True)
                embed_obj.add_field(name="Durum", value="İnceleniyor", inline=True)
                embed_obj.set_footer(text="WinterFall Partner Systems")

                await interaction.followup.send(f"Destek kanalınız oluşturuldu: {ticket_channel.mention}", ephemeral=True)
                await ticket_channel.send(content=birlesik_etiket, embed=embed_obj, view=view_nesnesi)
                
                partnerlik_metni_icerigi = (
                    "👑 KingDooms\n"
                    "\"Krallıklar yükselir imparatorluklar yıkılır.. Fakat KingDooms daima ayakta kalır\"\n\n"
                    "⚔️ • Büyük savaşlar\n\n"
                    "🏰 • Güçlü krallık sistemi\n\n"
                    "🛡️ • Sadakat • Onur • Birlik\n\n"
                    "🎁 • Çekilişler ve ödüller\n\n"
                    "🤝 • Partner toplulukları\n\n"
                    "Kılıcını kuşan ve KingDooms 'un saflarına katıl!\n\n"
                    "🔗 Davet: https://discord.gg/Tcq2fcdR2c"
                )
                await ticket_channel.send(partnerlik_metni_icerigi)

            elif secilen_kategori == "Ally":
                embed_obj = discord.Embed(
                    title="🤝 Ally (Müttefik) Başvuru Talebi",
                    description="Ally olmak için aşağıdaki bilgileri paylaşabilirsiniz:",
                    color=discord.Color.from_rgb(50, 205, 50)
                )
                embed_obj.add_field(name="Sorular", value="1. Sunucu davet linkiniz nedir?\n2. Sunucu üye ve aktiflik durumunuz?\n3. Hangi sunucularda oynuyorsun?", inline=False)
                embed_obj.set_footer(text="WinterFall Ally Systems")
                await interaction.followup.send(f"Destek kanalınız oluşturuldu: {ticket_channel.mention}", ephemeral=True)
                await ticket_channel.send(content=birlesik_etiket, embed=embed_obj, view=view_nesnesi)

            else:
                embed_obj = discord.Embed(
                    title="🛠️ Genel Destek Talebi",
                    description=f"Değerli **{interaction.user.name}**, yetkili ekibimiz en kısa süre içinde sizinle ilgilenecektir.\n\nLütfen sorununuzu veya talebinizi detaylı bir şekilde yazın.",
                    color=discord.Color.from_rgb(100, 150, 255)
                )
                embed_obj.add_field(name="Oluşturan Kullanıcı", value=interaction.user.mention, inline=False)
                embed_obj.set_footer(text="WinterFall Support & Security")

                await interaction.followup.send(f"Destek kanalınız oluşturuldu: {ticket_channel.mention}", ephemeral=True)
                await ticket_channel.send(content=birlesik_etiket, embed=embed_obj, view=view_nesnesi)
                
        except Exception as err:
            logger.error(f"Ticket oluşturma callback hatası: {err}")

class TicketMainView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelectMenu())

# ==========================================
# 5. BOT EVENTLERİ (ON_READY & ON_MEMBER_JOIN & ON_MESSAGE)
# ==========================================
@bot.event
async def on_ready():
    logger.info(f"Bot Başarıyla Giriş Yaptı: {bot.user.name} (ID: {bot.user.id})")
    try:
        synced_commands = await bot.tree.sync()
        logger.info(f"Global Slash Komutları Senkronize Edildi: {len(synced_commands)} komut aktif.")
    except Exception as sync_err:
        logger.error(f"Slash komut senkronizasyon hatası: {sync_err}")

@bot.event
async def on_member_join(member):
    try:
        otomatik_rol = discord.utils.get(member.guild.roles, name="❄ Member")
        if otomatik_rol:
            await member.add_roles(otomatik_rol, reason="Otomatik üye katılım rolü.")
            logger.info(f"{member.name} kullanıcısına otomatik rol verildi.")
    except Exception as role_err:
        logger.error(f"Üye katılım rol verme hatası: {role_err}")

@bot.event
async def on_message(message):
    if message.author.bot:
        await bot.process_commands(message)
        return

    if message.channel.name == "「🤝」partner":
        user_id = message.author.id
        mesaj_icerigi = message.content

        conn = get_database_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT real_partner, fake_partner, last_text FROM partner_stats WHERE user_id = ?", (user_id,))
                result = cursor.fetchone()

                is_fake = False
                if result:
                    real_p, fake_p, last_t = result
                    if last_t == mesaj_icerigi:
                        is_fake = True
                        fake_p += 1
                    else:
                        real_p += 1
                    cursor.execute("UPDATE partner_stats SET real_partner = ?, fake_partner = ?, last_text = ? WHERE user_id = ?", (real_p, fake_p, mesaj_icerigi, user_id))
                else:
                    real_p = 1
                    fake_p = 0
                    cursor.execute("INSERT INTO partner_stats (user_id, real_partner, fake_partner, last_text) VALUES (?, ?, ?, ?)", (user_id, real_p, fake_p, mesaj_icerigi))
                
                conn.commit()

                if not is_fake:
                    log_embed = discord.Embed(
                        title="🤝 Yeni Partnerlik Gerçekleştirildi",
                        description=f"**{message.author.mention}** adlı yetkili yeni bir partnerlik paylaştı!",
                        color=discord.Color.green()
                    )
                    log_embed.add_field(name="Yapan Yetkili", value=message.author.mention, inline=True)
                    log_embed.add_field(name="Toplam Başarılı Partnerlik", value=f"**{real_p}.** Partnerlik", inline=True)
                    log_embed.set_footer(text="WinterFall Partner Log Systems")

                    sayaç_kanali = discord.utils.get(message.guild.text_channels, name="「⏳」partnerlik-sayaç")
                    if sayaç_kanali:
                        await sayaç_kanali.send(embed=log_embed)
                else:
                    await message.delete()
                    uyari_mesaji = await message.channel.send(f"⚠️ {message.author.mention} Aynı metni tekrar girdiğiniz tespit edildi! Bu partnerlik **sahte (fake)** olarak algılandı ve silindi.")
                    await asyncio.sleep(5)
                    await uyari_mesaji.delete()

            except Exception as e:
                logger.error(f"Partner mesaj dinleme hatası: {e}")
            finally:
                conn.close()

    await bot.process_commands(message)

# ==========================================
# 6. LOG SİSTEMLERİ
# ==========================================
@bot.event
async def on_message_delete(message):
    if message.author.bot:
        return
    try:
        log_kanal_bulunan = discord.utils.get(message.guild.text_channels, name="mesaj-log")
        if log_kanal_bulunan:
            embed_log = discord.Embed(title="🗑️ Mesaj Silindi", color=discord.Color.red())
            embed_log.add_field(name="Yazan Kullanıcı", value=message.author.mention, inline=True)
            embed_log.add_field(name="Kanal", value=message.channel.mention, inline=True)
            embed_log.add_field(name="Silinen İçerik", value=message.content or "*(Metin içeriği yok)*", inline=False)
            embed_log.set_footer(text=f"Kullanıcı ID: {message.author.id}")
            await log_kanal_bulunan.send(embed=embed_log)
    except Exception as e:
        logger.error(f"Mesaj silme loglama hatası: {e}")

@bot.event
async def on_message_edit(before_msg, after_msg):
    if before_msg.author.bot or before_msg.content == after_msg.content:
        return
    try:
        log_kanal_bulunan = discord.utils.get(before_msg.guild.text_channels, name="mesaj-log")
        if log_kanal_bulunan:
            embed_log = discord.Embed(title="✏️ Mesaj Düzenlendi", color=discord.Color.orange())
            embed_log.add_field(name="Kullanıcı", value=before_msg.author.mention, inline=True)
            embed_log.add_field(name="Kanal", value=before_msg.channel.mention, inline=True)
            embed_log.add_field(name="Önceki Hali", value=before_msg.content or "*(Boş)*", inline=False)
            embed_log.add_field(name="Yeni Hali", value=after_msg.content or "*(Boş)*", inline=False)
            await log_kanal_bulunan.send(embed=embed_log)
    except Exception as e:
        logger.error(f"Mesaj düzenleme loglama hatası: {e}")

@bot.event
async def on_voice_state_update(member, before_state, after_state):
    try:
        ses_log_kanali = discord.utils.get(member.guild.text_channels, name="ses-log")
        if not ses_log_kanali:
            return

        if not before_state.mute and after_state.mute:
            embed_ses = discord.Embed(title="🔇 Ses Kanalında Susturuldu", color=discord.Color.orange())
            embed_ses.add_field(name="Etkilenen Kullanıcı", value=member.mention, inline=False)
            embed_ses.set_footer(text=f"Kullanıcı ID: {member.id} | WinterFall Voice Log")
            await ses_log_kanali.send(embed=embed_ses)

        if not before_state.deaf and after_state.deaf:
            embed_ses = discord.Embed(title="🎧 Kulaklığı Kapatıldı", color=discord.Color.orange())
            embed_ses.add_field(name="Etkilenen Kullanıcı", value=member.mention, inline=False)
            embed_ses.set_footer(text=f"Kullanıcı ID: {member.id} | WinterFall Voice Log")
            await ses_log_kanali.send(embed=embed_ses)
            
    except Exception as e:
        logger.error(f"Ses loglama işleminde hata: {e}")

# ==========================================
# 7. SLASH KOMUTLARI
# ==========================================
@bot.tree.command(name="ticket-kur", description="Destek sistem panelini gönderir.")
@app_commands.default_permissions(administrator=True)
async def ticket_kurulum_komutu(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    try:
        panel_embed = discord.Embed(
            title="❄️ WinterFall Profesyonel Destek & Talep Merkezi",
            description=(
                "Sunucumuzda herhangi bir konuda yardıma mı ihtiyacınız var?\n"
                "Aşağıdaki kategori menüsünü kullanarak hızlı bir şekilde destek talebi (ticket) oluşturabilirsiniz."
            ),
            color=discord.Color.from_rgb(88, 101, 242)
        )
        panel_embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)
        panel_embed.set_footer(text="WinterFall Security & Support Systems", icon_url=interaction.client.user.display_avatar.url)
        
        await interaction.channel.send(embed=panel_embed, view=TicketMainView())
        await interaction.followup.send("✅ Geliştirilmiş ticket paneli bu kanalda başarıyla aktif edildi!", ephemeral=True)
    except Exception as e:
        logger.error(f"Ticket kurulum komutu hatası: {e}")

@bot.tree.command(name="kişiekle", description="Aktif ticket kanalına belirttiğiniz kullanıcıyı ekler.")
@app_commands.describe(kullanici="Kanala eklenecek kullanıcı")
async def kisiekle_komutu(interaction: discord.Interaction, kullanici: discord.Member):
    if not interaction.channel.name.startswith("ticket-"):
        await interaction.response.send_message("❌ Bu komut sadece ticket kanallarında kullanılabilir!", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    try:
        kanal = interaction.channel
        await kanal.set_permissions(kullanici, view_channel=True, send_messages=True, read_message_history=True)
        
        await kanal.send(f"➕ {kullanici.mention} bu bilete eklendi!")
        await interaction.followup.send(f"✅ {kullanici.name} başarıyla ticket kanalına dahil edildi.", ephemeral=True)
    except Exception as e:
        logger.error(f"Kişi ekleme komut hatası: {e}")
        await interaction.followup.send("❌ Kullanıcı eklenirken bir hata oluştu.", ephemeral=True)

@bot.tree.command(name="partnersayaç", description="Partnerlik istatistiklerinizi gösterir.")
@app_commands.describe(kullanici="İstatistiklerine bakılacak kullanıcı")
async def partnersayac_komutu(interaction: discord.Interaction, kullanici: discord.Member = None):
     hedef_kanal_adi = "「💻」bot-komut"
     if interaction.channel.name != hedef_kanal_adi:
         await interaction.response.send_message(f"❌ Bu komut sadece **{hedef_kanal_adi}** kanalında kullanılabilir!", ephemeral=True)
         return

     hedef_kullanici = kullanici or interaction.user
     await interaction.response.defer(ephemeral=False)
     conn = get_database_connection()
     if not conn:
         await interaction.followup.send("❌ Veritabanı bağlantı hatası oluştu.", ephemeral=True)
         return

     try:
        cursor = conn.cursor()
        cursor.execute("SELECT real_partner, fake_partner FROM partner_stats WHERE user_id = ?", (hedef_kullanici.id,))
        result = cursor.fetchone()

        real_p = result[0] if result else 0
        fake_p = result[1] if result else 0

        embed = discord.Embed(
            title="📊 Partnerlik İstatistik Sistemi",
            description=f"**{hedef_kullanici.mention}** adlı kullanıcının partnerlik verileri:",
            color=discord.Color.blue()
        )
        embed.add_field(name="✅ Başarılı Partner", value=str(real_p), inline=True)
        embed.add_field(name="⚠️ Sahte (Fake) Partner", value=str(fake_p), inline=True)
        embed.set_thumbnail(url=hedef_kullanici.display_avatar.url)
        embed.set_footer(text="WinterFall Partner Systems")

        await interaction.followup.send(embed=embed)
     except Exception as e:
        logger.error(f"Partner sayaç komut hatası: {e}")
        await interaction.followup.send("❌ İstatistikler alınırken bir hata oluştu.", ephemeral=True)
     finally:
        conn.close()

@bot.tree.command(name="psıfırla", description="Tüm kullanıcıların partnerlik istatistiklerini sıfırlar.")
async def psifirla_komutu(interaction: discord.Interaction):
    gerekli_rol_adi = "♱ 𝐖𝐢𝐧𝐭𝐞𝐫𝐟𝐚𝐥𝐥"
    kullanici_rolleri = [rol.name for rol in interaction.user.roles]
    
    if gerekli_rol_adi not in kullanici_rolleri and not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(f"❌ Bu komutu kullanabilmek için **{gerekli_rol_adi}** rolüne sahip olmalısın!", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    conn = get_database_connection()
    if not conn:
        await interaction.followup.send("❌ Veritabanı bağlantı hatası oluştu.", ephemeral=True)
        return

    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM partner_stats")
        conn.commit()
        await interaction.followup.send("✅ Tüm kullanıcıların partnerlik istatistikleri başarıyla sıfırlandı!", ephemeral=True)
        logger.info(f"{interaction.user} tarafından partnerlik istatistikleri sıfırlandı.")
    except Exception as e:
        logger.error(f"Partner sıfırlama hatası: {e}")
        await interaction.followup.send("❌ Sıfırlama işlemi sırasında bir hata oluştu.", ephemeral=True)
    finally:
        conn.close()

@bot.tree.command(name="ban", description="Belirtilen kullanıcıyı sunucudan yasaklar.")
@app_commands.default_permissions(ban_members=True)
async def ban_komutu(interaction: discord.Interaction, member: discord.Member, sebep: str = "Sebep belirtilmedi"):
    await interaction.response.defer(ephemeral=True)
    try:
        await member.ban(reason=sebep)
        await interaction.followup.send(f"✅ **{member.name}** başarıyla banlandı.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Ban işlemi gerçekleştirilemedi: {e}", ephemeral=True)

@bot.tree.command(name="kick", description="Belirtilen kullanıcıyı sunucudan atar.")
@app_commands.default_permissions(kick_members=True)
async def kick_komutu(interaction: discord.Interaction, member: discord.Member, sebep: str = "Sebep belirtilmedi"):
    await interaction.response.defer(ephemeral=True)
    try:
        await member.kick(reason=sebep)
        await interaction.followup.send(f"👢 **{member.name}** sunucudan atıldı.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Kick işlemi gerçekleştirilemedi: {e}", ephemeral=True)

@bot.tree.command(name="timeout", description="Kullanıcıya süreli kısıtlama getirir.")
@app_commands.default_permissions(moderate_members=True)
async def timeout_komutu(interaction: discord.Interaction, member: discord.Member, dakika: int, sebep: str = "Belirtilmedi"):
    await interaction.response.defer(ephemeral=True)
    try:
        sure_hesaplama = timedelta(minutes=dakika)
        await member.timeout(sure_hesaplama, reason=sebep)
        await interaction.followup.send(f"🔇 {member.mention} kullanıcısına {dakika} dakika süreyle timeout uygulandı.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Timeout işleminde hata: {e}", ephemeral=True)

@bot.tree.command(name="konus", description="Yazdığınız metni ses kanalında okutur.")
async def konus_tts_komutu(interaction: discord.Interaction, metin: str):
    if not interaction.user.voice:
        await interaction.response.send_message("❌ Bu komutu kullanabilmek için önce bir ses kanalına bağlanmalısınız!", ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)
    try:
        voice_kanal_hedef = interaction.user.voice.channel
        tts_generator = gTTS(text=metin, lang='tr')
        dosya_adi = "winterfall_tts_audio.mp3"
        tts_generator.save(dosya_adi)
        
        if not interaction.guild.voice_client:
            voice_client_baglanti = await voice_kanal_hedef.connect()
        else:
            voice_client_baglanti = interaction.guild.voice_client

        if voice_client_baglanti.is_playing():
            voice_client_baglanti.stop()

        def ses_bitti_callback(error_param):
            if os.path.exists(dosya_adi):
                try:
                    os.remove(dosya_adi)
                except Exception as file_err:
                    logger.error(f"TTS dosya silme hatası: {file_err}")

        audio_source = discord.FFmpegPCMAudio(dosya_adi)
        voice_client_baglanti.play(audio_source, after=ses_bitti_callback)
        
        await interaction.followup.send("🔊 Metniniz sese dönüştürülüyor...", ephemeral=True)
    except Exception as tts_err:
        logger.error(f"TTS komut işleme hatası: {tts_err}")
        await interaction.followup.send("❌ Ses çalınırken bir hata oluştu.", ephemeral=True)

# ==========================================
# 8. ANA ÇALIŞTIRMA
# ==========================================
if __name__ == "__main__":
    logger.info("WinterFall Bot servisleri başlatılıyor...")
    
    flask_arkaplan_thread = threading.Thread(target=start_flask_server, daemon=True)
    flask_arkaplan_thread.start()
    
    DISCORD_BOT_TOKEN = os.getenv("DISCORD_TOKEN")
    
    if DISCORD_BOT_TOKEN:
        try:
            bot.run(DISCORD_BOT_TOKEN)
        except Exception as general_bot_err:
            logger.critical(f"Bot çalışırken beklenmeyen hata oluştu: {general_bot_err}")
    else:
        logger.critical("Kritik Hata: 'DISCORD_TOKEN' environment değişkeni bulunamadı!")
