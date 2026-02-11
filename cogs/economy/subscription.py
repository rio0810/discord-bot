import discord
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime, timedelta
from core.db_base import EconomyBase

class Subscription(commands.Cog, EconomyBase):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        
        # --- 設定値 ---
        self.sub_price = 500              # 月額料金
        self.sub_role_id = 1469376186147799050   # サブスク特典ロールのID
        self.guild_id = 1409401336943874130      # サーバーID

    # Cogがロードされたときに実行される（AttributeErrorを防ぐためにここで開始）
    async def cog_load(self):
        if not self.check_subscriptions.is_running():
            self.check_subscriptions.start()

    def cog_unload(self):
        self.check_subscriptions.cancel()

    # --- 毎日チェックするバックグラウンド処理 ---
    @tasks.loop(hours=24)
    async def check_subscriptions(self):
        """24時間ごとにサブスクの更新・通知・期限切れをチェック"""
        conn = self.get_db()
        cur = conn.cursor(dictionary=True)
        now = datetime.now()
        
        guild = self.bot.get_guild(self.guild_id)
        if not guild:
            return 

        role = guild.get_role(self.sub_role_id)

        # 1. 【自動更新】
        cur.execute("SELECT user_id FROM subscriptions WHERE end_date <= %s AND active = 1", (now,))
        due_users = cur.fetchall()
        
        for sub in due_users:
            uid = sub['user_id']
            balance = self.get_balance_logic(uid)
            member = guild.get_member(uid)

            if balance >= self.sub_price:
                new_end = now + timedelta(days=30)
                self.update_balance_logic(uid, -self.sub_price)
                cur.execute("UPDATE subscriptions SET end_date = %s WHERE user_id = %s", (new_end, uid))
                if member:
                    try: await member.send(f"✅ サブスクを自動更新しました（-{self.sub_price}コイン）。次回の更新日は {new_end.strftime('%Y/%m/%d')} です。")
                    except: pass
            else:
                cur.execute("UPDATE subscriptions SET active = 0 WHERE user_id = %s", (uid,))
                if member and role: 
                    await member.remove_roles(role)
                if member:
                    try: await member.send(f"⚠️ コイン不足のためサブスクを継続できませんでした（必要: {self.sub_price}）。特典ロールを削除しました。")
                    except: pass

        # 2. 【事前通知】
        three_days_later = now + timedelta(days=3)
        two_days_later = now + timedelta(days=2)
        cur.execute("SELECT user_id, end_date FROM subscriptions WHERE end_date BETWEEN %s AND %s AND active = 1", 
                    (two_days_later, three_days_later))
        notice_users = cur.fetchall()

        for sub in notice_users:
            member = guild.get_member(sub['user_id'])
            if member:
                try: await member.send(f"📢 【事前通知】あと3日でサブスクが更新されます。\n更新料 **{self.sub_price}** コインが必要です。")
                except: pass

        # 3. 【期限終了】
        cur.execute("SELECT user_id FROM subscriptions WHERE end_date <= %s AND active = 0", (now,))
        expired_subs = cur.fetchall()
        for sub in expired_subs:
            member = guild.get_member(sub['user_id'])
            if member and role and role in member.roles:
                await member.remove_roles(role)
                try: await member.send("ℹ️ サブスクの有効期限が終了したため、ロールを解除しました。")
                except: pass

        conn.commit()
        cur.close()
        conn.close()

    # --- コマンド: サブスク登録 ---
    @app_commands.command(name="subscribe", description="月額500コインで限定ロールを取得（自動更新あり）")
    async def subscribe(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        conn = self.get_db()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT active FROM subscriptions WHERE user_id = %s", (user_id,))
        row = cur.fetchone()

        if row and row['active'] == 1:
            cur.close()
            conn.close()
            return await interaction.response.send_message("すでにサブスクリプションは有効です。", ephemeral=True)

        balance = self.get_balance_logic(user_id)
        if balance < self.sub_price:
            cur.close()
            conn.close()
            return await interaction.response.send_message(f"コインが足りません（必要: {self.sub_price}）", ephemeral=True)

        self.update_balance_logic(user_id, -self.sub_price)
        end_date = datetime.now() + timedelta(days=30)
        
        cur.execute("""
            INSERT INTO subscriptions (user_id, end_date, active) VALUES (%s, %s, 1)
            ON DUPLICATE KEY UPDATE end_date = %s, active = 1
        """, (user_id, end_date, end_date))
        
        conn.commit()
        cur.close()
        conn.close()

        role = interaction.guild.get_role(self.sub_role_id)
        if role:
            await interaction.user.add_roles(role)
            await interaction.response.send_message(f"🎉 サブスク登録完了！**{role.name}** ロールを付与しました（有効期限: 30日間）", ephemeral=True)
        else:
            await interaction.response.send_message("✅ 登録完了しましたが、ロールが見つかりませんでした。", ephemeral=True)

    # --- コマンド: ステータス確認（自分にしか見えない） ---
    @app_commands.command(name="sub_status", description="自分のサブスクリプション状況を確認します")
    async def sub_status(self, interaction: discord.Interaction):
        conn = self.get_db()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT end_date, active FROM subscriptions WHERE user_id = %s", (interaction.user.id,))
        row = cur.fetchone()
        cur.close()
        conn.close()

        if not row:
            return await interaction.response.send_message("サブスクリプション履歴がありません。", ephemeral=True)

        status_text = "✅ 有効（自動更新あり）" if row['active'] == 1 else "⚠️ 自動更新OFF（期限終了まで有効）"
        
        embed = discord.Embed(
            title="サブスクリプション状況",
            color=discord.Color.blue() if row['active'] == 1 else discord.Color.orange(),
            timestamp=datetime.now()
        )
        embed.add_field(name="現在の状態", value=status_text, inline=False)
        embed.add_field(name="有効期限", value=row['end_date'].strftime('%Y/%m/%d %H:%M'), inline=False)
        embed.set_footer(text=f"ユーザー: {interaction.user.display_name}")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # --- コマンド: 解約予約 ---
    @app_commands.command(name="unsubscribe", description="サブスクの自動更新を停止します")
    async def unsubscribe(self, interaction: discord.Interaction):
        conn = self.get_db()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT end_date, active FROM subscriptions WHERE user_id = %s", (interaction.user.id,))
        row = cur.fetchone()

        if not row or row['active'] == 0:
            cur.close()
            conn.close()
            return await interaction.response.send_message("現在、有効なサブスクリプション（自動更新設定）はありません。", ephemeral=True)

        cur.execute("UPDATE subscriptions SET active = 0 WHERE user_id = %s", (interaction.user.id,))
        conn.commit()
        cur.close()
        conn.close()

        await interaction.response.send_message(
            f"✅ サブスクの自動更新を停止しました。現在の期限（{row['end_date'].strftime('%Y/%m/%d')}）まではロールを利用できます。", 
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(Subscription(bot))
