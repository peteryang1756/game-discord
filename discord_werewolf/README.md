# Discord 狼人殺 Bot（Telegram Agent/LLM 同步版）

此版本將 `discord_werewolf` 對齊 telegram 的 Agent + LLM 玩法：
- 6 個固定 AI 角色（各自人格、記憶、懷疑度）
- 夜晚 / 討論 / 投票流程與 `werewolf_agents_v21.py` 一致
- AI 發言與投票由 LLM 驅動，並用 webhook 顯示為多角色發言

## 1) 安裝

```bash
cd /home/runner/work/game-discord/game-discord/discord_werewolf
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
- `LLM_API_KEY`

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
- `!wolf_start`：依目前模式開局
- `!start`：`!wolf_start` 別名
- `!wolf_changeto2`：切到「誰是臥底」
- `!wolf_changeto1`：切回「狼人殺」
- `!wolf_join` / `!wolf_leave`：真人玩家加入/離開（有上限）
- `!wolf_players`：查看真人名單
- `!wolf_vote 名字`：誰是臥底模式投票（真人玩家）
- `!wolf_stop`：臨時關閉目前遊戲
- `!wolf_status`：查看狀態

## 6) 主要環境變數

- `LLM_API_BASE`：LLM API Base URL（預設 `https://elysiver.h-e.top/v1`）
- `LLM_API_KEY`：LLM API 金鑰
- `LLM_MODEL`：模型名稱（預設 `gpt-5.4`）
- `TURN_SLEEP`：AI 發言間隔秒數
- `OPENING_SLEEP`：系統訊息間隔秒數
- `MAX_DAYS`：最大天數，超過後強制結束
- `MAX_HUMAN_PLAYERS`：真人玩家可加入上限（預設 `2`）
- `HUMAN_VOTE_TIMEOUT`：誰是臥底真人投票等待秒數（預設 `35`）
- `DRY_RUN`：`1` 時只印出不送 Discord
