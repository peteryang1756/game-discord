import json
import random
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import List, Dict

CHAT_ID = -5103856268
BOTS = [
    {"name": "阿哲", "token": "8550197535:AAEARCOL1BX-_zRNQirrKDXXGYd-_74bDMo", "style": "冷靜理性，講話短，喜歡抓矛盾"},
    {"name": "彼得", "token": "8745144739:AAFQsp_Njw3hzMcS3FkPrAzfSx2-h9pdBlc", "style": "話多，喜歡帶節奏"},
    {"name": "小P", "token": "8750936435:AAGEeEV-qmSuVx-oXQi_VlXdQr5P0qhRl7s", "style": "裝無辜，容易懷疑別人"},
    {"name": "顧問", "token": "8131010210:AAHzy8Nt2GqZX0-xwKauxJB4HNX_AZbXVVY", "style": "像分析師，常說機率和邏輯"},
    {"name": "小羊", "token": "7962732534:AAHz6goSZbi8oGsXBTeu9r_YrMQcZwlSaWc", "style": "膽小保守，常跟票"},
    {"name": "阿J", "token": "8706615057:AAFmtNLASJuAiRfJ6k0beBwVupyIxfYvcmc", "style": "嘴砲型，愛挑釁"},
]
ROLES = ["狼人", "狼人", "預言家", "女巫", "村民", "村民"]
STATE_FILE = "game_state.json"


@dataclass
class Player:
    idx: int
    name: str
    token: str
    style: str
    role: str
    alive: bool = True
    revealed: bool = False


def tg_api(token: str, method: str, data: Dict):
    url = f"https://api.telegram.org/bot{token}/{method}"
    payload = urllib.parse.urlencode(data).encode()
    with urllib.request.urlopen(url, data=payload, timeout=20) as r:
        return json.loads(r.read().decode())


def send_as(player: Player, text: str):
    print(f"[{player.name}] {text}")
    tg_api(player.token, "sendMessage", {"chat_id": CHAT_ID, "text": text})
    time.sleep(1.6)


def send_system(text: str):
    print(f"[SYSTEM] {text}")
    tg_api(BOTS[0]["token"], "sendMessage", {"chat_id": CHAT_ID, "text": text})
    time.sleep(1.2)


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def load_state():
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def alive_players(players: List[Player]):
    return [p for p in players if p.alive]


def is_wolf(role: str):
    return role == "狼人"


def villagers_alive(players):
    return [p for p in players if p.alive and p.role != "狼人"]


def wolves_alive(players):
    return [p for p in players if p.alive and p.role == "狼人"]


def check_win(players):
    wolves = wolves_alive(players)
    villagers = villagers_alive(players)
    if not wolves:
        return "好人"
    if len(wolves) >= len(villagers):
        return "狼人"
    return None


def intro_line(player: Player):
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


def accusation_line(player: Player, target: Player):
    templates = [
        f"我先點一個，{target.name} 發言有點怪，我目前偏懷疑他。",
        f"如果今天要出票，我會想看 {target.name}，他剛剛像在做身份。",
        f"{target.name} 那個邏輯不太順，我先把票型壓在他身上。",
        f"我覺得 {target.name} 有狼味，先記一票。",
    ]
    return random.choice(templates)


def defense_line(player: Player):
    templates = [
        "我不是狼，票我真的會投在我最懷疑的人身上。",
        "你們可以懷疑我，但我的發言一直很一致。",
        "我這位置如果是狼不會這樣聊，自己想一下。",
        "先別被帶節奏，我的邏輯很乾淨。",
    ]
    return random.choice(templates)


def vote_line(player: Player, target: Player):
    templates = [
        f"我投 {target.name}。",
        f"這票我給 {target.name}。",
        f"我今天先出 {target.name}。",
    ]
    return random.choice(templates)


def death_line(player: Player):
    if player.role == "獵人":
        return f"{player.name} 倒下，身份是獵人。"
    return f"{player.name} 出局，身份是{player.role}。"


def assign_players():
    roles = ROLES[:]
    random.shuffle(roles)
    players = []
    for i, bot in enumerate(BOTS):
        players.append(Player(i, bot["name"], bot["token"], bot["style"], roles[i]))
    return players


