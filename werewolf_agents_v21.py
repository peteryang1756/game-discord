import json
import os
import random
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple

API_BASE = os.environ.get('LLM_API_BASE', 'https://free.9e.nz/v1')
API_KEY = os.environ.get('LLM_API_KEY', '')
MODEL = os.environ.get('LLM_MODEL', 'gpt-5.4')
CHAT_ID = int(os.environ.get('TG_CHAT_ID', '-1003644055956'))
STATE_FILE = os.environ.get('STATE_FILE', 'game_state_v21.json')
TURN_SLEEP = float(os.environ.get('TURN_SLEEP', '1.5'))
SYSTEM_SLEEP = float(os.environ.get('SYSTEM_SLEEP', '1.0'))
POLL_SLEEP = float(os.environ.get('POLL_SLEEP', '2.0'))
VOTE_APPEAL_SECONDS = int(os.environ.get('VOTE_APPEAL_SECONDS', '120'))
BOT_STYLES = [
    '冷靜理性，會抓矛盾，講話短。',
    '話多愛帶節奏，喜歡先壓人。',
    '自保型，被踩會反打。',
    '分析師型，常談資訊量、票型、邏輯。',
    '保守膽小，容易跟票，但會記仇。',
    '嘴砲型，故意戳人看反應。',
]
BOT_NAMES = ['阿哲', '排排', '小P', '小白', '川普', '維尼']
BOT_TOKENS = [
    os.environ.get('TG_BOT_1', ''),
    os.environ.get('TG_BOT_2', ''),
    os.environ.get('TG_BOT_3', ''),
    os.environ.get('TG_BOT_4', ''),
    os.environ.get('TG_BOT_5', ''),
    os.environ.get('TG_BOT_6', ''),
]
ROLES = ['狼人', '狼人', '預言家', '女巫', '村民', '村民']
UNDERCOVER_WORD_PAIRS = [
    ('牛奶', '豆漿'),
    ('烤肉', '涮肉'),
    ('壁紙', '貼畫'),
    ('男友', '前男友'),
    ('情人節', '光棍節'),
    ('沐浴露', '沐浴鹽'),
    ('公車', '地鐵'),
    ('同學', '同桌'),
    ('冠軍', '第一'),
    ('圖書館', '圖書店'),
    ('紅燒牛肉麵', '香辣牛肉麵'),
    ('高麗菜', '生菜'),
    ('牛肉乾', '豬肉脯'),
    ('泡泡糖', '棒棒糖'),
    ('薰衣草', '滿天星'),
    ('生活費', '零用錢'),
    ('氣泡', '水泡'),
    ('電腦', 'ipad'),
    ('口香糖', '木糖醇'),
    ('雲霄飛車', '碰碰車'),
    ('鴨舌帽', '遮陽帽'),
    ('雙胞胎', '龍鳳胎'),
    ('保安', '保鑣'),
    ('唇膏', '口紅'),
    ('結婚', '訂婚'),
    ('近視眼鏡', '隱形眼鏡'),
    ('紙巾', '濕紙巾'),
    ('海豚', '海獅'),
    ('印表機', '掃描機'),
    ('魚香肉絲', '四喜丸子'),
    ('蝴蝶', '蜜蜂'),
    ('魔術師', '魔法師'),
    ('枕頭', '抱枕'),
    ('作家', '編劇'),
    ('醜小鴨', '灰姑娘'),
    ('端午節', '中秋節'),
    ('高跟鞋', '增高鞋'),
    ('洗髮精', '護髮素'),
    ('葡萄', '提子'),
    ('小籠包', '灌湯包'),
    ('反彈琵琶', '亂彈棉花'),
    ('風扇', '空調'),
    ('玫瑰', '月季'),
    ('龍鳳呈祥', '鴛鴦戲水'),
    ('油條', '麻花'),
    ('玻璃', '鏡子'),
    ('十面埋伏', '四面楚歌'),
    ('臉盆', '水桶'),
    ('作文', '論文'),
    ('麵包', '蛋糕'),
    ('婚紗', '喜服'),
    ('酸菜魚', '水煮魚'),
    ('果粒橙', '鮮橙多'),
    ('麥克風', '擴音器'),
    ('手機', '座機'),
    ('辣椒', '芥末'),
    ('被子', '床單'),
    ('獎牌', '金牌'),
    ('餅乾', '薯片'),
    ('小品', '話劇'),
    ('盒子', '箱子'),
    ('吉他', '琵琶'),
    ('媽媽', '娘'),
    ('哈密瓜', '西瓜'),
    ('兩小無猜', '青梅竹馬'),
    ('麻婆豆腐', '皮蛋豆腐'),
    ('自行車', '電動車'),
    ('綠茶', '苦茶'),
    ('餃子', '包子'),
    ('洗衣粉', '皂角粉'),
    ('童話', '神話'),
    ('暗戀', '備胎'),
    ('馬鈴薯粉', '酸辣粉'),
    ('乾洗機', '甩乾機'),
    ('捲髮', '直髮'),
    ('絲襪', '秋褲'),
    ('漢堡包', '肉夾饃'),
    ('太陽傘', '雨傘'),
    ('鵝毛', '雞毛'),
    ('飯桶', '飯碗'),
    ('胖子', '肥肉'),
    ('動物', '植物'),
    ('積木', '樹木'),
    ('蝴蝶', '飛蛾'),
    ('奶茶', '珍珠奶茶'),
    ('漢堡', '三明治'),
    ('捷運', '火車'),
    ('蘋果', '梨子'),
    ('警察', '保全'),
    ('咖啡', '可可'),
    ('籃球', '排球'),
    ('牙膏', '洗面乳'),
    ('新年', '跨年'),
    ('沐浴露', '護膚水'),
    ('紙巾', '手帕'),
    ('包子', '餃子'),
    ('飯桶', '飯碗'),
]


SYSTEM_PROMPT = '你在扮演真人玩家玩繁體中文派對遊戲。不要提到AI、模型、程式。說話像台灣年輕人聊天，口語自然、有情緒、有立場，不要中國用語。若要求JSON，僅輸出合法JSON。'

NAME_ALIAS_MAP = {}


def _normalize_name(value: str) -> str:
    if not value:
        return value
    for old, new in NAME_ALIAS_MAP.items():
        value = value.replace(old, new)
    return value


def _normalize_state_names(obj):
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            nk = _normalize_name(k) if isinstance(k, str) else k
            out[nk] = _normalize_state_names(v)
        return out
    if isinstance(obj, list):
        return [_normalize_state_names(v) for v in obj]
    if isinstance(obj, str):
        return _normalize_name(obj)
    return obj

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
    trust: Dict[str, float] = field(default_factory=dict)
    grudges: Dict[str, float] = field(default_factory=dict)
    defended_by: List[str] = field(default_factory=list)
    attacked_by: List[str] = field(default_factory=list)
    last_vote: Optional[str] = None


@dataclass
class HumanPlayer:
    user_id: int = 0
    name: str = ''
    joined: bool = False
    alive: bool = False
    role: Optional[str] = None
    replaced_bot: Optional[str] = None
    pending_action: Optional[dict] = None
    dm_ready: bool = False


class LLM:
    def chat(self, messages: List[Dict], temperature: float = 0.9) -> str:
        if not API_KEY:
            raise RuntimeError('missing API key')
        req = urllib.request.Request(
            f'{API_BASE.rstrip("/")}/chat/completions',
            data=json.dumps({
                'model': MODEL,
                'messages': messages,
                'temperature': temperature,
            }, ensure_ascii=False).encode(),
            headers={
                'Authorization': f'Bearer {API_KEY}',
                'Content-Type': 'application/json',
                'User-Agent': 'curl/8.5.0',
                'Accept': 'application/json',
            },
            method='POST',
        )
        with urllib.request.urlopen(req, timeout=90) as r:
            data = json.loads(r.read().decode())
        return data['choices'][0]['message']['content'].strip()


class TG:
    def __init__(self, token: str):
        self.token = token

    def call(self, method: str, data: Dict = None):
        data = data or {}
        req = urllib.request.Request(
            f'https://api.telegram.org/bot{self.token}/{method}',
            data=urllib.parse.urlencode(data).encode(),
            method='POST',
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())

    def get_updates(self, offset: Optional[int] = None, timeout: int = 20):
        params = {'timeout': timeout}
        if offset is not None:
            params['offset'] = offset
        req = urllib.request.Request(
            f'https://api.telegram.org/bot{self.token}/getUpdates?{urllib.parse.urlencode(params)}'
        )
        with urllib.request.urlopen(req, timeout=timeout + 10) as r:
            return json.loads(r.read().decode())


