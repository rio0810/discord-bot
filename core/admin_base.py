import discord
from discord.ext import commands
from datetime import datetime
from .db_base import EconomyBase

class AdminCogBase(commands.Cog, EconomyBase):
    ADMIN_ROLE_ID = 1409402749161832518
    LOG_CHANNEL_ID = 1469597296181117021

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    async def send_admin_log(self, title, member, amount, executor, color):
        channel = self.bot.get_channel(self.LOG_CHANNEL_ID)
        if not channel:
            print(f"⚠️ [Log Error] チャンネルID {self.LOG_CHANNEL_ID} が見つかりません。")
            return

        embed = discord.Embed(
            title=f"📜 管理者ログ: {title}",
            color=color,
            timestamp=datetime.now()
        )
        embed.add_field(name="実行者", value=f"{executor.mention}", inline=False)
        embed.add_field(name="対象者", value=f"{member.mention}", inline=True)
        embed.add_field(name="枚数", value=f"**{amount}** 枚", inline=True)
        embed.set_thumbnail(url=member.display_avatar.url)
        await channel.send(embed=embed)
