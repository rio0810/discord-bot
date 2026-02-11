import discord
from discord import app_commands
from core.admin_base import AdminCogBase

class AdminManage(AdminCogBase):
    @app_commands.command(name="admin_give", description="【管理者専用】指定したユーザーにコインを付与します")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_any_role(AdminCogBase.ADMIN_ROLE_ID)
    async def admin_give(self, interaction: discord.Interaction, member: discord.Member, amount: int):
        if amount <= 0:
            return await interaction.response.send_message("1枚以上の数値を指定してください。", ephemeral=True)
        
        self.update_balance_logic(member.id, amount)
        await self.send_admin_log("コイン付与", member, amount, interaction.user, 0x2ecc71)
        await interaction.response.send_message(f"✅ {member.mention} に **{amount}** 枚付与しました。", ephemeral=True)

    @app_commands.command(name="admin_take", description="【管理者専用】指定したユーザーからコインを没収します")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_any_role(AdminCogBase.ADMIN_ROLE_ID)
    async def admin_take(self, interaction: discord.Interaction, member: discord.Member, amount: int):
        if amount <= 0:
            return await interaction.response.send_message("1枚以上の数値を指定してください。", ephemeral=True)
        
        current_bal = self.get_balance_logic(member.id)
        actual_take = min(amount, current_bal)
        self.update_balance_logic(member.id, -actual_take)
        
        await self.send_admin_log("コイン没収", member, actual_take, interaction.user, 0xe74c3c)
        await interaction.response.send_message(f"✅ {member.mention} から **{actual_take}** 枚没収しました。", ephemeral=True)

async def setup(bot):
    await bot.add_cog(AdminManage(bot))
