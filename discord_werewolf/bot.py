import asyncio
import json
import os
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional

import discord
from discord.ext import commands

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID", "0"))
STATE_FILE = Path(os.getenv("STATE_FILE", "discord_werewolf/game_state_discord.json"))
COMMAND_PREFIX = os.getenv("COMMAND_PREFIX", "!")
MAX_PLAYERS = 6

AI_PROFILES = [
    {
        "name": "阿哲",
        "style": "冷靜理性，講話短，喜歡抓矛盾",
        "avatar_url": "https://api.dicebear.com/8.x/adventurer/png?seed=azhe",
    },
    {
        "name": "彼得",
        "style": "話多，喜歡帶節奏",
        "avatar_url": "https://api.dicebear.com/8.x/adventurer/png?seed=peter",
    },
    {
        "name": "小P",
        "style": "裝無辜，容易懷疑別人",
        "avatar_url": "https://api.dicebear.com/8.x/adventurer/png?seed=xiaop",
    },
    {
        "name": "顧問",
        "style": "像分析師，常說機率和邏輯",
        "avatar_url": "https://api.dicebear.com/8.x/adventurer/png?seed=consultant",
    },
    {
        "name": "小羊",
        "style": "膽小保守，常跟票",
        "avatar_url": "https://api.dicebear.com/8.x/adventurer/png?seed=sheep",
    },
    {
        "name": "阿J",
        "style": "嘴砲型，愛挑釁",
        "avatar_url": "https://api.dicebear.com/8.x/adventurer/png?seed=aj",
    },
]
ROLES = ["狼人", "狼人", "預言家", "女巫", "村民", "村民"]


@dataclass
class Player:
    idx: int
    name: str
    style: str
    role: str
    alive: bool = True
    is_human: bool = False
    user_id: Optional[int] = None
    avatar_url: str = ""


def serialize_players(players: List[Player]) -> List[Dict]:
    return [asdict(p) for p in players]


def deserialize_players(data: List[Dict]) -> List[Player]:
    return [Player(**x) for x in data]


