# Quran Reels — Setup Checklist

Fully automated: a GitHub Action generates the next Quran page as a Reel
(Sheikh Yasser Al-Dosari) 3× a day and posts it to Instagram. You do nothing
once this is set up.

## Part A — Instagram + Facebook (only you can do this)

1. Create the Instagram account (pick a handle, e.g. @quran.daily).
2. Settings → switch the account to **Professional → Creator (or Business)**.
3. Create a **Facebook Page** (facebook.com/pages/create).
4. Link the IG account to that Page (IG: Settings → Linked accounts, or via
   Meta Business Suite).

## Part B — Meta Developer app (to get the API token)

1. Go to https://developers.facebook.com → My Apps → Create App → type "Business".
2. Add the **Instagram Graph API** product.
3. In the Graph API Explorer, generate a **User access token** with these scopes:
   `instagram_basic`, `instagram_content_publish`, `pages_show_list`,
   `pages_read_engagement`, `business_management`.
4. Exchange it for a **long-lived token** (~60 days):
   `GET /oauth/access_token?grant_type=fb_exchange_token&client_id=APP_ID&client_secret=APP_SECRET&fb_exchange_token=SHORT_TOKEN`
5. Get your **Instagram User ID**:
   `GET /me/accounts` → find the Page → `GET /{page-id}?fields=instagram_business_account`
   → that id is your `IG_USER_ID`.

> The token expires ~every 60 days. We can add an auto-refresh step later, or
> you paste a fresh token every ~2 months (2-minute job).

## Part C — GitHub (the runner)

1. Create a GitHub account (free) and a **PUBLIC** repo (must be public so
   Instagram can fetch the released video file).
2. Push this whole `quran-reels/` folder to it:
   ```
   cd ~/quran-reels
   git init && git add -A && git commit -m "init"
   git branch -M main
   git remote add origin https://github.com/USERNAME/REPO.git
   git push -u origin main
   ```
3. In the repo: **Settings → Secrets and variables → Actions → New secret**, add:
   - `IG_USER_ID`     = your Instagram business account id
   - `IG_ACCESS_TOKEN`= the long-lived token
4. Done. The workflow `.github/workflows/post.yml` runs 3×/day automatically.
   Test it now with **Actions tab → Post Quran Reel → Run workflow**.

## Local commands (manual / testing)

- Generate next 3 reels locally:  `./venv/bin/python make_next.py 3`
- Current position:               `cat progress.json`  (page N of 604)
- One-off surah range:            `./venv/bin/python generate_reel.py 1 1 7 output/x.mp4`
