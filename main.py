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
            
            conn.commit()
            logger.info("Veritabanı tabloları başarıyla oluşturuldu ve doğrulandı.")
        except sqlite3.Error as err:
            logger.error(f"Tablo oluşturma sırasında hata: {err}")
        finally:
            conn.close()

initialize_database_structure()

# ==========================================
# 4. TİCKET SİSTEMİ (BUTONLAR, MENÜLER VE YENİ SORULAR)
# ==========================================
class TicketKapatView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

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

            if secilen_kategori == "Ekip Alım":
                embed_obj = discord.Embed(
                    title="📥 Ekip Alım Başvuru Talebi",
                    description="Ekibimize katılmak istiyorsan harika! Lütfen aşağıdaki soruları yanıtla:",
                    color=discord.Color.from_rgb(0, 200, 255)
                )
                embed_obj.add_field(name="Sorular", value="1. Eski ekibin neresi?\n2. Oyun içi ismin?\n3. Hangi sunucularda oynuyorsun?", inline=False)
                embed_obj.set_footer(text="WinterFall Ekip Alım Sistemleri")
                await interaction.response.send_message(f"Destek kanalınız oluşturuldu: {ticket_channel.mention}", ephemeral=True)
                await ticket_channel.send(content=birlesik_etiket, embed=embed_obj, view=TicketKapatView())

            elif secilen_kategori == "Merge":
                embed_obj = discord.Embed(
                    title="🔗 Merge (Birleşim) Teklif Talebi",
                    description="Sunucu birleşim teklifiniz için teşekkürler. Lütfen aşağıdaki bilgileri sağlayın:",
                    color=discord.Color.from_rgb(150, 50, 250)
                )
                embed_obj.add_field(name="Sorular", value="1. Kim kime katılcak?\n2. Sunucunuzun üye sayısı ve aktifliği nedir?\n3. Hangi sunucularda oynuyorsunuz?", inline=False)
                embed_obj.set_footer(text="WinterFall Merge Systems")
                await interaction.response.send_message(f"Destek kanalınız oluşturuldu: {ticket_channel.mention}", ephemeral=True)
                await ticket_channel.send(content=birlesik_etiket, embed=embed_obj, view=TicketKapatView())

            elif secilen_kategori == "Partnerlik":
                embed_obj = discord.Embed(
                    title="💖 Partnerlik Başvuru Talebi",
                    description="Aramıza katılmak için sunucuya gelip ticket açmanız yeterli.",
                    color=discord.Color.from_rgb(255, 105, 180)
                )
                embed_obj.add_field(name="Talep Eden", value=interaction.user.mention, inline=True)
                embed_obj.add_field(name="Durum", value="İnceleniyor", inline=True)
                embed_obj.set_footer(text="WinterFall Partner Systems")

                await interaction.response.send_message(f"Destek kanalınız oluşturuldu: {ticket_channel.mention}", ephemeral=True)
                await ticket_channel.send(content=birlesik_etiket, embed=embed_obj, view=TicketKapatView())
                
                partnerlik_metni_icerigi = (
                    "📢 Winterfall 𝐓𝐎𝐏𝐋𝐔𝐋𝐔𝐆̆𝐔 𝐍𝐄𝐃𝐈𝐑?\n\n"
                    "⚔️ 𝐀𝐤𝐭𝐢𝐟 & 𝐒𝐚𝐦𝐢𝐦𝐢 𝐄𝐤𝐢𝐩\n"
                    "🛡️ 𝐒𝐚𝐯𝐚𝐬̧𝐥𝐚𝐫𝐝𝐚 𝐘𝐚𝐫𝐝𝐢𝐦 & 𝐃𝐞𝐬𝐭𝐞𝐤\n"
                    "🔗 𝐌𝐞𝐫𝐠𝐞 𝐓𝐞𝐤𝐥𝐢𝐟𝐥𝐞𝐫𝐢𝐧𝐞 𝐀𝐜̧𝐢𝐠̆𝐢𝐳\n"
                    "📥 𝐄𝐤𝐢𝐩 𝐀𝐥𝐢𝐦𝐥𝐚𝐫𝐢 𝐀𝐤𝐭𝐢𝐟\n"
                    "🎮 𝐅𝐚𝐫𝐤𝐥𝐢 𝐎𝐲𝐮𝐧𝐥𝐚𝐫 – 𝐎𝐲𝐮𝐧 𝐀𝐫𝐤𝐚𝐝𝐚𝐬̧𝐢 𝐁𝐮𝐥𝐚𝐛𝐢𝐥𝐢𝐫siniz\n"
                    "🤝 𝐒𝐚𝐦𝐢𝐦𝐢 & 𝐃𝐨𝐬𝐭𝐚𝐧𝐞 𝐎𝐫𝐭𝐚𝐦\n\n"
                    "🔥 Winterfall – 𝐁𝐢𝐫𝐥𝐢𝐤𝐭𝐞 𝐆𝐮̈𝐜̧𝐥𝐮̈𝐲𝐮̈𝐳!\n\n"
                    "Aramıza katılmak için sunucuya gelip ticket açmanız yeterli\n"
                    "https://discord.gg/NgfQafxkDV"
                )
                await ticket_channel.send(partnerlik_metni_icerigi)

            elif secilen_kategori == "Ally":
                embed_obj = discord.Embed(
                    title="🤝 Ally (Müttefik) Başvuru Talebi",
                    description="Ally olmak için aşağıdaki bilgileri paylaşabilirsiniz:",
                    color=discord.Color.from_rgb(50, 205, 50)
                )
                embed_obj.add_field(name="Sorular", value="1. Sunucu davet linkiniz nedir?\n2. Sunucu üye ve aktiflik durumunuz?\n3. Hangi sunucularda oynuyorsunuz?", inline=False)
                embed_obj.set_footer(text="WinterFall Ally Systems")
                await interaction.response.send_message(f"Destek kanalınız oluşturuldu: {ticket_channel.mention}", ephemeral=True)
                await ticket_channel.send(content=birlesik_etiket, embed=embed_obj, view=TicketKapatView())

            else:  # Genel Destek
                embed_obj = discord.Embed(
                    title="🛠️ Genel Destek Talebi",
                    description=f"Değerli **{interaction.user.name}**, yetkili ekibimiz en kısa süre içinde sizinle ilgilenecektir.\n\nLütfen sorununuzu veya talebinizi detaylı bir şekilde yazın.",
                    color=discord.Color.from_rgb(100, 150, 255)
                )
                embed_obj.add_field(name="Oluşturan Kullanıcı", value=interaction.user.mention, inline=False)
                embed_obj.set_footer(text="WinterFall Support & Security")

                await interaction.response.send_message(f"Destek kanalınız oluşturuldu: {ticket_channel.mention}", ephemeral=True)
                await ticket_channel.send(content=birlesik_etiket, embed=embed_obj, view=TicketKapatView())
                
        except Exception as err:
            logger.error(f"Ticket oluşturma callback hatası: {err}")

