import discord
from discord import app_commands
from discord.ext import commands
from core.db_base import EconomyBase

class EconomyPay(commands.Cog, EconomyBase):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    @app_commands.command(name="pay", description="他のユーザーにコインを送ります")
    @app_commands.describe(
        target="送る相手を選択してください",
        amount="送る金額を入力してください"
    )
    async def pay(self, interaction: discord.Interaction, target: discord.Member, amount: int):
        sender = interaction.user
        
        # --- バリデーション（入力チェック） ---
        
        # 1. 自分自身には送れない
        if sender.id == target.id:
            return await interaction.response.send_message("自分自身にコインを送ることはできません！", ephemeral=True)
        
        # 2. Botには送れない
        if target.bot:
            return await interaction.response.send_message("Botにコインを送ることはできません。", ephemeral=True)
        
        # 3. 金額が1以上か
        if amount <= 0:
            return await interaction.response.send_message("1コイン以上を指定してください。", ephemeral=True)

        # --- 送金処理 ---
        conn = self.get_db()
        cur = conn.cursor(dictionary=True)
        
        try:
            # 送信者の残高確認
            cur.execute("SELECT balance FROM users WHERE user_id = %s", (sender.id,))
            sender_row = cur.fetchone()
            sender_balance = sender_row['balance'] if sender_row else 0
            
            if sender_balance < amount:
                return await interaction.response.send_message(
                    f"残高が足りません。現在の所持金: **{sender_balance}** コイン", 
                    ephemeral=True
                )
            
            # トランザクション処理: 送信者から引き、受信者に足す
            # update_balance_logic は内部で INSERT ... ON DUPLICATE KEY UPDATE を使っているため
            # 受信者が初対面でも自動的に登録されます
            self.update_balance_logic(sender.id, -amount)
            self.update_balance_logic(target.id, amount)
            
            # 完了メッセージ（チャンネル全体に公開）
            embed = discord.Embed(
                title="💸 送金完了",
                description=f"{sender.mention} さんから {target.mention} さんへコインが送られました！",
                color=0x00ff00
            )
            embed.add_field(name="金額", value=f"**{amount}** コイン", inline=True)
            
            await interaction.response.send_message(embed=embed)

        except Exception as e:
            print(f"Pay Error: {e}")
            await interaction.response.send_message("送金処理中にエラーが発生しました。", ephemeral=True)
        finally:
            cur.close()
            conn.close()

async def setup(bot):
    await bot.add_cog(EconomyPay(bot))
