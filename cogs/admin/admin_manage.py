import discord
from discord import app_commands
import re
from core.admin_base import AdminCogBase

class AdminManage(AdminCogBase):
    def __init__(self, bot):
        super().__init__(bot)

    def parse_mentions(self, text: str):
        """文字列からユーザーIDのみを抽出する正規表現"""
        return re.findall(r'<@!?([0-9]+)>', text)

    # --- 1. 付与 ---
    @app_commands.command(name="admin_give", description="【管理者専用】指定したユーザー（複数可）にコインを付与します")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_any_role(AdminCogBase.ADMIN_ROLE_ID)
    @app_commands.describe(members_text="付与したい相手をメンション（複数可）", amount="一人あたりの枚数")
    async def admin_give(self, interaction: discord.Interaction, members_text: str, amount: int):
        if amount <= 0:
            return await interaction.response.send_message("1枚以上の数値を指定してください。", ephemeral=True)
        
        await interaction.response.defer(ephemeral=True)
        user_ids = self.parse_mentions(members_text)
        
        if not user_ids:
            return await interaction.followup.send("有効なユーザーメンションが見つかりませんでした。")

        success_count = 0
        for user_id_str in set(user_ids):
            user_id = int(user_id_str)
            member = interaction.guild.get_member(user_id)
            if member:
                self.update_balance_logic(user_id, amount)
                await self.send_admin_log("コイン付与", member, amount, interaction.user, 0x2ecc71)
                success_count += 1

        await interaction.followup.send(f"✅ {success_count} 名に **{amount}** 枚ずつ付与しました。")

    # --- 2. 没収 ---
    @app_commands.command(name="admin_take", description="【管理者専用】指定したユーザー（複数可）からコインを没収します")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_any_role(AdminCogBase.ADMIN_ROLE_ID)
    @app_commands.describe(members_text="没収したい相手をメンション（複数可）", amount="一人あたりの没収枚数")
    async def admin_take(self, interaction: discord.Interaction, members_text: str, amount: int):
        if amount <= 0:
            return await interaction.response.send_message("1枚以上の数値を指定してください。", ephemeral=True)
        
        await interaction.response.defer(ephemeral=True)
        user_ids = self.parse_mentions(members_text)

        if not user_ids:
            return await interaction.followup.send("有効なユーザーメンションが見つかりませんでした。")

        success_count = 0
        for user_id_str in set(user_ids):
            user_id = int(user_id_str)
            member = interaction.guild.get_member(user_id)
            if member:
                current_bal = self.get_balance_logic(user_id)
                actual_take = min(amount, current_bal)
                self.update_balance_logic(user_id, -actual_take)
                await self.send_admin_log("コイン没収", member, actual_take, interaction.user, 0xe74c3c)
                success_count += 1

        await interaction.followup.send(f"✅ {success_count} 名から没収処理を完了しました。")

    # --- 3. サーバー全員付与 ---
    @app_commands.command(name="admin_give_all", description="【管理者専用】サーバー内の全メンバーにコインを付与します")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_any_role(AdminCogBase.ADMIN_ROLE_ID)
    @app_commands.describe(amount="全員に付与する枚数")
    async def admin_give_all(self, interaction: discord.Interaction, amount: int):
        if amount <= 0:
            return await interaction.response.send_message("1枚以上の数値を指定してください。", ephemeral=True)
        
        await interaction.response.defer(ephemeral=True)

        # Botを除外した全メンバーを取得
        members = [m for m in interaction.guild.members if not m.bot]
        member_count = len(members)

        conn = self.get_db()
        cur = conn.cursor()
        
        try:
            batch_size = 100
            sql = """
            INSERT INTO users (user_id, balance) VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE balance = balance + VALUES(balance)
            """
            
            for i in range(0, member_count, batch_size):
                batch = members[i : i + batch_size]
                data = [(m.id, amount) for m in batch]
                
                cur.executemany(sql, data)
                conn.commit()

            # ログ送信
            log_channel = self.bot.get_channel(self.LOG_CHANNEL_ID)
            if log_channel:
                embed = discord.Embed(
                    title="📜 管理者ログ: サーバー全員付与",
                    description=f"サーバー内の全メンバー（未登録者を含む）に配布を行いました。",
                    color=0x2ecc71,
                    timestamp=discord.utils.utcnow()
                )
                embed.add_field(name="実行者", value=interaction.user.mention, inline=True)
                embed.add_field(name="配布枚数", value=f"**{amount}** 枚", inline=True)
                embed.add_field(name="総対象人数", value=f"{member_count} 名", inline=True)
                await log_channel.send(embed=embed)

            await interaction.followup.send(f"✅ サーバー内の全メンバー {member_count} 名（未登録者含む）に **{amount}** 枚ずつ付与しました。")

        except Exception as e:
            print(f"Give all Error: {e}")
            await interaction.followup.send(f"⚠️ 処理中にエラーが発生しました: {e}")
        finally:
            cur.close()
            conn.close()

async def setup(bot):
    await bot.add_cog(AdminManage(bot))