class Game:
    def __init__(self):
        self.llm = LLM()
        self.day = 1
        self.phase = 'idle'
        self.game_mode = 'werewolf'
        self.turn_order: List[str] = []
        self.turn_index = 0
        self.log: List[str] = []
        self.witch_heal_used = False
        self.witch_poison_used = False
        self.wolf_plan: List[str] = []
        self.pending_night_deaths: List[str] = []
        self.auto_run = False
        self.last_auto_ts = 0.0
        self.night_prompted_users: List[int] = []
        self.night_started_day: int = 0
        self.night_deadline_ts: float = 0.0
        self.human_speech_wait_user_id: int = 0
        self.human_speech_deadline_ts: float = 0.0
        self.vote_prompted: bool = False
        self.vote_deadline_ts: float = 0.0
        self.vote_round: int = 1
        self.vote_appeal_deadline_ts: float = 0.0
        self.vote_round2_candidates: List[str] = []
        self.vote_appeal_target: Optional[str] = None
        self.undercover_word_civil: str = ''
        self.undercover_word_under: str = ''
        self.undercover_name: str = ''
        self.humans: List[HumanPlayer] = []
        self.human = HumanPlayer()
        self.human_role: Optional[str] = None
        self.agents = self._make_agents()

    def sanitize_humans(self):
        cleaned = []
        seen_ids = set()
        for h in self.humans:
            if not h.joined:
                continue
            if not h.name:
                continue
            if h.user_id <= 0:
                continue
            if h.user_id in seen_ids:
                continue
            seen_ids.add(h.user_id)
            cleaned.append(h)
        self.humans = cleaned

    def active_players_names(self):
        names = [a.name for a in self.alive()]
        for h in self.humans:
            if h.joined and h.alive:
                names.append(h.name)
        return names

    def alive_humans(self):
        return [h for h in self.humans if h.joined and h.alive]

    def find_human_by_user(self, user_id: int):
        for h in self.humans:
            if h.user_id == user_id:
                return h
        return None

    def _make_agents(self):
        roles = ROLES[:]
        random.shuffle(roles)
        agents = []
        for i, name in enumerate(BOT_NAMES):
            a = Agent(i, name, BOT_TOKENS[i], BOT_STYLES[i], roles[i])
            agents.append(a)
        for a in agents:
            others = [x.name for x in agents if x.name != a.name]
            a.suspicion = {n: round(random.uniform(0.18, 0.48), 2) for n in others}
            a.trust = {n: round(random.uniform(0.15, 0.4), 2) for n in others}
            a.grudges = {n: 0.0 for n in others}
            if a.role == '狼人':
                mate = [x.name for x in agents if x.role == '狼人' and x.name != a.name][0]
                a.private_notes.append(f'你的狼人隊友是 {mate}。')
            elif a.role == '預言家':
                a.private_notes.append('你每晚可查驗一人身份。')
            elif a.role == '女巫':
                a.private_notes.append('你有解藥與毒藥，各一次。')
        return agents

    def _reset_round_state(self):
        self.turn_order = []
        self.turn_index = 0
        self.log = []
        self.witch_heal_used = False
        self.witch_poison_used = False
        self.wolf_plan = []
        self.pending_night_deaths = []
        self.night_prompted_users = []
        self.night_started_day = 0
        self.night_deadline_ts = 0.0
        self.human_speech_wait_user_id = 0
        self.human_speech_deadline_ts = 0.0
        self.vote_prompted = False
        self.vote_deadline_ts = 0.0
        self.vote_round = 1
        self.vote_appeal_deadline_ts = 0.0
        self.vote_round2_candidates = []
        self.vote_appeal_target = None
        self.undercover_word_civil = ''
        self.undercover_name = ''


    def _apply_human_replacements(self):
        live_agents = [a for a in self.agents if a.alive]
        random.shuffle(live_agents)
        roles_assigned = []
        for h in self.humans:
            if not h.joined:
                continue
            if not live_agents:
                break
            replaced = live_agents.pop()
            h.replaced_bot = replaced.name
            h.alive = True
            h.role = replaced.role
            replaced.alive = False
            replaced.revealed_role = '替補離場'
            roles_assigned.append(f'{h.name} 取代 {replaced.name}')
        return roles_assigned

    def _vote_candidates(self):
        alive = self.active_players_names()
        if self.vote_round == 2 and self.vote_round2_candidates:
            narrowed = [n for n in self.vote_round2_candidates if n in alive]
            return narrowed[:2]
        return alive

    def _clear_human_actions(self):
        for h in self.alive_humans():
            h.pending_action = None

    def _finalize_vote(self, out_name: str):
        out_human = next((h for h in self.alive_humans() if h.name == out_name), None)
        if out_human:
            out_human.alive = False
            self.say_system(f'📢 票型結算，{out_human.name} 被放逐。')
            self.say_system(f'🪦 {out_human.name} 的身份是{out_human.role}。')
            return

        out = self.get(out_name)
        out.alive = False
        out.revealed_role = out.role
        self.say_system(f'📢 票型結算，{out.name} 被放逐。')
        self.say_system(f'🪦 {out.name} 的身份是{out.role}。')
        for a in self.alive():
            a.public_memory.append(f'{out.name} 被放逐，身份是{out.role}。')
            if out.role == '狼人':
                a.trust = {k: round(min(0.99, v + (0.15 if k == out.name else 0)), 2) for k, v in a.trust.items()}

    def to_dict(self):
        return {
            'day': self.day,
            'phase': self.phase,
            'game_mode': self.game_mode,
            'turn_order': self.turn_order,
            'turn_index': self.turn_index,
            'log': self.log,
            'witch_heal_used': self.witch_heal_used,
            'witch_poison_used': self.witch_poison_used,
            'wolf_plan': self.wolf_plan,
            'pending_night_deaths': self.pending_night_deaths,
            'auto_run': self.auto_run,
            'last_auto_ts': self.last_auto_ts,
            'night_prompted_users': self.night_prompted_users,
            'night_started_day': self.night_started_day,
            'night_deadline_ts': self.night_deadline_ts,
            'human_speech_wait_user_id': self.human_speech_wait_user_id,
            'human_speech_deadline_ts': self.human_speech_deadline_ts,
            'vote_prompted': self.vote_prompted,
            'vote_deadline_ts': self.vote_deadline_ts,
            'vote_round': self.vote_round,
            'vote_appeal_deadline_ts': self.vote_appeal_deadline_ts,
            'vote_round2_candidates': self.vote_round2_candidates,
            'vote_appeal_target': self.vote_appeal_target,
            'undercover_word_civil': self.undercover_word_civil,
            'undercover_word_under': self.undercover_word_under,
            'undercover_name': self.undercover_name,
            'human': asdict(self.human),
            'humans': [asdict(h) for h in self.humans],
            'human_role': self.human_role,
            'agents': [asdict(a) for a in self.agents],
        }

    @classmethod
    def from_dict(cls, data):
        g = cls()
        g.day = data['day']
        g.phase = data['phase']
        g.game_mode = data.get('game_mode', 'werewolf')
        g.turn_order = [_normalize_name(n) for n in data.get('turn_order', [])]
        g.turn_index = data.get('turn_index', 0)
        g.log = [
            _normalize_name(x) if isinstance(x, str) else x for x in data.get('log', [])
        ]
        g.witch_heal_used = data.get('witch_heal_used', False)
        g.witch_poison_used = data.get('witch_poison_used', False)
        g.wolf_plan = data.get('wolf_plan', [])
        g.pending_night_deaths = data.get('pending_night_deaths', [])
        g.auto_run = data.get('auto_run', False)
        g.last_auto_ts = data.get('last_auto_ts', 0.0)
        g.night_prompted_users = data.get('night_prompted_users', [])
        g.night_started_day = data.get('night_started_day', 0)
        g.night_deadline_ts = data.get('night_deadline_ts', 0.0)
        g.human_speech_wait_user_id = data.get('human_speech_wait_user_id', 0)
        g.human_speech_deadline_ts = data.get('human_speech_deadline_ts', 0.0)
        g.vote_prompted = data.get('vote_prompted', False)
        g.vote_deadline_ts = data.get('vote_deadline_ts', 0.0)
        g.vote_round = data.get('vote_round', 1)
        g.vote_appeal_deadline_ts = data.get('vote_appeal_deadline_ts', 0.0)
        g.vote_round2_candidates = data.get('vote_round2_candidates', [])
        g.vote_appeal_target = data.get('vote_appeal_target')
        g.undercover_word_civil = data.get('undercover_word_civil', '')
        g.undercover_word_under = data.get('undercover_word_under', '')
        g.undercover_name = data.get('undercover_name', '')
        # normalize legacy/swap names in saved dict keys (suspicion/trust/grudges)
        legacy_agents = []
        for a in data.get('agents', []):
            name = _normalize_name(a.get('name', ''))
            a['name'] = name
            if isinstance(a, dict) and 'replaced_bot' in a:
                a.pop('replaced_bot', None)
            for key in ['suspicion', 'trust', 'grudges']:
                if key in a and isinstance(a[key], dict):
                    a[key] = { _normalize_name(k): v for k, v in a[key].items() }
            legacy_agents.append(a)

        g.human = HumanPlayer(**_normalize_state_names(data.get('human', {})))
        g.humans = [HumanPlayer(**_normalize_state_names(h)) for h in data.get('humans', ([] if not data.get('human', {}).get('joined') else [data.get('human')]))]
        g.human_role = data.get('human_role')
        g.agents = [Agent(**a) for a in legacy_agents]
        g.sanitize_humans()
        return g

    def save(self):
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(_normalize_state_names(self.to_dict()), f, ensure_ascii=False, indent=2)

    @staticmethod
    def load():
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            return Game.from_dict(json.load(f))

    def alive(self):
        return [a for a in self.agents if a.alive]

    def wolves(self, alive_only=True):
        arr = [a for a in self.agents if a.role == '狼人']
        return [a for a in arr if a.alive] if alive_only else arr

    def villagers(self):
        return [a for a in self.agents if a.alive and a.role != '狼人']

    def get(self, name: str):
        return next(a for a in self.agents if a.name == name)

    def winner(self):
        if self.game_mode == 'undercover':
            alive_names = self.active_players_names()
            if self.undercover_name and self.undercover_name not in alive_names:
                return '平民'
            if len(alive_names) <= 2 and self.undercover_name in alive_names:
                return '臥底'
            return None
        wolves = len(self.wolves(True)) + len([h for h in self.alive_humans() if h.role == '狼人'])
        villagers = len([a for a in self.agents if a.alive and a.role != '狼人']) + len([h for h in self.alive_humans() if h.role != '狼人'])
        if wolves == 0:
            return '好人'
        if wolves >= villagers:
            return '狼人'
        return None

    def send(self, token: str, text: str):
        TG(token).call('sendMessage', {'chat_id': CHAT_ID, 'text': text})

    def send_private(self, user_id: int, text: str):
        try:
            TG(BOT_TOKENS[0]).call('sendMessage', {'chat_id': user_id, 'text': text})
            return True
        except Exception:
            return False

    def ensure_private_contact(self, human: HumanPlayer):
        ok = self.send_private(human.user_id, '✅ 連線成功：你可以在這裡收到身份與夜晚提示。')
        human.dm_ready = bool(ok)
        return human.dm_ready

    def say_system(self, text: str):
        print('[SYSTEM]', text)
        self.log.append(f'[SYSTEM] {text}')
        self.send(BOT_TOKENS[0], text)
        time.sleep(SYSTEM_SLEEP)

    def say(self, agent: Agent, text: str):
        text = text.strip().replace('\n', ' ')
        if not text:
            text = '我先保留。'
        print(f'[{agent.name}]', text)
        self.log.append(f'[{agent.name}] {text}')
        self.send(agent.token, text)
        time.sleep(TURN_SLEEP)
        self.update_memories_after_speech(agent.name, text)

    def update_memories_after_speech(self, speaker: str, text: str):
        bad_words = ['狼', '怪', '不對', '做身份', '帶節奏', '可疑', '想出']
        good_words = ['像好人', '先保', '站邊', '比較白']
        for a in self.alive():
            if a.name == speaker:
                continue
            a.public_memory.append(f'{speaker}：{text}')
            if a.name in text and any(w in text for w in bad_words):
                if speaker in a.grudges:
                    a.grudges[speaker] = round(min(1.0, a.grudges[speaker] + 0.2), 2)
                a.attacked_by.append(speaker)
            if a.name in text and any(w in text for w in good_words):
                a.defended_by.append(speaker)
        for name in BOT_NAMES:
            if name == speaker:
                continue
            if name in text and any(w in text for w in bad_words):
                sp = self.get(speaker)
                if name in sp.suspicion:
                    sp.suspicion[name] = round(min(0.99, sp.suspicion[name] + 0.12), 2)
            if name in text and any(w in text for w in good_words):
                sp = self.get(speaker)
                if name in sp.trust:
                    sp.trust[name] = round(min(0.99, sp.trust[name] + 0.1), 2)

    def snapshot_public(self):
        alive = '、'.join(self.active_players_names())
        dead_parts = [f'{a.name}({a.revealed_role or "未知"})' for a in self.agents if not a.alive]
        dead = '、'.join(dead_parts) or '無'
        recent = '\n'.join(self.log[-60:]) or '無'
        return f'第{self.day}天，階段：{self.phase}\n存活：{alive}\n出局：{dead}\n最近訊息（完整脈絡）：\n{recent}'

    def snapshot_private(self, agent: Agent):
        data = {
            'name': agent.name,
            'role': agent.role,
            'style': agent.style,
            'private_notes': agent.private_notes[-20:],
            'long_memory': agent.public_memory[-120:],
            'suspicion': agent.suspicion,
            'trust': agent.trust,
            'grudges': agent.grudges,
            'attacked_by': agent.attacked_by[-12:],
            'defended_by': agent.defended_by[-12:],
            'wolf_plan': self.wolf_plan[-8:] if agent.role == '狼人' else [],
        }
        return json.dumps(data, ensure_ascii=False)

    def llm_text(self, prompt: str):
        last_err = None
        for _ in range(4):
            try:
                text = self.llm.chat([
                    {'role': 'system', 'content': SYSTEM_PROMPT},
                    {'role': 'user', 'content': prompt},
                ], temperature=0.95).strip()
                if text:
                    return text
            except Exception as e:
                last_err = e
                time.sleep(1.2)
        print('llm_text failed', last_err)
        return None

    def llm_json(self, prompt: str):
        last_err = None
        for _ in range(4):
            try:
                raw = self.llm.chat([
                    {'role': 'system', 'content': SYSTEM_PROMPT},
                    {'role': 'user', 'content': prompt},
                ], temperature=0.8)
                if raw.startswith('```'):
                    raw = raw.strip('`').split('\n', 1)[-1]
                data = json.loads(raw)
                if isinstance(data, dict):
                    return data
            except Exception as e:
                last_err = e
                time.sleep(1.2)
        print('llm_json failed', last_err)
        return None

    def start_werewolf_game(self):
        self.phase = 'night'
        self.auto_run = True
        self.last_auto_ts = time.time()
        self.agents = self._make_agents()
        self._reset_round_state()
        roles_assigned = self._apply_human_replacements()

        if self.humans:
            self.say_system('🎭 V2.3 狼人殺開始。真人玩家正式入局：' + '、'.join(roles_assigned))
            self.say_system('玩家：' + '、'.join(self.active_players_names()))
            for h in self.humans:
                if h.joined and h.role:
                    ok = self.send_private(h.user_id, f'🔐 你的身份是：{h.role}')
                    h.dm_ready = bool(ok)
                    if not ok:
                        self.say_system(f'📩 {h.name} 無法收到私訊身份，請先私訊機器人 /start。')
                    else:
                        self.say_system(f'✅ {h.name} 已收到私訊身份。')
            self.say_system('規則：白天按輪次發言；投票用 /vote 名字；夜晚技能請私訊機器人使用 /kill /check /save /poison /pass；可用 /quit 退出本局')
        else:
            self.say_system('🎭 V2.3 狼人殺開始。')
            self.say_system('玩家：' + '、'.join(a.name for a in self.agents if a.alive))

    def start_undercover_game(self):
        self.phase = 'discussion'
        self.auto_run = True
        self.last_auto_ts = time.time()
        self.day = 1
        self.agents = self._make_agents()
        self._reset_round_state()
        roles_assigned = self._apply_human_replacements()
        civil, under = random.choice(UNDERCOVER_WORD_PAIRS)
        self.undercover_word_civil = civil
        self.undercover_word_under = under

        alive_names = self.active_players_names()
        self.undercover_name = random.choice(alive_names) if alive_names else ''

        for a in self.alive():
            a.role = '臥底' if a.name == self.undercover_name else '平民'
            if a.role == '臥底':
                a.private_notes.append(f'你是臥底，你的詞是「{under}」。盡量裝成平民。')
            else:
                a.private_notes.append(f'你是平民，你的詞是「{civil}」。找出臥底。')

        for h in self.alive_humans():
            h.role = '臥底' if h.name == self.undercover_name else '平民'

        if self.humans:
            self.say_system('🕵️ 誰是臥底開始。真人玩家入局：' + '、'.join(roles_assigned))
            self.say_system('玩家：' + '、'.join(self.active_players_names()))
            for h in self.humans:
                if h.joined and h.alive:
                    word = under if h.role == '臥底' else civil
                    ok = self.send_private(h.user_id, f'🔐 你的身份：{h.role}，你的詞：{word}')
                    h.dm_ready = bool(ok)
                    if not ok:
                        self.say_system(f'📩 {h.name} 無法收到私訊詞語，請先私訊機器人 /start。')
                    else:
                        self.say_system(f'✅ {h.name} 已收到私訊詞語。')
            self.say_system('規則：每輪發言描述你的詞但不要直接講出來；之後投票 /vote 名字；可用 /quit 退出本局')
        else:
            self.say_system('🕵️ 誰是臥底開始。')
            self.say_system('玩家：' + '、'.join(a.name for a in self.agents if a.alive))

        self.turn_order = [a.name for a in self.alive()] + [h.name for h in self.alive_humans()]
        random.shuffle(self.turn_order)
        self.turn_index = 0

    def start_game(self):
        if self.game_mode == 'undercover':
            self.start_undercover_game()
        else:
            self.start_werewolf_game()
        self.save()

    def plan_wolves(self):
        wolves = self.wolves(True)
        if len(wolves) == 0:
            return None
        targets = [a for a in self.alive() if a.role != '狼人']
        if not targets:
            return None
        prompt = f'''你現在要扮演狼人團隊的共同策略腦，只輸出JSON。\n狼人：{[w.name for w in wolves]}\n目標候選：{[t.name for t in targets]}\n公開局勢：\n{self.snapshot_public()}\n\n請輸出 {{"kill":"名字","cover":"白天想保的人","push":"白天想踩的人","note":"20字內策略"}}'''
        plan = self.llm_json(prompt)
        if not plan:
            return None
        valid_targets = [t.name for t in targets]
        if plan.get('kill') not in valid_targets:
            return None
        self.wolf_plan.append(f"夜裡共識：刀{plan['kill']}，白天保{plan.get('cover')}，踩{plan.get('push')}，{plan.get('note')}")
        for w in wolves:
            w.private_notes.append(self.wolf_plan[-1])
            if plan.get('push') in w.suspicion:
                w.suspicion[plan['push']] = round(min(0.99, w.suspicion[plan['push']] + 0.18), 2)
            if plan.get('cover') in w.trust:
                w.trust[plan['cover']] = round(min(0.99, w.trust[plan['cover']] + 0.2), 2)
        return self.get(plan['kill'])

    def seer_check(self):
        seer = next((a for a in self.agents if a.alive and a.role == '預言家'), None)
        if not seer:
            return
        cands = [a for a in self.alive() if a.name != seer.name]
        if not cands:
            return
        prompt = f'''你是{seer.name}，身份是預言家。\n私人狀態：{self.snapshot_private(seer)}\n公開局勢：\n{self.snapshot_public()}\n候選查驗對象：{[a.name for a in cands]}\n只輸出JSON：{{"target":"名字","reason":"20字內"}}'''
        data = self.llm_json(prompt)
        if not data:
            return
        target_name = data.get('target')
        if target_name not in [a.name for a in cands]:
            return
        target = self.get(target_name)
        result = '狼人' if target.role == '狼人' else '好人'
        note = f'昨晚查驗 {target.name}，結果是{result}。'
        seer.private_notes.append(note)
        seer.suspicion[target.name] = 0.99 if result == '狼人' else 0.05

    def witch_act(self, victim: Optional[Agent]) -> Tuple[bool, Optional[Agent]]:
        witch = next((a for a in self.agents if a.alive and a.role == '女巫'), None)
        if not witch:
            return False, None
        alive_targets = [a.name for a in self.alive() if a.name != witch.name]
        prompt = f'''你是{witch.name}，身份是女巫。\n私人狀態：{self.snapshot_private(witch)}\n公開局勢：\n{self.snapshot_public()}\n昨晚狼人目標：{victim.name if victim else '無'}\n可毒對象：{alive_targets}\n\n只輸出JSON：{{"save":true或false,"poison":"名字或空字串","reason":"20字內"}}\n注意：解藥和毒藥都可能已用過。'''
        data = self.llm_json(prompt)
        if not data:
            return False, None
        saved = False
        poisoned = None
        if victim and not self.witch_heal_used and bool(data.get('save')):
            saved = True
            self.witch_heal_used = True
            witch.private_notes.append(f'你昨晚救了 {victim.name}。')
        poison_name = (data.get('poison') or '').strip()
        if poison_name and not self.witch_poison_used and poison_name in alive_targets:
            poisoned = self.get(poison_name)
            self.witch_poison_used = True
            witch.private_notes.append(f'你昨晚毒了 {poisoned.name}。')
        return saved, poisoned

    def _alive_names_for_human(self):
        return self.active_players_names()

    def _night_waiting_tip(self, mode: str):
        alive_names = '、'.join(self._alive_names_for_human())
        if mode == 'witch':
            return f'目前存活：{alive_names}\n指令：/save、/poison 名字、/pass'
        if mode == 'seer':
            return f'目前存活：{alive_names}\n指令：/check 名字'
        return f'目前存活：{alive_names}\n指令：/kill 名字'

    def need_human_night_action(self):
        waiting = []
        for h in self.alive_humans():
            role = h.role
            if role == '女巫':
                if not (self.witch_heal_used and self.witch_poison_used) and not h.pending_action:
                    waiting.append((h, 'witch'))
            elif role == '預言家':
                if not h.pending_action:
                    waiting.append((h, 'seer'))
            elif role == '狼人':
                if not h.pending_action:
                    waiting.append((h, 'wolf'))
        return waiting

    def prompt_human_night_action(self):
        waiting = self.need_human_night_action()
        if not waiting:
            self.night_prompted_users = []
            return False
        waiting_ids = {h.user_id for h, _ in waiting}
        self.night_prompted_users = [uid for uid in self.night_prompted_users if uid in waiting_ids]
        for h, mode in waiting:
            if h.user_id in self.night_prompted_users:
                continue
            tip = self._night_waiting_tip(mode)
            if mode == 'witch':
                msg = f'🌙 你是女巫。請選擇：/save 救人、/poison 名字 毒人、/pass 不行動。\n{tip}'
            elif mode == 'seer':
                msg = f'🌙 你是預言家。請用 /check 名字 查驗。\n{tip}'
            else:
                msg = f'🌙 你是狼人。請用 /kill 名字 指定今晚目標。\n{tip}'
            if not h.dm_ready:
                h.dm_ready = self.ensure_private_contact(h)
            if h.dm_ready and self.send_private(h.user_id, msg):
                self.night_prompted_users.append(h.user_id)
            else:
                self.say_system(f'📩 {h.name} 尚未私訊機器人，夜晚無法送達提示（請先私訊 /start）。')
        return True

    def human_night_ready(self):
        return len(self.need_human_night_action()) == 0

    def resolve_night(self):
        self.night_prompted_users = []
        self.seer_check()
        victim = self.plan_wolves()
        human_target = None

        for h in self.alive_humans():
            if h.role == '預言家' and h.pending_action and h.pending_action.get('type') == 'check':
                target = h.pending_action.get('target')
                valid = [a.name for a in self.alive() if a.name != h.name] + [x.name for x in self.alive_humans() if x.name != h.name]
                if target in valid and target in [a.name for a in self.agents]:
                    real = self.get(target)
                    self.send_private(h.user_id, f'🔐 你的查驗結果：{target} 是{"狼人" if real.role=="狼人" else "好人"}')

        saved, poisoned = self.witch_act(victim)

        for h in self.alive_humans():
            if h.role == '女巫' and h.pending_action:
                act = h.pending_action
                if act.get('type') == 'save' and victim and not self.witch_heal_used:
                    saved = True
                    self.witch_heal_used = True
                    self.send_private(h.user_id, '🔐 你使用了解藥。')
                elif act.get('type') == 'poison' and not self.witch_poison_used:
                    t = act.get('target')
                    bot_valid = [a.name for a in self.alive() if a.name != h.name]
                    human_valid = [x.name for x in self.alive_humans() if x.name != h.name]
                    if t in bot_valid:
                        poisoned = self.get(t)
                        self.witch_poison_used = True
                        self.send_private(h.user_id, f'🔐 你使用了毒藥，目標：{t}')
                    elif t in human_valid:
                        human_target = next((x for x in self.alive_humans() if x.name == t), None)
                        self.witch_poison_used = True
                        self.send_private(h.user_id, f'🔐 你使用了毒藥，目標：{t}')

        for h in self.alive_humans():
            if h.role == '狼人' and h.pending_action and h.pending_action.get('type') == 'kill':
                t = h.pending_action.get('target')
                bot_valid = [a.name for a in self.alive() if a.role != '狼人']
                human_valid = [x.name for x in self.alive_humans() if x.role != '狼人' and x.name != h.name]
                if t in bot_valid:
                    victim = self.get(t)
                    human_target = None
                elif t in human_valid:
                    victim = None
                    human_target = next((x for x in self.alive_humans() if x.name == t), None)

        deaths = []
        if victim and not saved:
            victim.alive = False
            victim.revealed_role = victim.role
            deaths.append(victim.name)
        if human_target and not saved and human_target.alive:
            human_target.alive = False
            if human_target.name not in deaths:
                deaths.append(human_target.name)
        if poisoned and poisoned.alive:
            poisoned.alive = False
            poisoned.revealed_role = poisoned.role
            if poisoned.name not in deaths:
                deaths.append(poisoned.name)

        for h in self.humans:
            h.pending_action = None
        self.pending_night_deaths = deaths

    def advance_night(self):
        if self.night_started_day != self.day:
            self.say_system(f'🌙 第 {self.day} 夜開始，天黑請閉眼。')
            self.night_started_day = self.day
            self.night_deadline_ts = time.time() + 60
            self.night_prompted_users = []
        if self.prompt_human_night_action() and not self.human_night_ready():
            return
        self.resolve_night()
        self.night_deadline_ts = 0.0
        if not self.pending_night_deaths:
            self.say_system('🌤 天亮了，昨晚平安夜。')
        else:
            self.say_system('🌤 天亮了。')
            for name in self.pending_night_deaths:
                dead_human = next((x for x in self.humans if x.joined and x.name == name), None)
                if dead_human:
                    self.say_system(f'💀 {dead_human.name} 出局，身份是{dead_human.role}。')
                    for a in self.alive():
                        a.public_memory.append(f'{dead_human.name} 夜裡出局，身份是{dead_human.role}。')
                    continue
                dead = self.get(name)
                self.say_system(f'💀 {dead.name} 出局，身份是{dead.role}。')
                for a in self.alive():
                    a.public_memory.append(f'{dead.name} 夜裡出局，身份是{dead.role}。')
        self.turn_order = [a.name for a in self.alive()]
        for h in self.alive_humans():
            self.turn_order.append(h.name)
        random.shuffle(self.turn_order)
        self.turn_index = 0
        self.human_speech_wait_user_id = 0
        self.human_speech_deadline_ts = 0.0
        self.phase = 'discussion'

    def maybe_claim_role(self, agent: Agent) -> bool:
        if self.game_mode != 'werewolf':
            return False
        if agent.role == '預言家':
            wolf_hits = [n for n, v in agent.suspicion.items() if v >= 0.95 and self.get(n).alive]
            return bool(wolf_hits) and (self.day >= 2 or len(self.alive()) <= 4)
        return False

    def undercover_discussion_turn(self):
        if self.turn_index == 0:
            self.say_system(f'🕵️ 第 {self.day} 輪發言開始。請描述你的詞，但不要直接講詞。')
        if self.turn_index >= len(self.turn_order):
            self.turn_index = 0
            self.human_speech_wait_user_id = 0
            self.human_speech_deadline_ts = 0.0
            self.phase = 'vote'
            return

        current_name = self.turn_order[self.turn_index]
        human_current = next((h for h in self.alive_humans() if h.name == current_name), None)
        if human_current:
            if self.human_speech_wait_user_id != human_current.user_id:
                self.human_speech_wait_user_id = human_current.user_id
                self.human_speech_deadline_ts = time.time() + 60
                self.say_system(f'🎙 輪到真人玩家 {human_current.name} 描述，60秒內發言。')
            return

        self.human_speech_wait_user_id = 0
        self.human_speech_deadline_ts = 0.0
        agent = self.get(current_name)
        if not agent.alive:
            self.turn_index += 1
            return

        my_word = self.undercover_word_under if agent.role == '臥底' else self.undercover_word_civil
        prompt = f'''你是{agent.name}，在玩誰是臥底。你的身份：{agent.role}，你的詞：{my_word}。
公開局勢：
{self.snapshot_public()}
請輸出40到110字發言，描述你的詞特徵但不要直接講詞，語氣像台灣玩家，並可點名一位你懷疑的人。'''
        text = self.llm_text(prompt)
        if text:
            self.say(agent, text)
        self.turn_index += 1

    def undercover_voting_step(self):
        self.say_system(f'🗳 第 {self.day} 輪投票開始。')
        votes: Dict[str, int] = {}
        alive_humans = self.alive_humans()

        if alive_humans and not self.vote_prompted:
            self.say_system('🙋 真人玩家請用 /vote 名字 投票（60秒，逾時視為棄權）。')
            self.vote_prompted = True
            self.vote_deadline_ts = time.time() + 60
            return

        if alive_humans and self.vote_prompted:
            all_ready = all(h.pending_action and h.pending_action.get('type') in ('vote', 'pass') for h in alive_humans)
            if not all_ready and time.time() < self.vote_deadline_ts:
                return

        alive_names = self.active_players_names()
        for agent in self.alive():
            candidates = [n for n in alive_names if n != agent.name]
            prompt = f'''你是{agent.name}，身份：{agent.role}。公開局勢：
{self.snapshot_public()}
候選人：{candidates}
只輸出JSON：{{"target":"名字","reason":"20字內"}}'''
            data = self.llm_json(prompt)
            if not data:
                continue
            target = data.get('target')
            if target not in candidates:
                continue
            reason = str(data.get('reason', ''))[:30]
            self.say(agent, f'我投 {target}，{reason}' if reason else f'我投 {target}')
            votes[target] = votes.get(target, 0) + 1

        valid_human_targets = self.active_players_names()
        for h in alive_humans:
            act = h.pending_action or {}
            if act.get('type') == 'vote':
                target = act.get('target')
                valid = [n for n in valid_human_targets if n != h.name]
                if target in valid:
                    votes[target] = votes.get(target, 0) + 1
                    self.say_system(f'🗳 {h.name} 投給了 {target}。')
                else:
                    self.say_system(f'⚠️ {h.name} 投票目標無效，視為棄權。')
            else:
                self.say_system(f'⌛ {h.name} 投票逾時，視為棄權。')
            h.pending_action = None

        self.vote_prompted = False
        self.vote_deadline_ts = 0.0

        if not votes:
            self.day += 1
            self.phase = 'discussion'
            self.turn_order = self.active_players_names()
            random.shuffle(self.turn_order)
            return

        top = max(votes.values())
        out_name = random.choice([n for n, c in votes.items() if c == top])
        out_human = next((h for h in self.alive_humans() if h.name == out_name), None)
        if out_human:
            out_human.alive = False
            self.say_system(f'📢 票型結算，{out_human.name} 被淘汰。')
        else:
            out = self.get(out_name)
            out.alive = False
            out.revealed_role = out.role
            self.say_system(f'📢 票型結算，{out.name} 被淘汰。')

        if self.winner():
            self.phase = 'ended'
        else:
            self.day += 1
            self.phase = 'discussion'
            self.turn_order = self.active_players_names()
            random.shuffle(self.turn_order)

    def discussion_turn(self):
        if self.turn_index == 0:
            self.say_system(f'🗣 第 {self.day} 天討論開始。')
        if self.turn_index >= len(self.turn_order):
            self.turn_index = 0
            self.human_speech_wait_user_id = 0
            self.human_speech_deadline_ts = 0.0
            self.phase = 'defense'
            return
        current_name = self.turn_order[self.turn_index]
        human_current = next((h for h in self.alive_humans() if h.name == current_name), None)
        if human_current:
            if self.human_speech_wait_user_id != human_current.user_id:
                self.human_speech_wait_user_id = human_current.user_id
                self.human_speech_deadline_ts = time.time() + 60
                self.say_system(f'🎙 輪到真人玩家 {human_current.name} 發言，60秒內請直接在群組說話。')
            return
        self.human_speech_wait_user_id = 0
        self.human_speech_deadline_ts = 0.0
        agent = self.get(current_name)
        if not agent.alive:
            self.turn_index += 1
            return
        top_sus = sorted(agent.suspicion.items(), key=lambda kv: kv[1] + agent.grudges.get(kv[0], 0), reverse=True)
        extra = ''
        if agent.attacked_by:
            extra += f'最近踩你的人：{agent.attacked_by[-3:] }。可以選一個回嘴。\n'
        if agent.defended_by:
            extra += f'最近保你的人：{agent.defended_by[-3:] }。可稍微給信任。\n'
        if self.maybe_claim_role(agent):
            extra += '你可以考慮跳預言家，並給查驗資訊。\n'
        prompt = f'''你是{agent.name}。身份：{agent.role}。人格：{agent.style}\n私人狀態：{self.snapshot_private(agent)}\n公開局勢：\n{self.snapshot_public()}\n{extra}\n請輸出一段35到120字的群組發言，要像台灣玩家自然聊天，可帶口語語氣，最好點名1到2個人，並明確說你的懷疑或站邊。'''
        text = self.llm_text(prompt)
        if not text:
            self.turn_index += 1
            return
        self.say(agent, text)
        self.turn_index += 1

    def defense_step(self):
        alive = self.alive()
        target = random.choice(alive)
        prompt = f'''你是{target.name}，有人正在懷疑你。身份：{target.role}。人格：{target.style}\n私人狀態：{self.snapshot_private(target)}\n公開局勢：\n{self.snapshot_public()}\n請輸出一段40到110字的辯解，口氣像台灣玩家，具體回應質疑，不要空話。'''
        text = self.llm_text(prompt)
        if text:
            self.say(target, text)
        self.phase = 'vote'

    def voting_step(self):
        self.say_system(f'🗳 第 {self.day} 天投票開始。')
        alive_humans = self.alive_humans()
        candidates = self._vote_candidates()

        if len(candidates) <= 1:
            self.say_system('❗ 有效票型候選不足，直接進入下一日。')
            self.phase = 'night'
            self.day += 1
            self.vote_round = 1
            self.vote_round2_candidates = []
            self.vote_appeal_target = None
            self.vote_appeal_deadline_ts = 0.0
            self._clear_human_actions()
            return

        votes: Dict[str, int] = {}

        if self.vote_round == 1:
            if alive_humans and not self.vote_prompted:
                self.say_system('🙋 真人玩家請用 /vote 名字 投票（60秒，逾時視為棄權）。')
                self.vote_prompted = True
                self.vote_deadline_ts = time.time() + 60
                return

            if alive_humans and self.vote_prompted:
                all_ready = all(h.pending_action and h.pending_action.get('type') in ('vote', 'pass') for h in alive_humans)
                if not all_ready and time.time() < self.vote_deadline_ts:
                    return

        if self.vote_round == 2 and not self.vote_prompted:
            target = self.vote_appeal_target
            if not target:
                self.vote_prompted = False
            else:
                self.say_system(f'🔁 複議階段：請在 {VOTE_APPEAL_SECONDS} 秒內重新提交 /vote {target} 或其他。')
                self.vote_prompted = True
                self.vote_deadline_ts = time.time() + VOTE_APPEAL_SECONDS
                return

        if self.vote_round == 2 and self.vote_prompted:
            all_ready = all(h.pending_action and h.pending_action.get('type') in ('vote', 'pass') for h in alive_humans)
            if alive_humans and not all_ready and time.time() < self.vote_deadline_ts:
                return

        for agent in self.alive():
            ai_candidates = [a for a in candidates if a != agent.name]
            if not ai_candidates:
                continue
            prompt = f'''你是{agent.name}。身份：{agent.role}。人格：{agent.style}\n私人狀態：{self.snapshot_private(agent)}\n公開局勢：\n{self.snapshot_public()}\n候選人：{ai_candidates}\n只輸出JSON：{{"target":"名字","reason":"20字內"}}'''
            data = self.llm_json(prompt)
            if not data:
                continue
            target = data.get('target')
            if target not in ai_candidates:
                continue
            reason = str(data.get('reason', ''))[:30]
            agent.last_vote = target
            self.say(agent, f'我投 {target}，{reason}' if reason else f'我投 {target}')
            votes[target] = votes.get(target, 0) + 1

        valid_human_targets = [a.name for a in self.alive()] + [h.name for h in alive_humans]
        valid_human_targets = [n for n in valid_human_targets if n in candidates]
        for h in alive_humans:
            act = h.pending_action or {}
            if act.get('type') == 'vote':
                target = act.get('target')
                valid = [n for n in valid_human_targets if n != h.name]
                if target in valid:
                    votes[target] = votes.get(target, 0) + 1
                    self.say_system(f'🗳 {h.name} 投給了 {target}。')
                else:
                    self.say_system(f'⚠️ {h.name} 投票目標無效，視為棄權。')
            else:
                self.say_system(f'⌛ {h.name} 投票逾時，視為棄權。')
            h.pending_action = None

        self.vote_prompted = False
        self.vote_deadline_ts = 0.0

        if not votes:
            self.phase = 'night'
            self.day += 1
            self.vote_round = 1
            self.vote_round2_candidates = []
            self.vote_appeal_target = None
            return

        top = max(votes.values())
        top_targets = [n for n, c in votes.items() if c == top]
        tied_top = len(top_targets) > 1

        if self.vote_round == 1 and tied_top:
            self.vote_round = 2
            self.vote_round2_candidates = top_targets
            self.vote_appeal_target = top_targets[0]
            self._clear_human_actions()
            self.say_system(f'🔁 本輪平票，候選為：{"、".join(top_targets)}，發起複議，進入第二輪。')
            return

        out_name = random.choice(top_targets)
        self._finalize_vote(out_name)
        if self.winner():
            self.phase = 'ended'
        else:
            self.day += 1
            self.phase = 'night'

        self.vote_round = 1
        self.vote_round2_candidates = []
        self.vote_appeal_target = None

    def current_human_speaker(self):
        if self.phase != 'discussion' or self.human_speech_wait_user_id == 0:
            return None
        return self.find_human_by_user(self.human_speech_wait_user_id)

    def is_human_turn(self, user_id: int):
        return self.phase == 'discussion' and self.human_speech_wait_user_id == user_id

    def record_human_message(self, speaker: str, text: str):
        line = f'[{speaker}] {text.strip()}'
        self.log.append(line)
        for a in self.alive():
            a.public_memory.append(f'{speaker}：{text.strip()}')
            lower = text.strip()
            for name in BOT_NAMES:
                if name in lower:
                    if any(w in lower for w in ['狼', '怪', '可疑', '不對', '出', '投']):
                        if name in a.suspicion:
                            a.suspicion[name] = round(min(0.99, a.suspicion[name] + 0.08), 2)
                    if any(w in lower for w in ['保', '白', '好人']):
                        if name in a.trust:
                            a.trust[name] = round(min(0.99, a.trust[name] + 0.06), 2)

    def process_human_quit(self, human: HumanPlayer):
        if not human.alive:
            human.joined = False
            human.pending_action = None
            return
        human.alive = False
        human.joined = False
        human.pending_action = None
        self.say_system(f'🚪 {human.name} 已退出本局。')
        if human.name in self.turn_order:
            self.turn_order = [n for n in self.turn_order if n != human.name]
            if self.turn_index >= len(self.turn_order):
                self.turn_index = 0
        self.human_speech_wait_user_id = 0
        self.human_speech_deadline_ts = 0.0
        if self.winner():
            self.phase = 'ended'



    def handle_timeouts(self):
        changed = False
        now = time.time()

        if self.game_mode == 'werewolf' and self.phase == 'night' and self.night_deadline_ts > 0 and now >= self.night_deadline_ts:
            for h, _ in self.need_human_night_action():
                if not h.dm_ready:
                    self.say_system(f'📩 {h.name} 未完成私訊連線，本夜視為棄權。')
                h.pending_action = {'type': 'pass'}
                self.say_system(f'⌛ {h.name} 夜晚操作逾時，視為棄權。')
                changed = True

        if self.phase == 'discussion' and self.human_speech_wait_user_id and self.human_speech_deadline_ts > 0 and now >= self.human_speech_deadline_ts:
            h = self.find_human_by_user(self.human_speech_wait_user_id)
            if h and h.alive:
                self.say_system(f'⌛ {h.name} 發言逾時，視為棄權。')
            self.human_speech_wait_user_id = 0
            self.human_speech_deadline_ts = 0.0
            self.turn_index += 1
            changed = True

        if self.phase == 'vote' and self.vote_prompted and self.vote_deadline_ts > 0 and now >= self.vote_deadline_ts:
            if self.vote_round == 2 and self.vote_round2_candidates:
                # 第二輪逾時：仍然用目前投票最高票結算，不再等待
                self.vote_round = 2
                self.vote_appeal_target = self.vote_round2_candidates[0]
                for h in self.alive_humans():
                    if h.pending_action and h.pending_action.get('type') not in ('vote', 'pass'):
                        self.say_system(f'⌛ {h.name} 在複議階段逾時，視為棄權。')
                changed = True
            else:
                changed = True

        return changed

    def maybe_auto_advance(self):
        if not self.auto_run:
            return False
        if self.phase in ('done',):
            return False
        if time.time() - self.last_auto_ts < 3.0:
            return False
        self.advance()
        self.last_auto_ts = time.time()
        return True


    def reveal_all(self):
        if self.game_mode == 'undercover':
            self.say_system(
                '📜 本局結果公布：\n'
                + f'臥底：{self.undercover_name}\n'
                + f'平民詞：{self.undercover_word_civil}\n'
                + f'臥底詞：{self.undercover_word_under}'
            )
            return
        self.say_system('📜 本局身份公布：\n' + '\n'.join(f'{a.name}：{a.role}' for a in self.agents))

    def advance(self):
        if self.phase == 'idle':
            self.start_game()
            return
        if self.game_mode == 'undercover':
            if self.phase == 'discussion':
                self.undercover_discussion_turn()
            elif self.phase == 'vote':
                self.undercover_voting_step()
            elif self.phase == 'ended':
                win = self.winner() or '未知'
                self.say_system(f'🏁 遊戲結束，{win}陣營獲勝！')
                self.reveal_all()
                self.phase = 'done'
            self.save()
            return
        if self.phase == 'night':
            self.advance_night()
        elif self.phase == 'discussion':
            self.discussion_turn()
        elif self.phase == 'defense':
            self.defense_step()
        elif self.phase == 'vote':
            self.voting_step()
        elif self.phase == 'ended':
            win = self.winner() or '未知'
            self.say_system(f'🏁 遊戲結束，{win}陣營獲勝！')
            self.reveal_all()
            self.phase = 'done'
        self.save()

    def status_text(self):
        alive = '、'.join(self.active_players_names())
        dead_parts = [f'{a.name}({a.revealed_role or "未知"})' for a in self.agents if not a.alive]
        for h in self.humans:
            if h.joined and not h.alive and h.role:
                dead_parts.append(f'{h.name}({h.role})')
        dead = '、'.join(dead_parts) or '無'
        current_human = self.current_human_speaker()
        return f'模式：{self.game_mode}\n目前第 {self.day} 天，階段：{self.phase}\n自動模式：{"開" if self.auto_run else "關"}\n存活：{alive}\n出局：{dead}\n下一手：{self.turn_order[self.turn_index] if self.phase=="discussion" and self.turn_index < len(self.turn_order) else "-"}\n真人發言權：{current_human.name if current_human else "無"}'


