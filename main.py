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
# RÜTBE HİYERARŞİSİ TANIMLAMALARI (Co-Mayor ve Mayor Dahil)
# ==========================================
RANK_HIERARCHY = [
    "❄ Winterfall Ekip",
    "❄ Sorumlu",
    "❄ Baş Sorumlu",
    "❄ Moderatör",
    "❄ Moderatör +",
    "❄ Asistan",
    "❄ Asistan +",
    "❄ Denetleyici",
    "❄ Co-Mayor",
    "❄ Mayor" # Otomatik/Komut ile çıkılabilecek en son nokta (Founder ve üstü hariç)
]

async def update_member_rank(member: discord.Member, direction: str, kanal: discord.TextChannel = None, sebep: str = ""):
    """
    direction: 'up' veya 'down'
    """
    guild = member.guild
    member_rank_roles = [r for r in member.roles if r.name in RANK_HIERARCHY]
    
    current_index = -1
    for r in member_rank_roles:
        idx = RANK_HIERARCHY.index(r.name)
        if idx > current_index:
            current_index = idx

    target_index = current_index

    if direction == 'up':
        if current_index == -1:
            target_index = 0 
        elif current_index < len(RANK_HIERARCHY) - 1:
            target_index = current_index + 1
        else:
            return False, "Kullanıcı zaten maksimum otomatik rütbede (Mayor)."
    elif direction == 'down':
        if current_index > 0:
            target_index = current_index - 1
        else:
            return False, "Kullanıcı zaten en alt rütbede."
    else:
        return False, "Geçersiz yön."

    old_role_name = RANK_HIERARCHY[current_index] if current_index != -1 else None
    new_role_name = RANK_HIERARCHY[target_index]

    old_role_obj = discord.utils.get(guild.roles, name=old_role_name) if old_role_name else None
    new_role_obj = discord.utils.get(guild.roles, name=new_role_name)

    if not new_role_obj:
        return False, f"'{new_role_name}' rolü sunucuda bulunamadı!"

    try:
        if old_role_obj and old_role_obj in member.roles:
            await member.remove_roles(old_role_obj, reason=f"Rank {direction} işlemi.")
        await member.add_roles(new_role_obj, reason=f"Rank {direction} işlemi: {sebep}")

        if not kanal:
            kanal = discord.utils.get(guild.text_channels, name="「📈」rankup-rankdown")

        if kanal:
            embed = discord.Embed(
                title="📈 Rütbe Güncelleme Sistemi" if direction == 'up' else "📉 Rütbe Düşürme Sistemi",
                color=discord.Color.green() if direction == 'up' else discord.Color.red()
            )
            embed.add_field(name="Kullanıcı", value=member.mention, inline=False)
            embed.add_field(name="İşlem Türü", value="Terfi (Rank Up)" if direction == 'up' else "Tenzil (Rank Down)", inline=True)
            embed.add_field(name="Yeni Rütbe", value=new_role_obj.mention, inline=True)
            embed.add_field(name="Sebep / Durum", value=sebep, inline=False)
            embed.set_footer(text="WinterFall Rank Automation Systems")
            await kanal.send(embed=embed)

        return True, new_role_name
    except Exception as e:
        logger.error(f"Rol güncelleme hatası: {e}")
        return False, str(e)


