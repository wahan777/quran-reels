# HANDOFF — Quran Reels Instagram automation

**Project folder:** `/Users/apple/quran-reels`
**Goal:** Faceless Islamic IG page that auto-posts the whole Quran as Reels,
in order, 4×/day (~604 Mushaf pages ≈ 150 days). Reciter: **Sheikh Yasser
Al-Dosari**. Arabic only, no English, **no music** (halal). Audience first,
monetize later (donations / halal sponsors / digital product).

---

## 🟢 LIVE — READ THIS FIRST (last updated 2026-05-24)

**The whole pipeline is built, deployed, and auto-posting. Nothing is required to keep
it running** except one ~60-day token refresh (see below). Resume only if Avais asks
for a change or something broke.

- **Repo (public):** github.com/AvaisOnn/quran-reels
- **Instagram:** @thepathtonoor2026 · **FB Page:** "The Path of Noor" (ID 1190981554088688)
- **Posted so far (Instagram):** pages 1 (Al-Fatihah)–6 (Al-Baqara 30–37). Bookmark
  `progress.json` → **page 7** next.
- **Schedule:** 4×/day every 6h at **12 AM / 6 AM / 12 PM / 6 PM Pakistan time** =
  `19:00 / 01:00 / 07:00 / 13:00 UTC` (cron in `.github/workflows/post.yml`). *(Changed
  2026-05-24 from 3×/day to close a 12h overnight gap — now an even 6h spacing.)*
- **Action secrets (in GitHub, encrypted — NOT in repo):**
  - `IG_USER_ID` = `17841431955731562` (not sensitive)
  - `IG_ACCESS_TOKEN` = long-lived (~60-day) user token, **expires ~2026-07-21**.

### ⚠️ Token refresh (the ONLY recurring task)
Before ~2026-07-21, generate a fresh long-lived token (SETUP.md Part B) and set it with:
`gh secret set IG_ACCESS_TOKEN` **in a real Terminal app** — do NOT use the Claude Code
`!` prompt; it isn't interactive and silently stores an EMPTY value (this caused the
first live run to fail with HTTP 400). A `/schedule` reminder is set for ~2026-07-18.

> **2026-05-24:** evaluated swapping to a *permanent* Page access token (derived from a
> long-lived user token via `/me/accounts`, `expires_at: 0`) to end the refresh chore
> entirely — Avais chose to **leave the current 60-day token as-is** for now. So the
> manual refresh above still applies. Revisit the permanent-token route later if desired.

### Facebook cross-posting (added 2026-05-23) — BLOCKED on one scope
The workflow now also publishes each reel to the FB Page via `post_to_facebook.py`
(Reels API; the step is `continue-on-error` so FB can never block IG or the bookmark).
**It currently 403s** because `IG_ACCESS_TOKEN` lacks the **`pages_manage_posts`** scope
(it has `instagram_content_publish` + `pages_read_engagement` only). To enable FB:
regenerate the token in Graph API Explorer WITH `pages_manage_posts`, exchange to
long-lived, then `gh secret set IG_ACCESS_TOKEN` (real Terminal). `FB_PAGE_ID` secret is
already set. `fb_debug.yml` is a no-post scope checker. IG is unaffected and keeps posting.
> Note: the `fb_debug.yml` run on 2026-05-23 briefly printed a derived Page token to a
> public Actions log; that run was **deleted** and the script now redacts tokens. All
> remaining run logs scanned clean. Regenerating `IG_ACCESS_TOKEN` (above) invalidates
> that token for good — another reason to do the scope refresh sooner rather than later.

### Security / hygiene notes
- Token & App Secret exist ONLY in GitHub encrypted secrets + your local notes — never
  committed. History scanned clean.
- `.gitignore` excludes `.claude/`, `CLAUDE.md`, `*.env`, `venv/`, `tmp/`, `output/`,
  `.DS_Store`. Keep internal/Claude files out of the repo.
- Bookmark-push hardened with `git pull --rebase` so a concurrent push can't desync it.

## STATUS — what's DONE ✅

