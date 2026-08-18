import os
import threading
import asyncio
import discord
from discord import app_commands
from discord.ext import commands
from flask import Flask

# --- MİNİ FLASK SUNUCUSU (Render Port Uyarısını Çözmek İçin) ---
app = Flask(__name__)


@app.route("/")
def home():
  return "Vlandia Pro Bot aktif ve çalışıyor! 🚀"


def run_flask():
  port = int(os.environ.get("PORT", 8080))
  app.run(host="0.0.0.0", port=port)


# --- BOT TANIMLAMALARI ---
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# ID Tanımlamaları
TICKET_CHANNEL_ID = 1538271588254875740  # Komutun atılacağı kanal ID'si
TICKET_CATEGORY_ID = 1538271572295688262  # Ticket'ların açılacağı kategori ID'si
STAFF_ROLE_ID = 1538271541781987449  # Etiketlenecek Yetkili Rol ID'si
LOG_CHANNEL_ID = 1538982916087095296  # Log Kanalı ID'si


# --- YARDIMCI LOG FONKSİYONU ---
async def send_log(guild: discord.Guild, embed: discord.Embed):
  log_channel = guild.get_channel(LOG_CHANNEL_ID)
  if log_channel:
    try:
      await log_channel.send(embed=embed)
    except Exception as e:
      print(f"Log gönderilemedi: {e}")


# --- TICKET KAPATMA BUTONU ---
class TicketCloseView(discord.ui.View):

  def __init__(self):
    super().__init__(timeout=None)

  @discord.ui.button(
      label="Ticket'ı Kapat",
      style=discord.ButtonStyle.danger,
      emoji="🔒",
      custom_id="ticket_close",
  )
  async def close_button(
      self, interaction: discord.Interaction, button: discord.ui.Button
  ):
    await interaction.response.send_message(
        "🔒 Bu kanal 5 saniye içinde kapatılıyor...", ephemeral=False
    )
    await asyncio.sleep(5)
    await interaction.channel.delete()