# ==========================================
# 4. TİCKET SİSTEMİ (BUTONLAR VE MENÜLER)
# ==========================================
class TicketView(discord.ui.View):
    def __init__(self, ticket_sahibi_id: int):
        super().__init__(timeout=None)
        self.ticket_sahibi_id = ticket_sahibi_id

    @discord.ui.button(label="🙋‍♂️ Bileti Üstlen", style=discord.ButtonStyle.success, custom_id="persistent_ticket_ustlen_btn")
    async def ustlen_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        yetkili_rol = discord.utils.get(interaction.guild.roles, name="Ticket Yetkili")
        
        if not yetkili_rol or yetkili_rol not in interaction.user.roles:
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
            
            embed_obj = discord.Embed(
                title=f"🛠️ {secilen_kategori} Destek Talebi",
                description=f"Değerli **{interaction.user.name}**, yetkili ekibimiz en kısa süre içinde sizinle ilgilenecektir.",
                color=discord.Color.from_rgb(100, 150, 255)
            )
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
# 5. BOT EVENTLERİ (ON_READY, ON_MESSAGE, ROL LOGLAMA)
# ==========================================
YASAKLI_KELIMELER = ["küfür1", "küfür2"] # Buraya filtrelemek istediğin kelimeleri ekleyebilirsin

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
    except Exception as role_err:
        logger.error(f"Üye katılım rol verme hatası: {role_err}")

@bot.event
async def on_member_update(before, after):
    # ROL-LOG SİSTEMİ
    if before.roles != after.roles:
        try:
            rol_log_kanali = discord.utils.get(after.guild.text_channels, name="rol-log")
            if not rol_log_kanali:
                return

            eklenen_roller = [r for r in after.roles if r not in before.roles]
            silinen_roller = [r for r in before.roles if r not in after.roles]

            if eklenen_roller:
                for rol in eklenen_roller:
                    embed = discord.Embed(title="➕ Kullanıcıya Rol Verildi", color=discord.Color.green())
                    embed.add_field(name="Kullanıcı", value=after.mention, inline=False)
                    embed.add_field(name="Verilen Rol", value=rol.mention, inline=False)
                    embed.set_footer(text="WinterFall Role Log System")
                    await rol_log_kanali.send(embed=embed)

            if silinen_roller:
                for rol in silinen_roller:
                    embed = discord.Embed(title="➖ Kullanıcıdan Rol Alındı", color=discord.Color.red())
                    embed.add_field(name="Kullanıcı", value=after.mention, inline=False)
                    embed.add_field(name="Alınan Rol", value=rol.mention, inline=False)
                    embed.set_footer(text="WinterFall Role Log System")
                    await rol_log_kanali.send(embed=embed)
        except Exception as e:
            logger.error(f"Rol loglama event hatası: {e}")

@bot.event
async def on_message(message):
    if message.author.bot:
        await bot.process_commands(message)
        return

    # 1. KÜFÜR KONTROLÜ (Otomatik Rank Down)
    mesaj_icerigi_kucuk = message.content.lower()
    if any(kelime in mesaj_icerigi_kucuk for kelime in YASAKLI_KELIMELER):
        try:
            await message.delete()
            rank_kanal = discord.utils.get(message.guild.text_channels, name="「📈」rankup-rankdown")
            success, yeni_durum = await update_member_rank(
                message.author, 
                direction='down', 
                kanal=rank_kanal, 
                sebep=f"Sohbette yasaklı kelime/küfür kullanımı tespit edildi. Mesaj: ||{message.content}||"
            )
            if success:
                uyari = await message.channel.send(f"⚠️ {message.author.mention} Küfür/Yasaklı kelime kullanımı nedeniyle bir alt rütbeye düşürüldün!")
                await asyncio.sleep(5)
                await uyari.delete()
        except Exception as e:
            logger.error(f"Küfür yakalama otomatik rankdown hatası: {e}")

    # 2. PARTNER SİSTEMİ VE OTOMATİK RANK UP KONTROLÜ (12 Partner = Rank Up)
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
                    
                    sayaç_kanali = discord.utils.get(message.guild.text_channels, name="「⏳」partnerlik-sayaç")
                    if sayaç_kanali:
                        await sayaç_kanali.send(embed=log_embed)

                    if real_p >= 12:
                        rank_kanal = discord.utils.get(message.guild.text_channels, name="「📈」rankup-rankdown")
                        await update_member_rank(
                            message.author, 
                            direction='up', 
                            kanal=rank_kanal, 
                            sebep=f"Başarılı partnerlik sayısı **12** adede ulaştığı için otomatik terfi ettirildi."
                        )
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
# 6. LOG SİSTEMLERİ (MESAJ & SES)
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
            await log_kanal_bulunan.send(embed=embed_log)
    except Exception as e:
        logger.error(f"Mesaj silme loglama hatası: {e}")

