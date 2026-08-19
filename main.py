import asyncio
import os
import random
import time
from datetime import datetime
from io import BytesIO
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv  # Hatalı tire (_) ile düzeltildi
import easy_pil  # Resim/Canvas işlemleri için
from flask import Flask

# .env dosyasındaki token ve ayarları yükle
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Render'da 7/24 aktif tutmak için mini Flask sunucusu
app = Flask("")


@app.route("/")
def home():
  return "Vlandia Pro Bot Aktif ve Çalışıyor!"


def run_flask():
  app.run(host="0.0.0.0", port=8080)


# Bot ayarları ve Intent'ler
intents = discord.Intents.default()
intents.guilds = True
intents.guild_messages = True
intents.message_content = True
intents.guild_members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Sabit ID Tanımlamaları
CATEGORY_ID = 1538271572295688262
ROLE_ID = 1538271541781987449
PACK_CHANNEL_ID = 1539359596555149353  # Arama paneli kanalı
WELCOME_CHANNEL_ID = 1538271609419210835  # Gelen-Giden Kanalı

# Pack Veritabanı
PACK_DATABASE = {
    "smp": [
        {"name": "legolasxwanderone", "channelId": "1539279470064697394"},
        {"name": "arap-kone", "channelId": "1539279225234915498"},
        {"name": "arapkone-blue", "channelId": "1539279262136270959"},
        {"name": "kovadary-pvp", "channelId": "1539279371473264660"},
        {"name": "rıbıtık-pack", "channelId": "1539279388221112380"},
        {"name": "smp-pack", "channelId": "1539279403098579044"},
        {"name": "vanilla-pack", "channelId": "1539279410388144171"},
        {"name": "weembu-pack", "channelId": "1539279417916915742"},
        {"name": "wisquismaslazy-pack", "channelId": "1539279425181454366"},
        {"name": "wild-pack", "channelId": "1539279432999764050"},
        {"name": "ege4093-pack", "channelId": "1539279450926219345"},
        {"name": "head-pvp", "channelId": "1539279193454682213"},
        {"name": "cxkn-pack", "channelId": "1539279501660397578"},
        {"name": "faeroht-smp", "channelId": "1539279518890721361"},
        {"name": "field-smp", "channelId": "1539279535839780964"},
        {"name": "rewia-pack", "channelId": "1539279560300826751"},
        {"name": "unverion-pack", "channelId": "1539279580354060378"},
        {"name": "1rilly-private", "channelId": "1539279595801546912"},
        {"name": "ronnia-pack", "channelId": "1539279615003074750"},
        {"name": "zyan-pack", "channelId": "1539279662302240929"},
        {"name": "sharpnes-500k", "channelId": "1539279640097460235"},
        {"name": "spawnplayer-shield-edit", "channelId": "1539279683701571717"},
        {"name": "dark-smp-max", "channelId": "1539279723929280662"},
        {"name": "bnuy", "channelId": "1539279741876441230"},
        {"name": "mehmetalemdar", "channelId": "1539279759312162887"},
        {"name": "ancientivar-pack", "channelId": "1539279928531623958"},
        {"name": "digiwaitdlv", "channelId": "1539279775355379842"},
        {"name": "vanilla-edit", "channelId": "1539279793873485896"},
        {"name": "tester-pack", "channelId": "1539279811367665805"},
        {"name": "lvhs-pack", "channelId": "1539279833245421750"},
        {"name": "swightv3-pack", "channelId": "1539279856787787937"},
        {"name": "moonq-pack", "channelId": "1539279882209722468"},
        {"name": "drpuuusmp-pack", "channelId": "1539279912677019658"},
        {"name": "852gang-pack", "channelId": "1539279978422870067"},
        {"name": "default-pack", "channelId": "1539280010458697759"},
        {"name": "jokingoverlay-pack", "channelId": "1539280026334273637"},
        {"name": "mergenisthebest-pack", "channelId": "1539279896512299151"},
        {"name": "whyloser77-pack", "channelId": "1539280043522662501"},
        {"name": "tungtungsahur-pack", "channelId": "1539280056042389585"},
        {"name": "theosbarebones-pack", "channelId": "1539354661092462662"},
        {"name": "shazamsmp-pack", "channelId": "1539354682143674389"},
        {"name": "wlenzyx-pack", "channelId": "1539354698925215884"},
        {"name": "cl1ein-pack", "channelId": "1539354596726673468"},
        {"name": "marloww-pack", "channelId": "1539414313461219398"},
    ],
    "crystal": [
        {"name": "shadow-16x-pack", "channelId": "1539341555335434260"},
        {"name": "nymues-lavendar", "channelId": "1539349175320322169"},
        {"name": "bloodyzip", "channelId": "1539349198611423313"},
        {"name": "vape", "channelId": "1539349219259846697"},
        {"name": "ghost", "channelId": "1539349271781056573"},
        {"name": "hurricane-vanilla", "channelId": "1539349290067959858"},
        {"name": "jjxf-matte", "channelId": "1539349322204848238"},
        {"name": "purplfault", "channelId": "1539349366589100095"},
        {"name": "green-v-v2", "channelId": "1539349877039824956"},
        {"name": "marlowvplusaqua", "channelId": "1539349906332852254"},
    ],
    "nethpot": [
        {"name": "xkaru-pack", "channelId": "1539353474716926033"},
        {"name": "ckl_5llluuriisfl_800dl_packck", "channelId": "1539353521902587994"},
        {"name": "mqgic_v1", "channelId": "1539353536369004605"},
        {"name": "5d_christmas2b", "channelId": "1539353549618675873"},
        {"name": "blackbyjack", "channelId": "1539353563518603387"},
        {"name": "rea4per", "channelId": "1539353576261025802"},
        {"name": "espana", "channelId": "1539353589804310589"},
        {"name": "midnight-16x", "channelId": "1539353601284251779"},
        {"name": "pink", "channelId": "1539353617105027072"},
        {"name": "darkned_v2", "channelId": "1539353633785774221"},
        {"name": "creatorpack-118-v122", "channelId": "1539353649808023662"},
        {"name": "mata_private", "channelId": "1539353661652598874"},
        {"name": "phonk", "channelId": "1539353674910797884"},
        {"name": "1ruby", "channelId": "1539353688726962346"},
        {"name": "nacho-edit", "channelId": "1539353711879520256"},
        {"name": "lluris_aimbot_pack", "channelId": "1539353725397762120"},
        {"name": "miracle_32x", "channelId": "1539353738358034523"},
        {"name": "mardow-pack", "channelId": "1539353752002232441"},
        {"name": "xdxd", "channelId": "1539353804972236840"},
        {"name": "exe-pack", "channelId": "1539353819622936649"},
    ],
    "mace": [
        {"name": "_baseballbeans_3d_mace_pack", "channelId": "1539354804885913650"},
        {"name": "manepeare-scythe-mace", "channelId": "1539354922812965006"},
        {"name": "macepvp2", "channelId": "1539354938117718037"},
    ],
    "bedwars": [
        {"name": "purgatory_32", "channelId": "1539355817571127336"},
        {"name": "cryogenik_5b16x5d", "channelId": "1539355852920586260"},
        {"name": "whut_5b16x5d", "channelId": "1539355865981911160"},
        {"name": "bglaze_16x", "channelId": "1539355879000899584"},
        {"name": "ryuzoexe_5b32x5d", "channelId": "1539355892083073136"},
    ],
    "axe": [
        {"name": "lcolder", "channelId": "1539357028202324048"},
        {"name": "glory", "channelId": "1539357063048597575"},
        {"name": "sacrifice", "channelId": "1539357078093697144"},
        {"name": "doly_default", "channelId": "1539357090554839050"},
    ],
}