# --- TICKET AÇMA BUTONLARI VE GÖRÜNÜMÜ ---
class TicketView(discord.ui.View):

  def __init__(self):
    super().__init__(timeout=None)

  @discord.ui.button(
      label="Partnerlik",
      style=discord.ButtonStyle.secondary,
      emoji="🤝",
      custom_id="ticket_partner",
  )
  async def partner_button(
      self, interaction: discord.Interaction, button: discord.ui.Button
  ):
    await self.create_ticket_channel(interaction, "Partnerlik")

  @discord.ui.button(
      label="Genel Destek",
      style=discord.ButtonStyle.primary,
      emoji="🎫",
      custom_id="ticket_genel",
  )
  async def genel_button(
      self, interaction: discord.Interaction, button: discord.ui.Button
  ):
    await self.create_ticket_channel(interaction, "Genel Destek")

  @discord.ui.button(
      label="Pack Ekleme",
      style=discord.ButtonStyle.primary,
      emoji="📦",
      custom_id="ticket_pack",
  )
  async def pack_button(
      self, interaction: discord.Interaction, button: discord.ui.Button
  ):
    await self.create_ticket_channel(interaction, "Pack Ekleme")

  @discord.ui.button(
      label="Yetkili Alım",
      style=discord.ButtonStyle.secondary,
      emoji="🤍",
      custom_id="ticket_yetkili",
  )
  async def yetkili_button(
      self, interaction: discord.Interaction, button: discord.ui.Button
  ):
    await self.create_ticket_channel(interaction, "Yetkili Alım")

  async def create_ticket_channel(
      self, interaction: discord.Interaction, category_type: str
  ):
    guild = interaction.guild
    ticket_category = guild.get_channel(TICKET_CATEGORY_ID)

    safe_name = "".join(
        c for c in interaction.user.name if c.isalnum()
    ).lower()
    channel_name = f"ticket-{safe_name}"

    existing_channel = discord.utils.get(guild.text_channels, name=channel_name)
    if existing_channel:
      await interaction.response.send_message(
          f"Zaten açık olan bir ticket kanalın bulunuyor: {existing_channel.mention}",
          ephemeral=True,
      )
      return

    staff_role = guild.get_role(STAFF_ROLE_ID)
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        interaction.user: discord.PermissionOverwrite(
            read_messages=True, send_messages=True, attach_files=True
        ),
    }
    if staff_role:
      overwrites[staff_role] = discord.PermissionOverwrite(
          read_messages=True, send_messages=True, attach_files=True
      )

    ticket_channel = await guild.create_text_channel(
        name=channel_name,
        category=(
            ticket_category
            if isinstance(ticket_category, discord.CategoryChannel)
            else None
        ),
        overwrites=overwrites,
    )

    embed = discord.Embed(
        title=f"Vlandia Pack | {category_type} Destek Talebi",
        description=(
            f"Hoş geldin {interaction.user.mention}! 🚀\n\n"
            f"**{category_type}** ile ilgili talebin başarıyla alındı. Lütfen"
            " sorununuzu veya talebinizi detaylı bir şekilde açıklayın,"
            " yetkili ekibimiz en kısa sürede sizinle ilgilenecektir.\n\n"
            "⚠️ *Gereksiz yere ticket açmak cezai işlem sebebi olabilir.*"
        ),
        color=discord.Color.from_rgb(43, 45, 49),
    )
    embed.set_author(
        name="Vlandia Pro Bot • Güvenli Destek",
        icon_url=guild.icon.url if guild.icon else None,
    )
    embed.set_footer(
        text="Vlandia Pack © 2026",
        icon_url=(
            interaction.client.user.avatar.url
            if interaction.client.user.avatar
            else None
        ),
    )

    role_ping = f"<@&{STAFF_ROLE_ID}>" if staff_role else "@everyone"
    await ticket_channel.send(
        content=f"{interaction.user.mention} | {role_ping}",
        embed=embed,
        view=TicketCloseView(),
    )

    await interaction.response.send_message(
        f"✅ Destek kanalın başarıyla oluşturuldu: {ticket_channel.mention}",
        ephemeral=True,
    )


# --- SLASH KOMUTU ---
@bot.tree.command(
    name="ticket_kur",
    description="Harika görünümlü çoklu seçenekli ticket panelini kurar.",
)
@app_commands.checks.has_permissions(administrator=True)
async def ticket_kur(interaction: discord.Interaction):
  if interaction.channel.id != TICKET_CHANNEL_ID:
    await interaction.response.send_message(
        "❌ Bu komut sadece **🎟️-𝐓𝐢𝐜𝐤𝐞𝐭** kanalında kullanılabilir!",
        ephemeral=True,
    )
    return

  embed = discord.Embed(
      title="Vlandia Pack | Destek & İletişim",
      description=(
          "Sunucumuzla ilgili her türlü soru, sorun, öneri veya işlemleriniz"
          " için aşağıdaki butonları kullanarak bir destek talebi"
          " oluşturabilirsiniz.\n\n"
          "💎 **Kategoriler:**\n"
          "• 🤝 **Partnerlik**\n"
          "• 🎫 **Genel Destek**\n"
          "• 📦 **Pack Ekleme**\n"
          "• 🤍 **Yetkili Alım**\n\n"
          "*Lütfen gereksiz yere ticket açmaktan kaçınınız.*"
      ),
      color=discord.Color.from_rgb(30, 31, 34),
  )
  embed.set_author(
      name="Vlandia Pack Destek Sistemi",
      icon_url=interaction.guild.icon.url if interaction.guild.icon else None,
  )
  embed.set_footer(
      text="Powered by Ohrid & Vlandia Pro Bot",
      icon_url=(
          interaction.client.user.avatar.url
          if interaction.client.user.avatar
          else None
      ),
  )

  await interaction.channel.send(embed=embed, view=TicketView())
  await interaction.response.send_message(
      "✨ Ticket Paneli bu kanalda başarıyla kuruldu!", ephemeral=True
  )


