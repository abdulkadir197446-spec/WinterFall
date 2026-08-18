import os
import threading
import asyncio
import io
import re
import random
from datetime import datetime, timedelta
import discord
from discord import app_commands
from discord.ext import commands
from flask import Flask
from easy_pil import Editor, Canvas, Font

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
LOG_CHANNEL_ID = 1538982916087095296  # Kuş uçsa haber alacağımız Log Kanalı ID'si
WELCOME_CHANNEL_ID = 1538271609419210835  # Gelen-Giden Kart Kanalı ID'si


# --- YARDIMCI LOG FONKSİYONU ---
async def send_log(guild: discord.Guild, embed: discord.Embed):
  log_channel = guild.get_channel(LOG_CHANNEL_ID)
  if log_channel:
    try:
      await log_channel.send(embed=embed)
    except Exception as e:
      print(f"Log gönderilemedi: {e}")


# --- VLANDİA TEMALI GİRİŞ/ÇIKIŞ KART OLUŞTURUCU ---
async def send_welcome_card(member: discord.Member, action_type: str):
  channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
  if not channel:
    return

  try:
    background = Canvas(900, 500, color=(20, 22, 25))
    editor = Editor(background)
    editor.rectangle((20, 20, 860, 460), outline=(255, 140, 0), stroke_width=3)

    user_avatar_image = (
        await member.avatar.read()
        if member.avatar
        else await member.default_avatar.read()
    )
    avatar_image = Editor(user_avatar_image).resize((160, 160)).circle_image()
    editor.paste(avatar_image, (370, 110))

    title_font = Font.load_default(size=40)
    name_font = Font.load_default(size=35)

    title_text = (
        f"SENİNLE BERABER {member.guild.member_count} KİŞİ OLDUK!"
        if action_type == "join"
        else f"GÖRÜŞÜRÜZ {member.name.upper()}"
    )
    editor.text(
        (450, 50),
        title_text,
        color=(255, 255, 255),
        font=title_font,
        align="center",
    )
    editor.text(
        (450, 340),
        member.name.upper(),
        color=(255, 140, 0),
        font=name_font,
        align="center",
    )

    file = discord.File(fp=editor.image_bytes, filename="vlandia_card.png")
    message_content = (
        f"{member.mention} Hoşgeldin! Senle beraber **{member.guild.member_count}**"
        f" kişi olduk."
        if action_type == "join"
        else f"**{member.name}** aramızdan ayrıldı."
    )
    await channel.send(content=message_content, file=file)

  except Exception as e:
    print(f"Giriş/Çıkış kartı oluşturulurken hata: {e}")


# --- ÇEKİLİŞ SİSTEMİ (SÜRE ÇÖZÜCÜ VE BUTON) ---
def parse_time(time_str: str) -> int:
  time_str = time_str.strip().lower()
  match = re.match(r"^(\d+)([smhd])$", time_str)
  if not match:
    return 0
  amount, unit = int(match.group(1)), match.group(2)
  if unit == "s":
    return amount
  elif unit == "m":
    return amount * 60
  elif unit == "h":
    return amount * 3600
  elif unit == "d":
    return amount * 86400
  return 0


class GiveawayView(discord.ui.View):

  def __init__(self, duration_seconds: int, winners_count: int, prize: str, description: str, host: discord.Member):
    super().__init__(timeout=None)
    self.participants = set()
    self.duration_seconds = duration_seconds
    self.winners_count = winners_count
    self.prize = prize
    self.description = description
    self.host = host
    self.ended = False

  @discord.ui.button(
      label="🎉 Katıl",
      style=discord.ButtonStyle.primary,
      custom_id="giveaway_join_btn",
  )
  async def join_button(
      self, interaction: discord.Interaction, button: discord.ui.Button
  ):
    if self.ended:
      await interaction.response.send_message(
          "❌ Bu çekiliş sona ermiştir!", ephemeral=True
      )
      return

    if interaction.user.id in self.participants:
      self.participants.remove(interaction.user.id)
      await interaction.response.send_message(
          "❌ Çekilişten katılımınız kaldırıldı!", ephemeral=True
      )
    else:
      self.participants.add(interaction.user.id)
      await interaction.response.send_message(
          "✅ Çekilişe başarıyla katıldın!", ephemeral=True
      )

    # Buton üzerindeki katılımcı sayısını güncelleyebiliriz veya mesajı güncelleyebiliriz
    button.label = f"🎉 Katıl ({len(self.participants)})"
    await interaction.message.edit(view=self)


