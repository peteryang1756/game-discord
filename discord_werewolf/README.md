# Discord 狼人殺 Bot（1 主 bot + 多 webhook 角色）

玩法與原本版本相同，但改為 Discord，並支援真人補位：
- 一個主 bot 控流程與系統訊息
- AI 角色用 webhook 身份發言（看起來像多帳號）
- 朋友可用 `!wolf_join` 加入，取代部分 AI

## 1) 安裝

```bash
cd /home/exedev/werewolf-tg/discord_werewolf
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2) 設定環境變數

```bash
cp .env.example .env
# 編輯 .env
```

至少要填：
- `DISCORD_BOT_TOKEN`
- `DISCORD_CHANNEL_ID`

## 3) Discord Bot 權限

在 Discord Developer Portal：
- 打開 **MESSAGE CONTENT INTENT**

機器人在伺服器至少要有：
- Send Messages
- Read Message History
- Manage Webhooks（重要，AI 角色要用）

## 4) 啟動

```bash
python bot.py
```

## 5) 指令

- `!wolf_help`：顯示說明
- `!wolf_join`：加入下一局（真人）
- `!wolf_leave`：離開大廳
- `!wolf_lobby`：看目前真人名單
- `!wolf_start`：開局（不足 6 人自動補 AI）
- `!vote 玩家名稱`：白天投票
- `!wolf_status`：查看狀態