@bot.event
async def on_voice_state_update(member, before_state, after_state):
    try:
        ses_log_kanali = discord.utils.get(member.guild.text_channels, name="ses-log")
        if not ses_log_kanali:
            return

        if not before_state.mute and after_state.mute:
            embed_ses = discord.Embed(title="🔇 Ses Kanalında Susturuldu", color=discord.Color.orange())
            embed_ses.add_field(name="Etkilenen Kullanıcı", value=member.mention, inline=False)
            await ses_log_kanali.send(embed=embed_ses)
    except Exception as e:
        logger.error(f"Ses loglama hatası: {e}")

# ==========================================
# 7. SLASH KOMUTLARI
# ==========================================
@bot.tree.command(name="duyuru", description="Sunucuda herkesi etiketleyerek duyuru yapar.")
@app_commands.describe(mesaj="Yapılacak duyurunun içeriği")
async def duyuru_komutu(interaction: discord.Interaction, mesaj: str):
    gerekli_rol = discord.utils.get(interaction.guild.roles, name="♱ 𝐖𝐢𝐧𝐭𝐞𝐫𝐟𝐚ල්𝐥")
    if not gerekli_rol or gerekli_rol not in interaction.user.roles:
        await interaction.response.send_message("❌ Bu komutu kullanabilmek için **♱ 𝐖𝐢𝐧𝐭𝐞𝐫𝐟𝐚ල්𝐥** rolüne sahip olmalısın!", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    try:
        embed = discord.Embed(
            title="📢 WinterFall Duyuru Sistemi",
            description=mesaj,
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Duyuruyu Yapan: {interaction.user.name}", icon_url=interaction.user.display_avatar.url)
        
        await interaction.channel.send(content="@everyone", embed=embed)
        await interaction.followup.send("✅ Duyurunuz başarıyla gönderildi!", ephemeral=True)
    except Exception as e:
        logger.error(f"Duyuru gönderme hatası: {e}")
        await interaction.followup.send("❌ Duyuru gönderilirken bir hata oluştu.", ephemeral=True)

@bot.tree.command(name="mesaj", description="Belirtilen kullanıcıya bot üzerinden özel mesaj (DM) gönderir.")
@app_commands.describe(kullanici="Mesaj gönderilecek kullanıcı", mesaj="Gönderilecek metin")
async def dm_mesaj_komutu(interaction: discord.Interaction, kullanici: discord.Member, mesaj: str):
    gerekli_rol = discord.utils.get(interaction.guild.roles, name="♱ 𝐖𝐢𝐧𝐭𝐞𝐫𝐟𝐚ල්𝐥")
    if not gerekli_rol or gerekli_rol not in interaction.user.roles:
        await interaction.response.send_message("❌ Bu komutu kullanabilmek için **♱ 𝐖𝐢𝐧𝐭𝐞𝐫𝐟𝐚ල්𝐥** rolüne sahip olmalısın!", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    try:
        dm_embed = discord.Embed(
            title="📬 WinterFall Yetkili Mesajı",
            description=mesaj,
            color=discord.Color.from_rgb(100, 200, 255)
        )
        dm_embed.set_footer(text=f"Gönderen Yetkili Sunucu: {interaction.guild.name}")

        await kullanici.send(embed=dm_embed)
        await interaction.followup.send(f"✅ **{kullanici.name}** adlı kullanıcıya başarıyla DM gönderildi.", ephemeral=True)
    except Exception as e:
        logger.error(f"DM mesaj gönderme hatası: {e}")
        await interaction.followup.send("❌ Kullanıcının DM kutusu kapalı veya bir hata oluştu.", ephemeral=True)

@bot.tree.command(name="ticket-kur", description="Destek sistem panelini gönderir.")
@app_commands.default_permissions(administrator=True)
async def ticket_kurulum_komutu(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    panel_embed = discord.Embed(
        title="❄️ WinterFall Profesyonel Destek & Talep Merkezi",
        description="Aşağıdaki menüden destek talebi oluşturabilirsiniz.",
        color=discord.Color.from_rgb(88, 101, 242)
    )
    await interaction.channel.send(embed=panel_embed, view=TicketMainView())
    await interaction.followup.send("✅ Panel kuruldu!", ephemeral=True)

@bot.tree.command(name="rankup", description="Belirtilen kullanıcının rütbesini artırır.")
@app_commands.describe(kullanici="Seviyesi artırılacak kullanıcı")
async def rankup_komutu(interaction: discord.Interaction, kullanici: discord.Member):
    hedef_kanal_adi = "「📈」rankup-rankdown"
    if interaction.channel.name != hedef_kanal_adi:
        await interaction.response.send_message(f"❌ Bu komut sadece **{hedef_kanal_adi}** kanalında kullanılabilir!", ephemeral=True)
        return

    gerekli_rol = discord.utils.get(interaction.guild.roles, name="♱ 𝐖𝐢𝐧𝐭𝐞𝐫𝐟𝐚ල්𝐥")
    if not gerekli_rol or gerekli_rol not in interaction.user.roles:
        await interaction.response.send_message("❌ Bu komutu kullanabilmek için **♱ 𝐖𝐢𝐧𝐭𝐞𝐫𝐟𝐚ල්𝐥** rolüne sahip olmalısın!", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    rank_kanal = discord.utils.get(interaction.guild.text_channels, name=hedef_kanal_adi)
    success, result_msg = await update_member_rank(kullanici, direction='up', kanal=rank_kanal, sebep=f"Yetkili komutu ile ({interaction.user}) manuel terfi ettirildi.")

    if success:
        await interaction.followup.send(f"✅ {kullanici.mention} başarıyla üst rütbeye terfi ettirildi: **{result_msg}**", ephemeral=True)
    else:
        await interaction.followup.send(f"❌ İşlem başarısız: {result_msg}", ephemeral=True)

@bot.tree.command(name="rankdown", description="Belirtilen kullanıcının rütbesini düşürür.")
@app_commands.describe(kullanici="Seviyesi düşürülecek kullanıcı")
async def rankdown_komutu(interaction: discord.Interaction, kullanici: discord.Member):
    hedef_kanal_adi = "「📈」rankup-rankdown"
    if interaction.channel.name != hedef_kanal_adi:
        await interaction.response.send_message(f"❌ Bu komut sadece **{hedef_kanal_adi}** kanalında kullanılabilir!", ephemeral=True)
        return

    gerekli_rol = discord.utils.get(interaction.guild.roles, name="♱ 𝐖𝐢𝐧𝐭𝐞𝐫𝐟𝐚ල්𝐥")
    if not gerekli_rol or gerekli_rol not in interaction.user.roles:
        await interaction.response.send_message("❌ Bu komutu kullanabilmek için **♱ 𝐖𝐢𝐧𝐭𝐞𝐫𝐟𝐚ල්𝐥** rolüne sahip olmalısın!", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    rank_kanal = discord.utils.get(interaction.guild.text_channels, name=hedef_kanal_adi)
    success, result_msg = await update_member_rank(kullanici, direction='down', kanal=rank_kanal, sebep=f"Yetkili komutu ile ({interaction.user}) manuel rütbesi düşürüldü.")

    if success:
        await interaction.followup.send(f"✅ {kullanici.mention} rütbesi düşürüldü. Güncel rütbe: **{result_msg}**", ephemeral=True)
    else:
        await interaction.followup.send(f"❌ İşlem başarısız: {result_msg}", ephemeral=True)

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
