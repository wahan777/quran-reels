#!/usr/bin/env python3
"""
Publish a Reel to Instagram via the Graph API (Content Publishing).

Requires env vars:
  IG_USER_ID        Instagram Business/Creator account ID
  IG_ACCESS_TOKEN   long-lived access token with instagram_content_publish
Usage:
  python post_to_instagram.py <public_video_url> <caption_file>

Note: video_url MUST be a public HTTPS URL (the API fetches it; it cannot
take a local file). In CI we upload the mp4 to a GitHub Release first.
"""
import sys, os, time, json, urllib.parse, urllib.request

API = "https://graph.facebook.com/v21.0"
IG_USER_ID = os.environ["IG_USER_ID"]
TOKEN = os.environ["IG_ACCESS_TOKEN"]

def _post(path, params):
    data = urllib.parse.urlencode(params).encode()
    with urllib.request.urlopen(f"{API}/{path}", data=data, timeout=120) as r:
        return json.load(r)

def _get(path, params):
    url = f"{API}/{path}?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=120) as r:
        return json.load(r)

def publish(video_url, caption):
    # 1. create media container
    res = _post(f"{IG_USER_ID}/media", {
        "media_type": "REELS", "video_url": video_url,
        "caption": caption, "access_token": TOKEN})
    creation_id = res["id"]
    print("container:", creation_id)
    # 2. wait until Instagram finishes downloading/processing the video
    for attempt in range(40):
        st = _get(creation_id, {"fields": "status_code,status", "access_token": TOKEN})
        code = st.get("status_code")
        print(f"  status: {code}")
        if code == "FINISHED":
            break
        if code == "ERROR":
            raise SystemExit(f"Processing error: {st}")
        time.sleep(15)
    else:
        raise SystemExit("Timed out waiting for media processing")
    # 3. publish
    pub = _post(f"{IG_USER_ID}/media_publish",
                {"creation_id": creation_id, "access_token": TOKEN})
    print("published media id:", pub.get("id"))
    return pub.get("id")

if __name__ == "__main__":
    video_url, caption_file = sys.argv[1], sys.argv[2]
    caption = open(caption_file, encoding="utf-8").read()
    publish(video_url, caption)