def save_state(state: Dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with STATE_FILE.open("w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def load_state() -> Dict:
    with STATE_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def alive_players(players: List[Player]) -> List[Player]:
    return [p for p in players if p.alive]


def villagers_alive(players: List[Player]) -> List[Player]:
    return [p for p in players if p.alive and p.role != "狼人"]


def wolves_alive(players: List[Player]) -> List[Player]:
    return [p for p in players if p.alive and p.role == "狼人"]


def check_win(players: List[Player]) -> Optional[str]:
    wolves = wolves_alive(players)
    villagers = villagers_alive(players)
    if not wolves:
        return "好人"
    if len(wolves) >= len(villagers):
        return "狼人"
    return None


def intro_line(player: Player) -> str:
    lines = {
        "狼人": ["先說，我是好人，這把看發言抓狼。", "大家先別亂票，第一天資訊少。"],
        "預言家": ["我先聽發言，等等再決定站邊。", "先盤一下，太急著定狼的人不太對。"],
        "女巫": ["我偏觀望，先看誰邏輯最怪。", "先別衝票，我想多看一輪。"],
        "村民": ["我是平民視角，先聽大家怎麼聊。", "我先不站死邊，但會抓發言爆點。"],
    }
    return random.choice(lines[player.role])


def accusation_line(target: Player) -> str:
    templates = [
        f"我先點一個，{target.name} 發言有點怪，我目前偏懷疑他。",
        f"如果今天要出票，我會想看 {target.name}，他剛剛像在做身份。",
        f"{target.name} 那個邏輯不太順，我先把票型壓在他身上。",
        f"我覺得 {target.name} 有狼味，先記一票。",
    ]
    return random.choice(templates)


def defense_line() -> str:
    return random.choice(
        [
            "我不是狼，票我真的會投在我最懷疑的人身上。",
            "你們可以懷疑我，但我的發言一直很一致。",
            "我這位置如果是狼不會這樣聊，自己想一下。",
            "先別被帶節奏，我的邏輯很乾淨。",
        ]
    )


def vote_line(target: Player) -> str:
    return random.choice([f"我投 {target.name}。", f"這票我給 {target.name}。", f"我今天先出 {target.name}。"])


def death_line(player: Player) -> str:
    return f"{player.name} 出局，身份是{player.role}。"


class WerewolfDiscordBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix=COMMAND_PREFIX, intents=intents)

        self.game_running = False
        self.lobby_humans: Dict[int, str] = {}
        self.players: List[Player] = []
        self.vote_open = False
        self.current_votes: Dict[int, int] = {}
        self.webhook_cache: Dict[int, discord.Webhook] = {}

    async def setup_hook(self):
        @self.command(name="wolf_join")
        async def wolf_join(ctx: commands.Context):
            if not self._valid_channel(ctx):
                return
            if self.game_running:
                await ctx.send("⚠️ 遊戲進行中，下一局再加入。")
                return
            if len(self.lobby_humans) >= MAX_PLAYERS:
                await ctx.send("⚠️ 大廳已滿（6 人）。")
                return
            self.lobby_humans[ctx.author.id] = ctx.author.display_name
            await ctx.send(f"✅ {ctx.author.mention} 已加入大廳（{len(self.lobby_humans)}/{MAX_PLAYERS}）")

        @self.command(name="wolf_leave")
        async def wolf_leave(ctx: commands.Context):
            if not self._valid_channel(ctx):
                return
            if ctx.author.id in self.lobby_humans:
                self.lobby_humans.pop(ctx.author.id)
                await ctx.send(f"👋 {ctx.author.mention} 已離開大廳。")
            else:
                await ctx.send("你還沒加入大廳。")

        @self.command(name="wolf_lobby")
        async def wolf_lobby(ctx: commands.Context):
            if not self._valid_channel(ctx):
                return
            if not self.lobby_humans:
                await ctx.send("目前大廳沒人，輸入 `!wolf_join` 加入。")
                return
            names = "\n".join(f"- {name}" for name in self.lobby_humans.values())
            await ctx.send(f"目前大廳（{len(self.lobby_humans)}/{MAX_PLAYERS}）：\n{names}")

        @self.command(name="wolf_start")
        async def wolf_start(ctx: commands.Context):
            if not self._valid_channel(ctx):
                return
            if self.game_running:
                await ctx.send("⚠️ 遊戲進行中，請稍候。")
                return
            self.game_running = True
            try:
                await self.run_game(ctx.channel)
            finally:
                self.game_running = False
                self.vote_open = False
                self.current_votes = {}

        @self.command(name="vote")
        async def vote(ctx: commands.Context, *, target_name: str):
            if not self._valid_channel(ctx):
                return
            if not self.vote_open:
                await ctx.send("現在不是投票時間。")
                return
            voter = self._find_player_by_user(ctx.author.id)
            if not voter or not voter.alive:
                await ctx.send("你不是本局存活玩家。")
                return
            target = self._find_alive_player_by_name(target_name)
            if not target:
                await ctx.send("找不到這個存活玩家，請用名字投票。")
                return
            if target.idx == voter.idx:
                await ctx.send("不能投自己。")
                return
            self.current_votes[voter.idx] = target.idx
            await ctx.send(f"🗳️ {ctx.author.display_name} 已投給 {target.name}")

        @self.command(name="wolf_status")
        async def wolf_status(ctx: commands.Context):
            if not self._valid_channel(ctx):
                return
            if not STATE_FILE.exists():
                await ctx.send("目前沒有遊戲紀錄。")
                return
            state = load_state()
            await ctx.send(
                f"狀態: {state.get('status')} / Day: {state.get('day')} / Winner: {state.get('winner', '-')}"
            )

        @self.command(name="wolf_help")
        async def wolf_help(ctx: commands.Context):
            await ctx.send(
                "指令：\n"
                f"`{COMMAND_PREFIX}wolf_join` 加入下一局（真人）\n"
                f"`{COMMAND_PREFIX}wolf_leave` 離開大廳\n"
                f"`{COMMAND_PREFIX}wolf_lobby` 查看大廳\n"
                f"`{COMMAND_PREFIX}wolf_start` 開始（不足 6 人自動補 AI webhook）\n"
                f"`{COMMAND_PREFIX}vote 玩家名稱` 白天投票\n"
                f"`{COMMAND_PREFIX}wolf_status` 查看狀態"
            )

    async def on_ready(self):
        print(f"Logged in as {self.user} ({self.user.id})")
        if CHANNEL_ID:
            channel = self.get_channel(CHANNEL_ID)
            if channel:
                await channel.send("🐺 Werewolf Bot 已上線。輸入 !wolf_help 查看指令。")

    def _valid_channel(self, ctx: commands.Context) -> bool:
        if CHANNEL_ID and ctx.channel.id != CHANNEL_ID:
            return False
        return True

    def _find_player_by_user(self, user_id: int) -> Optional[Player]:
        return next((p for p in self.players if p.user_id == user_id), None)

    def _find_alive_player_by_name(self, name: str) -> Optional[Player]:
        query = name.strip().lower()
        exact = next((p for p in self.players if p.alive and p.name.lower() == query), None)
        if exact:
            return exact
        return next((p for p in self.players if p.alive and query in p.name.lower()), None)

    async def _get_webhook(self, channel: discord.TextChannel) -> discord.Webhook:
        if channel.id in self.webhook_cache:
            return self.webhook_cache[channel.id]
        hooks = await channel.webhooks()
        hook = next((h for h in hooks if h.name == "Werewolf Personas"), None)
        if not hook:
            hook = await channel.create_webhook(name="Werewolf Personas")
        self.webhook_cache[channel.id] = hook
        return hook

    async def send_system(self, channel: discord.abc.Messageable, text: str):
        print(f"[SYSTEM] {text}")
        await channel.send(text)
        await asyncio.sleep(0.9)

    async def send_as_ai(self, channel: discord.TextChannel, player: Player, text: str):
        hook = await self._get_webhook(channel)
        print(f"[{player.name}] {text}")
        await hook.send(text, username=player.name, avatar_url=player.avatar_url or None)
        await asyncio.sleep(1.1)

    async def prompt_human_speak(self, channel: discord.TextChannel, player: Player):
        if not player.user_id:
            return
        await self.send_system(channel, f"🎤 請 {player.name} 發言（20 秒內直接打字）")

        def check(m: discord.Message):
            return m.channel.id == channel.id and m.author.id == player.user_id and len(m.content.strip()) > 0

        try:
            await self.wait_for("message", check=check, timeout=20)
        except asyncio.TimeoutError:
            await self.send_system(channel, f"⏱️ {player.name} 超時，跳過。")

    def build_players(self) -> List[Player]:
        roles = ROLES[:]
        random.shuffle(roles)

        humans = list(self.lobby_humans.items())[:MAX_PLAYERS]
        players: List[Player] = []

        idx = 0
        for user_id, display_name in humans:
            players.append(
                Player(
                    idx=idx,
                    name=display_name,
                    style="真人玩家",
                    role=roles[idx],
                    is_human=True,
                    user_id=user_id,
                )
            )
            idx += 1

        ai_pool = AI_PROFILES[:]
        random.shuffle(ai_pool)
        while idx < MAX_PLAYERS:
            profile = ai_pool.pop()
            players.append(
                Player(
                    idx=idx,
                    name=profile["name"],
                    style=profile["style"],
                    role=roles[idx],
                    is_human=False,
                    avatar_url=profile["avatar_url"],
                )
            )
            idx += 1

        return players

    async def night_phase(self, channel: discord.TextChannel, players: List[Player], day: int):
        await self.send_system(channel, f"🌙 第 {day} 夜開始，天黑請閉眼。")

        wolves = wolves_alive(players)
        others = villagers_alive(players)
        kill = random.choice(others) if wolves and others else None

        seer = next((p for p in players if p.alive and p.role == "預言家"), None)
        witch = next((p for p in players if p.alive and p.role == "女巫"), None)

        if seer:
            targets = [p for p in players if p.alive and p.idx != seer.idx]
            if targets:
                checked = random.choice(targets)
                await self.send_system(channel, f"🔮 預言家查驗了 {checked.name}：{'狼人' if checked.role == '狼人' else '好人'}")

        saved = False
        poisoned = None
        if witch and kill and random.random() < 0.45:
            saved = True
            await self.send_system(channel, "🧪 女巫今晚使用了解藥。")

        if witch and random.random() < 0.25:
            poison_targets = [p for p in players if p.alive and p.role == "狼人"]
            if poison_targets:
                poisoned = random.choice(poison_targets)
                poisoned.alive = False
                await self.send_system(channel, "☠️ 女巫今晚用了毒藥。")

        deaths = []
        if kill and not saved:
            kill.alive = False
            deaths.append(kill)
        if poisoned:
            deaths.append(poisoned)

        if not deaths:
            await self.send_system(channel, "🌤 天亮了，昨晚是平安夜。")
            return

        await self.send_system(channel, "🌤 天亮了。")
        seen = set()
        for d in deaths:
            if d.idx not in seen:
                await self.send_system(channel, death_line(d))
                seen.add(d.idx)

    async def discussion_phase(self, channel: discord.TextChannel, players: List[Player], day: int):
        await self.send_system(channel, f"🗣 第 {day} 天討論開始。")
        alive = alive_players(players)

        for p in alive:
            if p.is_human:
                await self.prompt_human_speak(channel, p)
            else:
                await self.send_as_ai(channel, p, intro_line(p))

        for p in alive:
            choices = [x for x in alive if x.idx != p.idx and x.alive]
            if not choices:
                continue
            target = random.choice(choices)
            if p.is_human:
                await self.send_system(channel, f"👉 {p.name} 若想補充可繼續發言。")
            else:
                await self.send_as_ai(channel, p, accusation_line(target))

        if alive:
            target = random.choice(alive)
            if target.is_human:
                await self.send_system(channel, f"🛡️ {target.name} 想自辯可直接發言。")
                await asyncio.sleep(2)
            else:
                await self.send_as_ai(channel, target, defense_line())

    async def voting_phase(self, channel: discord.TextChannel, players: List[Player], day: int):
        await self.send_system(channel, f"🗳 第 {day} 天投票開始。真人請用 `!vote 名字`，限時 45 秒。")
        alive = alive_players(players)
        self.vote_open = True
        self.current_votes = {}

        human_alive = [p for p in alive if p.is_human]
        ai_alive = [p for p in alive if not p.is_human]

        for p in ai_alive:
            choices = [x for x in alive if x.idx != p.idx]
            target = random.choice(choices)
            self.current_votes[p.idx] = target.idx
            await self.send_as_ai(channel, p, vote_line(target))

        end_at = asyncio.get_event_loop().time() + 45
        while asyncio.get_event_loop().time() < end_at:
            pending = [p for p in human_alive if p.idx not in self.current_votes and p.alive]
            if not pending:
                break
            await asyncio.sleep(1)

        pending = [p for p in human_alive if p.idx not in self.current_votes and p.alive]
        for p in pending:
            choices = [x for x in alive if x.idx != p.idx]
            target = random.choice(choices)
            self.current_votes[p.idx] = target.idx
            await self.send_system(channel, f"⏱️ {p.name} 超時，系統代投 {target.name}。")

        self.vote_open = False

        tally: Dict[int, int] = {}
        for target_idx in self.current_votes.values():
            tally[target_idx] = tally.get(target_idx, 0) + 1

        out_idx = max(tally, key=tally.get)
        out = next(p for p in players if p.idx == out_idx)
        out.alive = False

        result_lines = []
        for target_idx, count in sorted(tally.items(), key=lambda x: x[1], reverse=True):
            name = next(p.name for p in players if p.idx == target_idx)
            result_lines.append(f"{name}: {count}")

        await self.send_system(channel, "📊 票型：\n" + "\n".join(result_lines))
        await self.send_system(channel, f"📢 票型結算，{out.name} 被放逐。")
        await self.send_system(channel, death_line(out))

    async def reveal_roles(self, channel: discord.TextChannel, players: List[Player]):
        lines = [f"{p.name}：{p.role}" for p in players]
        await self.send_system(channel, "📜 本局身份公布：\n" + "\n".join(lines))

    async def run_game(self, channel: discord.TextChannel):
        self.players = self.build_players()
        players = self.players

        humans = [p.name for p in players if p.is_human]
        ai_count = len([p for p in players if not p.is_human])

        await self.send_system(channel, "🎭 狼人殺 6 人局開始。")
        await self.send_system(channel, f"真人：{', '.join(humans) if humans else '0 人'}；AI 補位：{ai_count} 人")
        await self.send_system(channel, "玩家：" + "、".join(p.name for p in players))

        save_state({"players": serialize_players(players), "day": 1, "status": "running"})

        day = 1
        while True:
            players = deserialize_players(load_state()["players"])
            self.players = players

            await self.night_phase(channel, players, day)
            winner = check_win(players)
            save_state({"players": serialize_players(players), "day": day, "status": "running"})
            if winner:
                await self.send_system(channel, f"🏁 遊戲結束，{winner}陣營獲勝！")
                await self.reveal_roles(channel, players)
                save_state(
                    {"players": serialize_players(players), "day": day, "status": "finished", "winner": winner}
                )
                self.lobby_humans = {}
                return

            await self.discussion_phase(channel, players, day)
            await self.voting_phase(channel, players, day)
            winner = check_win(players)
            save_state({"players": serialize_players(players), "day": day + 1, "status": "running"})
            if winner:
                await self.send_system(channel, f"🏁 遊戲結束，{winner}陣營獲勝！")
                await self.reveal_roles(channel, players)
                save_state(
                    {"players": serialize_players(players), "day": day, "status": "finished", "winner": winner}
                )
                self.lobby_humans = {}
                return

            day += 1


def main():
    if not TOKEN:
        raise RuntimeError("Missing DISCORD_BOT_TOKEN")
    if not CHANNEL_ID:
        raise RuntimeError("Missing DISCORD_CHANNEL_ID")

    random.seed()
    bot = WerewolfDiscordBot()
    bot.run(TOKEN)


if __name__ == "__main__":
    main()
