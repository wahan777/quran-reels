#!/usr/bin/env python3
"""
Non-destructive Facebook diagnostics. Posts/publishes NOTHING.
Reports: which scopes the token granted, whether we can list the Page and
derive a Page token, and what the Page-token identity looks like.

Env: FB_PAGE_ID, FB_USER_TOKEN (and optional FB_PAGE_TOKEN).
"""
import os, json, urllib.parse, urllib.request, urllib.error

API = "https://graph.facebook.com/v21.0"
PAGE_ID = os.environ["FB_PAGE_ID"]
USER_TOKEN = os.environ.get("FB_USER_TOKEN", "")


def get(path, params):
    url = f"{API}/{path}?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        return {"_http_error": e.code, "_body": e.read().decode()}


print("== granted permissions (me/permissions) ==")
perms = get("me/permissions", {"access_token": USER_TOKEN})
print(json.dumps(perms, indent=2))

print("\n== me/accounts (pages this token manages) ==")
acct = get("me/accounts", {"access_token": USER_TOKEN})
# NEVER print raw page tokens — Actions logs on a public repo are public.
for p in acct.get("data", []):
    if "access_token" in p:
        p["access_token"] = "<redacted %d chars>" % len(p["access_token"])
print(json.dumps(acct, indent=2))

print("\n== page lookup + page token (fields=name,access_token) ==")
page = get(PAGE_ID, {"fields": "name,access_token", "access_token": USER_TOKEN})
# don't print the raw page token; just whether we got one
safe = {k: (("<%d chars>" % len(v)) if k == "access_token" else v)
        for k, v in page.items()}
print(json.dumps(safe, indent=2))

ptoken = page.get("access_token") or os.environ.get("FB_PAGE_TOKEN")
if ptoken:
    print("\n== page-token identity (debug_token-style /me) ==")
    print(json.dumps(get("me", {"fields": "id,name", "access_token": ptoken}), indent=2))
