import discord
from discord import app_commands
from discord.ext import commands
import random
from core.db_base import EconomyBase

class EconomyGames(commands.Cog, EconomyBase):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    @app_commands.command(name="balance", description="残高確認")
    async def balance(self, interaction: discord.Interaction):
        bal = self.get_balance_logic(interaction.user.id)
        await interaction.response.send_message(f"所持金: **{bal}** コイン")

    @app_commands.command(name="slot", description="スロットに挑戦")
    async def slot(self, interaction: discord.Interaction, bet: int):
        if bet <= 0:
            return await interaction.response.send_message("1枚以上賭けてください。", ephemeral=True)
        
        current_bal = self.get_balance_logic(interaction.user.id)
        if current_bal < bet:
            return await interaction.response.send_message("残高不足です。", ephemeral=True)

        emojis = ["🍎", "🍇", "🎰", "💎"]
        weights = [45, 35, 15, 5] 
        reel = random.choices(emojis, weights=weights, k=3)
        
        payout = 0
        if reel[0] == reel[1] == reel[2]:
            multipliers = {"🍎": 5, "🍇": 10, "🎰": 30, "💎": 100}
            payout = bet * multipliers[reel[0]]
            msg = "🎊 ジャックポット！"
        elif len(set(reel)) < 3:
            payout = int(bet * 1.5)
            msg = "✨ 当たり！"
        else:
            payout = 0
            msg = "ハズレ..."

        self.update_balance_logic(interaction.user.id, payout - bet)

        embed = discord.Embed(title="🎰 SLOT", color=0xffd700 if payout > 0 else 0x555555)
        embed.add_field(name="結果", value=f"┃ {reel[0]} ┃ {reel[1]} ┃ {reel[2]} ┃", inline=False)
        embed.add_field(name="獲得", value=f"{payout} コイン", inline=False)
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(EconomyGames(bot))
