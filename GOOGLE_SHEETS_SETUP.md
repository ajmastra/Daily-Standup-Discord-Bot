# Google Sheets Integration Setup Guide

This guide will walk you through setting up Google Sheets integration for the Discord bot's task management feature.

## Prerequisites

- A Google account
- Access to Google Cloud Console
- A Google Spreadsheet (or create a new one)

## Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click on the project dropdown at the top
3. Click **"New Project"**
4. Enter a project name (e.g., "Discord Bot Tasks")
5. Click **"Create"**
6. Wait for the project to be created and select it

## Step 2: Enable Google Sheets API

1. In the Google Cloud Console, go to **"APIs & Services" > "Library"**
2. Search for **"Google Sheets API"**
3. Click on it and click **"Enable"**
4. Also search for and enable **"Google Drive API"** (required for accessing the spreadsheet)

## Step 3: Create Service Account

1. Go to **"APIs & Services" > "Credentials"**
2. Click **"Create Credentials" > "Service Account"**
3. Fill in the service account details:
   - **Service account name**: `discord-bot-sheets` (or any name you prefer)
   - **Service account ID**: Will be auto-generated
   - **Description**: "Service account for Discord bot Google Sheets integration"
4. Click **"Create and Continue"**
5. Skip the optional steps (Grant this service account access to project) and click **"Done"**

## Step 4: Create and Download Credentials

1. In the **"Credentials"** page, find your newly created service account
2. Click on the service account email
3. Go to the **"Keys"** tab
4. Click **"Add Key" > "Create new key"**
5. Select **"JSON"** format
6. Click **"Create"**
7. The JSON file will automatically download - **save this file as `credentials.json`**

## Step 5: Place Credentials File

1. Move the downloaded `credentials.json` file to your bot's project root directory (same folder as `main.py`)
2. **Important**: The `credentials.json` file is already in `.gitignore` - **DO NOT** commit this file to version control!

## Step 6: Create or Prepare Google Spreadsheet

1. Go to [Google Sheets](https://sheets.google.com/)
2. Create a new spreadsheet or use an existing one
3. Name it something like "Discord Bot Tasks" or "Task Management"

### Format the Sheet Headers

The sheet should have the following headers (default is **Row 6**, but this is configurable):

| Task ID | Status | Description | Assigned to | Start Date | End Date | Measurable Outcome | Actual Outcome |
|--------|--------|-------------|-------------|------------|----------|-------------------|----------------|

**Note:** 
- The bot will automatically create these headers in the specified row if the sheet is empty, but you can set them up manually if preferred.
- By default, headers are expected in **Row 6**. You can change this by setting `GOOGLE_SHEETS_HEADER_ROW` in your `.env` file.
- Data rows should start **after** the header row (e.g., if headers are in row 6, data starts at row 7).

## Step 7: Share Spreadsheet with Service Account

1. Open your Google Spreadsheet
2. Click the **"Share"** button (top right)
3. Get the service account email from your `credentials.json` file:
   - Open `credentials.json`
   - Find the `"client_email"` field (it will look like: `discord-bot-sheets@your-project-id.iam.gserviceaccount.com`)
4. Paste this email address in the "Add people" field
5. Give it **"Editor"** permissions
6. **Uncheck** "Notify people" (optional, but recommended)
7. Click **"Send"**

## Step 8: Get Spreadsheet ID

1. Open your Google Spreadsheet
2. Look at the URL in your browser:
   ```
   https://docs.google.com/spreadsheets/d/SPREADSHEET_ID_HERE/edit#gid=0
   ```
3. Copy the `SPREADSHEET_ID_HERE` part (the long string between `/d/` and `/edit`)
4. Example: If your URL is:
   ```
   https://docs.google.com/spreadsheets/d/1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7/edit
   ```
   Then your Spreadsheet ID is: `1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7`

## Step 9: Configure Environment Variables

Add the following to your `.env` file:

```env
SPREADSHEET_ID=your_spreadsheet_id_here
GOOGLE_CREDENTIALS_PATH=credentials.json
GOOGLE_SHEETS_HEADER_ROW=6
```

**Example:**
```env
SPREADSHEET_ID=1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7
GOOGLE_CREDENTIALS_PATH=credentials.json
GOOGLE_SHEETS_HEADER_ROW=6
```

**Note:** 
- If your `credentials.json` is in the project root (same directory as `main.py`), you can omit `GOOGLE_CREDENTIALS_PATH` as it defaults to `credentials.json`.
- `GOOGLE_SHEETS_HEADER_ROW` defaults to 6 if not specified. Change this if your headers are in a different row.

## Step 10: Verify Setup

1. Restart your Discord bot
2. Check the bot logs - you should see:
   ```
   Google Sheets Manager initialized successfully
   ```
3. Try using `/add_task` command in Discord
4. Check your Google Sheet - a new task should appear!

## Troubleshooting

### "Credentials file not found"
- Make sure `credentials.json` is in the project root directory
- Check that the file path is correct in your `.env` file
- Verify the file name is exactly `credentials.json` (case-sensitive)

### "Permission denied" or "Access denied"
- Verify you shared the spreadsheet with the service account email
- Check that the service account has "Editor" permissions
- Make sure the spreadsheet ID is correct

### "Spreadsheet not found"
- Verify the `SPREADSHEET_ID` in your `.env` file is correct
- Make sure there are no extra spaces or quotes around the ID
- Check that the spreadsheet exists and is accessible

### "API not enabled"
- Go back to Google Cloud Console
- Enable both "Google Sheets API" and "Google Drive API"
- Wait a few minutes for changes to propagate

### "Rate limit exceeded"
- Google Sheets API has rate limits (100 requests per 100 seconds per user)
- If you're making many requests, you may need to add delays
- Consider caching data locally if needed

## Security Notes

⚠️ **IMPORTANT SECURITY REMINDERS:**

1. **Never commit `credentials.json` to version control** - It's already in `.gitignore`
2. **Never share your service account credentials** publicly
3. **Only share the spreadsheet with the service account** - don't share it publicly if it contains sensitive data
4. **Use environment variables** for the spreadsheet ID - don't hardcode it
5. **Rotate credentials** if they're ever exposed

## Additional Resources

- [Google Sheets API Documentation](https://developers.google.com/sheets/api)
- [gspread Documentation](https://gspread.readthedocs.io/)
- [Service Accounts Guide](https://cloud.google.com/iam/docs/service-accounts)

## Quick Reference

**Required Files:**
- `credentials.json` - Service account credentials (in project root)
- `.env` - Contains `SPREADSHEET_ID`

**Required Permissions:**
- Service account needs "Editor" access to the spreadsheet
- Bot needs "Use Slash Commands" permission in Discord

**Sheet Format:**
- Headers in Row 1: Number | Description | Assigned to | Start Date | End Date | Measurable Outcome | Actual Outcome
- Data starts in Row 2
- Number column auto-increments

