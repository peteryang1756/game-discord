import json
import os
import random
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional

API_BASE = os.environ.get('LLM_API_BASE', 'https://api.poe.com/v1')
API_KEY = os.environ.get('LLM_API_KEY', 'sk-poe-ai6w5hHUJydjHhVzIEwPWHlWELSsR5hGJErtiaqdaO4')

# 為每個角色分配不同模型
AGENT_MODELS = [
    'glm-5-t',        # 阿哲
    'gemma-4-31b-t',  # 排排
    'gemma-4-31b',    # 小P
    'gpt-5.3-codex-spark',  # 小白
    'gpt-5.3-codex-spark',  # 川普
    'gpt-5.3-codex-spark',  # 維尼
]
CHAT_ID = int(os.environ.get('TG_CHAT_ID', '-5103856268'))
TURN_SLEEP = float(os.environ.get('TURN_SLEEP', '1.8'))
OPENING_SLEEP = float(os.environ.get('OPENING_SLEEP', '1.2'))
STATE_FILE = os.environ.get('STATE_FILE', 'game_state_v2.json')
DRY_RUN = os.environ.get('DRY_RUN', '0') == '1'
MAX_DAYS = int(os.environ.get('MAX_DAYS', '6'))

BOT_NAMES = ['阿哲', '排排', '小P', '小白', '川普', '維尼']
BOT_STYLES = [
    '冷靜理性，講話短，喜歡抓矛盾，不容易被帶風向。',
    '話多，擅長帶節奏，喜歡先站邊再找理由。',
    '看似無辜，實際很會自保，被攻擊會立刻回擊。',
    '像分析師，常談機率、資訊量、行為一致性。',
    '偏保守，膽小，容易跟票，但偶爾會突然很準。',
    '嘴砲型，愛挑釁，會故意戳別人反應。',
]
BOT_TOKENS = [
    os.environ.get('TG_BOT_1', ''),
    os.environ.get('TG_BOT_2', ''),
    os.environ.get('TG_BOT_3', ''),
    os.environ.get('TG_BOT_4', ''),
    os.environ.get('TG_BOT_5', ''),
    os.environ.get('TG_BOT_6', ''),
]
ROLES = ['狼人', '狼人', '預言家', '女巫', '村民', '村民']

SYSTEM_PROMPT = '''
你在扮演真人玩家玩中文狼人殺，不要提到自己是AI、模型、程式。
輸出要像Telegram群組裡真人講話，自然、口語、短句為主。
遵守身份資訊邊界：只能使用你該知道的資訊。
不要代替別人說話，不要輸出旁白，不要用列表。
如果要求輸出JSON，必須輸出合法JSON，不能包 markdown。
'''.strip()


@dataclass
class Agent:
    idx: int
    name: str
    token: str
    style: str
    role: str
    alive: bool = True
    revealed_role: Optional[str] = None
    private_notes: List[str] = field(default_factory=list)
    public_memory: List[str] = field(default_factory=list)
    suspicion: Dict[str, float] = field(default_factory=dict)
    relations: Dict[str, str] = field(default_factory=dict)
    last_target: Optional[str] = None

    def short_state(self):
        return {
            'name': self.name,
            'role': self.role,
            'alive': self.alive,
            'revealed_role': self.revealed_role,
            'private_notes': self.private_notes[-12:],
            'public_memory': self.public_memory[-18:],
            'suspicion': self.suspicion,
            'relations': self.relations,
            'last_target': self.last_target,
        }


class LLM:
    def __init__(self, api_base: str, api_key: str):
        self.api_base = api_base.rstrip('/')
        self.api_key = api_key

    def chat(self, messages: List[Dict], model: str, temperature: float = 0.9) -> str:
        if not self.api_key:
            return ''
        url = f'{self.api_base}/chat/completions'
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'User-Agent': 'curl/8.5.0',
            'Accept': 'application/json',
        }
        payload = {
            'model': model,
            'messages': messages,
            'temperature': temperature,
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
            headers=headers,
            method='POST',
        )
        with urllib.request.urlopen(req, timeout=90) as r:
            data = json.loads(r.read().decode('utf-8'))
        return data['choices'][0]['message']['content'].strip()


