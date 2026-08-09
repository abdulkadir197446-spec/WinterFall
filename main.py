# --- ORTAK TICKET OLUŞTURMA FONKSİYONU ---
async def olustur_ticket_kanali(interaction: discord.Interaction, secilen_kategori: str, form_verileri: dict = None):
    guild = interaction.guild
    member = interaction.user

    for channel in guild.channels:
        if isinstance(channel, discord.TextChannel) and channel.name.endswith(f"-{member.name.lower()}" ):
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

    if ticket_yetkili_rol:
        etiket_metni = f"{member.mention} {ticket_yetkili_rol.mention}"
    else:
        etiket_metni = f"{member.mention} @Ticket Yetkili"

    if secilen_kategori == "Partnerlik":
        embed = discord.Embed(
            title="💖 Partnerlik Başvuru Talebi",
            description="Aramıza katılmak için sunucuya gelip ticket açmanız yeterli",
            color=discord.Color.from_rgb(255, 105, 180)
        )
        await interaction.response.send_message(f"**{secilen_kategori}** için destek kanalınız oluşturuldu: {ticket_channel.mention}", ephemeral=True)
        await ticket_channel.send(embed=embed, view=TicketKapatView())
        await ticket_channel.send(f"{etiket_metni}\n\n[https://discord.gg/NgfQafxkDV](https://discord.gg/NgfQafxkDV)")
    else:
        embed = discord.Embed(
            title=f"🎫 {secilen_kategori} Talebi Açıldı",
            description=f"Merhaba {member.mention}, yetkililerimiz ve yapay zeka asistanımız en kısa sürede sizinle ilgilenecektir.",
            color=discord.Color.blue()
        )

        if form_verileri:
            for baslik, cevap in form_verileri.items():
                embed.add_field(name=f"📌 {baslik}", value=f"```\n{cevap}\n```", inline=False)

        await interaction.response.send_message(f"**{secilen_kategori}** için destek kanalınız oluşturuldu: {ticket_channel.mention}", ephemeral=True)
        await ticket_channel.send(content=etiket_metni, embed=embed, view=TicketKapatView())