def ensure_env():
    miss = []
    if not API_KEY:
        miss.append('LLM_API_KEY')
    for i, t in enumerate(BOT_TOKENS, 1):
        if not t:
            miss.append(f'TG_BOT_{i}')
    if miss:
        raise SystemExit('缺少環境變數：' + ', '.join(miss))


def post_status(game: Game):
    game.say_system(game.status_text())


def run_controller():
    ensure_env()
    tg = TG(BOT_TOKENS[0])
    offset = None
    if os.path.exists(STATE_FILE):
        game = Game.load()
    else:
        game = Game()
        game.save()
    print('controller started')
    while True:
        try:
            data = tg.get_updates(offset=offset, timeout=20)
            handled_message = False
            for upd in data.get('result', []):
                offset = upd['update_id'] + 1
                msg = upd.get('message') or upd.get('edited_message') or {}
                chat = msg.get('chat', {})
                text = (msg.get('text') or '').strip()
                from_user = msg.get('from', {})
                user_id = from_user.get('id', 0)
                is_group = chat.get('id') == CHAT_ID
                is_private = chat.get('type') == 'private'
                game = Game.load()
                known_human = game.find_human_by_user(user_id)

                if not is_group and not is_private:
                    continue

                if text.startswith('/join'):
                    if not is_group:
                        continue
                    existing = game.find_human_by_user(user_id)
                    if not existing:
                        existing = HumanPlayer(user_id=user_id)
                        game.humans.append(existing)
                    existing.joined = True
                    existing.name = from_user.get('first_name') or from_user.get('username') or '玩家'
                    existing.dm_ready = game.ensure_private_contact(existing)
                    game.sanitize_humans()
                    game.say_system(f'🙋 真人玩家 {existing.name} 已加入。')
                    if not existing.dm_ready:
                        game.say_system(f'📩 {existing.name} 請先私訊機器人 /start，否則收不到身份與夜晚提示。')
                    game.save()
                    handled_message = True
                elif text.startswith('/switchgame'):
                    if not is_group:
                        continue
                    parts = text.split(maxsplit=1)
                    if len(parts) < 2:
                        game.say_system('⚙️ 用法：/switchgame werewolf 或 /switchgame undercover')
                    else:
                        mode = parts[1].strip().lower()
                        if mode in ('werewolf', 'wolf', '狼人殺'):
                            game.game_mode = 'werewolf'
                            game.phase = 'idle'
                            game.day = 1
                            game.auto_run = False
                            game.say_system('✅ 已切換到 狼人殺。請用 /start_game 開局。')
                            game.save()
                        elif mode in ('undercover', 'whoisundercover', '誰是臥底', '臥底'):
                            game.game_mode = 'undercover'
                            game.phase = 'idle'
                            game.day = 1
                            game.auto_run = False
                            game.say_system('✅ 已切換到 誰是臥底。請用 /start_game 開局。')
                            game.save()
                        else:
                            game.say_system('⚠️ 未知模式，請用 werewolf 或 undercover。')
                    handled_message = True
                elif text.startswith('/start_game') or text.startswith('/start') or text.startswith('/new'):
                    if is_private:
                        if known_human:
                            known_human.dm_ready = True
                            game.save()
                            game.send_private(user_id, '✅ 私訊連線已啟用。回群組用 /start_game 開局。')
                            handled_message = True
                        continue
                    if not is_group:
                        continue
                    old = game
                    game = Game()
                    game.game_mode = old.game_mode
                    game.humans = old.humans
                    game.start_game()
                    game.save()
                    handled_message = True
                elif text.startswith('/next'):
                    if not is_group:
                        continue
                    game.auto_run = False
                    game.advance()
                    game.save()
                    handled_message = True
                elif text.startswith('/vote'):
                    human = game.find_human_by_user(user_id)
                    if human and human.alive:
                        if game.phase != 'vote':
                            if is_group:
                                game.say_system(f'⛔ {human.name}，現在不是投票階段。')
                            else:
                                game.send_private(user_id, '⛔ 現在不是投票階段。')
                        else:
                            parts = text.split(maxsplit=1)
                            if len(parts) > 1:
                                target = parts[1].split('@')[0].strip()
                                if target == 'pass':
                                    human.pending_action = {'type': 'pass'}
                                else:
                                    candidates = game._vote_candidates()
                                    if target in candidates and target != human.name:
                                        human.pending_action = {'type': 'vote', 'target': target}
                                    else:
                                        if is_group:
                                            game.say_system(f'⚠️ {human.name}，目標無效。')
                                        else:
                                            game.send_private(user_id, '⚠️ 目標無效。')
                                        game.save()
                                if human.pending_action:
                                    if is_group:
                                        game.say_system(f'✅ 已收到 {human.name} 的投票。')
                                    else:
                                        game.send_private(user_id, f'✅ 已收到你的投票：{target}')
                            else:
                                if is_group:
                                    game.say_system(f'⚠️ {human.name}，請用 /vote 名字。')
                                else:
                                    game.send_private(user_id, '⚠️ 請用 /vote 名字。')
                            game.save()
                    handled_message = True
                elif text.startswith('/kill'):
                    human = game.find_human_by_user(user_id)
                    if human and human.alive and human.role == '狼人':
                        if game.phase != 'night':
                            if is_group:
                                game.say_system(f'⛔ {human.name}，現在不是夜晚。')
                            else:
                                game.send_private(user_id, '⛔ 現在不是夜晚。')
                        else:
                            parts = text.split(maxsplit=1)
                            if len(parts) > 1:
                                target = parts[1].split('@')[0].strip()
                                human.pending_action = {'type': 'kill', 'target': target}
                                if is_group:
                                    game.say_system(f'✅ 已收到 {human.name} 的狼人行動。')
                                else:
                                    game.send_private(user_id, f'✅ 已收到你的狼人行動：{target}')
                                game.save()
                            else:
                                if is_group:
                                    game.say_system(f'⚠️ {human.name}，請用 /kill 名字。')
                                else:
                                    game.send_private(user_id, '⚠️ 請用 /kill 名字。')
                    handled_message = True
                elif text.startswith('/check'):
                    human = game.find_human_by_user(user_id)
                    if human and human.alive and human.role == '預言家':
                        if game.phase != 'night':
                            if is_group:
                                game.say_system(f'⛔ {human.name}，現在不是夜晚。')
                            else:
                                game.send_private(user_id, '⛔ 現在不是夜晚。')
                        else:
                            parts = text.split(maxsplit=1)
                            if len(parts) > 1:
                                target = parts[1].split('@')[0].strip()
                                valid = [a.name for a in game.alive() if a.name != human.name] + [x.name for x in game.alive_humans() if x.name != human.name]
                                if target in valid:
                                    human.pending_action = {'type': 'check', 'target': target}
                                    if is_group:
                                        game.say_system(f'✅ 已收到 {human.name} 的查驗目標。')
                                    else:
                                        game.send_private(user_id, f'✅ 已收到你的查驗目標：{target}')
                                    game.save()
                                else:
                                    if is_group:
                                        game.say_system(f'⚠️ {human.name}，查驗目標無效。')
                                    else:
                                        game.send_private(user_id, '⚠️ 查驗目標無效。')
                            else:
                                if is_group:
                                    game.say_system(f'⚠️ {human.name}，請用 /check 名字。')
                                else:
                                    game.send_private(user_id, '⚠️ 請用 /check 名字。')
                    handled_message = True
                elif text.startswith('/save'):
                    human = game.find_human_by_user(user_id)
                    if human and human.alive and human.role == '女巫':
                        if game.phase != 'night':
                            if is_group:
                                game.say_system(f'⛔ {human.name}，現在不是夜晚。')
                            else:
                                game.send_private(user_id, '⛔ 現在不是夜晚。')
                        elif game.witch_heal_used:
                            if is_group:
                                game.say_system(f'⚠️ {human.name}，你的解藥已使用過。')
                            else:
                                game.send_private(user_id, '⚠️ 你的解藥已使用過。')
                        else:
                            human.pending_action = {'type': 'save'}
                            if is_group:
                                game.say_system(f'✅ 已收到 {human.name} 的解藥指令。')
                            else:
                                game.send_private(user_id, '✅ 已收到你的解藥指令。')
                            game.save()
                    handled_message = True
                elif text.startswith('/poison'):
                    human = game.find_human_by_user(user_id)
                    if human and human.alive and human.role == '女巫':
                        if game.phase != 'night':
                            if is_group:
                                game.say_system(f'⛔ {human.name}，現在不是夜晚。')
                            else:
                                game.send_private(user_id, '⛔ 現在不是夜晚。')
                        elif game.witch_poison_used:
                            if is_group:
                                game.say_system(f'⚠️ {human.name}，你的毒藥已使用過。')
                            else:
                                game.send_private(user_id, '⚠️ 你的毒藥已使用過。')
                        else:
                            parts = text.split(maxsplit=1)
                            if len(parts) > 1:
                                target = parts[1].split('@')[0].strip()
                                human.pending_action = {'type': 'poison', 'target': target}
                                if is_group:
                                    game.say_system(f'✅ 已收到 {human.name} 的毒藥指令。')
                                else:
                                    game.send_private(user_id, f'✅ 已收到你的毒藥指令：{target}')
                                game.save()
                            else:
                                if is_group:
                                    game.say_system(f'⚠️ {human.name}，請用 /poison 名字。')
                                else:
                                    game.send_private(user_id, '⚠️ 請用 /poison 名字。')
                    handled_message = True
                elif text.startswith('/pass'):
                    human = game.find_human_by_user(user_id)
                    if human and human.alive:
                        if game.phase not in ('night', 'vote'):
                            game.say_system(f'⛔ {human.name}，現在不能 /pass。')
                        else:
                            human.pending_action = {'type': 'pass'}
                            game.say_system(f'✅ {human.name} 本回合選擇不行動。')
                            game.save()
                    handled_message = True
                elif text.startswith('/quit') or text.startswith('/leave'):
                    human = game.find_human_by_user(user_id)
                    if human and human.joined:
                        game.process_human_quit(human)
                        game.save()
                        if is_private:
                            game.send_private(user_id, '✅ 你已退出本局。')
                    handled_message = True
                elif text.startswith('/status'):
                    if not is_group:
                        continue
                    post_status(game)
                    handled_message = True
                elif text.startswith('/appeal'):
                    human = game.find_human_by_user(user_id)
                    if human and human.alive:
                        if game.phase != 'vote':
                            if is_group:
                                game.say_system(f'⚠️ {human.name}，現在不是投票複議階段。')
                            else:
                                game.send_private(user_id, '⚠️ 現在不是投票複議階段。')
                        elif game.vote_round != 2:
                            if is_group:
                                game.say_system(f'⚠️ {human.name}，目前非第二輪平票複議。')
                            else:
                                game.send_private(user_id, '⚠️ 目前非第二輪平票複議。')
                        else:
                            if not game.vote_appeal_target:
                                game.say_system(f'ℹ️ {human.name}，目前平票票型仍未確定。')
                            else:
                                game.send_private(user_id, '🗳 請使用 /vote 名字 參與複議。')
                            handled_message = True
                    handled_message = True
                elif text.startswith('/reveal'):
                    if not is_group:
                        continue
                    game.reveal_all()
                    game.save()
                    handled_message = True
                elif text.startswith('/stop_game') or text.startswith('/stop'):
                    if not is_group:
                        continue
                    game.phase = 'done'
                    game.auto_run = False
                    game.say_system('⏹ 遊戲已停止。')
                    game.save()
                    handled_message = True
                elif text.startswith('/auto_on'):
                    if not is_group:
                        continue
                    game.auto_run = True
                    game.say_system('▶️ 已開啟自動推進。')
                    game.save()
                    handled_message = True
                elif text.startswith('/auto_off'):
                    if not is_group:
                        continue
                    game.auto_run = False
                    game.say_system('⏸ 已關閉自動推進。')
                    game.save()
                    handled_message = True
                elif text and not from_user.get('is_bot'):
                    human = game.find_human_by_user(user_id)
                    if not human:
                        handled_message = True
                        continue
                    if is_private:
                        game.send_private(user_id, '📩 已收到。夜晚請用私訊送 /kill /check /save /poison；投票可用 /vote。')
                        handled_message = True
                        continue
                    if game.is_human_turn(user_id):
                        game.record_human_message(human.name, text)
                        game.human_speech_wait_user_id = 0
                        game.human_speech_deadline_ts = 0.0
                        game.turn_index += 1
                        game.save()
                    elif game.phase == 'discussion':
                        game.say_system(f'⛔ {human.name}，現在不是你的發言時間。')
                    elif game.phase == 'night':
                        if game.game_mode == 'werewolf':
                            game.say_system(f'🤫 {human.name}，現在是夜晚，請只使用夜間指令。')
                        else:
                            game.say_system(f'⛔ {human.name}，現在不是你的發言時間。')
                    elif game.phase == 'vote':
                        game.say_system(f'🗳 {human.name}，現在是投票階段，請用 /vote 名字。')
                    handled_message = True
            if os.path.exists(STATE_FILE):
                game = Game.load()
                if game.handle_timeouts():
                    game.save()
                if game.maybe_auto_advance():
                    game.save()
        except Exception as e:
            print('loop error', e)
            time.sleep(POLL_SLEEP)


if __name__ == '__main__':
    run_controller()

def normalize_state_text(text: str) -> str:
    return _normalize_name(text)
