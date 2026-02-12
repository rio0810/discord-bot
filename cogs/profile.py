import discord
from discord.ext import commands
import os

class VoiceProfile(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        env_channels = os.getenv("PROFILE_TARGET_CHANNEL_IDS", "")
        if env_channels:
            self.profile_target_channel_ids = [int(id_str.strip()) for id_str in env_channels.split(",")]
        else:
            self.profile_target_channel_ids = []
            
        self.sent_messages = {}

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot:
            return

        if before.channel == after.channel:
            return

        # --- 古いメッセージを削除する処理 ---
        # 以前のチャンネルにメッセージが残っていれば、移動・退出に関わらず削除する
        bot_msg = self.sent_messages.pop(member.id, None)
        if bot_msg:
            try:
                await bot_msg.delete()
            except (discord.NotFound, discord.Forbidden):
                pass

        # --- 新しいチャンネルにメッセージを送る処理 ---
        if after.channel is not None:
            latest_message = None

            # プロフィール投稿用チャンネルから最新の投稿を探す
            for channel_id in self.profile_target_channel_ids:
                channel = self.bot.get_channel(channel_id)
                if channel:
                    async for msg in channel.history(limit=100):
                        if msg.author.id == member.id:
                            if latest_message is None or msg.created_at > latest_message.created_at:
                                latest_message = msg
                            break

            if latest_message:
                embed = discord.Embed(
                    title=f"{member.display_name} さんのプロフィール",
                    description=latest_message.content or "（本文なし）",
                    color=discord.Color.blue(),
                    timestamp=latest_message.created_at
                )
                embed.set_author(
                    name=f"{member.display_name} (@{member.name})",
                    icon_url=member.display_avatar.url
                )
                
                if latest_message.attachments:
                    embed.set_image(url=latest_message.attachments[0].url)

                view = discord.ui.View()
                btn = discord.ui.Button(
                    label="プロフィールへ移動",
                    url=latest_message.jump_url,
                    style=discord.ButtonStyle.link
                )
                view.add_item(btn)

                # 新しいチャンネルに送信し、記録を更新
                try:
                    bot_msg = await after.channel.send(view=view, embed=embed)
                    self.sent_messages[member.id] = bot_msg
                except discord.Forbidden:
                    print(f"チャンネル {after.channel.name} でメッセージ送信権限がありません。")

async def setup(bot):
    await bot.add_cog(VoiceProfile(bot))
