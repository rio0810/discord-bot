import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
import math, os
from core.db_base import EconomyBase

class VCReward(commands.Cog, EconomyBase):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        # 入室時間を一時的に記録する辞書 {user_id: join_time}
        self.vc_start_times = {}
        
        # --- 基本設定 ---
        self.reward_interval = 30  # 30分ごと
        self.base_reward = 50      # 通常時の報酬
        
        # --- 特典設定 ---
        self.special_role_id = int(os.getenv("SPECIAL_ROLE_ID", "0")) # 特典を与えるロールID
        self.multiplier = 1.5                     # 倍率 (1.5倍)
        
        # --- 除外チャンネル設定 ---
        env_excluded = os.getenv("EXCLUDED_CHANNEL_IDS")
        if env_excluded:
            self.excluded_channel_ids = [int(i.strip()) for i in env_excluded.split(",")]
        else:
            self.excluded_channel_ids = []

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        # Botの動きは無視
        if member.bot:
            return

        now = datetime.now()

        # --- 1. チャンネルを移動した「本人」の処理 ---
        if before.channel != after.channel:
            # 退出・移動元の精算
            join_time = self.vc_start_times.pop(member.id, None)
            if join_time:
                minutes_spent = int((now - join_time).total_seconds() / 60)
                if minutes_spent > 0:
                    await self.add_vc_time(member, minutes_spent)

            # 移動先（after.channel）で計測条件を満たしているかは下の「共通スキャン」で判定されるため、ここでは何もしない

        # --- 2. チャンネル内の全員の状態をチェックして、計測の開始/停止を判定 ---
        # 変化があったチャンネル（移動前 or 移動後）を対象にする
        target_channels = filter(None, [before.channel, after.channel])
        
        for channel in target_channels:
            if channel.id in self.excluded_channel_ids:
                # 除外チャンネルにいる全員の計測を停止・精算
                for m in channel.members:
                    if m.id in self.vc_start_times:
                        join_time = self.vc_start_times.pop(m.id, None)
                        if join_time:
                            minutes = int((now - join_time).total_seconds() / 60)
                            if minutes > 0: await self.add_vc_time(m, minutes)
                continue

            # チャンネル内にいる人間（Bot除く）をリストアップ
            humans_in_vc = [m for m in channel.members if not m.bot]
            num_humans = len(humans_in_vc)

            for m in humans_in_vc:
                is_tracking = m.id in self.vc_start_times
                # 条件：自分以外に人間が1人以上いる
                eligible = num_humans >= 2

                if eligible and not is_tracking:
                    # 計測開始：2人以上揃ったのに計測していなかった人
                    self.vc_start_times[m.id] = now
                elif not eligible and is_tracking:
                    # 計測停止：1人きりになったのに計測したままの人
                    join_time = self.vc_start_times.pop(m.id, None)
                    if join_time:
                        minutes = int((now - join_time).total_seconds() / 60)
                        if minutes > 0: await self.add_vc_time(m, minutes)

    async def add_vc_time(self, member, minutes):
        """滞在時間をDBに記録し、30分に達していたら報酬を付与"""
        conn = self.get_db()
        cur = conn.cursor(dictionary=True)
        
        cur.execute("SELECT vc_minutes_total FROM users WHERE user_id = %s", (member.id,))
        row = cur.fetchone()
        current_total = row['vc_minutes_total'] if row and 'vc_minutes_total' in row else 0
        
        new_total = current_total + minutes
        reward_count = new_total // self.reward_interval
        remaining_minutes = new_total % self.reward_interval
        
        # データベースを更新
        cur.execute("""
            INSERT INTO users (user_id, vc_minutes_total) VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE vc_minutes_total = %s
        """, (member.id, remaining_minutes, remaining_minutes))
        
        if reward_count > 0:
            reward_per_unit = self.base_reward
            multiplier_text = ""
            
            # 1.5倍の計算 (math.floorで整数化)
            if any(role.id == self.special_role_id for role in member.roles):
                reward_per_unit = math.floor(self.base_reward * self.multiplier)
                multiplier_text = f" (✨特典: {self.multiplier}倍！)"
            
            total_reward = reward_count * reward_per_unit
            self.update_balance_logic(member.id, total_reward)
            
            try:
                await member.send(
                    f"🎙️ VCでの交流により **{total_reward}** コインを獲得しました！\n"
                    f"合計滞在時間: {reward_count * self.reward_interval} 分{multiplier_text}"
                )
            except:
                pass
                
        conn.commit()
        cur.close()
        conn.close()

    @app_commands.command(name="vc_status", description="現在のVC累計滞在時間を確認します")
    async def vc_status(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        
        conn = self.get_db()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT vc_minutes_total FROM users WHERE user_id = %s", (user_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()

        saved_minutes = row['vc_minutes_total'] if row and 'vc_minutes_total' in row else 0
        
        current_session_minutes = 0
        is_tracking = False
        if user_id in self.vc_start_times:
            join_time = self.vc_start_times[user_id]
            current_session_minutes = int((datetime.now() - join_time).total_seconds() / 60)
            is_tracking = True

        total_minutes = saved_minutes + current_session_minutes
        next_reward_in = self.reward_interval - (total_minutes % self.reward_interval)
        
        embed = discord.Embed(title="🎙️ VC滞在ステータス", color=0x2ecc71)
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        
        status_msg = "🟢 計測中..." if is_tracking else "🔴 計測停止中（一人、または除外VC）"
        embed.add_field(name="現在の状態", value=status_msg, inline=False)
        embed.add_field(name="合計滞在（端数込）", value=f"**{total_minutes}** 分", inline=True)
        embed.add_field(name="次の報酬まで", value=f"あと **{next_reward_in}** 分", inline=True)
        
        if any(role.id == self.special_role_id for role in interaction.user.roles):
            embed.set_footer(text=f"✨ ロール特典適用中 ({self.multiplier}倍)")

        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(VCReward(bot))
