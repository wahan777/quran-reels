#!/usr/bin/env python3
"""
Generate the next batch of reels, in order, advancing a persistent bookmark.
Each reel = one Mushaf page (604 total). Default 3 reels per run.

Usage: python make_next.py [count]   (default 3)
Outputs: output/page_XXX.mp4 + output/page_XXX.txt (caption) for each.
State:   progress.json  -> {"next_page": N}
"""
import sys, os, json
import quran_reel as qr

HERE = os.path.dirname(os.path.abspath(__file__))
PROGRESS = os.path.join(HERE, "progress.json")
OUT = os.path.join(HERE, "output")
TOTAL_PAGES = 604

def load_next_page():
    if os.path.exists(PROGRESS):
        return json.load(open(PROGRESS)).get("next_page", 1)
    return 1

def save_next_page(p):
    json.dump({"next_page": p}, open(PROGRESS, "w"), indent=2)

def main():
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    os.makedirs(OUT, exist_ok=True)
    page = load_next_page()
    made = []
    for _ in range(count):
        if page > TOTAL_PAGES:
            print("Reached end of the Quran — masha'Allah, complete.")
            break
        print(f"== Page {page}/{TOTAL_PAGES} ==", flush=True)
        ayahs = qr.fetch_page(page)
        mp4 = os.path.join(OUT, f"page_{page:03d}.mp4")
        qr.build_reel(ayahs, mp4, bg_seed=page)
        caption = qr.build_caption(ayahs, page)
        open(os.path.join(OUT, f"page_{page:03d}.txt"), "w").write(caption)
        made.append((page, mp4))
        print(f"   -> {mp4}", flush=True)
        page += 1
    save_next_page(page)
    print(f"\nDone. Made {len(made)} reel(s). Next run starts at page {page}.")

if __name__ == "__main__":
    main()