# --- INTERACTIVE VIEWS (Butonlar ve Menüler) ---


class PackCategorySelect(discord.ui.Select):

  def __init__(self):
    options = [
        discord.SelectOption(
            label="SMP Packleri",
            description="SMP packleri arasında arama yap",
            value="smp",
            emoji="🛡️",
        ),
        discord.SelectOption(
            label="Crystal Packleri",
            description="Crystal packleri arasında arama yap",
            value="crystal",
            emoji="💎",
        ),
        discord.SelectOption(
            label="Nethpot Packleri",
            description="Nethpot packleri arasında arama yap",
            value="nethpot",
            emoji="🧪",
        ),
        discord.SelectOption(
            label="Mace Packleri",
            description="Mace packleri arasında arama yap",
            value="mace",
            emoji="🔨",
        ),
        discord.SelectOption(
            label="Bedwars Packleri",
            description="Bedwars packleri arasında arama yap",
            value="bedwars",
            emoji="🛏️",
        ),
        discord.SelectOption(
            label="Axe Packleri",
            description="Axe packleri arasında arama yap",
            value="axe",
            emoji="🪓",
        ),
    ]
    super().__init__(
        placeholder="Görmek istediğin pack kategorisini seç...",
        min_values=1,
        max_values=1,
        custom_id="pack_category_select",
    )

  async def callback(self, interaction: discord.Interaction):
    if interaction.channel_id != PACK_CHANNEL_ID:
      return await interaction.response.send_message(
          f"Bu özellik sadece <#{PACK_CHANNEL_ID}> kanalında kullanılabilir!",
          ephemeral=True,
      )

    selected_category = self.values[0]
    modal = PackSearchModal(selected_category)
    await interaction.response.send_modal(modal)


