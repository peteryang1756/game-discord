import asyncio
import json
import os
import random
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import discord
from discord.ext import commands

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID", "0"))
COMMAND_PREFIX = os.getenv("COMMAND_PREFIX", "!")
STATE_FILE = Path(os.getenv("STATE_FILE", "discord_werewolf/game_state_discord.json"))

LLM_API_BASE = os.getenv("LLM_API_BASE", "https://elysiver.h-e.top/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-5.4")
TURN_SLEEP = float(os.getenv("TURN_SLEEP", "1.8"))
OPENING_SLEEP = float(os.getenv("OPENING_SLEEP", "1.2"))
MAX_DAYS = int(os.getenv("MAX_DAYS", "6"))
DRY_RUN = os.getenv("DRY_RUN", "0") == "1"

AI_PROFILES = [
    {
        "name": "阿哲",
        "style": "冷靜理性，講話短，喜歡抓矛盾，不容易被帶風向。",
        "avatar_url": "https://api.dicebear.com/8.x/adventurer/png?seed=azhe",
    },
    {
        "name": "彼得",
        "style": "話多，擅長帶節奏，喜歡先站邊再找理由。",
        "avatar_url": "https://api.dicebear.com/8.x/adventurer/png?seed=peter",
    },
    {
        "name": "小P",
        "style": "看似無辜，實際很會自保，被攻擊會立刻回擊。",
        "avatar_url": "https://api.dicebear.com/8.x/adventurer/png?seed=xiaop",
    },
    {
        "name": "顧問",
        "style": "像分析師，常談機率、資訊量、行為一致性。",
        "avatar_url": "https://api.dicebear.com/8.x/adventurer/png?seed=consultant",
    },
    {
        "name": "小羊",
        "style": "偏保守，膽小，容易跟票，但偶爾會突然很準。",
        "avatar_url": "https://api.dicebear.com/8.x/adventurer/png?seed=sheep",
    },
    {
        "name": "阿J",
        "style": "嘴砲型，愛挑釁，會故意戳別人反應。",
        "avatar_url": "https://api.dicebear.com/8.x/adventurer/png?seed=aj",
    },
]
ROLES = ["狼人", "狼人", "預言家", "女巫", "村民", "村民"]

SYSTEM_PROMPT = """
你在扮演真人玩家玩中文狼人殺，不要提到自己是AI、模型、程式。
輸出要像Telegram群組裡真人講話，自然、口語、短句為主。
遵守身份資訊邊界：只能使用你該知道的資訊。
不要代替別人說話，不要輸出旁白，不要用列表。
如果要求輸出JSON，必須輸出合法JSON，不能包 markdown。
""".strip()


@dataclass
class Agent:
    idx: int
    name: str
    style: str
    role: str
    avatar_url: str = ""
    alive: bool = True
    revealed_role: Optional[str] = None
    private_notes: List[str] = field(default_factory=list)
    public_memory: List[str] = field(default_factory=list)
    suspicion: Dict[str, float] = field(default_factory=dict)
    relations: Dict[str, str] = field(default_factory=dict)
    last_target: Optional[str] = None

    def short_state(self) -> Dict:
        return {
            "name": self.name,
            "role": self.role,
            "alive": self.alive,
            "revealed_role": self.revealed_role,
            "private_notes": self.private_notes[-12:],
            "public_memory": self.public_memory[-18:],
            "suspicion": self.suspicion,
            "relations": self.relations,
            "last_target": self.last_target,
        }


