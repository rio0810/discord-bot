import discord
from typing import Dict, Optional, List

class HiddenVoiceChannelManager:
    def __init__(self):
        # owner_id: channel_id
        self.channels: Dict[int, int] = {}
        # channel_id: owner_id
        self.channel_owners: Dict[int, int] = {}
        # channel_id: 一度でも誰かが参加したか
        self.joined_status: Dict[int, bool] = {}

    async def create_hidden_vc(self, guild: discord.Guild, owner: discord.Member, category: Optional[discord.CategoryChannel]) -> Optional[discord.VoiceChannel]:
        if owner.id in self.channels:
            return None

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            owner: discord.PermissionOverwrite(view_channel=True, connect=True, manage_channels=True)
        }

        try:
            vc = await guild.create_voice_channel(
                # name=f"🔒 {owner.display_name}の部屋",
                name=f"🔒 | 相談部屋",
                category=category,
                overwrites=overwrites
            )
            self.channels[owner.id] = vc.id
            self.channel_owners[vc.id] = owner.id
            self.joined_status[vc.id] = False
            return vc
        except Exception:
            return None

    async def delete_hidden_vc(self, guild: discord.Guild, owner_id: int) -> bool:
        channel_id = self.channels.pop(owner_id, None)
        if not channel_id:
            return False
        
        self.channel_owners.pop(channel_id, None)
        self.joined_status.pop(channel_id, None)
        
        channel = guild.get_channel(channel_id)
        if channel:
            await channel.delete()
            return True
        return False

    def is_owner(self, channel_id: int, user_id: int) -> bool:
        return self.channel_owners.get(channel_id) == user_id

    def get_owner_by_channel(self, channel_id: int) -> Optional[int]:
        return self.channel_owners.get(channel_id)
