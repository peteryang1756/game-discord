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

PLAYER_PROFILES = [
    {"name": "阿哲", "style": "冷靜理性，講話短，喜歡抓矛盾"},
    {"name": "彼得", "style": "話多，喜歡帶節奏"},
    {"name": "小P", "style": "裝無辜，容易懷疑別人"},
    {"name": "顧問", "style": "像分析師，常說機率和邏輯"},
    {"name": "小羊", "style": "膽小保守，常跟票"},
    {"name": "阿J", "style": "嘴砲型，愛挑釁"},
]
ROLES = ["狼人", "狼人", "預言家", "女巫", "村民", "村民"]


@dataclass
class Player:
    idx: int
    name: str
    style: str
    role: str
    alive: bool = True


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
        "狼人": [
            "先說，我是好人，這把看發言抓狼。",
            "大家先別亂票，第一天資訊少。",
        ],
        "預言家": [
            "我先聽發言，等等再決定站邊。",
            "先盤一下，太急著定狼的人不太對。",
        ],
        "女巫": [
            "我偏觀望，先看誰邏輯最怪。",
            "先別衝票，我想多看一輪。",
        ],
        "村民": [
            "我是平民視角，先聽大家怎麼聊。",
            "我先不站死邊，但會抓發言爆點。",
        ],
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
    templates = [
        "我不是狼，票我真的會投在我最懷疑的人身上。",
        "你們可以懷疑我，但我的發言一直很一致。",
        "我這位置如果是狼不會這樣聊，自己想一下。",
        "先別被帶節奏，我的邏輯很乾淨。",
    ]
    return random.choice(templates)


def vote_line(target: Player) -> str:
    templates = [
        f"我投 {target.name}。",
        f"這票我給 {target.name}。",
        f"我今天先出 {target.name}。",
    ]
    return random.choice(templates)


def death_line(player: Player) -> str:
    return f"{player.name} 出局，身份是{player.role}。"


def assign_players() -> List[Player]:
    roles = ROLES[:]
    random.shuffle(roles)
    return [
        Player(idx=i, name=p["name"], style=p["style"], role=roles[i])
        for i, p in enumerate(PLAYER_PROFILES)
    ]


class WerewolfDiscordBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix=COMMAND_PREFIX, intents=intents)
        self.game_running = False

    async def setup_hook(self):
        @self.command(name="wolf_start")
        async def wolf_start(ctx: commands.Context):
            if CHANNEL_ID and ctx.channel.id != CHANNEL_ID:
                return
            if self.game_running:
                await ctx.send("⚠️ 遊戲進行中，請稍候。")
                return
            self.game_running = True
            try:
                await self.run_game(ctx.channel)
            finally:
                self.game_running = False

        @self.command(name="wolf_status")
        async def wolf_status(ctx: commands.Context):
            if not STATE_FILE.exists():
                await ctx.send("目前沒有遊戲紀錄。")
                return
            state = load_state()
            await ctx.send(f"狀態: {state.get('status')} / Day: {state.get('day')} / Winner: {state.get('winner', '-')}")

        @self.command(name="wolf_help")
        async def wolf_help(ctx: commands.Context):
            await ctx.send(
                "指令：\n"
                f"`{COMMAND_PREFIX}wolf_start` 開始一局\n"
                f"`{COMMAND_PREFIX}wolf_status` 查看狀態\n"
                f"`{COMMAND_PREFIX}wolf_help` 顯示說明"
            )

    async def on_ready(self):
        print(f"Logged in as {self.user} ({self.user.id})")
        if CHANNEL_ID:
            channel = self.get_channel(CHANNEL_ID)
            if channel:
                await channel.send("🐺 Werewolf Discord Bot 已上線，輸入 !wolf_help 查看指令。")

    async def send_system(self, channel: discord.abc.Messageable, text: str):
        print(f"[SYSTEM] {text}")
        await channel.send(text)
        await asyncio.sleep(1.0)

    async def send_as(self, channel: discord.abc.Messageable, player: Player, text: str):
        line = f"**[{player.name}]** {text}"
        print(line)
        await channel.send(line)
        await asyncio.sleep(1.4)

    async def night_phase(self, channel: discord.abc.Messageable, players: List[Player], day: int):
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

    async def discussion_phase(self, channel: discord.abc.Messageable, players: List[Player], day: int):
        await self.send_system(channel, f"🗣 第 {day} 天討論開始。")
        alive = alive_players(players)
        for p in alive:
            await self.send_as(channel, p, intro_line(p))
        for p in alive:
            choices = [x for x in alive if x.idx != p.idx and x.alive]
            if choices:
                target = random.choice(choices)
                await self.send_as(channel, p, accusation_line(target))

        if alive:
            target = random.choice(alive)
            await self.send_as(channel, target, defense_line())

    async def voting_phase(self, channel: discord.abc.Messageable, players: List[Player], day: int):
        await self.send_system(channel, f"🗳 第 {day} 天投票開始。")
        alive = alive_players(players)
        votes = {}
        for p in alive:
            choices = [x for x in alive if x.idx != p.idx]
            target = random.choice(choices)
            votes[target.idx] = votes.get(target.idx, 0) + 1
            await self.send_as(channel, p, vote_line(target))

        out_idx = max(votes, key=votes.get)
        out = next(p for p in players if p.idx == out_idx)
        out.alive = False
        await self.send_system(channel, f"📢 票型結算，{out.name} 被放逐。")
        await self.send_system(channel, death_line(out))

    async def reveal_roles(self, channel: discord.abc.Messageable, players: List[Player]):
        lines = [f"{p.name}：{p.role}" for p in players]
        await self.send_system(channel, "📜 本局身份公布：\n" + "\n".join(lines))

    async def run_game(self, channel: discord.abc.Messageable):
        players = assign_players()
        await self.send_system(channel, "🎭 狼人殺 6 人局開始。角色已分配。")
        await self.send_system(channel, "玩家：" + "、".join(p.name for p in players))
        save_state({"players": serialize_players(players), "day": 1, "status": "running"})

        day = 1
        while True:
            players = deserialize_players(load_state()["players"])
            await self.night_phase(channel, players, day)
            winner = check_win(players)
            save_state({"players": serialize_players(players), "day": day, "status": "running"})
            if winner:
                await self.send_system(channel, f"🏁 遊戲結束，{winner}陣營獲勝！")
                await self.reveal_roles(channel, players)
                save_state({"players": serialize_players(players), "day": day, "status": "finished", "winner": winner})
                return

            await self.discussion_phase(channel, players, day)
            await self.voting_phase(channel, players, day)
            winner = check_win(players)
            save_state({"players": serialize_players(players), "day": day + 1, "status": "running"})
            if winner:
                await self.send_system(channel, f"🏁 遊戲結束，{winner}陣營獲勝！")
                await self.reveal_roles(channel, players)
                save_state({"players": serialize_players(players), "day": day, "status": "finished", "winner": winner})
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