# ==========================================
# 🦅 GELİŞMİŞ KUŞ UÇURMAYAN LOG SİSTEMİ
# ==========================================


# 1. Mesaj Silindiğinde (Kim Sildi Tespiti ile)
@bot.event
async def on_message_delete(message):
  if message.author.bot or not message.guild:
    return

  deleter = "Bilinmiyor (Kendi silmiş olabilir)"
  try:
    async for entry in message.guild.audit_logs(
        limit=1, action=discord.AuditLogAction.message_delete
    ):
      # Hedef veya zaman kontrolüyle eşleştirme yapılabilir
      if (
          entry.target
          and entry.target.id == message.author.id
          and (discord.utils.utcnow() - entry.created_at).total_seconds() < 5
      ):
        deleter = entry.user.mention
        break
  except Exception:
    pass

  embed = discord.Embed(
      title="🗑️ Mesaj Silindi",
      description=(
          f"**Kanal:** {message.channel.mention}\n**Mesaj Sahibi:**"
          f" {message.author.mention}\n**İşlemi Yapan (Silen):**"
          f" {deleter}\n**Silinen İçerik:**\n```"
          f"{message.content or 'İçerik yok (Fotoğraf/Embed)'}```"
      ),
      color=discord.Color.red(),
  )
  embed.set_footer(text=f"Kullanıcı ID: {message.author.id}")
  await send_log(message.guild, embed)


# 2. Mesaj Düzenlendiğinde
@bot.event
async def on_message_edit(before, after):
  if before.author.bot or not before.guild or before.content == after.content:
    return
  embed = discord.Embed(
      title="✏️ Mesaj Düzenlendi",
      description=(
          f"**Kanal:** {before.channel.mention}\n**İşlem Yapan (Kullanıcı):**"
          f" {before.author.mention}\n\n**Eski Hali:**\n```"
          f"{before.content}```\n**Yeni Hali:**\n```{after.content}```"
      ),
      color=discord.Color.orange(),
  )
  embed.set_footer(text=f"Kullanıcı ID: {before.author.id}")
  await send_log(before.guild, embed)


# 3. Sunucuya Üye Katıldığında
@bot.event
async def on_member_join(member):
  embed = discord.Embed(
      title="📥 Sunucuya Biri Katıldı",
      description=(
          f"**İşlem Gören Üye:** {member.mention} (`{member.name}`)\n**Hesap"
          f" Kuruluş:** {member.created_at.strftime('%d-%m-%Y %H:%M:%S')}"
      ),
      color=discord.Color.green(),
  )
  embed.set_thumbnail(
      url=member.avatar.url if member.avatar else member.default_avatar.url
  )
  embed.set_footer(text=f"Kullanıcı ID: {member.id}")
  await send_log(member.guild, embed)


# 4. Sunucudan Üye Ayrıldığında
@bot.event
async def on_member_remove(member):
  embed = discord.Embed(
      title="📤 Sunucudan Biri Ayrıldı",
      description=f"**İşlem Gören Üye:** {member.mention} (`{member.name}`)",
      color=discord.Color.dark_red(),
  )
  embed.set_thumbnail(
      url=member.avatar.url if member.avatar else member.default_avatar.url
  )
  embed.set_footer(text=f"Kullanıcı ID: {member.id}")
  await send_log(member.guild, embed)


# 5. Kanal Oluşturulduğunda (Kim Yaptı Tespiti)
@bot.event
async def on_guild_channel_create(channel):
  creator = "Bilinmiyor"
  try:
    async for entry in channel.guild.audit_logs(
        limit=1, action=discord.AuditLogAction.channel_create
    ):
      if entry.target.id == channel.id:
        creator = entry.user.mention
        break
  except Exception:
    pass

  embed = discord.Embed(
      title="➕ Kanal Oluşturuldu",
      description=(
          f"**Kanal Adı:** `{channel.name}`\n**Tür:**"
          f" `{channel.type}`\n**İşlemi Yapan:** {creator}"
      ),
      color=discord.Color.blue(),
  )
  await send_log(channel.guild, embed)


