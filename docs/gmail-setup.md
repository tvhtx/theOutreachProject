# Gmail API Setup Guide

This guide walks you through setting up Gmail API credentials to send emails through Outreach.

## Overview

Outreach uses Google's OAuth 2.0 to securely send emails from your Gmail account. This requires:
1. A Google Cloud project with Gmail API enabled
2. OAuth 2.0 credentials (a `credentials.json` file)
3. First-time authorization (creates a `token.json` file)

**Time required:** ~10 minutes

---

## Step 1: Create a Google Cloud Project

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Click the project dropdown at the top of the page
3. Click **"New Project"**
4. Enter a project name (e.g., "Outreach Email App")
5. Click **"Create"**
6. Wait for the project to be created, then select it

---

## Step 2: Enable the Gmail API

1. In your Google Cloud project, go to **APIs & Services** > **Library**
2. Search for "Gmail API"
3. Click on **Gmail API** in the results
4. Click the **"Enable"** button
5. Wait for the API to be enabled

---

## Step 3: Configure OAuth Consent Screen

Before creating credentials, you need to configure the OAuth consent screen.

1. Go to **APIs & Services** > **OAuth consent screen**
2. Select **"External"** user type (unless you have a Google Workspace organization)
3. Click **"Create"**
4. Fill in the required fields:
   - **App name:** "Outreach" (or your preferred name)
   - **User support email:** Your email address
   - **Developer contact email:** Your email address
5. Click **"Save and Continue"**
6. On the **Scopes** page, click **"Add or Remove Scopes"**
7. Search for and select:
   - `https://www.googleapis.com/auth/gmail.send`
8. Click **"Update"** then **"Save and Continue"**
9. On the **Test users** page, click **"Add Users"**
10. Add your email address
11. Click **"Save and Continue"**
12. Click **"Back to Dashboard"**

> **Note:** While your app is in "Testing" mode, only test users you've added can authorize it. You can add up to 100 test users.

---

## Step 4: Create OAuth 2.0 Credentials

1. Go to **APIs & Services** > **Credentials**
2. Click **"+ Create Credentials"** > **"OAuth client ID"**
3. Select **"Desktop app"** as the application type
4. Enter a name (e.g., "Outreach Desktop Client")
5. Click **"Create"**
6. Click **"Download JSON"** to download the credentials file
7. Rename the downloaded file to `credentials.json`
8. Move it to your project's `outreach_proj/` directory

Your file structure should look like:
```
theOutreachProject/
├── outreach_proj/
│   ├── credentials.json  ← Place the file here
│   ├── config.py
│   └── ...
```

---

## Step 5: Authorize the Application

The first time you send an email, Outreach will open a browser window for authorization.

1. Start the API server:
   ```bash
   python api_server.py
   ```

2. Try to send an email (either through the UI or API)

3. A browser window will open asking you to sign in to Google

4. Sign in with the Google account you added as a test user

5. You'll see a warning: "Google hasn't verified this app"
   - Click **"Advanced"**
   - Click **"Go to [App Name] (unsafe)"**

6. Grant the requested permissions by clicking **"Continue"**

7. The browser will show "The authentication flow has completed"

8. A `token.json` file will be created in your `outreach_proj/` directory

> **Important:** Keep `token.json` secure. It allows sending emails from your account.

---

## Troubleshooting

### "Access blocked: App has not completed Google verification"

This is expected for new apps. Make sure you:
1. Added yourself as a test user in the OAuth consent screen
2. Are signing in with that same email

### "Error 403: access_denied"

Check that:
1. You've enabled the Gmail API (Step 2)
2. You've added the correct scope (`gmail.send`) in Step 3
3. Your test user was added correctly

### "redirect_uri_mismatch"

This happens if you created "Web application" credentials instead of "Desktop app". 
Delete the credentials and create new ones as a "Desktop app" (Step 4).

### Token expired

Delete `token.json` and go through the authorization flow again (Step 5).

---

## Alternative: SMTP Setup

If you prefer not to use the Gmail API, you can use SMTP with an app password:

1. Enable 2-Step Verification on your Google account
2. Go to [App Passwords](https://myaccount.google.com/apppasswords)
3. Generate a new app password for "Mail"
4. Add these to your `.env` file:

```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_USE_TLS=true
```

> **Note:** SMTP with Gmail has lower daily sending limits than the API.

---

## Security Best Practices

1. **Never commit credentials** - Add to `.gitignore`:
   ```
   credentials.json
   token.json
   ```

2. **Rotate tokens periodically** - Delete `token.json` and re-authorize every few months

3. **Use a dedicated account** - Consider creating a separate Gmail account for sending outreach emails

4. **Monitor usage** - Check your Google Cloud Console for API usage and quotas

---

## Need Help?

If you encounter issues not covered here:
1. Check the [Gmail API Documentation](https://developers.google.com/gmail/api)
2. Review error messages in the server logs
3. Open an issue on the GitHub repository
