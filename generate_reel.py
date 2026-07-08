#!/usr/bin/env python3
"""
Quran Reel generator — Sheikh Yasser Al-Dosari (Arabic only).
Per-ayah Arabic text (with tashkeel) + recitation audio, in order,
over slow-moving nature / galaxy backgrounds (Ken Burns).

Usage: python generate_reel.py <surah> <ayah_start> <ayah_end> <out.mp4>
Example (Al-Fatihah): python generate_reel.py 1 1 7 output/fatihah.mp4
"""
import sys, os, subprocess, json, glob, urllib.request, textwrap

HERE = os.path.dirname(os.path.abspath(__file__))
RECITER = "Yasser_Ad-Dussary_128kbps"
AUDIO_BASE = f"https://everyayah.com/data/{RECITER}"
TEXT_API = "https://api.alquran.cloud/v1/ayah/{key}/quran-uthmani"
FONT = "/System/Library/Fonts/Supplemental/GeezaPro.ttc"   # traditional naskh, full tashkeel, renders via presentation forms
LATIN_FONT = "/System/Library/Fonts/Helvetica.ttc"
BG_DIR = os.path.join(HERE, "backgrounds")
TMP = os.path.join(HERE, "tmp")
W, H, FPS = 1080, 1920, 30
TAIL = 0.25          # small breath after each ayah's audio
GOLD = (212, 175, 110, 255)
WHITE = (245, 245, 240, 255)

def fetch_text(surah, ayah):
    key = f"{surah}:{ayah}"
    with urllib.request.urlopen(TEXT_API.format(key=key), timeout=30) as r:
        return json.load(r)["data"]["text"]

def fetch_audio(surah, ayah, dest):
    urllib.request.urlretrieve(f"{AUDIO_BASE}/{surah:03d}{ayah:03d}.mp3", dest)
    return dest

def audio_duration(path):
    out = subprocess.check_output(["ffprobe","-v","quiet","-show_entries",
        "format=duration","-of","csv=p=0", path])
    return float(out.strip())

def render_text_overlay(arabic_text, surah, ayah, dest):
    """Transparent RGBA overlay: dark scrim + shadowed Arabic + gold ref."""
    from PIL import Image, ImageDraw, ImageFont
    import arabic_reshaper
    from bidi.algorithm import get_display

    # CRITICAL: keep harakat (tashkeel). Default reshaper deletes them.
    reshaper = arabic_reshaper.ArabicReshaper(
        configuration={"delete_harakat": False, "support_ligatures": True})

    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    size = 92 if len(arabic_text) < 120 else (70 if len(arabic_text) < 260 else 52)
    font = ImageFont.truetype(FONT, size)

    # Wrap on RAW arabic (logical order), shape each line, draw top->bottom.
    chars_per_line = max(16, int(W / (size * 0.62)))
    raw_lines = textwrap.wrap(arabic_text, width=chars_per_line) or [arabic_text]
    lines = [get_display(reshaper.reshape(l)) for l in raw_lines]

    line_h = int(size * 1.95)   # Amiri + tashkeel needs generous spacing
    block_h = line_h * len(lines)
    y0 = (H - block_h) // 2

    # Soft dark scrim behind the text block so white reads on any photo.
    pad_x, pad_y = 70, 90
    scrim = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(scrim)
    sdraw.rectangle([pad_x, y0 - pad_y, W - pad_x, y0 + block_h + pad_y],
                    fill=(0, 0, 0, 120))
    scrim = scrim.filter(__import__("PIL.ImageFilter", fromlist=["ImageFilter"]).GaussianBlur(40))
    img = Image.alpha_composite(img, scrim)
    draw = ImageDraw.Draw(img)

    y = y0
    for line in lines:
        bb = draw.textbbox((0, 0), line, font=font)
        lw = bb[2] - bb[0]
        x = (W - lw) // 2
        # shadow then text
        draw.text((x + 3, y + 3), line, font=font, fill=(0, 0, 0, 200))
        draw.text((x, y), line, font=font, fill=WHITE)
        y += line_h

    ref_font = ImageFont.truetype(LATIN_FONT, 38)
    ref = f"{surah}:{ayah}"
    rb = draw.textbbox((0, 0), ref, font=ref_font)
    draw.text(((W - (rb[2]-rb[0]))//2, H - 190), ref, font=ref_font, fill=GOLD)

    img.save(dest)

def make_clip(bg_img, overlay_png, audio_path, dest):
    dur = audio_duration(audio_path) + TAIL
    frames = int(dur * FPS)
    # Ken Burns: scale up, slow zoom-in, darken slightly, then overlay text.
    vf = (
        f"[0:v]scale=2160:3840:force_original_aspect_ratio=increase,"
        f"crop=2160:3840,"
        f"zoompan=z='min(zoom+0.00035,1.18)':"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"d={frames}:s={W}x{H}:fps={FPS},"
        f"eq=brightness=-0.12:saturation=0.92[bg];"
        f"[bg][1:v]overlay=0:0[v]"
    )
    subprocess.run([
        "ffmpeg","-y","-loop","1","-i",bg_img,"-i",overlay_png,"-i",audio_path,
        "-filter_complex",vf,"-map","[v]","-map","2:a",
        "-t",f"{dur:.2f}","-r",str(FPS),
        "-c:v","libx264","-pix_fmt","yuv420p","-c:a","aac","-b:a","192k",
        "-shortest", dest
    ], check=True, capture_output=True)

def main():
    surah, a_start, a_end, out = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
    os.makedirs(TMP, exist_ok=True)
    bgs = sorted(glob.glob(os.path.join(BG_DIR, "*.jpg")))
    if not bgs:
        sys.exit("No backgrounds in backgrounds/")

    clips = []
    for i, ayah in enumerate(range(a_start, a_end + 1)):
        print(f"  ayah {surah}:{ayah} ...", flush=True)
        text = fetch_text(surah, ayah)
        ov = os.path.join(TMP, f"{surah:03d}{ayah:03d}_ov.png")
        aud = os.path.join(TMP, f"{surah:03d}{ayah:03d}.mp3")
        clip = os.path.join(TMP, f"{surah:03d}{ayah:03d}.mp4")
        bg = bgs[i % len(bgs)]                  # rotate backgrounds per ayah
        render_text_overlay(text, surah, ayah, ov)
        fetch_audio(surah, ayah, aud)
        make_clip(bg, ov, aud, clip)
        clips.append(clip)

    listfile = os.path.join(TMP, "concat.txt")
    with open(listfile, "w") as f:
        for c in clips:
            f.write(f"file '{c}'\n")
    # RE-ENCODE on concat (not -c copy) -> fixes audio pops / breaking at joins.
    subprocess.run([
        "ffmpeg","-y","-f","concat","-safe","0","-i",listfile,
        "-c:v","libx264","-pix_fmt","yuv420p","-c:a","aac","-b:a","192k",
        "-r",str(FPS), out
    ], check=True, capture_output=True)
    print(f"DONE -> {out}")

if __name__ == "__main__":
    main()
