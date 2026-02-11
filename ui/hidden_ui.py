import discord

class InviteUserSelect(discord.ui.UserSelect):
    def __init__(self):
        super().__init__(placeholder="招待するメンバーを選んでください...", min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        target = self.values[0]
        # 権限付与
        await interaction.channel.set_permissions(target, view_channel=True, connect=True)
        await interaction.response.send_message(f"✅ {target.mention} を招待しました。")

class HiddenVCControlView(discord.ui.View):
    """作成されたVCの中に送信される操作パネル"""
    def __init__(self, manager):
        super().__init__(timeout=None)
        self.manager = manager

    @discord.ui.button(label="メンバーを招待", style=discord.ButtonStyle.primary, emoji="👤", custom_id="persistent:invite")
    async def invite(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.manager.is_owner(interaction.channel_id, interaction.user.id):
            return await interaction.response.send_message("❌ あなたはこの部屋のオーナーではありません。", ephemeral=True)
        
        view = discord.ui.View().add_item(InviteUserSelect())
        await interaction.response.send_message("招待するユーザーを選択してください：", view=view, ephemeral=True)

    @discord.ui.button(label="部屋を削除", style=discord.ButtonStyle.danger, emoji="🗑️", custom_id="persistent:delete")
    async def delete_self(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.manager.is_owner(interaction.channel_id, interaction.user.id):
            return await interaction.response.send_message("❌ オーナーのみ削除可能です。", ephemeral=True)
        
        await interaction.response.send_message("部屋を削除します...", ephemeral=True)
        await self.manager.delete_hidden_vc(interaction.guild, interaction.user.id)
