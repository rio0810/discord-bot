import discord
import math

class PaginationView(discord.ui.View):
    def __init__(self, data, per_page=10):
        super().__init__(timeout=60)
        self.data = data
        self.per_page = per_page
        self.current_page = 1
        self.max_page = math.ceil(len(data) / per_page)
    
    def create_embed(self):
        start = (self.current_page - 1) * self.per_page
        description = "\n".join(self.data[start:start + self.per_page])
        embed = discord.Embed(title="💰 ユーザーリスト", description=description, color=0x00ff00)
        embed.set_footer(text=f"Page {self.current_page}/{self.max_page}")
        return embed

    @discord.ui.button(label="← 前へ", style=discord.ButtonStyle.gray)
    async def prev(self, interaction, button):
        if self.current_page > 1:
            self.current_page -= 1
            await interaction.response.edit_message(embed=self.create_embed())

    @discord.ui.button(label="次へ →", style=discord.ButtonStyle.gray)
    async def next(self, interaction, button):
        if self.current_page < self.max_page:
            self.current_page += 1
            await interaction.response.edit_message(embed=self.create_embed())
