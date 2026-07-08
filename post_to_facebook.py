#!/usr/bin/env python3
"""
Publish a Reel to a Facebook Page via the Graph API (Reels Publishing).

Mirrors post_to_instagram.py but targets the FB Page. Facebook Reels use a
3-phase flow: start -> upload (hosted file_url) -> finish/publish.

Requires env vars:
  FB_PAGE_ID        Facebook Page ID (e.g. 1190981554088688)
  FB_PAGE_TOKEN     Page access token. If unset, it is derived at runtime
                    from FB_USER_TOKEN via /{FB_PAGE_ID}?fields=access_token.
  FB_USER_TOKEN     (fallback) long-lived user token with pages_manage_posts +
                    pages_read_engagement. We reuse the same secret as IG.
Usage:
  python post_to_facebook.py <public_video_url> <caption_file>

Note: video_url MUST be a public HTTPS URL — Facebook fetches it directly
(hosted upload). In CI we upload the mp4 to a GitHub Release first.
"""
import sys, os, time, json, urllib.parse, urllib.request, urllib.error

API = "https://graph.facebook.com/v21.0"
PAGE_ID = os.environ["FB_PAGE_ID"]


def _read_err(e):
    """Surface Facebook's JSON error body instead of a bare HTTP 403."""
    try:
        return e.read().decode()
    except Exception:
        return str(e)


def _post(path, params):
    data = urllib.parse.urlencode(params).encode()
    try:
        with urllib.request.urlopen(f"{API}/{path}", data=data, timeout=120) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise SystemExit(f"POST {path} -> HTTP {e.code}: {_read_err(e)}")


def _get(path, params):
    url = f"{API}/{path}?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=120) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise SystemExit(f"GET {path} -> HTTP {e.code}: {_read_err(e)}")


def page_token():
    """Use an explicit page token if given, else derive one from the user token."""
    tok = os.environ.get("FB_PAGE_TOKEN")
    if tok:
        return tok
    user_tok = os.environ["FB_USER_TOKEN"]
    res = _get(PAGE_ID, {"fields": "access_token", "access_token": user_tok})
    if "access_token" not in res:
        raise SystemExit(f"Could not derive Page token (check scopes): {res}")
    return res["access_token"]


def publish(video_url, caption):
    token = page_token()
    # 1. start: get a video_id + upload_url
    start = _post(f"{PAGE_ID}/video_reels",
                  {"upload_phase": "start", "access_token": token})
    video_id = start["video_id"]
    upload_url = start["upload_url"]
    print("video_id:", video_id)

    # 2. upload by reference: Facebook fetches the hosted file_url itself
    req = urllib.request.Request(upload_url, method="POST")
    req.add_header("Authorization", f"OAuth {token}")
    req.add_header("file_url", video_url)
    with urllib.request.urlopen(req, timeout=120) as r:
        up = json.load(r)
    if not up.get("success", False):
        raise SystemExit(f"Upload phase failed: {up}")

    # 3. finish + publish, then poll until the reel is ready/published
    fin = _post(f"{PAGE_ID}/video_reels", {
        "video_id": video_id, "upload_phase": "finish",
        "video_state": "PUBLISHED", "description": caption,
        "access_token": token})
    print("finish:", fin)

    for _ in range(40):
        st = _get(video_id, {"fields": "status", "access_token": token})
        status = (st.get("status") or {})
        vstatus = status.get("video_status")
        print(f"  video_status: {vstatus}")
        if vstatus in ("ready", "published"):
            break
        if vstatus == "error":
            raise SystemExit(f"Processing error: {st}")
        time.sleep(15)
    print("published reel video id:", video_id)
    return video_id


if __name__ == "__main__":
    video_url, caption_file = sys.argv[1], sys.argv[2]
    caption = open(caption_file, encoding="utf-8").read()
    publish(video_url, caption)