class Game:
    def __init__(self):
        self.llm = LLM(API_BASE, API_KEY)
        self.agents = self._make_agents()
        self.day = 1
        self.phase = 'init'
        self.log: List[str] = []
        self.witch_heal_used = False
        self.witch_poison_used = False
        self.seer_checks: List[str] = []
        self.wolf_chat: List[str] = []

    def _make_agents(self):
        roles = ROLES[:]
        random.shuffle(roles)
        agents = []
        for i, name in enumerate(BOT_NAMES):
            token = BOT_TOKENS[i]
            agents.append(Agent(i, name, token, BOT_STYLES[i], roles[i]))
        names = [a.name for a in agents]
        for agent in agents:
            agent.suspicion = {n: round(random.uniform(0.18, 0.48), 2) for n in names if n != agent.name}
            if agent.role == '狼人':
                mates = [a.name for a in agents if a.role == '狼人' and a.name != agent.name]
                if mates:
                    agent.private_notes.append(f'你的狼人隊友是：{mates[0]}')
            if agent.role == '女巫':
                agent.private_notes.append('你有一瓶解藥與一瓶毒藥，各只能用一次。')
            if agent.role == '預言家':
                agent.private_notes.append('每晚可查驗一人是好人或狼人。')
        return agents

    def alive_agents(self):
        return [a for a in self.agents if a.alive]

    def wolves_alive(self):
        return [a for a in self.agents if a.alive and a.role == '狼人']

    def villagers_alive(self):
        return [a for a in self.agents if a.alive and a.role != '狼人']

    def winner(self):
        wolves = self.wolves_alive()
        villagers = self.villagers_alive()
        if not wolves:
            return '好人'
        if len(wolves) >= len(villagers):
            return '狼人'
        return None

    def send(self, token: str, text: str):
        if DRY_RUN:
            print(text)
            return
        url = f'https://api.telegram.org/bot{token}/sendMessage'
        payload = urllib.parse.urlencode({'chat_id': CHAT_ID, 'text': text}).encode()
        with urllib.request.urlopen(url, data=payload, timeout=30) as r:
            r.read()

    def say_system(self, text: str):
        self.log.append(f'[SYSTEM] {text}')
        print(f'[SYSTEM] {text}')
        self.send(BOT_TOKENS[0], text)
        time.sleep(OPENING_SLEEP)

    def say_agent(self, agent: Agent, text: str):
        text = text.strip().replace('\n', ' ')
        if not text:
            text = '我先保留，等等再補。'
        self.log.append(f'[{agent.name}] {text}')
        print(f'[{agent.name}] {text}')
        self.send(agent.token, text)
        time.sleep(TURN_SLEEP)
        for other in self.alive_agents():
            if other.name != agent.name:
                other.public_memory.append(f'{agent.name} 說：{text}')
                if agent.name in other.suspicion and any(k in text for k in ['怪', '狼', '不對', '做身份', '帶節奏']):
                    other.suspicion[agent.name] = round(min(0.99, other.suspicion[agent.name] + 0.03), 2)

    def json_response(self, messages: List[Dict], agent_idx: int, fallback: Dict) -> Dict:
        try:
            raw = self.llm.chat(messages, AGENT_MODELS[agent_idx % len(AGENT_MODELS)], temperature=0.8)
            raw = raw.strip()
            if raw.startswith('```'):
                raw = raw.strip('`')
                raw = raw.split('\n', 1)[-1]
            return json.loads(raw)
        except Exception:
            return fallback

    def text_response(self, messages: List[Dict], agent_idx: int, fallback: str) -> str:
        try:
            txt = self.llm.chat(messages, AGENT_MODELS[agent_idx % len(AGENT_MODELS)], temperature=0.95)
            return txt.strip() or fallback
        except Exception:
            return fallback

    def public_snapshot(self) -> str:
        alive = '、'.join(a.name for a in self.alive_agents())
        dead = '、'.join(f'{a.name}({a.role})' for a in self.agents if not a.alive) or '無'
        recent = '\n'.join(self.log[-14:]) or '無'
        return f'存活：{alive}\n出局：{dead}\n最近對話：\n{recent}'

    def private_snapshot(self, agent: Agent) -> str:
        return json.dumps(agent.short_state(), ensure_ascii=False)

    def think_speech(self, agent: Agent, context: str, goal: str, fallback: str) -> str:
        messages = [
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user', 'content': f'''你是玩家「{agent.name}」。\n人格：{agent.style}\n身份：{agent.role}\n\n你的私人狀態：{self.private_snapshot(agent)}\n\n公開局勢：\n{context}\n\n當前任務：{goal}\n\n請只輸出一段 18 到 60 字的 Telegram 群組發言。\n不要加引號，不要解釋。'''}
        ]
        return self.text_response(messages, agent.idx, fallback)

    def think_vote(self, agent: Agent) -> str:
        alive_targets = [a.name for a in self.alive_agents() if a.name != agent.name]
        top = sorted(agent.suspicion.items(), key=lambda kv: kv[1], reverse=True)
        fallback = {'target': next((n for n, _ in top if n in alive_targets), random.choice(alive_targets)), 'reason': '我先投最可疑的。'}
        messages = [
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user', 'content': f'''你是玩家「{agent.name}」。\n身份：{agent.role}\n人格：{agent.style}\n\n可投票對象：{alive_targets}\n你的私人狀態：{self.private_snapshot(agent)}\n公開局勢：\n{self.public_snapshot()}\n\n請輸出 JSON：{{"target":"名字","reason":"20字內理由"}}\n只能從可投票對象選一人。'''}
        ]
        data = self.json_response(messages, agent.idx, fallback)
        target = data.get('target', fallback['target'])
        if target not in alive_targets:
            target = fallback['target']
        reason = str(data.get('reason', fallback['reason']))[:40]
        return target, reason

    def wolf_kill_target(self) -> Agent:
        wolves = self.wolves_alive()
        targets = [a for a in self.alive_agents() if a.role != '狼人']
        if not targets:
            return random.choice(self.alive_agents())
        score = {}
        for target in targets:
            score[target.name] = 0.0
            if target.role == '預言家':
                score[target.name] += 0.35
            if target.role == '女巫':
                score[target.name] += 0.20
            score[target.name] += random.random() * 0.25
            for w in wolves:
                score[target.name] += w.suspicion.get(target.name, 0) * 0.2
        best = max(score, key=score.get)
        return next(a for a in targets if a.name == best)

    def seer_action(self):
        seer = next((a for a in self.agents if a.alive and a.role == '預言家'), None)
        if not seer:
            return
        candidates = [a for a in self.alive_agents() if a.name != seer.name]
        if not candidates:
            return
        unchecked = [a for a in candidates if a.name not in ' '.join(self.seer_checks)]
        target = random.choice(unchecked or candidates)
        result = '狼人' if target.role == '狼人' else '好人'
        note = f'你昨晚查驗 {target.name}，結果是：{result}。'
        self.seer_checks.append(note)
        seer.private_notes.append(note)
        if result == '狼人':
            seer.suspicion[target.name] = 0.99
        else:
            seer.suspicion[target.name] = 0.05

    def witch_action(self, victim: Optional[Agent]):
        witch = next((a for a in self.agents if a.alive and a.role == '女巫'), None)
        saved = False
        poisoned = None
        if not witch:
            return saved, poisoned
        if victim and not self.witch_heal_used:
            use_heal = victim.role in ('預言家', '女巫') or random.random() < 0.38
            if use_heal:
                self.witch_heal_used = True
                witch.private_notes.append(f'昨晚你使用解藥救了 {victim.name}。')
                saved = True
        if not self.witch_poison_used and random.random() < 0.32:
            targets = [a for a in self.alive_agents() if a.name != witch.name]
            suspect = sorted([(n, s) for n, s in witch.suspicion.items() if n in [x.name for x in targets]], key=lambda kv: kv[1], reverse=True)
            if suspect and suspect[0][1] > 0.62:
                poisoned = next(a for a in targets if a.name == suspect[0][0])
                self.witch_poison_used = True
                witch.private_notes.append(f'昨晚你毒死了 {poisoned.name}。')
        return saved, poisoned

    def night(self):
        self.phase = 'night'
        self.say_system(f'🌙 第 {self.day} 夜開始，天黑請閉眼。')
        self.seer_action()
        victim = self.wolf_kill_target() if self.wolves_alive() and self.villagers_alive() else None
        saved, poisoned = self.witch_action(victim)
        deaths = []
        if victim and not saved:
            victim.alive = False
            deaths.append(victim)
        if poisoned and poisoned.alive:
            poisoned.alive = False
            deaths.append(poisoned)
        if not deaths:
            self.say_system('🌤 天亮了，昨晚平安夜。')
        else:
            self.say_system('🌤 天亮了。')
            seen = set()
            for d in deaths:
                if d.name in seen:
                    continue
                seen.add(d.name)
                d.revealed_role = d.role
                self.say_system(f'💀 {d.name} 出局，身份是{d.role}。')
                for a in self.alive_agents():
                    a.public_memory.append(f'{d.name} 夜裡出局，身份是{d.role}。')

    def day_discussion(self):
        self.phase = 'discussion'
        self.say_system(f'🗣 第 {self.day} 天討論開始。')
        ordered = self.alive_agents()[:]
        random.shuffle(ordered)
        context = self.public_snapshot()
        for agent in ordered:
            goal = '先做一段開場發言，表達你目前對局勢的看法，可以點出一名最可疑的人。'
            top = sorted(agent.suspicion.items(), key=lambda kv: kv[1], reverse=True)
            fallback = f'我先聽大家，但目前我比較想看 {top[0][0]}，他剛剛有點怪。'
            speech = self.think_speech(agent, context, goal, fallback)
            self.say_agent(agent, speech)
            context = self.public_snapshot()
        target = random.choice(self.alive_agents())
        goal = '有人質疑你，請你做一段短辯解，維持自己像真人，不要太長。'
        fallback = '先別急著踩我，我發言一直都很一致。'
        speech = self.think_speech(target, self.public_snapshot(), goal, fallback)
        self.say_agent(target, speech)

    def voting(self):
        self.phase = 'vote'
        self.say_system(f'🗳 第 {self.day} 天投票開始。')
        votes: Dict[str, int] = {}
        ordered = self.alive_agents()[:]
        random.shuffle(ordered)
        for agent in ordered:
            target, reason = self.think_vote(agent)
            agent.last_target = target
            self.say_agent(agent, f'我投 {target}，{reason}')
            votes[target] = votes.get(target, 0) + 1
            if target in agent.suspicion:
                agent.suspicion[target] = round(min(0.99, agent.suspicion[target] + 0.08), 2)
        top_count = max(votes.values())
        finalists = [name for name, count in votes.items() if count == top_count]
        out_name = random.choice(finalists)
        out = next(a for a in self.agents if a.name == out_name)
        out.alive = False
        out.revealed_role = out.role
        self.say_system(f'📢 票型結算，{out.name} 被放逐。')
        self.say_system(f'🪦 {out.name} 的身份是{out.role}。')
        for a in self.alive_agents():
            a.public_memory.append(f'{out.name} 被放逐，身份是{out.role}。')
            if out.role == '狼人':
                a.suspicion[out.name] = 0.0

    def reveal_all(self):
        lines = [f'{a.name}：{a.role}' for a in self.agents]
        self.say_system('📜 本局身份公布：\n' + '\n'.join(lines))

    def save(self):
        payload = {
            'day': self.day,
            'phase': self.phase,
            'witch_heal_used': self.witch_heal_used,
            'witch_poison_used': self.witch_poison_used,
            'seer_checks': self.seer_checks,
            'log': self.log,
            'agents': [asdict(a) for a in self.agents],
        }
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def run(self):
        self.say_system('🎭 真獨立 Agent 狼人殺開始。每個 bot 會用自己的記憶與身份發言。')
        self.say_system('玩家：' + '、'.join(a.name for a in self.agents))
        self.save()
        while self.day <= MAX_DAYS:
            self.night()
            self.save()
            win = self.winner()
            if win:
                self.say_system(f'🏁 遊戲結束，{win}陣營獲勝！')
                self.reveal_all()
                self.save()
                return
            self.day_discussion()
            self.save()
            self.voting()
            self.save()
            win = self.winner()
            if win:
                self.say_system(f'🏁 遊戲結束，{win}陣營獲勝！')
                self.reveal_all()
                self.save()
                return
            self.day += 1
        self.say_system('⌛ 達到最大天數，本局強制結束。')
        self.reveal_all()
        self.save()


def ensure_env():
    missing = [f'TG_BOT_{i}' for i in range(1, 7) if not BOT_TOKENS[i - 1]]
    if not API_KEY:
        missing.append('LLM_API_KEY')
    if missing:
        raise SystemExit('缺少環境變數：' + ', '.join(missing))


if __name__ == '__main__':
    ensure_env()
    random.seed()
    Game().run()
