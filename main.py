import discord
from discord import app_commands
from discord.ext import commands

# 1. Bot tanımlaması (Eğer değişken adın farklıysa burayı bot'una göre düzenle)
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)


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
    import asyncio

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

    # 2. Açılan ticketlerin gitmesini istediğin "Ticket" kategorisini buluyoruz
    ticket_category = discord.utils.get(
        guild.categories, name="Ticket"
    )  # İsim büyük/küçük harfe duyarlıdır

    # Kullanıcı adı temizleme (Örn: türkçe karakter veya boşluk hatası olmasın diye)
    safe_name = "".join(
        c for c in interaction.user.name if c.isalnum()
    ).lower()
    channel_name = f"ticket-{safe_name}"

    # Eğer aynı isimde kanal varsa tekrar açmasın
    existing_channel = discord.utils.get(guild.text_channels, name=channel_name)
    if existing_channel:
      await interaction.response.send_message(
          f"Zaten açık olan bir ticket kanalın bulunuyor: {existing_channel.mention}",
          ephemeral=True,
      )
      return

    # İzinler: Sadece kullanıcı ve yetkililer görebilsin
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        interaction.user: discord.PermissionOverwrite(
            read_messages=True, send_messages=True, attach_files=True
        ),
    }

    # Kanalı "Ticket" kategorisinin içine oluşturuyoruz
    ticket_channel = await guild.create_text_channel(
        name=channel_name,
        category=ticket_category,
        overwrites=overwrites,
    )

    embed = discord.Embed(
        title=f"Vlandia Pack | {category_type} Talebi",
        description=(
            f"Destek talebiniz **{category_type}** kategorisinde açıldı"
            f" {interaction.user.mention}.\n\nLütfen yetkililerin sizinle"
            " ilgilenmesini bekleyin ve talebinizin detaylarını"
            " buraya yazın."
        ),
        color=discord.Color.from_rgb(43, 45, 49),
    )
    embed.set_footer(text="Vlandia Pro Bot Destek Sistemi")

    await ticket_channel.send(
        content=f"{interaction.user.mention}",
        embed=embed,
        view=TicketCloseView(),
    )
    await interaction.response.send_message(
        f"✅ Destek kanalın başarıyla oluşturuldu: {ticket_channel.mention}",
        ephemeral=True,
    )


# --- SLASH KOMUTU (Sadece 🎫-ticket kanalında çalışır) ---
@bot.tree.command(
    name="ticket_kur",
    description="Harika görünümlü çoklu seçenekli ticket panelini kurar.",
)
@app_commands.checks.has_permissions(administrator=True)
async def ticket_kur(interaction: discord.Interaction):
  # Sadece isminde "ticket" geçen veya tam adı "🎫-ticket" olan kanalda çalışmasını istiyorsan:
  if "ticket" not in interaction.channel.name.lower():
    await interaction.response.send_message(
        "❌ Bu komut sadece **🎫-ticket** kanalında kullanılabilir!",
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


# --- BOT HAZIR OLDUĞUNDA ---
@bot.event
async def on_ready():
  bot.add_view(
      TicketView()
  )  # Bot yeniden başlatıldığında butonların çalışmaya devam etmesi için
  bot.add_view(TicketCloseView())
  print(f"{bot.user} olarak giriş yapıldı ve ticket görünümleri aktif!")
  try:
    synced = await bot.tree.sync()
    print(f"Synced {len(synced)} command(s).")
  except Exception as e:
    print(e)


# Bot token'ını buraya veya environment variable'a koyabilirsin
# bot.run("SENIN_BOT_TOKENIN")