# 6. Kanal Silindiğinde
@bot.event
async def on_guild_channel_delete(channel):
  deleter = "Bilinmiyor"
  try:
    async for entry in channel.guild.audit_logs(
        limit=1, action=discord.AuditLogAction.channel_delete
    ):
      if entry.target.id == channel.id:
        deleter = entry.user.mention
        break
  except Exception:
    pass

  embed = discord.Embed(
      title="➖ Kanal Silindi",
      description=(
          f"**Kanal Adı:** `{channel.name}`\n**İşlemi Yapan:** {deleter}"
      ),
      color=discord.Color.dark_blue(),
  )
  await send_log(channel.guild, embed)


# 7. Rol Oluşturulduğunda
@bot.event
async def on_guild_role_create(role):
  creator = "Bilinmiyor"
  try:
    async for entry in role.guild.audit_logs(
        limit=1, action=discord.AuditLogAction.role_create
    ):
      if entry.target.id == role.id:
        creator = entry.user.mention
        break
  except Exception:
    pass

  embed = discord.Embed(
      title="✨ Rol Oluşturuldu",
      description=f"**Rol Adı:** `{role.name}`\n**İşlemi Yapan:** {creator}",
      color=discord.Color.gold(),
  )
  await send_log(role.guild, embed)


# 8. Rol Silindiğinde
@bot.event
async def on_guild_role_delete(role):
  deleter = "Bilinmiyor"
  try:
    async for entry in role.guild.audit_logs(
        limit=1, action=discord.AuditLogAction.role_delete
    ):
      if entry.target.id == role.id:
        deleter = entry.user.mention
        break
  except Exception:
    pass

  embed = discord.Embed(
      title="❌ Rol Silindi",
      description=f"**Rol Adı:** `{role.name}`\n**İşlemi Yapan:** {deleter}",
      color=discord.Color.dark_gold(),
  )
  await send_log(role.guild, embed)


# 9. Ses Kanalı Hareketleri
@bot.event
async def on_voice_state_update(member, before, after):
  if member.bot:
    return

  if before.channel is None and after.channel is not None:
    embed = discord.Embed(
        title="🔊 Ses Kanalına Katıldı",
        description=(
            f"**Üye (İşlem Gören):** {member.mention}\n**Kanal:**"
            f" **{after.channel.name}**"
        ),
        color=discord.Color.teal(),
    )
    await send_log(member.guild, embed)
  elif before.channel is not None and after.channel is None:
    embed = discord.Embed(
        title="🔇 Ses Kanalından Ayrıldı",
        description=(
            f"**Üye (İşlem Gören):** {member.mention}\n**Kanal:**"
            f" **{before.channel.name}**"
        ),
        color=discord.Color.dark_teal(),
    )
    await send_log(member.guild, embed)
  elif (
      before.channel != after.channel
      and before.channel is not None
      and after.channel is not None
  ):
    embed = discord.Embed(
        title="🔀 Ses Kanalı Değiştirdi",
        description=(
            f"**Üye (İşlem Gören):** {member.mention}\n**Eski Kanal:**"
            f" **{before.channel.name}** ➡️ **Yeni Kanal:**"
            f" **{after.channel.name}**"
        ),
        color=discord.Color.blurple(),
    )
    await send_log(member.guild, embed)


# --- ON READY ---
@bot.event
async def on_ready():
  bot.add_view(TicketView())
  bot.add_view(TicketCloseView())
  print(
      f"{bot.user} olarak giriş yapıldı ve log sistemi işlem yapan/gören"
      " detaylarıyla aktif!"
  )
  try:
    synced = await bot.tree.sync()
    print(f"Synced {len(synced)} command(s).")
  except Exception as e:
    print(e)


# --- ANA ÇALIŞTIRMA BLOĞU ---
if __name__ == "__main__":
  flask_thread = threading.Thread(target=run_flask)
  flask_thread.start()
  bot.run(os.environ.get("DISCORD_TOKEN"))
