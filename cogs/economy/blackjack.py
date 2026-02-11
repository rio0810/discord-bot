import discord
from discord import app_commands
from discord.ext import commands
import random
from core.db_base import EconomyBase

# --- ブラックジャックのロジック用関数 ---
def get_card_value(card):
    """カードの文字列（例: ♠A, ♣10）から数値を返す"""
    rank = card[1:]
    if rank in ["J", "Q", "K"]:
        return 10
    if rank == "A":
        return 11
    return int(rank)

def calculate_score(hand):
    """手札の合計値を計算し、Aの調整を行う"""
    score = sum(get_card_value(card) for card in hand)
    aces = sum(1 for card in hand if card[1:] == "A")
    while score > 21 and aces:
        score -= 10
        aces -= 1
    return score

# --- ゲーム画面のインタラクション（ボタン） ---
class BlackjackView(discord.ui.View):
    def __init__(self, interaction, bet, cog):
        super().__init__(timeout=60)
        self.interaction = interaction
        self.bet = bet
        self.cog = cog
        # 山札の作成
        suits = ["♠", "♥", "♦", "♣"]
        ranks = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
        self.deck = [f"{s}{r}" for s in suits for r in ranks]
        random.shuffle(self.deck)
        
        # 初期配分
        self.player_hand = [self.deck.pop(), self.deck.pop()]
        self.dealer_hand = [self.deck.pop(), self.deck.pop()]

    def create_embed(self, finished=False):
        p_score = calculate_score(self.player_hand)
        d_score = calculate_score(self.dealer_hand)
        
        # 進行状況に合わせて色を変える
        color = 0x2f3136 # デフォルト（グレー）
        if finished:
            if p_score > 21: color = 0xe74c3c # 赤（負け）
            elif d_score > 21 or p_score > d_score: color = 0x2ecc71 # 緑（勝ち）
            elif p_score < d_score: color = 0xe74c3c # 赤（負け）
            else: color = 0xf1c40f # 黄（引き分け）

        embed = discord.Embed(title="🃏 ブラックジャック", color=color)
        embed.add_field(name=f"あなたの手 (計 {p_score})", value=" ".join(self.player_hand), inline=False)
        
        if finished:
            embed.add_field(name=f"ディーラーの手 (計 {d_score})", value=" ".join(self.dealer_hand), inline=False)
        else:
            embed.add_field(name="ディーラーの手", value=f"{self.dealer_hand[0]} 🎴", inline=False)
            
        return embed

    @discord.ui.button(label="ヒット (引く)", style=discord.ButtonStyle.primary)
    async def hit(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.interaction.user:
            return await interaction.response.send_message("これはあなたのゲームではありません。", ephemeral=True)

        # 2枚以上になったらダブルダウンはできない
        self.double_down.disabled = True
        
        self.player_hand.append(self.deck.pop())
        if calculate_score(self.player_hand) > 21:
            await self.end_game(interaction, "バースト！あなたの負けです 💸", -self.bet)
        else:
            await interaction.response.edit_message(embed=self.create_embed(), view=self)

    @discord.ui.button(label="ダブルダウン", style=discord.ButtonStyle.danger)
    async def double_down(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.interaction.user:
            return await interaction.response.send_message("これはあなたのゲームではありません。", ephemeral=True)

        # 追加の賭け金が払えるか確認
        if self.cog.get_balance_logic(interaction.user.id) < self.bet * 2:
            return await interaction.response.send_message("ダブルダウンするための残高が足りません！", ephemeral=True)

        self.bet *= 2
        self.player_hand.append(self.deck.pop())
        
        # ダブルダウンは1枚引いて強制終了
        if calculate_score(self.player_hand) > 21:
            await self.end_game(interaction, "バースト！(倍賭け失敗) 💸💸", -self.bet)
        else:
            await self.dealer_turn(interaction)

    @discord.ui.button(label="スタンド (勝負)", style=discord.ButtonStyle.secondary)
    async def stand(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.interaction.user:
            return await interaction.response.send_message("これはあなたのゲームではありません。", ephemeral=True)
        await self.dealer_turn(interaction)

    async def dealer_turn(self, interaction):
        """ディーラーの思考ロジック"""
        while calculate_score(self.dealer_hand) < 17:
            self.dealer_hand.append(self.deck.pop())

        p_score = calculate_score(self.player_hand)
        d_score = calculate_score(self.dealer_hand)

        if d_score > 21:
            await self.end_game(interaction, "ディーラーがバースト！あなたの勝ちです 🎉", self.bet)
        elif p_score > d_score:
            await self.end_game(interaction, "おめでとうございます！あなたの勝ちです 🎉", self.bet)
        elif p_score < d_score:
            await self.end_game(interaction, "残念、ディーラーの勝ちです 💸", -self.bet)
        else:
            await self.end_game(interaction, "引き分け（プッシュ）です 🤝", 0)

    async def end_game(self, interaction, message, profit):
        """ゲーム終了時の処理、DB更新とUI更新"""
        self.cog.update_balance_logic(self.interaction.user.id, profit)
        
        for btn in self.children:
            btn.disabled = True
            
        final_embed = self.create_embed(finished=True)
        result_msg = f"### {message}\n"
        if profit > 0:
            result_msg += f"💰 **+{profit}** コイン獲得！"
        elif profit < 0:
            result_msg += f"📉 **{abs(profit)}** コイン失いました..."
        else:
            result_msg += "🪙 コインの変動はありません。"
            
        final_embed.add_field(name="最終結果", value=result_msg, inline=False)
        await interaction.response.edit_message(embed=final_embed, view=self)
        self.stop()

# --- コグクラス ---
class Blackjack(commands.Cog, EconomyBase):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    @app_commands.command(name="blackjack", description="ブラックジャックに挑戦します（ダブルダウン対応）")
    @app_commands.describe(bet="賭ける金額")
    async def blackjack(self, interaction: discord.Interaction, bet: int):
        if bet <= 0:
            return await interaction.response.send_message("1枚以上賭けてください。", ephemeral=True)
        
        current_bal = self.get_balance_logic(interaction.user.id)
        if current_bal < bet:
            return await interaction.response.send_message("残高が足りません！", ephemeral=True)

        view = BlackjackView(interaction, bet, self)
        await interaction.response.send_message(embed=view.create_embed(), view=view)

async def setup(bot):
    await bot.add_cog(Blackjack(bot))