class PackCategoryView(discord.ui.View):

  def __init__(self):
    super().__init__(timeout=None)
    self.add_item(PackCategorySelect())


class PackSearchModal(discord.ui.Modal):

  def __init__(self, category: str):
    super().__init__(title="🔍 Pack Arama")
    self.category = category

    self.pack_query = discord.ui.TextInput(
        label="Aradığın packin adı (veya bir kısmı)",
        placeholder="Örn: lcolder, glory, sacrifice...",
        style=discord.TextStyle.short,
        required=False,
    )
    self.add_item(self.pack_query)

  async def on_submit(self, interaction: discord.Interaction):
    query = self.pack_query.value.lower().strip()
    packs = PACK_DATABASE.get(self.category, [])

    category_names = {
        "smp": "🛡️ SMP",
        "crystal": "💎 Crystal",
        "nethpot": "🧪 Nethpot",
        "mace": "🔨 Mace",
        "bedwars": "🛏️ Bedwars",
        "axe": "🪓 Axe",
    }
    cat_name = category_names.get(self.category, "Bilinmeyen")

    filtered_packs = (
        [p for p in packs if query in p["name"].lower()] if query else packs
    )

    result_text = f"📦 **{cat_name} Kategorisi**"
    if query:
      result_text += f' (Aranan: "{query}")'
    result_text += f" - **{len(filtered_packs)} sonuç bulundu:**\n\n"

    if filtered_packs:
      lines = [
          f"• `{p['name']}` ➡️ <#{p['channelId']}>" for p in filtered_packs
      ]
      result_text += "\n".join(lines)
    else:
      result_text += "Aradığın kriterlere uygun pack bulunamadı! ❌"

    await interaction.response.send_message(result_text, ephemeral=True)


class TicketButtons(discord.ui.View):

  def __init__(self):
    super().__init__(timeout=None)

  @discord.ui.button(
      label="Partnerlik",
      style=discord.ButtonStyle.success,
      emoji="🤝",
      custom_id="ticket_partner",
  )
  async def partner(
      self, interaction: discord.Interaction, button: discord.ui.Button
  ):
    await self.create_ticket(interaction)

  @discord.ui.button(
      label="Genel Destek",
      style=discord.ButtonStyle.primary,
      emoji="🎟️",
      custom_id="ticket_genel",
  )
  async def genel(
      self, interaction: discord.Interaction, button: discord.ui.Button
  ):
    await self.create_ticket(interaction)

  @discord.ui.button(
      label="Pack Ekleme",
      style=discord.ButtonStyle.secondary,
      emoji="📦",
      custom_id="ticket_pack",
  )
  async def pack(
      self, interaction: discord.Interaction, button: discord.ui.Button
  ):
    await self.create_ticket(interaction)

  @discord.ui.button(
      label="Yetkili Alım",
      style=discord.ButtonStyle.danger,
      emoji="🤍",
      custom_id="ticket_yetkili",
  )
  async def yetkili(
      self, interaction: discord.Interaction, button: discord.ui.Button
  ):
    await self.create_ticket(interaction)

  async def create_ticket(self, interaction: discord.Interaction):
    await interaction.response.send_message(
        "Destek talebin oluşturuluyor, lütfen bekle...", ephemeral=True
    )
    guild = interaction.guild
    user = interaction.user

    existing = discord.utils.get(
        guild.text_channels, name=f"ticket-{user.name.lower()}"
    )
    if existing:
      return await interaction.edit_original_response(
          content=f"Zaten açık olan bir destek talebin bulunuyor: {existing}"
      )

    try:
      overwrites = {
          guild.default_role:
          discord.PermissionOverwrite(view_channel=False),
          user:
          discord.PermissionOverwrite(
              view_channel=True,
              send_messages=True,
              read_message_history=True,
          ),
          guild.get_role(ROLE_ID):
          discord.PermissionOverwrite(
              view_channel=True,
              send_messages=True,
              read_message_history=True,
          ),
      }
      category = guild.get_channel(CATEGORY_ID)

      ticket_channel = await guild.create_text_channel(
          name=f"ticket-{user.name}",
          category=category if isinstance(category, discord.CategoryChannel)
          else None,
          overwrites=overwrites,
      )

      embed = discord.Embed(
          title="Destek Talebi Oluşturuldu",
          description=(
              f"Merhaba {user},"
              " yetkililerimiz kısa süre içinde sizinle ilgilenecektir."
          ),
          color=0x5865F2,
      )
      close_view = TicketCloseView()

      await ticket_channel.send(
          content=f"<@&{ROLE_ID}> | {user}",
          embed=embed,
          view=close_view,
      )
      await interaction.edit_original_response(
          content=f"Destek talebin başarıyla oluşturuldu: {ticket_channel}"
      )
    except Exception as e:
      print(e)
      await interaction.edit_original_response(
          content="Destek kanalı oluşturulurken bir hata oluştu!"
      )


