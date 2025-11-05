# Discord Daily Standup Bot

A Python Discord bot that automates daily standup meetings by sending prompts at scheduled times, tracking responses, and following up on commitments.

## Features

- **Daily Standup Messages**: Automatically sends standup prompts at 5:00 PM (configurable)
- **Response Tracking**: Monitors and collects user responses to standup questions
- **Commitment Extraction**: Parses user messages to extract what they worked on today and what they'll work on tomorrow
- **Accountability Follow-ups**: Sends follow-up messages the next day asking if users completed their commitments
- **Persistent Storage**: Uses SQLite database to save commitments between bot restarts
- **Slash Commands**: Easy-to-use commands for configuration and management
- **Optional OpenAI Integration**: Uses OpenAI API for intelligent message parsing (falls back to pattern matching if not available)

## Prerequisites

- Python 3.8 or higher
- [uv](https://github.com/astral-sh/uv) package manager (install with: `curl -LsSf https://astral.sh/uv/install.sh | sh` or `pip install uv`)
- A Discord account and bot token
- (Optional) OpenAI API key for intelligent parsing

## Setup Instructions

### 1. Create a Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give it a name
3. Go to the "Bot" section
4. Click "Add Bot" and confirm
5. Under "Token", click "Reset Token" or "Copy" to get your bot token
6. Save this token for later

### 2. Set Bot Permissions

1. In the Discord Developer Portal, go to the "OAuth2" > "URL Generator" section
2. Select the following scopes:
   - `bot`
   - `applications.commands`
3. Select the following bot permissions:
   - `Send Messages`
   - `Read Message History`
   - `View Channels`
   - `Use Slash Commands`
   - `Read Messages/View Channels`
   - `Embed Links` (optional, for better formatting)
4. Copy the generated URL and open it in your browser
5. Select the server where you want to add the bot
6. Click "Authorize"

### 3. Get Channel ID

1. Enable Developer Mode in Discord:
   - Go to User Settings > Advanced
   - Enable "Developer Mode"
2. Right-click on the channel where you want standup messages
3. Click "Copy ID"
4. Save this ID for later

### 4. Install uv (if not already installed)

Install `uv` using one of these methods:

**macOS/Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Or via pip:**
```bash
pip install uv
```

### 5. Install Dependencies

`uv` will automatically create and manage a virtual environment for you:

```bash
cd bot
uv sync
```

This will:
- Create a virtual environment automatically (`.venv/`)
- Install all dependencies from `pyproject.toml`
- Create a `uv.lock` file for reproducible builds
- Make it ready to use

**Note:** The first time you run `uv sync`, it will create a `uv.lock` file. You should commit this file to version control for reproducible builds across different environments.

### 6. Configure Environment Variables

1. Create a `.env` file in the `bot/` directory:
   ```bash
   cd bot
   touch .env
   ```

2. Edit `.env` and add the following variables:
   ```env
   # Discord Bot Configuration
   DISCORD_BOT_TOKEN=your_actual_bot_token
   DISCORD_CHANNEL_ID=your_channel_id
   
   # Standup Time Configuration (optional, defaults to 5:00 PM)
   STANDUP_HOUR=17
   STANDUP_MINUTE=0
   
   # Timezone Configuration (optional, defaults to UTC)
   # Examples: 'America/New_York', 'America/Los_Angeles', 'Europe/London', 'Asia/Tokyo'
   # See https://en.wikipedia.org/wiki/List_of_tz_database_time_zones for full list
   TIMEZONE=UTC
   
   # OpenAI API Configuration (optional)
   USE_OPENAI=false
   OPENAI_API_KEY=your_openai_key_if_using
   ```

   Replace `your_actual_bot_token` with your Discord bot token and `your_channel_id` with your Discord channel ID.

### 7. Run the Bot

Using `uv` to run the bot (automatically uses the virtual environment):

```bash
cd bot
uv run python main.py
```

Or activate the virtual environment manually:

```bash
cd bot
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
python main.py
```

The bot should now be running and will send standup messages at the configured time.

## Usage

### Slash Commands

The bot supports the following slash commands:

- `/set_channel <channel>` - Set the channel for daily standups
- `/set_time <hour> <minute>` - Change the daily message time (24-hour format)
- `/view_commitments` - View all pending commitments for today
- `/skip_today` - Skip today's standup (feature in development)
- `/test_standup` - Send a test standup message (admin only)

### How It Works

1. **Daily Standup**: At the configured time (default 5:00 PM), the bot sends a message asking:
   - "What did you work on today for the project? What will you work on tomorrow?"

2. **Response Tracking**: Users reply to the standup message. The bot:
   - Monitors responses for 2-3 hours after the standup message
   - Parses the message to extract today's work and tomorrow's commitment
   - Saves the information to the database

3. **Follow-up Messages**: The next day, before the new standup (at 4:30 PM by default), the bot:
   - Sends a message to each user asking if they completed their commitment
   - Format: "Hey @user, yesterday you said you'd [commitment]. Did you get this done?"

## File Structure

```
bot/
├── main.py              # Bot initialization and event handlers
├── scheduler.py         # Scheduling logic for daily messages
├── message_parser.py    # Parse and extract commitments from messages
├── database.py          # SQLite database storage layer
├── pyproject.toml       # Project dependencies and metadata (for uv)
├── uv.lock              # Lock file for reproducible builds (created by uv)
├── requirements.txt     # Python dependencies (backup, pyproject.toml is primary)
├── .env                 # Environment variables (create this yourself)
├── .venv/               # Virtual environment (created automatically by uv)
└── standup_bot.db       # SQLite database (created automatically)
```

## Configuration

### Environment Variables

- `DISCORD_BOT_TOKEN` (required): Your Discord bot token
- `DISCORD_CHANNEL_ID` (optional): Channel ID for standups (can be set via command)
- `STANDUP_HOUR` (optional): Hour for standup (0-23, default: 17 for 5:00 PM)
- `STANDUP_MINUTE` (optional): Minute for standup (0-59, default: 0)
- `TIMEZONE` (optional): Timezone for scheduling (default: UTC). Use IANA timezone names like 'America/New_York', 'Europe/London', etc.
- `USE_OPENAI` (optional): Enable OpenAI parsing (true/false, default: false)
- `OPENAI_API_KEY` (optional): OpenAI API key if using OpenAI parsing

### Message Parsing

The bot has two modes for parsing messages:

1. **Simple Pattern Matching** (default): Uses regex patterns to extract commitments
   - Looks for keywords like "today", "tomorrow", "will", "plan to"
   - Works well for structured responses

2. **OpenAI Parsing** (optional): Uses GPT-3.5-turbo for intelligent parsing
   - Better at understanding natural language
   - Requires OpenAI API key
   - Falls back to simple parsing if unavailable

## Database Schema

The bot uses SQLite with the following tables:

- `standup_responses`: Stores user responses with parsed commitments
- `follow_ups`: Tracks follow-up messages sent
- `bot_config`: Stores bot configuration settings

## Troubleshooting

### Bot doesn't respond

- Check that the bot token is correct in `.env`
- Verify the bot has the necessary permissions in the server
- Check the console/logs for error messages

### Messages not being sent

- Verify the channel ID is correct
- Ensure the bot has "Send Messages" permission in that channel
- Check that the bot is online in Discord

### Commands not working

- Wait a few minutes after starting the bot for commands to sync
- Ensure the bot has "Use Slash Commands" permission
- Try restarting the bot

### Parsing not working correctly

- Try using more structured responses (e.g., "Today: ... Tomorrow: ...")
- If using OpenAI, verify your API key is valid
- Check the bot logs for parsing errors

## Logging

The bot logs to both:
- Console output
- `bot.log` file

Log levels include INFO, WARNING, and ERROR messages.

## License

This project is open source and available for use.

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the bot logs for error messages
3. Open an issue on the project repository

pip