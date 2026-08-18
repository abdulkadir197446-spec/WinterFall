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

    # Kategoriyi ID ile buluyoruz
    ticket_category = guild.get_channel(TICKET_CATEGORY_ID)

    # Kullanıcı adını güvenli formata çevirir
    safe_name = "".join(
        c for c in interaction.user.name if c.isalnum()
    ).lower()
    channel_name = f"ticket-{safe_name}"

    # Zaten açık kanalı varsa engeller
    existing_channel = discord.utils.get(guild.text_channels, name=channel_name)
    if existing_channel:
      await interaction.response.send_message(
          f"Zaten açık olan bir ticket kanalın bulunuyor: {existing_channel.mention}",
          ephemeral=True,
      )
      return

    # İzinler: Kullanıcı ve yetkili rolü görebilsin
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

    # Ticket kanalını oluştur
    ticket_channel = await guild.create_text_channel(
        name=channel_name,
        category=(
            ticket_category
            if isinstance(ticket_category, discord.CategoryChannel)
            else None
        ),
        overwrites=overwrites,
    )

    # Havalı Karşılama Embed'i
    embed = discord.Embed(
        title=f"Vlandia Pack | {category_type} Destek Talebi",
        description=(
            f"Hoş geldin {interaction.user.mention}! 🚀\n\n"
            f"**{category_type}** ile ilgili talebin başarıyla alındı. Lütfen"
            " sorununuzu veya talebinizi detaylı bir şekilde açıklayın,"
            " yetkili ekibimiz en kısa sürede sizinle ilgilenecektir.\n\n"
            "⚠️ *Gereksiz yere ticket açmak cezai işlem sebep olabilir.*"
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

    # Etiketleme mesajı (Kullanıcı + Belirttiğin Yetkili Rolü)
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


# --- ON READY ---
@bot.event
async def on_ready():
  bot.add_view(TicketView())
  bot.add_view(TicketCloseView())
  print(f"{bot.user} olarak giriş yapıldı!")
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
