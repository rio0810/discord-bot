import discord
from discord import app_commands
from datetime import datetime
from core.admin_base import AdminCogBase
from ui.pagenation_ui import PaginationView

class AdminView(AdminCogBase):
    @app_commands.command(name="admin_list", description="【管理者専用】全ユーザーのランキングを表示します")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_any_role(AdminCogBase.ADMIN_ROLE_ID)
    async def admin_list(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        conn = self.get_db()
        cur = conn.cursor()
        cur.execute("SELECT user_id, balance FROM users ORDER BY balance DESC")
        rows = cur.fetchall()
        cur.close()
        conn.close()

        if not rows:
            return await interaction.followup.send("データベースにユーザーが存在しません。")

        all_lines = []
        for i, (uid, bal) in enumerate(rows, 1):
            try:
                member = interaction.guild.get_member(uid) or await self.bot.fetch_user(uid)
                name = member.display_name if hasattr(member, 'display_name') else member.name
            except: name = f"Unknown({uid})"
            all_lines.append(f"`{i:02d}.` **{name}**: {bal} 枚")

        view = PaginationView(all_lines)
        await interaction.followup.send(embed=view.create_embed(), view=view)

    @app_commands.command(name="admin_check", description="【管理者専用】指定したユーザーの情報を確認します")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_any_role(AdminCogBase.ADMIN_ROLE_ID)
    async def admin_check(self, interaction: discord.Interaction, member: discord.Member):
        conn = self.get_db()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT balance, vc_minutes_total FROM users WHERE user_id = %s", (member.id,))
        row = cur.fetchone()
        cur.close()
        conn.close()

        bal, vc = (row['balance'], row['vc_minutes_total']) if row else (0, 0)
        embed = discord.Embed(title=f"🔍 照会: {member.display_name}", color=0x3498db, timestamp=datetime.now())
        embed.add_field(name="所持金", value=f"{bal} 枚", inline=True)
        embed.add_field(name="VC端数", value=f"{vc} 分", inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        await self.send_admin_log("残高照会", member, bal, interaction.user, 0x3498db)

async def setup(bot):
    await bot.add_cog(AdminView(bot))
