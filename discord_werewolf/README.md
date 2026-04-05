# Discord 狼人殺 Bot（6 人自動對局）

跟 `werewolf_telegram.py` 同樣玩法，但改成發在 Discord 頻道。

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
- 邀請 bot 進伺服器並給該頻道發言權限

## 4) 啟動

```bash
python bot.py
```

上線後在指定頻道輸入：
- `!wolf_help`
- `!wolf_start`
- `!wolf_status`
