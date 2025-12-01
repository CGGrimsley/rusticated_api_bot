# Rusticated API Bot

Rusticated API Bot is a Discord bot designed to track clan performance and individual player statistics on Rusticated servers. The bot interacts with the Rusticated API, automatically pulls leaderboard data, and provides real-time summaries, alerts, and tracking tools for PvP, PvE, gambling, and looting metrics. It is built for reliability, fast responses, and hands-off automated stat collection.

## Features

### 📊 Clan & Player Tracking
- Track one or more clans automatically
- Real-time delta tracking for any metric Rusticated exposes
- Individual player lookup commands
- Persistent tracking toggle `!toggle`

### 📈 Leaderboard Tools
- Pulls all leaderboard tables and sorts them by any metric
- Calculates wins, losses, and changes over time
- Automatic “watched clan” alerts with timestamps
- Announces wipe winners with formatted embeds and per-member stat dumps

### 🛠️ Commands
- `!me <steam64>` — Shows personal stats for a user  
- `!trackplayer <steam64>` — Adds a single-player tracker  
- `!track <clanName>` — Appends a clan to the tracking list  
- `!help` — Shows all commands in a persistent message  
- `!status` — Displays whether tracking is enabled  
- `!clear` — Clears channel messages while preserving pinned/locked messages  
- More utilities for debugging and metric evaluation

### 🧠 Automation & Stability
- Periodic evaluation of tracked metrics  
- Logging for debugging and detailed watch events  
- Optional persistent messages (help/status)  
- Environment variable support for tokens, watched clans, and settings

## Tech Stack
- **Python 3.10+**
- **discord.py** for interaction and embeds  
- **Requests / AIOHTTP** for API pulls  
- **dotenv** for environment configuration  
- Optional: Scheduled tasks & async loops

## Setup

1. Clone the repo:
   ```bash
   git clone https://github.com/CGGrimsley/rusticated_api_bot.git

2. Install dependencies
   ```bash
   pip install -r requirements.txt

3. Create .env File
   ```bash
   Follow the example in **.env.example**
   
4. Run the bot or make changes!
   ```bash
   python bot.py