class TicketMainView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelectMenu())

# ==========================================
# 5. BOT EVENTLERİ (ON_READY & ON_MEMBER_JOIN)
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

# ==========================================
# 6. Kapsamlı LOG SİSTEMLERİ
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
            embed_log.add_field(name="Silinen İçerik", value=message.content or "*(Metin içeriği yok veya dosya/görsel)*", inline=False)
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

@bot.tree.command(name="ticket-kur", description="Destek (Ticket) sistem panelini geniş ve şık bir şekilde kurulacak kanala gönderir.")
@app_commands.default_permissions(administrator=True)
async def ticket_kurulum_komutu(interaction: discord.Interaction):
    try:
        panel_embed = discord.Embed(
            title="❄️ WinterFall Profesyonel Destek & Talep Merkezi",
            description=(
                "Sunucumuzda herhangi bir konuda yardıma mı ihtiyacınız var?\n"
                "Aşağıdaki kategori menüsünü kullanarak hızlı bir şekilde destek talebi (ticket) oluşturabilirsiniz.\n\n"
                "📥 **Ekip Alım:** Ekibimize katılmak için başvuru.\n"
                "🔗 **Merge:** Sunucu birleşim / merge teklifleri.\n"
                "💖 **Partnerlik:** Sunucu ortaklık ve iş birliği başvuruları.\n"
                "🤝 **Ally:** Müttefik (Ally) başvuru işlemleri.\n"
                "🛠️ **Genel Destek:** Genel teknik ve sunucu içi yardımlar."
            ),
            color=discord.Color.from_rgb(88, 101, 242)
        )
        panel_embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)
        panel_embed.add_field(name="Kurallar", value="Lütfen gereksiz yere ticket açmaktan kaçınınız.", inline=False)
        panel_embed.set_footer(text="WinterFall Security & Support Systems • Tüm hakları saklıdır.", icon_url=interaction.client.user.display_avatar.url)
        
        await interaction.channel.send(embed=panel_embed, view=TicketMainView())
        await interaction.response.send_message("✅ Geliştirilmiş ticket paneli bu kanalda başarıyla aktif edildi!", ephemeral=True)
    except Exception as e:
        logger.error(f"Ticket kurulum komutu hatası: {e}")

