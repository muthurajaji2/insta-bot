# Instagram AI AutoPoster — GitHub Actions

Posts 8 times daily to Instagram. Every post is **100% AI-generated**:
- Caption → written by **Claude AI** (Anthropic)
- Image → created by **Pollinations.ai** (free, no key needed)
- Schedule → automated by **GitHub Actions** cron

Zero manual work. Just set your niche and let it run.

---

## Setup (5 minutes)

### 1. Add GitHub Secrets

Go to: **Repo → Settings → Secrets and variables → Actions → New secret**

| Secret | What it is |
|---|---|
| `IG_USER_ID` | Your Instagram Business account numeric ID |
| `IG_ACCESS_TOKEN` | Meta Graph API long-lived token |
| `ANTHROPIC_API_KEY` | Your Anthropic API key (console.anthropic.com) |
| `INSTAGRAM_NICHE` | Your niche e.g. `fitness lifestyle`, `food blog`, `travel` |

### 2. Get Instagram Credentials

1. Go to https://developers.facebook.com → Create App → Add **Instagram Graph API**
2. Connect your **Professional/Business** Instagram account
3. In Graph API Explorer: add permission `instagram_content_publish`
4. Generate token → copy it to `IG_ACCESS_TOKEN` secret

Find your User ID:
```
GET https://graph.facebook.com/v19.0/me?fields=id&access_token=YOUR_TOKEN
```

### 3. Get Anthropic API Key

Sign up at https://console.anthropic.com → API Keys → Create key
Add it as `ANTHROPIC_API_KEY` secret.

### 4. Set Your Niche

Add a secret `INSTAGRAM_NICHE` with your content niche, e.g.:
- `motivational fitness lifestyle`
- `healthy food and recipes`
- `travel and adventure`
- `business and entrepreneurship`
- `fashion and style tips`

Claude will use this to tailor every caption to your brand.

### 5. Customise Post Themes (Optional)

Edit `post_instagram.py` → `SLOT_THEMES` dictionary to change what each time slot focuses on.

### 6. Test It

**Actions tab → "Instagram Daily 8 AI Posts" → "Run workflow" → enter slot number 1**

---

## How It Works

```
GitHub Actions cron triggers
        ↓
Claude generates caption (tailored to your niche + time slot theme)
        ↓
Claude generates image description prompt
        ↓
Pollinations.ai creates a 1080×1080 image from the prompt
        ↓
Meta Graph API uploads image + caption to Instagram
        ↓
Post goes live ✅  Log saved as artifact
```

## Post Schedule

| Slot | UTC Time | Theme |
|---|---|---|
| 1 | 07:00 | Morning motivation |
| 2 | 09:00 | Productivity & energy |
| 3 | 11:00 | Positive mindset |
| 4 | 13:00 | Lunch & wellness |
| 5 | 15:00 | Afternoon hustle |
| 6 | 17:00 | Evening reflection |
| 7 | 19:00 | Golden hour lifestyle |
| 8 | 21:00 | Nighttime wind-down |

To change times, edit the `cron:` lines in `.github/workflows/instagram-daily-posts.yml`.
**Convert your timezone:** IST (India) = UTC−5:30, so 9 AM IST = `30 3 * * *`

---

## Token Refresh (every 60 days)

Long-lived tokens expire. Refresh with:
```
GET https://graph.facebook.com/v19.0/oauth/access_token
  ?grant_type=fb_exchange_token
  &client_id=YOUR_APP_ID
  &client_secret=YOUR_APP_SECRET
  &fb_exchange_token=CURRENT_TOKEN
```
Update `IG_ACCESS_TOKEN` secret with the new token.

---

## Common Errors

| Error | Fix |
|---|---|
| `OAuthException` | Token expired or missing `instagram_content_publish` permission |
| `Invalid image URL` | Pollinations image failed to generate — retry the workflow |
| `ANTHROPIC_API_KEY missing` | Add the secret in repo settings |
| Workflow not running | Push a commit — GitHub pauses cron on inactive repos |
