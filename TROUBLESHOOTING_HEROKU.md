# Troubleshooting Heroku Deployment

If your bot isn't showing as online on Discord, follow these steps:

## Step 1: Check if the Worker Dyno is Running

```bash
heroku ps
```

You should see something like:
```
=== worker (Free): python main.py (1)
worker.1: up 2024/01/15 10:30:00 +0000 (~ 5m ago)
```

If you see `idle` or nothing, the dyno isn't running. Scale it:
```bash
heroku ps:scale worker=1
```

## Step 2: Check the Logs

```bash
heroku logs --tail
```

Look for:
- **"Bot has logged in"** - This means the bot connected successfully
- **Error messages** - These will tell you what's wrong
- **"DISCORD_BOT_TOKEN not found"** - Bot token is missing or incorrect

## Common Issues and Solutions

### Issue 1: Worker Dyno Not Scaled

**Symptom:** `heroku ps` shows no worker dyno

**Solution:**
```bash
heroku ps:scale worker=1
```

### Issue 2: Missing Bot Token

**Symptom:** Logs show "DISCORD_BOT_TOKEN not found in environment variables!"

**Solution:**
```bash
heroku config:set DISCORD_BOT_TOKEN=your_actual_bot_token
heroku restart
```

### Issue 3: Invalid Bot Token

**Symptom:** Logs show authentication errors or connection failures

**Solution:**
1. Go to Discord Developer Portal
2. Get a fresh bot token
3. Reset the token if needed
4. Set it again:
   ```bash
   heroku config:set DISCORD_BOT_TOKEN=your_new_token
   heroku restart
   ```

### Issue 4: Bot Not in Server

**Symptom:** Bot token is valid but bot doesn't appear online

**Solution:**
1. Make sure the bot is invited to your Discord server
2. Check that the bot has proper permissions
3. Re-invite the bot using the OAuth2 URL generator

### Issue 5: Import Errors

**Symptom:** Logs show "ModuleNotFoundError" or import errors

**Solution:**
The Procfile might need adjustment. Check if `uv` is available:
```bash
# Check Heroku build logs
heroku logs --tail

# If uv is not available, you might need to install dependencies differently
# Check your Procfile - it should use: worker: uv run python main.py
```

### Issue 6: Database Initialization Errors

**Symptom:** Logs show SQLite errors

**Solution:**
This might be expected on Heroku (ephemeral filesystem). The bot should still start, but data won't persist. For now, this is okay.

### Issue 7: Google Sheets Credentials Error

**Symptom:** Logs show "Failed to initialize Google Sheets Manager"

**Solution:**
If you're using Google Sheets, make sure:
```bash
heroku config:set GOOGLE_CREDENTIALS_BASE64="<your_base64_string>"
heroku config:set SPREADSHEET_ID=your_spreadsheet_id
```

If you're NOT using Google Sheets, this error won't prevent the bot from starting (it's logged as a warning).

## Quick Diagnostic Commands

```bash
# Check dyno status
heroku ps

# Check recent logs
heroku logs --tail

# Check all config vars
heroku config

# Restart the bot
heroku restart

# Check if bot token is set
heroku config:get DISCORD_BOT_TOKEN
```

## Expected Log Output (Success)

When the bot starts successfully, you should see:
```
2024-01-15 10:30:00 - __main__ - INFO - Synced X command(s)
2024-01-15 10:30:01 - __main__ - INFO - BotName#1234 has logged in
2024-01-15 10:30:01 - __main__ - INFO - Bot is in 1 guild(s)
2024-01-15 10:30:01 - __main__ - INFO - Bot status set to "Watching daily standups"
2024-01-15 10:30:01 - scheduler - INFO - Scheduler started. Standup at 17:00, follow-ups at 16:30 (UTC)
```

## Still Not Working?

1. **Share the logs** - Run `heroku logs --tail` and share the output
2. **Check dyno status** - Run `heroku ps` and share the output
3. **Verify config vars** - Run `heroku config` and verify DISCORD_BOT_TOKEN is set (don't share the actual token value)

