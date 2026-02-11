import discord
from discord.ext import commands, tasks
from discord import app_commands
from datetime import datetime, timezone
import logging

from core.admin_base import AdminCogBase
from core.hidden_base import HiddenVoiceChannelManager
from ui.hidden_ui import HiddenVCControlView

logger = logging.getLogger(__name__)

class VoiceCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.manager = HiddenVoiceChannelManager()
        self.auto_cleaner.start()

    def cog_unload(self):
        self.auto_cleaner.cancel()

    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_any_role(AdminCogBase.ADMIN_ROLE_ID)
    @app_commands.command(name="set_hidden_vc_panel", description="【管理者専用】裏通話作成パネルを設置します")
    async def set_panel(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🔒 裏通話システム",
            description="下のボタンを押すと、あなた専用の隠しVCを作成します。\n作成後、部屋の中のパネルでメンバーを招待できます。",
            color=discord.Color.blue()
        )
        
        view = discord.ui.View(timeout=None)
        create_btn = discord.ui.Button(label="裏通話を作成", style=discord.ButtonStyle.green, emoji="➕", custom_id="persistent:create")
        
        async def create_callback(it: discord.Interaction):
            vc = await self.manager.create_hidden_vc(it.guild, it.user, it.channel.category)
            if vc:
                # VC内にコントロールパネルを送信
                await vc.send(embed=discord.Embed(description="オーナー用操作パネル", color=0x2f3136), view=HiddenVCControlView(self.manager))
                await it.response.send_message(f"✅ {vc.mention} を作成しました！", ephemeral=True)
            else:
                await it.response.send_message("❌ 既に部屋を作成済みか、エラーが発生しました。", ephemeral=True)
        
        create_btn.callback = create_callback
        view.add_item(create_btn)
        
        await interaction.channel.send(embed=embed, view=view)
        await interaction.response.send_message("パネルを設置しました。", ephemeral=True)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        # 参加時：フラグを立てる
        if after.channel and after.channel.id in self.manager.channel_owners:
            self.manager.joined_status[after.channel.id] = True

        # 退出時：無人なら削除
        if before.channel and before.channel.id in self.manager.channel_owners:
            if len(before.channel.members) == 0 and self.manager.joined_status.get(before.channel.id):
                owner_id = self.manager.get_owner_by_channel(before.channel.id)
                if owner_id:
                    await self.manager.delete_hidden_vc(member.guild, owner_id)

    @tasks.loop(minutes=1.0)
    async def auto_cleaner(self):
        """作成から3分以上経過して誰もいないチャンネルを掃除"""
        now = datetime.now(timezone.utc)
        for channel_id in list(self.manager.channel_owners.keys()):
            channel = self.bot.get_channel(channel_id)
            if not channel: continue
            
            diff = (now - channel.created_at).total_seconds()
            if len(channel.members) == 0 and diff > 180:
                owner_id = self.manager.get_owner_by_channel(channel_id)
                if owner_id:
                    await self.manager.delete_hidden_vc(channel.guild, owner_id)

async def setup(bot: commands.Bot):
    await bot.add_cog(VoiceCog(bot))
