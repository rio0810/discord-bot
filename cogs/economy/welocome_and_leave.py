import discord
from discord.ext import commands
from core.db_base import EconomyBase

class WelcomeAndLeave(commands.Cog, EconomyBase):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.bonus_amount = 300

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """ユーザーがサーバーに参加したとき：300コインを静かに付与"""
        if member.bot:
            return

        try:
            # データベースに初期コインを付与
            self.update_balance_logic(member.id, self.bonus_amount)
            # コンソールログ（デバッグ用）
            print(f"[JOIN] {member.display_name} ({member.id}) に {self.bonus_amount} コインを付与しました。")
        except Exception as e:
            print(f"[ERROR] Join process for {member.id}: {e}")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """ユーザーがサーバーから脱退したとき：DBからデータを削除"""
        if member.bot:
            return

        conn = self.get_db()
        cur = conn.cursor()
        
        try:
            # ユーザー情報の削除
            cur.execute("DELETE FROM users WHERE user_id = %s", (member.id,))
            
            conn.commit()
            print(f"[LEAVE] {member.display_name} ({member.id}) のデータをDBから削除しました。")
        except Exception as e:
            print(f"[ERROR] Leave process for {member.id}: {e}")
        finally:
            cur.close()
            conn.close()

async def setup(bot):
    await bot.add_cog(WelcomeAndLeave(bot))
