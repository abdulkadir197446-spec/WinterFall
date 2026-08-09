import os
import asyncio
import threading
import random
import time
from datetime import datetime, timedelta
from flask import Flask
import discord
from discord.ext import commands

# --- Render İçin Web Sunucusu ---
app = Flask('')

@app.route('/')
def home():
    return "WinterFall Bot 7/24 Aktif!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

# --- Discord Bot Kurulumu ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# --- EKİP ALIM BAŞVURU FORMU (MODAL) ---
class EkipAlimFormu(discord.ui.Modal, title="Ekip Alım Başvuru Formu"):
    eski_ekip = discord.ui.TextInput(
        label="Eski ekibin?",
        placeholder="Örn: Vanguard",
        style=discord.TextStyle.short,
        required=True
    )
    sunucu = discord.ui.TextInput(
        label="Hangi sunucuda oynuyorsun?",
        placeholder="Örn: CraftRise",
        style=discord.TextStyle.short,
        required=True
    )
    oyun_ici_isim = discord.ui.TextInput(
        label="Oyun içi ismin ne?",
        placeholder="Örn: Steve",
        style=discord.TextStyle.short,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        await olustur_ticket_kanali(interaction, "Ekip Alım", {
            "Eski Ekibi": self.eski_ekip.value,
            "Oynadığı Sunucu": self.sunucu.value,
            "Oyun İçi İsmi": self.oyun_ici_isim.value
        })

# --- TICKET KAPATMA BUTONU ---
class TicketKapatView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Desteği Kapat", style=discord.ButtonStyle.red, custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        kullanici_rolleri = [role.name for role in interaction.user.roles]
        yetkili_mi = interaction.user.id == interaction.guild.owner_id or "Ticket Yetkili" in kullanici_rolleri

        if not yetkili_mi:
            await interaction.response.send_message("❌ Desteği sadece **Ticket Yetkili** rolüne sahip kişiler kapatabilir!", ephemeral=True)
            return

        await interaction.response.send_message("Destek kanalı 5 saniye içinde siliniyor...", ephemeral=True)
        await asyncio.sleep(5)
        await interaction.channel.delete()

# --- ORTAK TICKET OLUŞTURMA FONKSİYONU ---
async def olustur_ticket_kanali(interaction: discord.Interaction, secilen_kategori: str, form_verileri: dict = None):
    guild = interaction.guild
    member = interaction.user

    for channel in guild.channels:
        if isinstance(channel, discord.TextChannel) and channel.name.endswith(f"-{member.name.lower()}"):
            await interaction.response.send_message(f"❌ Zaten açık bir destek talebiniz bulunuyor: {channel.mention}", ephemeral=True)
            return

    kategori_adi = "AÇIK TICKETLAR"
    category = discord.utils.get(guild.categories, name=kategori_adi)
    if not category:
        category = await guild.create_category(kategori_adi)

    ticket_yetkili_rol = discord.utils.get(guild.roles, name="Ticket Yetkili")

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        member: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }

    if ticket_yetkili_rol:
        overwrites[ticket_yetkili_rol] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

    kanal_adi = f"{secilen_kategori.lower().replace(' ', '-')}-{member.name.lower()}"

    ticket_channel = await guild.create_text_channel(
        name=kanal_adi,
        category=category,
        overwrites=overwrites
    )

    embed = discord.Embed(
        title=f"🎫 {secilen_kategori} Talebi Açıldı",
        description=f"Merhaba {member.mention}, yetkililer en kısa sürede sizinle ilgilenecektir.\n\nDesteği kapatmak için aşağıdaki **Desteği Kapat** butonuna basabilirsiniz.",
        color=discord.Color.blue()
    )

    if form_verileri:
        for baslik, cevap in form_verileri.items():
            embed.add_field(name=f"📌 {baslik}", value=f"```\n{cevap}\n```", inline=False)

    if ticket_yetkili_rol:
        etiket_metni = f"{member.mention} {ticket_yetkili_rol.mention}"
    else:
        etiket_metni = f"{member.mention} @Ticket Yetkili"

    await ticket_channel.send(content=etiket_metni, embed=embed, view=TicketKapatView())
    await interaction.response.send_message(f"**{secilen_kategori}** için destek kanalınız oluşturuldu: {ticket_channel.mention}", ephemeral=True)

# --- AÇILIR MENÜ (SELECT MENU) ---
class TicketSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Ekip Alım", emoji="👤", description="Ekip başvurusu için form doldurun."),
            discord.SelectOption(label="Merge", emoji="🔗", description="Merge işlemleri için ticket açar."),
            discord.SelectOption(label="Partnerlik", emoji="💖", description="Partnerlik görüşmeleri için ticket açar."),
            discord.SelectOption(label="Ally", emoji="⚔️", description="Müttefiklik (Ally) için ticket açar."),
            discord.SelectOption(label="Genel Destek", emoji="⚙️", description="Genel yardım ve destek için ticket açar.")
        ]
        super().__init__(placeholder="Seçim yap", min_values=1, max_values=1, options=options, custom_id="ticket_select_menu")

    async def callback(self, interaction: discord.Interaction):
        secilen_kategori = self.values[0]

        if secilen_kategori == "Ekip Alım":
            await interaction.response.send_modal(EkipAlimFormu())
        else:
            await olustur_ticket_kanali(interaction, secilen_kategori)

class TicketSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())

# --- ÇEKİLİŞ SİSTEMİ ---
def parse_time(time_str):
    time_str = time_str.lower().strip()
    if time_str.endswith('m'):
        return int(time_str[:-1]) * 60
    elif time_str.endswith('h'):
        return int(time_str[:-1]) * 3600
    elif time_str.endswith('d'):
        return int(time_str[:-1]) * 86400
    return int(time_str) * 60

class CekilisKatilView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.katilimcilar = set()

    @discord.ui.button(label="🎉 Katıl", style=discord.ButtonStyle.blurple, custom_id="cekilis_katil")
    async def katil(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in self.katilimcilar:
            self.katilimcilar.add(interaction.user.id)
            await interaction.response.send_message("🎉 Çekilişe başarıyla katıldın!", ephemeral=True)
        else:
            self.katilimcilar.remove(interaction.user.id)
            await interaction.response.send_message("Çekilişten ayrıldın.", ephemeral=True)

class CekilisModal(discord.ui.Modal, title="Çekiliş Oluştur"):
    sure = discord.ui.TextInput(label="Süre (Örn: 10m, 1h, 1d)", placeholder="Örn: 10m", style=discord.TextStyle.short)
    kazanan = discord.ui.TextInput(label="Kazanan Sayısı", placeholder="1", style=discord.TextStyle.short)
    odul = discord.ui.TextInput(label="Ödül", placeholder="Örn: VIP Üyelik", style=discord.TextStyle.short)
    aciklama = discord.ui.TextInput(label="Açıklama (İsteğe Bağlı)", placeholder="Şartlar vs.", style=discord.TextStyle.paragraph, required=False)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            saniye = parse_time(self.sure.value)
            kazanan_sayisi = int(self.kazanan.value)
        except:
            await interaction.response.send_message("❌ Hatalı süre veya kazanan sayısı girdiniz!", ephemeral=True)
            return

        bitis_zamani = datetime.now() + timedelta(seconds=saniye)
        timestamp = int(time.time() + saniye)

        embed = discord.Embed(title=f"🎉 {self.odul.value}", color=discord.Color.dark_theme())
        if self.aciklama.value:
            embed.description = f"{self.aciklama.value}\n\n**Sona Erme:** <t:{timestamp}:R>\n**Düzenleyen:** {interaction.user.mention}\n**Kazanan Sayısı:** {kazanan_sayisi}"
        else:
            embed.description = f"**Sona Erme:** <t:{timestamp}:R>\n**Düzenleyen:** {interaction.user.mention}\n**Kazanan Sayısı:** {kazanan_sayisi}"
        
        view = CekilisKatilView()
        
        await interaction.response.send_message("Çekiliş başarıyla başlatıldı!", ephemeral=True)
        mesaj = await interaction.channel.send(content="🎉 **ÇEKİLİŞ BAŞLADI** 🎉", embed=embed, view=view)

        await asyncio.sleep(saniye)

        # Çekiliş Bitiş İşlemleri
        mesaj = await interaction.channel.fetch_message(mesaj.id)
        katilimcilar_listesi = list(view.katilimcilar)

        if len(katilimcilar_listesi) == 0:
            sonuc_embed = discord.Embed(title=f"🎉 {self.odul.value}", description=f"Yeterli katılım olmadığı için çekiliş iptal edildi.\n\n**Düzenleyen:** {interaction.user.mention}", color=discord.Color.red())
            await mesaj.edit(content="🎉 **ÇEKİLİŞ BİTTİ** 🎉", embed=sonuc_embed, view=None)
            return

        kazananlar_id = random.sample(katilimcilar_listesi, min(kazanan_sayisi, len(katilimcilar_listesi)))
        kazananlar_mention = ", ".join([f"<@{uid}>" for uid in kazananlar_id])

        sonuc_embed = discord.Embed(title=f"🎉 {self.odul.value}", color=discord.Color.dark_theme())
        if self.aciklama.value:
            sonuc_embed.description = f"{self.aciklama.value}\n\nSona Erdi: <t:{timestamp}:f>\nDüzenleyen: {interaction.user.mention}\nKatılım: **{len(katilimcilar_listesi)}**\nKazananlar: {kazananlar_mention}"
        else:
            sonuc_embed.description = f"Sona Erdi: <t:{timestamp}:f>\nDüzenleyen: {interaction.user.mention}\nKatılım: **{len(katilimcilar_listesi)}**\nKazananlar: {kazananlar_mention}"

        await mesaj.edit(content="🎉 **ÇEKİLİŞ BİTTİ** 🎉", embed=sonuc_embed, view=None)
        await interaction.channel.send(f"Tebrikler {kazananlar_mention}! **{self.odul.value}** kazandınız!")

class CekilisSetupView(discord.ui.View):
    @discord.ui.button(label="Çekilişi Ayarla", style=discord.ButtonStyle.green)
    async def ayarla(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CekilisModal())

# --- KOMUTLAR ---
@bot.command()
async def ticket_kur(ctx):
    izinli_roller = ["𝐖𝐢𝐧𝐭𝐞𝐫𝐟𝐚𝐥𝐥 Yönetim", "♱ 𝐖𝐢𝐧𝐭𝐞𝐫𝐟𝐚𝐥𝐥"]
    kullanici_rolleri = [role.name for role in ctx.author.roles]
    yetkili_mi = ctx.author.id == ctx.guild.owner_id or any(r in kullanici_rolleri for r in izinli_roller)

    if not yetkili_mi:
        await ctx.send("❌ Bu komutu sadece **𝐖𝐢𝐧𝐭𝐞𝐫𝐟𝐚𝐥𝐥 Yönetim** ve **♱ 𝐖𝐢𝐧𝐭𝐞𝐫𝐟𝐚𝐥𝐥** yetkilileri kullanabilir!", delete_after=5)
        return

    try:
        await ctx.message.delete()
    except:
        pass

    embed = discord.Embed(
        title="Bilet Oluştur",
        description="Ticket açmak için aşağıdaki **Seçim yap** menüsünden uygun kategoriyi seçin.",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed, view=TicketSelectView())

@bot.command()
async def çekiliş(ctx):
    izinli_roller = [
        "❄ 𝙁𝙤𝙪𝙣𝙙𝙚𝙧",
        "❄ 𝙈𝙖𝙮𝙤𝙧",
        "❄𝘾𝙤-𝙈𝙖𝙮𝙤𝙧",
        "♱ 𝐖𝐢𝐧𝐭𝐞𝐫𝐟𝐚𝐥𝐥",
        "𝐖𝐢𝐧𝐭𝐞𝐫𝐟𝐚𝐥𝐥 Yönetim"
    ]
    
    kullanici_rolleri = [role.name for role in ctx.author.roles]
    yetkili_mi = ctx.author.id == ctx.guild.owner_id or any(r in kullanici_rolleri for r in izinli_roller)

    if not yetkili_mi:
        await ctx.send("❌ Bu komutu sadece **WinterFall Yetkilileri** kullanabilir!", delete_after=5)
        return

    try:
        await ctx.message.delete()
    except:
        pass

    await ctx.send("Çekiliş detaylarını girmek için aşağıdaki butona tıklayın.", view=CekilisSetupView(), delete_after=30)

@bot.command()
async def sil(ctx, miktar: int = None):
    izinli_roller = [
        "❄ 𝙁𝙤𝙪𝙣𝙙𝙚𝙧",
        "❄ 𝙈𝙖𝙮𝙤𝙧",
        "❄𝘾𝙤-𝙈𝙖𝙮𝙤𝙧",
        "♱ 𝐖𝐢𝐧𝐭𝐞𝐫𝐟𝐚𝐥𝐥",
        "𝐖𝐢𝐧𝐭𝐞𝐫𝐟𝐚𝐥𝐥 Yönetim"
    ]
    
    kullanici_rolleri = [role.name for role in ctx.author.roles]
    yetkili_mi = ctx.author.id == ctx.guild.owner_id or any(r in kullanici_rolleri for r in izinli_roller)

    if not yetkili_mi:
        await ctx.send("❌ Bu komutu sadece belirlenen **WinterFall Yetkilileri** kullanabilir!", delete_after=5)
        return

    if miktar is None or miktar <= 0 or miktar > 100:
        await ctx.send("❌ Lütfen 1 ile 100 arasında bir sayı girin. Örnek: `!sil 10`", delete_after=5)
        return

    deleted = await ctx.channel.purge(limit=miktar + 1)
    embed = discord.Embed(description=f"🧹 **{len(deleted)-1}** adet mesaj başarıyla silindi.", color=discord.Color.green())
    await ctx.send(embed=embed, delete_after=4)

# --- ETKİNLİKLER ---
@bot.event
async def on_ready():
    bot.add_view(TicketSelectView())
    bot.add_view(TicketKapatView())
    bot.add_view(CekilisKatilView()) # Çekiliş butonlarının aktif kalması için
    print(f'Bot başarıyla giriş yaptı: {bot.user.name}')
    await bot.change_presence(activity=discord.Game(name="!yardım | WinterFall"))

# --- BAŞLATMA ---
if __name__ == '__main__':
    server_thread = threading.Thread(target=run_flask)
    server_thread.start()
    
    token = os.environ.get('BOT_TOKEN')
    if token:
        bot.run(token)
    else:
        print("HATA: BOT_TOKEN bulunamadı!")