def save_state(state: Dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with STATE_FILE.open("w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def load_state() -> Dict:
    with STATE_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def deserialize_agents(data: List[Dict]) -> List[Agent]:
    return [Agent(**x) for x in data]


class LLM:
    def __init__(self, api_base: str, api_key: str, model: str):
        self.api_base = api_base.rstrip("/")
        self.api_key = api_key
        self.model = model

    def chat(self, messages: List[Dict], temperature: float = 0.9) -> str:
        url = f"{self.api_base}/chat/completions"
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "discord-werewolf/1.0",
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=90) as r:
            data = json.loads(r.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"].strip()


class WerewolfDiscordBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix=COMMAND_PREFIX, intents=intents)
        self.game_running = False
        self.webhook_cache: Dict[int, discord.Webhook] = {}
        self.llm = LLM(LLM_API_BASE, LLM_API_KEY, LLM_MODEL)
        self.agents: List[Agent] = []
        self.day = 1
        self.phase = "init"
        self.log: List[str] = []
        self.witch_heal_used = False
        self.witch_poison_used = False
        self.seer_checks: List[str] = []

    async def setup_hook(self):
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

        @self.command(name="start")
        async def start_alias(ctx: commands.Context):
            await ctx.invoke(self.get_command("wolf_start"))

        @self.command(name="wolf_status")
        async def wolf_status(ctx: commands.Context):
            if not self._valid_channel(ctx):
                return
            if not STATE_FILE.exists():
                await ctx.send("目前沒有遊戲紀錄。")
                return
            state = load_state()
            await ctx.send(
                " / ".join(
                    [
                        f"status: {state.get('status', '-')}",
                        f"day: {state.get('day', '-')}",
                        f"phase: {state.get('phase', '-')}",
                        f"winner: {state.get('winner', '-')}",
                    ]
                )
            )

        @self.command(name="wolf_help")
        async def wolf_help(ctx: commands.Context):
            await ctx.send(
                "指令：\n"
                f"`{COMMAND_PREFIX}wolf_start` 或 `{COMMAND_PREFIX}start` 開始全 AI Agent + LLM 狼人殺\n"
                f"`{COMMAND_PREFIX}wolf_status` 查看局面狀態\n"
                f"`{COMMAND_PREFIX}wolf_help` 顯示說明"
            )

    async def on_ready(self):
        print(f"Logged in as {self.user} ({self.user.id})")
        if CHANNEL_ID:
            channel = self.get_channel(CHANNEL_ID)
            if channel and not DRY_RUN:
                await channel.send(f"🐺 Werewolf Bot 已上線。輸入 {COMMAND_PREFIX}wolf_help 查看指令。")

    def _valid_channel(self, ctx: commands.Context) -> bool:
        return not CHANNEL_ID or ctx.channel.id == CHANNEL_ID

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
        self.log.append(f"[SYSTEM] {text}")
        print(f"[SYSTEM] {text}")
        if not DRY_RUN:
            await channel.send(text)
        await asyncio.sleep(OPENING_SLEEP)

    async def send_agent(self, channel: discord.TextChannel, agent: Agent, text: str):
        text = text.strip().replace("\n", " ")
        if not text:
            text = "我先保留，等等再補。"
        self.log.append(f"[{agent.name}] {text}")
        print(f"[{agent.name}] {text}")
        if not DRY_RUN:
            hook = await self._get_webhook(channel)
            await hook.send(text, username=agent.name, avatar_url=agent.avatar_url or None)
        await asyncio.sleep(TURN_SLEEP)
        for other in self.alive_agents():
            if other.name == agent.name:
                continue
            other.public_memory.append(f"{agent.name} 說：{text}")
            if agent.name in other.suspicion and any(k in text for k in ["怪", "狼", "不對", "做身份", "帶節奏"]):
                other.suspicion[agent.name] = round(min(0.99, other.suspicion[agent.name] + 0.03), 2)

    def build_agents(self) -> List[Agent]:
        roles = ROLES[:]
        random.shuffle(roles)
        agents: List[Agent] = []
        names = [x["name"] for x in AI_PROFILES]
        for i, profile in enumerate(AI_PROFILES):
            agent = Agent(
                idx=i,
                name=profile["name"],
                style=profile["style"],
                role=roles[i],
                avatar_url=profile["avatar_url"],
            )
            agent.suspicion = {n: round(random.uniform(0.18, 0.48), 2) for n in names if n != agent.name}
            if agent.role == "狼人":
                mates = [x.name for x in agents if x.role == "狼人"] + [
                    AI_PROFILES[j]["name"] for j in range(i + 1, len(roles)) if roles[j] == "狼人"
                ]
                if mates:
                    agent.private_notes.append(f"你的狼人隊友是：{mates[0]}")
            if agent.role == "女巫":
                agent.private_notes.append("你有一瓶解藥與一瓶毒藥，各只能用一次。")
            if agent.role == "預言家":
                agent.private_notes.append("每晚可查驗一人是好人或狼人。")
            agents.append(agent)
        return agents

    def alive_agents(self) -> List[Agent]:
        return [a for a in self.agents if a.alive]

    def wolves_alive(self) -> List[Agent]:
        return [a for a in self.agents if a.alive and a.role == "狼人"]

    def villagers_alive(self) -> List[Agent]:
        return [a for a in self.agents if a.alive and a.role != "狼人"]

    def winner(self) -> Optional[str]:
        wolves = self.wolves_alive()
        villagers = self.villagers_alive()
        if not wolves:
            return "好人"
        if len(wolves) >= len(villagers):
            return "狼人"
        return None

    def public_snapshot(self) -> str:
        alive = "、".join(a.name for a in self.alive_agents())
        dead = "、".join(f"{a.name}({a.role})" for a in self.agents if not a.alive) or "無"
        recent = "\n".join(self.log[-14:]) or "無"
        return f"存活：{alive}\n出局：{dead}\n最近對話：\n{recent}"

    def private_snapshot(self, agent: Agent) -> str:
        return json.dumps(agent.short_state(), ensure_ascii=False)

    async def _llm_chat(self, messages: List[Dict], temperature: float) -> str:
        return await asyncio.to_thread(self.llm.chat, messages, temperature)

    async def text_response(self, messages: List[Dict], fallback: str) -> str:
        try:
            text = (await self._llm_chat(messages, 0.95)).strip()
            return text or fallback
        except Exception:
            return fallback

    async def json_response(self, messages: List[Dict], fallback: Dict) -> Dict:
        try:
            raw = (await self._llm_chat(messages, 0.8)).strip()
            if raw.startswith("```"):
                raw = raw.strip("`")
                raw = raw.split("\n", 1)[-1]
            return json.loads(raw)
        except Exception:
            return fallback

    async def think_speech(self, agent: Agent, context: str, goal: str, fallback: str) -> str:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"你是玩家「{agent.name}」。\n人格：{agent.style}\n身份：{agent.role}\n\n"
                    f"你的私人狀態：{self.private_snapshot(agent)}\n\n公開局勢：\n{context}\n\n"
                    f"當前任務：{goal}\n\n請只輸出一段 18 到 60 字的 Telegram 群組發言。\n不要加引號，不要解釋。"
                ),
            },
        ]
        return await self.text_response(messages, fallback)

    async def think_vote(self, agent: Agent) -> Tuple[str, str]:
        alive_targets = [a.name for a in self.alive_agents() if a.name != agent.name]
        top = sorted(agent.suspicion.items(), key=lambda kv: kv[1], reverse=True)
        fallback = {
            "target": next((n for n, _ in top if n in alive_targets), random.choice(alive_targets)),
            "reason": "我先投最可疑的。",
        }
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"你是玩家「{agent.name}」。\n身份：{agent.role}\n人格：{agent.style}\n\n"
                    f"可投票對象：{alive_targets}\n你的私人狀態：{self.private_snapshot(agent)}\n"
                    f"公開局勢：\n{self.public_snapshot()}\n\n"
                    '請輸出 JSON：{"target":"名字","reason":"20字內理由"}\n只能從可投票對象選一人。'
                ),
            },
        ]
        data = await self.json_response(messages, fallback)
        target = str(data.get("target", fallback["target"]))
        if target not in alive_targets:
            target = fallback["target"]
        reason = str(data.get("reason", fallback["reason"]))[:40]
        return target, reason

    def seer_action(self):
        seer = next((a for a in self.agents if a.alive and a.role == "預言家"), None)
        if not seer:
            return
        candidates = [a for a in self.alive_agents() if a.name != seer.name]
        if not candidates:
            return
        unchecked = [a for a in candidates if a.name not in " ".join(self.seer_checks)]
        target = random.choice(unchecked or candidates)
        result = "狼人" if target.role == "狼人" else "好人"
        note = f"你昨晚查驗 {target.name}，結果是：{result}。"
        self.seer_checks.append(note)
        seer.private_notes.append(note)
        seer.suspicion[target.name] = 0.99 if result == "狼人" else 0.05

    def wolf_kill_target(self) -> Agent:
        wolves = self.wolves_alive()
        targets = [a for a in self.alive_agents() if a.role != "狼人"]
        if not targets:
            return random.choice(self.alive_agents())
        score: Dict[str, float] = {}
        for target in targets:
            score[target.name] = 0.0
            if target.role == "預言家":
                score[target.name] += 0.35
            if target.role == "女巫":
                score[target.name] += 0.20
            score[target.name] += random.random() * 0.25
            for w in wolves:
                score[target.name] += w.suspicion.get(target.name, 0) * 0.2
        best = max(score, key=score.get)
        return next(a for a in targets if a.name == best)

    def witch_action(self, victim: Optional[Agent]) -> Tuple[bool, Optional[Agent]]:
        witch = next((a for a in self.agents if a.alive and a.role == "女巫"), None)
        saved = False
        poisoned = None
        if not witch:
            return saved, poisoned
        if victim and not self.witch_heal_used:
            use_heal = victim.role in ("預言家", "女巫") or random.random() < 0.38
            if use_heal:
                self.witch_heal_used = True
                witch.private_notes.append(f"昨晚你使用解藥救了 {victim.name}。")
                saved = True
        if not self.witch_poison_used and random.random() < 0.32:
            targets = [a for a in self.alive_agents() if a.name != witch.name]
            suspect = sorted(
                [(n, s) for n, s in witch.suspicion.items() if n in [x.name for x in targets]],
                key=lambda kv: kv[1],
                reverse=True,
            )
            if suspect and suspect[0][1] > 0.62:
                poisoned = next(a for a in targets if a.name == suspect[0][0])
                self.witch_poison_used = True
                witch.private_notes.append(f"昨晚你毒死了 {poisoned.name}。")
        return saved, poisoned

    async def night_phase(self, channel: discord.TextChannel):
        self.phase = "night"
        await self.send_system(channel, f"🌙 第 {self.day} 夜開始，天黑請閉眼。")
        self.seer_action()
        victim = self.wolf_kill_target() if self.wolves_alive() and self.villagers_alive() else None
        saved, poisoned = self.witch_action(victim)
        deaths: List[Agent] = []
        if victim and not saved:
            victim.alive = False
            deaths.append(victim)
        if poisoned and poisoned.alive:
            poisoned.alive = False
            deaths.append(poisoned)
        if not deaths:
            await self.send_system(channel, "🌤 天亮了，昨晚平安夜。")
            return
        await self.send_system(channel, "🌤 天亮了。")
        seen = set()
        for d in deaths:
            if d.name in seen:
                continue
            seen.add(d.name)
            d.revealed_role = d.role
            await self.send_system(channel, f"💀 {d.name} 出局，身份是{d.role}。")
            for a in self.alive_agents():
                a.public_memory.append(f"{d.name} 夜裡出局，身份是{d.role}。")

    async def discussion_phase(self, channel: discord.TextChannel):
        self.phase = "discussion"
        await self.send_system(channel, f"🗣 第 {self.day} 天討論開始。")
        ordered = self.alive_agents()[:]
        random.shuffle(ordered)
        context = self.public_snapshot()
        for agent in ordered:
            goal = "先做一段開場發言，表達你目前對局勢的看法，可以點出一名最可疑的人。"
            top = sorted(agent.suspicion.items(), key=lambda kv: kv[1], reverse=True)
            fallback = f"我先聽大家，但目前我比較想看 {top[0][0]}，他剛剛有點怪。"
            speech = await self.think_speech(agent, context, goal, fallback)
            await self.send_agent(channel, agent, speech)
            context = self.public_snapshot()
        target = random.choice(self.alive_agents())
        goal = "有人質疑你，請你做一段短辯解，維持自己像真人，不要太長。"
        fallback = "先別急著踩我，我發言一直都很一致。"
        speech = await self.think_speech(target, self.public_snapshot(), goal, fallback)
        await self.send_agent(channel, target, speech)

    async def voting_phase(self, channel: discord.TextChannel):
        self.phase = "vote"
        await self.send_system(channel, f"🗳 第 {self.day} 天投票開始。")
        votes: Dict[str, int] = {}
        ordered = self.alive_agents()[:]
        random.shuffle(ordered)
        for agent in ordered:
            target, reason = await self.think_vote(agent)
            agent.last_target = target
            await self.send_agent(channel, agent, f"我投 {target}，{reason}")
            votes[target] = votes.get(target, 0) + 1
            if target in agent.suspicion:
                agent.suspicion[target] = round(min(0.99, agent.suspicion[target] + 0.08), 2)
        top_count = max(votes.values())
        finalists = [name for name, count in votes.items() if count == top_count]
        out_name = random.choice(finalists)
        out = next(a for a in self.agents if a.name == out_name)
        out.alive = False
        out.revealed_role = out.role
        await self.send_system(channel, f"📢 票型結算，{out.name} 被放逐。")
        await self.send_system(channel, f"🪦 {out.name} 的身份是{out.role}。")
        for a in self.alive_agents():
            a.public_memory.append(f"{out.name} 被放逐，身份是{out.role}。")
            if out.role == "狼人":
                a.suspicion[out.name] = 0.0

    async def reveal_all(self, channel: discord.TextChannel):
        lines = [f"{a.name}：{a.role}" for a in self.agents]
        await self.send_system(channel, "📜 本局身份公布：\n" + "\n".join(lines))

    def save_game(self, status: str, winner: Optional[str] = None):
        payload = {
            "status": status,
            "winner": winner,
            "day": self.day,
            "phase": self.phase,
            "witch_heal_used": self.witch_heal_used,
            "witch_poison_used": self.witch_poison_used,
            "seer_checks": self.seer_checks,
            "log": self.log,
            "agents": [asdict(a) for a in self.agents],
        }
        save_state(payload)

    async def run_game(self, channel: discord.TextChannel):
        self.agents = self.build_agents()
        self.day = 1
        self.phase = "init"
        self.log = []
        self.witch_heal_used = False
        self.witch_poison_used = False
        self.seer_checks = []
        await self.send_system(channel, "🎭 真獨立 Agent 狼人殺開始。每個角色會用自己的記憶與身份發言。")
        await self.send_system(channel, "玩家：" + "、".join(a.name for a in self.agents))
        self.save_game("running")
        while self.day <= MAX_DAYS:
            await self.night_phase(channel)
            self.save_game("running")
            win = self.winner()
            if win:
                await self.send_system(channel, f"🏁 遊戲結束，{win}陣營獲勝！")
                await self.reveal_all(channel)
                self.save_game("finished", win)
                return
            await self.discussion_phase(channel)
            self.save_game("running")
            await self.voting_phase(channel)
            self.save_game("running")
            win = self.winner()
            if win:
                await self.send_system(channel, f"🏁 遊戲結束，{win}陣營獲勝！")
                await self.reveal_all(channel)
                self.save_game("finished", win)
                return
            self.day += 1
        await self.send_system(channel, "⌛ 達到最大天數，本局強制結束。")
        await self.reveal_all(channel)
        self.save_game("finished", "無")


def main():
    if not TOKEN:
        raise RuntimeError("Missing DISCORD_BOT_TOKEN")
    if not CHANNEL_ID:
        raise RuntimeError("Missing DISCORD_CHANNEL_ID")
    if not LLM_API_KEY:
        raise RuntimeError("Missing LLM_API_KEY")
    random.seed()
    bot = WerewolfDiscordBot()
    bot.run(TOKEN)


if __name__ == "__main__":
    main()
