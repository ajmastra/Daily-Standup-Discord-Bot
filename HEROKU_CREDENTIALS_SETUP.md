# Setting Up Google Sheets Credentials on Heroku

Since Heroku's filesystem is ephemeral and you can't commit `credentials.json` to version control, you need to store your Google service account credentials as a Heroku config variable.

## Option 1: Base64 Encoded Credentials (Recommended)

This is the most secure and straightforward approach.

### Step 1: Encode Your Credentials File

On your local machine, encode your `credentials.json` file to base64:

**macOS:**
```bash
base64 -i credentials.json | pbcopy
```

Or to save to a file:
```bash
base64 -i credentials.json > credentials_base64.txt
```

**Linux:**
```bash
base64 credentials.json | xclip  # or xsel -b
```

Or to save to a file:
```bash
base64 credentials.json > credentials_base64.txt
```

**Windows (PowerShell):**
```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("credentials.json")) | Set-Content credentials_base64.txt
```

**Alternative (Python):**
```python
import base64
with open('credentials.json', 'rb') as f:
    encoded = base64.b64encode(f.read()).decode('utf-8')
    print(encoded)
```

### Step 2: Set Heroku Config Variable

Copy the base64-encoded string and set it as a Heroku config variable:

```bash
heroku config:set GOOGLE_CREDENTIALS_BASE64="<paste_your_base64_string_here>"
```

**Important:** Make sure to include the quotes and paste the entire base64 string. It should be very long (typically 2000+ characters).

### Step 3: Verify

Check that the config variable was set:
```bash
heroku config:get GOOGLE_CREDENTIALS_BASE64
```

The bot will automatically:
1. Read the base64 string from the config var
2. Decode it to JSON
3. Write it to `credentials.json` at runtime
4. Use it to authenticate with Google Sheets

## Option 2: Direct JSON String (Alternative)

If you prefer, you can store the JSON directly (but base64 is recommended for escaping issues):

```bash
# Read the JSON file and set it directly
cat credentials.json | heroku config:set GOOGLE_CREDENTIALS_BASE64="$(cat)"
```

However, this can cause issues with special characters, so base64 encoding is preferred.

## Complete Heroku Setup Example

```bash
# 1. Encode credentials (macOS)
base64 -i credentials.json > temp_base64.txt

# OR on Linux:
# base64 credentials.json > temp_base64.txt

# 2. Set all required config vars
heroku config:set DISCORD_BOT_TOKEN=your_bot_token
heroku config:set DISCORD_CHANNEL_ID=your_channel_id
heroku config:set SPREADSHEET_ID=your_spreadsheet_id
heroku config:set GOOGLE_SHEETS_HEADER_ROW=6
heroku config:set TIMEZONE=America/New_York

# 3. Set base64 credentials (copy the entire content from temp_base64.txt)
heroku config:set GOOGLE_CREDENTIALS_BASE64="<paste_entire_base64_string>"

# 4. Clean up temporary file
rm temp_base64.txt

# 5. Deploy
git push heroku main

# 6. Check logs to verify credentials are working
heroku logs --tail
```

## Verification

After deploying, check the logs for:
```
Credentials decoded from GOOGLE_CREDENTIALS_BASE64 and written to credentials.json
Google Sheets Manager initialized successfully (headers in row 6)
```

If you see errors, check:
1. The base64 string is complete (no truncation)
2. The original `credentials.json` file is valid JSON
3. The service account email has access to your spreadsheet
4. The `SPREADSHEET_ID` is correct

## Troubleshooting

### "Failed to decode base64 credentials"
- Make sure you copied the entire base64 string (it's very long)
- Verify there are no line breaks or extra spaces
- Try re-encoding the credentials file

### "Credentials file not found"
- The bot should automatically create the file from the base64 string
- Check logs to see if decoding succeeded
- Verify `GOOGLE_CREDENTIALS_BASE64` is set correctly

### "Invalid JSON"
- Your original `credentials.json` might be corrupted
- Re-download the credentials from Google Cloud Console
- Re-encode and set the config var again

## Security Notes

- **Never commit** `credentials.json` or base64 strings to version control
- The `GOOGLE_CREDENTIALS_BASE64` config var is encrypted by Heroku
- Only people with access to your Heroku app can see the config vars
- Rotate credentials if they're ever exposed