@bot.tree.command(name="ban", description="Belirtilen kullanıcıyı sunucudan kalıcı olarak yasaklar.")
@app_commands.default_permissions(ban_members=True)
async def ban_komutu(interaction: discord.Interaction, member: discord.Member, sebep: str = "Sebep belirtilmedi"):
    try:
        await member.ban(reason=sebep)
        await interaction.response.send_message(f"✅ **{member.name}** başarıyla banlandı.", ephemeral=True)
        
        mod_log_kanali = discord.utils.get(interaction.guild.text_channels, name="moderasyon-log")
        if mod_log_kanali:
            ban_embed = discord.Embed(title="🔨 Kullanıcı Sunucudan Yasaklandı (Ban)", color=discord.Color.red())
            ban_embed.add_field(name="Yasaklanan Kişi", value=member.mention, inline=True)
            ban_embed.add_field(name="İşlemi Yapan Yetkili", value=interaction.user.mention, inline=True)
            ban_embed.add_field(name="Sebep", value=sebep, inline=False)
            await mod_log_kanali.send(embed=ban_embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ Ban işlemi gerçekleştirilemedi: {e}", ephemeral=True)

@bot.tree.command(name="kick", description="Belirtilen kullanıcıyı sunucudan atar.")
@app_commands.default_permissions(kick_members=True)
async def kick_komutu(interaction: discord.Interaction, member: discord.Member, sebep: str = "Sebep belirtilmedi"):
    try:
        await member.kick(reason=sebep)
        await interaction.response.send_message(f"👢 **{member.name}** sunucudan atıldı.", ephemeral=True)
        
        mod_log_kanali = discord.utils.get(interaction.guild.text_channels, name="moderasyon-log")
        if mod_log_kanali:
            kick_embed = discord.Embed(title="👢 Kullanıcı Sunucudan Atıldı (Kick)", color=discord.Color.orange())
            kick_embed.add_field(name="Atılan Kişi", value=member.mention, inline=True)
            kick_embed.add_field(name="İşlemi Yapan Yetkili", value=interaction.user.mention, inline=True)
            kick_embed.add_field(name="Sebep", value=sebep, inline=False)
            await mod_log_kanali.send(embed=kick_embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ Kick işlemi gerçekleştirilemedi: {e}", ephemeral=True)

@bot.tree.command(name="timeout", description="Kullanıcıya süreli ses/mesaj yazma kısıtlaması getirir.")
@app_commands.default_permissions(moderate_members=True)
async def timeout_komutu(interaction: discord.Interaction, member: discord.Member, dakika: int, sebep: str = "Belirtilmedi"):
    try:
        sure_hesaplama = timedelta(minutes=dakika)
        await member.timeout(sure_hesaplama, reason=sebep)
        await interaction.response.send_message(f"🔇 {member.mention} kullanıcısına {dakika} dakika süreyle timeout uygulandı.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Timeout işleminde hata: {e}", ephemeral=True)

@bot.tree.command(name="rankup", description="Bir kullanıcının derecesini yükseltir.")
async def rankup_komutu(interaction: discord.Interaction, member: discord.Member):
    if interaction.channel.name != "📈rankup-rankdown":
        await interaction.response.send_message("❌ Bu komut sadece `📈rankup-rankdown` kanalında kullanılabilir!", ephemeral=True)
        return
    await interaction.response.send_message(f"⭐ {member.mention} adlı üye için rank yükseltme işlemi başarıyla tamamlandı!")

@bot.tree.command(name="rankdown", description="Bir kullanıcının derecesini düşürür.")
async def rankdown_komutu(interaction: discord.Interaction, member: discord.Member):
    if interaction.channel.name != "📈rankup-rankdown":
        await interaction.response.send_message("❌ Bu komut sadece `📈rankup-rankdown` kanalında kullanılabilir!", ephemeral=True)
        return
    await interaction.response.send_message(f"⚠️ {member.mention} adlı üye için rank düşürme işlemi uygulandı!")

@bot.tree.command(name="çekiliş", description="Sunucuda yeni bir ödüllü çekiliş başlatır.")
@app_commands.default_permissions(administrator=True)
async def cekilis_baslat_komutu(interaction: discord.Interaction, sure_dakika: int, odul: str):
    try:
        cekilis_embed = discord.Embed(
            title="🎉 YEPYENİ BİR ÇEKİLİŞ BAŞLADI! 🎉",
            description=f"Kazanılacak Ödül: **{odul}**\nSüre: **{sure_dakika} dakika**\n\nKatılım sağlamak için hemen aşağıdaki 🎉 emojisine tıklayın!",
            color=discord.Color.gold()
        )
        cekilis_embed.set_footer(text="WinterFall Giveaways")
        
        await interaction.response.send_message("Çekiliş paneli başarıyla oluşturuldu!", ephemeral=True)
        mesaj_objesi = await interaction.channel.send(embed=cekilis_embed)
        await mesaj_objesi.add_reaction("🎉")
    except Exception as e:
        logger.error(f"Çekiliş başlatma hatası: {e}")

@bot.tree.command(name="konus", description="Yazdığınız metni o an bulunduğunuz ses kanalında sesli olarak okutur.")
async def konus_tts_komutu(interaction: discord.Interaction, metin: str):
    try:
        if not interaction.user.voice:
            await interaction.response.send_message("❌ Bu komutu kullanabilmek için önce bir ses kanalına bağlanmalısınız!", ephemeral=True)
            return
        
        voice_kanal_hedef = interaction.user.voice.channel
        await interaction.response.send_message("🔊 Metniniz sese dönüştürülüyor...", ephemeral=True)
        
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
        
    except Exception as tts_err:
        logger.error(f"TTS komut işleme hatası: {tts_err}")

# ==========================================
# 8. ANA ÇALIŞTIRMA VE BAŞLATICI BLOK
# ==========================================
if __name__ == "__main__":
    logger.info("WinterFall Bot servisleri başlatılıyor...")
    
    flask_arkaplan_thread = threading.Thread(target=start_flask_server, daemon=True)
    flask_arkaplan_thread.start()
    logger.info("Flask 7/24 web sunucusu arka planda tetiklendi.")
    
    DISCORD_BOT_TOKEN = os.getenv("DISCORD_TOKEN")
    
    if DISCORD_BOT_TOKEN:
        try:
            bot.run(DISCORD_BOT_TOKEN)
        except discord.LoginFailure:
            logger.critical("Kritik Hata: Girdiğiniz DISCORD_TOKEN geçersiz veya hatalı!")
        except Exception as general_bot_err:
            logger.critical(f"Bot çalışırken beklenmeyen hata oluştu: {general_bot_err}")
    else:
        logger.critical("Kritik Hata: 'DISCORD_TOKEN' environment değişkeni bulunamadı!")