- **Reel generator** works end-to-end and is verified on macOS:
  Arabic + full tashkeel, Al-Dosari per-ayah audio, calm NASA galaxy/nature
  backgrounds with slow Ken Burns zoom, dark scrim for legibility, one
  background per reel.
- **Batch + bookmark**: `make_next.py` generates the next N pages and advances
  `progress.json`. Live and advancing — currently at **page 5**.
- **Captions**: auto-generated with surah range + hashtags (`output/page_XXX.txt`).
- **Instagram publisher** (`post_to_instagram.py`) via Graph API — built & live.
- **Facebook publisher** (`post_to_facebook.py`) via Reels API — built & wired in,
  blocked on the `pages_manage_posts` scope (see LIVE section above).
- **GitHub Actions workflow** (`.github/workflows/post.yml`) — cron 4×/day (every 6h),
  generates → uploads to a public GitHub Release → posts → commits bookmark.
- **Cross-platform fonts**: uses Amiri Quran + HarfBuzz (raqm) on Linux/CI,
  GeezaPro + arabic_reshaper on macOS. **CI path verified live** (pages 1–4 rendered
  and posted from GitHub Actions).

## STATUS — what's NOT done / TODO ⏳

1. **Accounts** — all done ✅ (Page, IG account, Meta app, `IG_USER_ID`,
   long-lived `IG_ACCESS_TOKEN`, GitHub push + Action secrets, first live test).
   The whole IG pipeline is live; see the LIVE section at the top.
2. **Enable Facebook posting** — regenerate `IG_ACCESS_TOKEN` with the
   **`pages_manage_posts`** scope (details in the LIVE section). Code is ready;
   this is the only blocker. *(Avais is doing this later.)*
3. **Open tuning items (not blockers):**
   - Long pages → long reels (e.g. Al-Baqarah ~160s). Optionally cap at ~90s by
     splitting long pages into 2 reels.
   - Auto token-refresh so the ~60-day token never has to be re-pasted manually.

---

## RESUME HERE TOMORROW

**If the accounts/token are ready** → do GitHub push + secrets (`SETUP.md` Part C),
then run the workflow once and check the posted reel.

**If still working on the Meta app** → finish `SETUP.md` Part B; the tricky bits:
get `IG_USER_ID` via `me/accounts` → `{page-id}?fields=instagram_business_account`,
then exchange the short token for a long-lived one.

**To preview/generate locally meanwhile:**
```
cd ~/quran-reels
./venv/bin/python make_next.py 3      # next 3 reels -> output/page_XXX.mp4 (+ .txt)
cat progress.json                     # current page (of 604)
open output/page_001.mp4              # preview
```
> Note: `make_next.py` advances `progress.json`. If you only want to *preview*
> without burning the bookmark, reset it after: `echo '{"next_page": 1}' > progress.json`

## KEY FILES
- `quran_reel.py`     — core builder (text render, audio, ffmpeg, captions)
- `make_next.py`      — batch + bookmark
- `post_to_instagram.py` — IG Graph API publisher
- `post_to_facebook.py`  — FB Page Reels publisher (blocked on `pages_manage_posts`)
- `fb_debug.py` / `.github/workflows/fb-debug.yml` — no-post token/scope checker
- `.github/workflows/post.yml` — the 4×/day (every 6h) automation (IG + FB)
- `SETUP.md`          — full account + token + GitHub checklist
- `progress.json`     — bookmark (next page to post)
- `backgrounds/`      — NASA galaxy + nature images (committed, used by CI)
- `fonts/`            — Amiri Quran (for CI HarfBuzz path)
- `venv/`, `tmp/`, `output/` — gitignored

## DECISIONS LOCKED
- Reciter: Yasser Al-Dosari (`everyayah.com/data/Yasser_Ad-Dussary_128kbps/SSSAAA.mp3`)
- Arabic text: alquran.cloud `quran-uthmani`
- Chunking: one Mushaf page per reel (604 total)
- Runner: GitHub Actions; backgrounds = one per reel (calmer)
- Halal: no music; can't charge for recitation, but view/ad income on da'wah is OK.