class TicketCloseView(discord.ui.View):

  def __init__(self):
    super().__init__(timeout=None)

  @discord.ui.button(
      label="Talebi Kapat",
      style=discord.ButtonStyle.danger,
      emoji="🔒",
      custom_id="ticket_close",
  )
  async def close(
      self, interaction: discord.Interaction, button: discord.ui.Button
  ):
    await interaction.response.send_message(
        "Destek talebi 5 saniye içinde kapatılıyor..."
    )
    await asyncio.sleep(5)
    try:
      await interaction.channel.delete()
    except:
      pass


# --- BOT EVENTS ---


@bot.event
async def on_ready():
  print(f"Bot başarıyla giriş yaptı: {bot.user.tag}")
  try:
    synced = await bot.tree.sync()
    print(f"{len(synced)} adet slash komutu senkronize edildi.")
  except Exception as e:
    print(e)


@bot.event
async def on_member_join(member: discord.Member):
  channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
  if not channel:
    return

  try:
    # Canvas ile karşılama kartı
    background = easy_pil.Editor(
        easy_pil.Canvas(700, 350, color="#1e1f22")
    )
    background.rectangle(
        position=(10, 10),
        width=680,
        height=330,
        outline="#f0a500",
        stroke_width=6,
    )

    profile_image = await easy_pil.load_image_async(
        str(member.display_avatar.url)
    )
    profile = easy_pil.Editor(profile_image).resize((150, 150)).circle()
    background.paste(profile, (275, 60))
    background.ellipse(
        position=(275, 60),
        width=150,
        height=150,
        outline="#5865F2",
        stroke_width=5,
    )

    file = discord.File(
        fp=BytesIO(background.image_bytes), filename="vlandia-welcome.png"
    )
    await channel.send(
        content=(
            f"<@{member.id}> Hoşgeldin brom ! senle beraber"
            f" **{member.guild.memberCount}** kişi olduk."
        ),
        file=file,
    )
  except Exception as e:
    print(f"Karşılama resmi oluşturulurken hata oluştu: {e}")


# --- SLASH KOMUTLARI ---


@bot.tree.command(
    name="vlandia-ticket-kur",
    description="Vlandia Pack havalı destek panelini bu kanala kurar.",
)
@app_commands.default_permissions(administrator=True)
async def ticket_kur(interaction: discord.Interaction):
  embed = discord.Embed(
      color=0x2F3136,
      title="🎫 Vlandia Pack | Destek & İletişim",
      description=(
          "Sunucumuzla ilgili her türlü soru, sorun, öneri veya işlemleriniz"
          " için aşağıdaki butonları kullanarak bir destek talebi"
          " oluşturabilirsiniz.\n\n💎 **Kategoriler:**\n🤝"
          " **Partnerlik**\n🎟️ **Genel Destek**\n📦 **Pack"
          " Ekleme**\n🤍 **Yetkili Alım**"
      ),
  )
  embed.set_footer(
      text="Powered by Ohrid & Vlandia Pro Bot",
      icon_url=interaction.guild.icon.url if interaction.guild.icon else None,
  )
  embed.set_timestamp()

  await interaction.response.send_message(
      "Ticket paneli başarıyla kuruldu! 👍", ephemeral=True
  )
  await interaction.channel.send(embed=embed, view=TicketButtons())