# --- ÇEKİLİŞ MODAL (FORM) PANELİ ---
class GiveawayModal(discord.ui.Modal, title="🎉 Çekiliş Oluştur"):
  duration = discord.ui.TextInput(
      label="Süre",
      placeholder="Örn: 10m (10 dakika), 1h (1 saat), 1d (1 gün)",
      required=True,
      max_length=10,
  )

  winners = discord.ui.TextInput(
      label="Kazanan Sayısı",
      placeholder="Örn: 1",
      default="1",
      required=True,
      max_length=3,
  )

  prize = discord.ui.TextInput(
      label="Ödül",
      placeholder="Verilecek ödül nedir?",
      required=True,
      max_length=100,
  )

  description = discord.ui.TextInput(
      label="Açıklama",
      placeholder="Çekiliş şartları veya detayları buraya...",
      style=discord.TextStyle.paragraph,
      required=False,
      max_length=500,
  )

  async def on_submit(self, interaction: discord.Interaction):
    sec = parse_time(self.duration.value)
    if sec <= 0:
      await interaction.response.send_message(
          "❌ Geçersiz süre formatı! Örn: `10m`, `1h`, `1d` kullanmalısın.",
          ephemeral=True,
      )
      return

    try:
      w_count = int(self.winners.value)
      if w_count < 1:
        raise ValueError()
    except ValueError:
      await interaction.response.send_message(
          "❌ Kazanan sayısı pozitif bir sayı olmalıdır!", ephemeral=True
      )
      return

    end_time = datetime.now() + timedelta(seconds=sec)
    timestamp = int(end_time.timestamp())

    embed = discord.Embed(
        title=self.prize.value,
        description=(
            f"{self.description.value}\n\n"
            if self.description.value
            else ""
        )
        + f"⏳ Bitiş: <t:{timestamp}:R> (<t:{timestamp}:F>)\n"
        f"👑 Düzenleyen: {interaction.user.mention}\n"
        f"🎟️ Katılımcı: **0**\n"
        f"🏆 Kazanan Sayısı: **{w_count}**",
        color=discord.Color.from_rgb(255, 140, 0),
    )
    embed.set_author(name="Vlandia Çekiliş Sistemi", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)

    view = GiveawayView(sec, w_count, self.prize.value, self.description.value, interaction.user)
    
    await interaction.response.send_message(
        "✨ Çekiliş başarıyla başlatıldı!", ephemeral=True
    )
    msg = await interaction.channel.send(embed=embed, view=view)

    # Arka planda sürenin bitmesini bekleyen görev (Task)
    async def finish_giveaway():
      await asyncio.sleep(sec)
      view.ended = True
      for child in view.children:
        child.disabled = True
      
      try:
        await msg.edit(view=view)
      except Exception:
        pass

      if len(view.participants) > 0:
        actual_winners_count = min(w_count, len(view.participants))
        winner_ids = random.sample(list(view.participants), actual_winners_count)
        winner_mentions = ", ".join([f"<@{uid}>" for uid in winner_ids])
        
        result_embed = discord.Embed(
            title=f"🎉 Çekiliş Sonuçlandı: {self.prize.value}",
            description=f"🏆 **Kazananlar:** {winner_mentions}\n👑 **Düzenleyen:** {interaction.user.mention}",
            color=discord.Color.green(),
        )
        await interaction.channel.send(content=winner_mentions, embed=result_embed)
      else:
        result_embed = discord.Embed(
            title=f"🎉 Çekiliş Sonuçlandı: {self.prize.value}",
            description="❌ Yeterli katılım olmadığı için kazanan seçilemedi.",
            color=discord.Color.red(),
        )
        await interaction.channel.send(embed=result_embed)

    bot.loop.create_task(finish_giveaway())


# --- SLASH KOMUTU: /ÇEKİLİŞ ---
@bot.tree.command(
    name="çekiliş",
    description="Vlandia temalı Türkçe çekiliş paneli açar.",
)
@app_commands.checks.has_permissions(administrator=True)
async def çekiliş(interaction: discord.Interaction):
  await interaction.response.send_modal(GiveawayModal())


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


# --- TICKET SLASH KOMUTU ---
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
# 🦅 GİRİŞ / ÇIKIŞ VE LOG SİSTEMİ OLAYLARI
# ==========================================

@bot.event
async def on_member_join(member):
  await send_welcome_card(member, "join")

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


@bot.event
async def on_member_remove(member):
  await send_welcome_card(member, "remove")

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


@bot.event
async def on_message_delete(message):
  if message.author.bot or not message.guild:
    return

  deleter = "Bilinmiyor (Kendi silmiş olabilir)"
  try:
    async for entry in message.guild.audit_logs(
        limit=1, action=discord.AuditLogAction.message_delete
    ):
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
      f"{bot.user} olarak giriş yapıldı, Türkçe çekiliş ve Vlandia sistemleri"
      " aktif!"
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