def serialize_players(players):
    return [p.__dict__ for p in players]


def deserialize_players(data):
    return [Player(**x) for x in data]


def night_phase(players, day):
    send_system(f"🌙 第 {day} 夜開始，天黑請閉眼。")
    wolves = wolves_alive(players)
    others = villagers_alive(players)
    if wolves and others:
        kill = random.choice(others)
    else:
        kill = None

    seer = next((p for p in players if p.alive and p.role == "預言家"), None)
    witch = next((p for p in players if p.alive and p.role == "女巫"), None)

    if seer:
        targets = [p for p in players if p.alive and p.idx != seer.idx]
        if targets:
            checked = random.choice(targets)
            send_system(f"🔮 預言家查驗了 {checked.name}：{'狼人' if checked.role == '狼人' else '好人'}")

    saved = False
    poisoned = None
    if witch and kill and random.random() < 0.45:
        saved = True
        send_system(f"🧪 女巫今晚使用了解藥。")
    if witch and random.random() < 0.25:
        poison_targets = [p for p in players if p.alive and p.role == '狼人']
        if poison_targets:
            poisoned = random.choice(poison_targets)
            poisoned.alive = False
            send_system(f"☠️ 女巫今晚用了毒藥。")

    deaths = []
    if kill and not saved:
        kill.alive = False
        deaths.append(kill)
    if poisoned:
        deaths.append(poisoned)

    if not deaths:
        send_system("🌤 天亮了，昨晚是平安夜。")
    else:
        send_system("🌤 天亮了。")
        seen = set()
        for d in deaths:
            if d.idx not in seen:
                send_system(death_line(d))
                seen.add(d.idx)


def discussion_phase(players, day):
    send_system(f"🗣 第 {day} 天討論開始。")
    alive = alive_players(players)
    suspects = [p for p in alive]
    for p in alive:
        send_as(p, intro_line(p))
    for p in alive:
        choices = [x for x in suspects if x.idx != p.idx and x.alive]
        if choices:
            target = random.choice(choices)
            send_as(p, accusation_line(p, target))
    target = random.choice(alive)
    send_as(target, defense_line(target))


def voting_phase(players, day):
    send_system(f"🗳 第 {day} 天投票開始。")
    alive = alive_players(players)
    votes = {}
    for p in alive:
        choices = [x for x in alive if x.idx != p.idx]
        target = random.choice(choices)
        votes[target.idx] = votes.get(target.idx, 0) + 1
        send_as(p, vote_line(p, target))
    out_idx = max(votes, key=votes.get)
    out = next(p for p in players if p.idx == out_idx)
    out.alive = False
    send_system(f"📢 票型結算，{out.name} 被放逐。")
    send_system(death_line(out))


def reveal_roles(players):
    lines = [f"{p.name}：{p.role}" for p in players]
    send_system("📜 本局身份公布：\n" + "\n".join(lines))


def run_game():
    players = assign_players()
    send_system("🎭 狼人殺 6 人局開始。角色已分配。")
    send_system("玩家：" + "、".join(p.name for p in players))
    state = {"players": serialize_players(players), "day": 1, "status": "running"}
    save_state(state)

    day = 1
    while True:
        players = deserialize_players(load_state()["players"])
        night_phase(players, day)
        winner = check_win(players)
        save_state({"players": serialize_players(players), "day": day, "status": "running"})
        if winner:
            send_system(f"🏁 遊戲結束，{winner}陣營獲勝！")
            reveal_roles(players)
            save_state({"players": serialize_players(players), "day": day, "status": "finished", "winner": winner})
            return
        discussion_phase(players, day)
        voting_phase(players, day)
        winner = check_win(players)
        save_state({"players": serialize_players(players), "day": day + 1, "status": "running"})
        if winner:
            send_system(f"🏁 遊戲結束，{winner}陣營獲勝！")
            reveal_roles(players)
            save_state({"players": serialize_players(players), "day": day, "status": "finished", "winner": winner})
            return
        day += 1


if __name__ == "__main__":
    random.seed()
    run_game()