@bot.tree.command(
    name="pack-paneli-gonder",
    description=(
        "Pack arama ve kategori panelini doğrudan ilgili kanala gönderir."
    ),
)
@app_commands.default_permissions(administrator=True)
async def pack_paneli_gonder(interaction: discord.Interaction):
  target_channel = interaction.guild.get_channel(PACK_CHANNEL_ID)
  if not target_channel:
    return await interaction.response.send_message(
        "Belirtilen ID'ye sahip kanal bulunamadı!", ephemeral=True
    )

  embed = discord.Embed(
      color=0x5865F2,
      title="📦 Vlandia Pack Arama & Keşif Merkezi",
      description=(
          "Aradığın packi nokta atışı bulmak için aşağıdaki **\"Pack"
          " Kategorisi Seç\"** butonuna tıkla, kategorini seç ve aradığın"
          " ismi yaz!\n\n🔍 **Kategoriler:**\n• 🛡️ SMP Packleri\n• 💎 Crystal"
          " Packleri\n• 🧪 Nethpot Packleri\n• 🔨 Mace Packleri\n• 🛏️ Bedwars"
          " Packleri\n• 🪓 Axe Packleri"
      ),
  )
  embed.set_footer(text="Vlandia Pro Bot • Kolay Pack Sistemi")
  embed.set_timestamp()

  class OpenPackButton(discord.ui.View):

    def __init__(self):
      super().__init__(timeout=None)

    @discord.ui.button(
        label="Pack Kategorisi Seç",
        style=discord.ButtonStyle.primary,
        emoji="🔍",
        custom_id="open_pack_menu",
    )
    async def open_menu(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
      if interaction.channel_id != PACK_CHANNEL_ID:
        return await interaction.response.send_message(
            f"Bu özellik sadece <#{PACK_CHANNEL_ID}> kanalında kullanılabilir!",
            ephemeral=True,
        )
      view = PackCategoryView()
      await interaction.response.send_message(
          "Önce incelemek istediğin kategoriyi seç:",
          view=view,
          ephemeral=True,
      )

  await target_channel.send(embed=embed, view=OpenPackButton())
  await interaction.response.send_message(
      f"Pack arama paneli başarıyla <#{PACK_CHANNEL_ID}> kanalına gönderildi! 🚀",
      ephemeral=True,
  )


@bot.tree.command(
    name="çekiliş", description="Havalı ve profesyonel bir çekiliş paneli açar."
)
@app_commands.default_permissions(administrator=True)
async def cekilis(interaction: discord.Interaction):

  class GiveawayModal(discord.ui.Modal, title="🎉 Vlandia | Çekiliş Oluşturucu"):
    duration = discord.ui.TextInput(
        label="Süre (Örn: 1m, 1h, 1d)",
        placeholder="10m, 1h vb.",
        style=discord.TextStyle.short,
        required=True,
    )
    winners = discord.ui.TextInput(
        label="Kazanan Sayısı",
        placeholder="1",
        style=discord.TextStyle.short,
        required=True,
    )
    prize = discord.ui.TextInput(
        label="Ödül",
        placeholder="Örn: 1 Dia Kit / VIP",
        style=discord.TextStyle.short,
        required=True,
    )
    description = discord.ui.TextInput(
        label="Açıklama / Şartlar",
        placeholder="Örn: 2 invite yapmanız yeterli...",
        style=discord.TextStyle.paragraph,
        required=False,
    )

    async def on_submit(self, interaction: discord.Interaction):
      dur_str = self.duration.value
      win_count = int(self.winners.value) if self.winners.value.isdigit() else 1
      prz = self.prize.value
      desc = self.description.value or "Ek şart belirtilmedi."

      ms_time = 10 * 60 * 1000
      if dur_str.endswith("m"):
        ms_time = int(dur_str[:-1]) * 60 * 1000
      elif dur_str.endswith("h"):
        ms_time = int(dur_str[:-1]) * 60 * 60 * 1000
      elif dur_str.endswith("d"):
        ms_time = int(dur_str[:-1]) * 24 * 60 * 60 * 1000

      ends_at = int(time.time() * 1000) + ms_time
      unix_ts = int(ends_at / 1000)

      await interaction.response.send_message(
          "Çekiliş başarıyla başlatıldı! 🎉", ephemeral=True
      )

      embed = discord.Embed(
          color=0x5865F2,
          title=f"🎉 {prz}",
          description=(
              f"{desc}\n\n**Düzenleyen:**"
              f" {interaction.user}\n**Kazanan:**"
              f" {win_count}\n**Bitiş:** <t:{unix_ts}:F> (<t:{unix_ts}:R>)"
          ),
      )

      participants = set()

      class GiveawayView(discord.ui.View):

        def __init__(self):
          super().__init__(timeout=ms_time / 1000)

        @discord.ui.button(
            label=f"Katıl • 0",
            style=discord.ButtonStyle.primary,
            emoji="🎉",
            custom_id="join_giveaway",
        )
        async def join(
            self, interaction: discord.Interaction, button: discord.ui.Button
        ):
          if interaction.user.id in participants:
            participants.remove(interaction.user.id)
            await interaction.response.send_message(
                "Çekilişten başarıyla ayrıldın!", ephemeral=True
            )
          else:
            participants.add(interaction.user.id)
            await interaction.response.send_message(
                "Çekilişe başarıyla katıldın! Şanslı kişi sen olabilirsin 🍀",
                ephemeral=True,
            )
          button.label = f"Katıl • {len(participants)}"
          await interaction.message.edit(view=self)

        @discord.ui.button(
            label="Katılımcılar",
            style=discord.ButtonStyle.secondary,
            emoji="👥",
            custom_id="show_participants",
        )
        async def show(
            self, interaction: discord.Interaction, button: discord.ui.Button
        ):
          if not participants:
            await interaction.response.send_message(
                "Henüz kimse katılmadı!", ephemeral=True
            )
          else:
            list_str = ", ".join([f"<@{uid}>" for uid in participants])
            await interaction.response.send_message(
                f"Şu ana kadar katılanlar ({len(participants)}"
                f" kişi):\n{list_str}",
                ephemeral=True,
            )

      view = GiveawayView()
      msg = await interaction.channel.send(embed=embed, view=view)

      await asyncio.sleep(ms_time / 1000)

      # Çekiliş Bitişi
      for child in view.children:
        child.disabled = True
      await msg.edit(view=view)

      part_array = list(participants)
      if not part_array:
        ended_embed = discord.Embed(
            color=0xED4245,
            title=f"🎉 {prz} (Sona Erdi)",
            description=(
                f"**Düzenleyen:** {interaction.user}\n**Toplam Katılımcı: 0"
                " Kişi**\n\n🏆 **Kazananlar:**\nHiç kimse katılmadığı için"
                " kazanan olamadı!"
            ),
        )
        await msg.edit(embed=ended_embed)
      else:
        winners_list = []
        for _ in range(min(win_count, len(part_array))):
          chosen = random.choice(part_array)
          part_array.remove(chosen)
          winners_list.append(f"<@{chosen}>")

        winners_text = ", ".join(winners_list)
        ended_embed = discord.Embed(
            color=0xED4245,
            title=f"🎉 {prz} (Sona Erdi)",
            description=(
                f"**Düzenleyen:** {interaction.user}\n**Toplam Katılımcı:**"
                f" {len(participants)} Kişi\n\n🏆"
                f" **Kazananlar:**\n{winners_text}"
            ),
        )
        await msg.edit(embed=ended_embed)
        await interaction.channel.send(
            f"Tebrikler {winners_text}! **{prz}** ödülünü kazandınız! 🥳"
            f" (**{len(participants)}** kişi arasından seçildiniz.)"
        )

  await interaction.response.send_modal(GiveawayModal())


# Flask sunucusunu arka planda thread ile başlat
import threading

threading.Thread(target=run_flask).start()

# Botu Çalıştır
bot.run(TOKEN)
