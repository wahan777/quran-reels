#!/usr/bin/env python3
"""Core reel builder. One background per reel, Arabic + tashkeel, Al-Dosari audio."""
import os, subprocess, json, glob, urllib.request, textwrap, random

HERE = os.path.dirname(os.path.abspath(__file__))
RECITER = "Yasser_Ad-Dussary_128kbps"
AUDIO_BASE = f"https://everyayah.com/data/{RECITER}"
PAGE_API = "https://api.alquran.cloud/v1/page/{page}/quran-uthmani"
# Rendering Arabic correctly needs either (a) a HarfBuzz shaper (raqm) — present
# in Pillow's Linux/CI wheels — used with raw Unicode + a proper Quran font, or
# (b) on macOS (no raqm), the arabic_reshaper hack + a presentation-form font.
from PIL import features as _pil_features
HAS_RAQM = _pil_features.check("raqm")
AMIRI = os.path.join(HERE, "fonts/AmiriQuran-Regular.ttf")  # bundled, for raqm path
GEEZA = "/System/Library/Fonts/Supplemental/GeezaPro.ttc"   # macOS fallback
ARABIC_FONT = AMIRI if HAS_RAQM else GEEZA
LATIN_FONT = ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
              if HAS_RAQM else "/System/Library/Fonts/Helvetica.ttc")
BG_DIR = os.path.join(HERE, "backgrounds")
TMP = os.path.join(HERE, "tmp")
W, H, FPS = 1080, 1920, 30
TAIL = 0.25
GOLD = (212, 175, 110, 255)
WHITE = (245, 245, 240, 255)

def fetch_page(page):
    """Return (ayahs, surah_meta) for a Mushaf page. ayahs: list of dicts."""
    with urllib.request.urlopen(PAGE_API.format(page=page), timeout=30) as r:
        data = json.load(r)["data"]
    ayahs = [{"surah": a["surah"]["number"], "ayah": a["numberInSurah"],
              "text": a["text"], "surah_en": a["surah"]["englishName"],
              "surah_ar": a["surah"]["name"]} for a in data["ayahs"]]
    return ayahs

def fetch_audio(surah, ayah, dest):
    urllib.request.urlretrieve(f"{AUDIO_BASE}/{surah:03d}{ayah:03d}.mp3", dest)
    return dest

def audio_duration(path):
    out = subprocess.check_output(["ffprobe","-v","quiet","-show_entries",
        "format=duration","-of","csv=p=0", path])
    return float(out.strip())

def _shape_lines(arabic_text, chars_per_line):
    """Return display-ready lines. With raqm, Pillow shapes raw text itself
    (we just wrap logically). Without raqm, apply reshaper+bidi per line."""
    raw_lines = textwrap.wrap(arabic_text, width=chars_per_line) or [arabic_text]
    if HAS_RAQM:
        return raw_lines                      # Pillow + HarfBuzz shapes on draw
    import arabic_reshaper
    from bidi.algorithm import get_display
    reshaper = arabic_reshaper.ArabicReshaper(
        configuration={"delete_harakat": False, "support_ligatures": True})
    return [get_display(reshaper.reshape(l)) for l in raw_lines]

def render_text_overlay(arabic_text, surah, ayah, dest):
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    size = 92 if len(arabic_text) < 120 else (70 if len(arabic_text) < 260 else 52)
    font = ImageFont.truetype(ARABIC_FONT, size)
    draw_kw = {"direction": "rtl"} if HAS_RAQM else {}   # let HarfBuzz do RTL
    chars_per_line = max(16, int(W / (size * 0.62)))
    lines = _shape_lines(arabic_text, chars_per_line)
    line_h = int(size * 1.95)
    block_h = line_h * len(lines)
    y0 = (H - block_h) // 2
    scrim = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(scrim)
    sdraw.rectangle([70, y0 - 90, W - 70, y0 + block_h + 90], fill=(0, 0, 0, 130))
    scrim = scrim.filter(ImageFilter.GaussianBlur(40))
    img = Image.alpha_composite(img, scrim)
    draw = ImageDraw.Draw(img)
    y = y0
    for line in lines:
        bb = draw.textbbox((0, 0), line, font=font, **draw_kw)
        x = (W - (bb[2]-bb[0])) // 2
        draw.text((x + 3, y + 3), line, font=font, fill=(0, 0, 0, 200), **draw_kw)
        draw.text((x, y), line, font=font, fill=WHITE, **draw_kw)
        y += line_h
    ref_font = ImageFont.truetype(LATIN_FONT, 38)
    ref = f"{surah}:{ayah}"
    rb = draw.textbbox((0, 0), ref, font=ref_font)
    draw.text(((W - (rb[2]-rb[0]))//2, H - 190), ref, font=ref_font, fill=GOLD)
    img.save(dest)

def make_clip(bg_img, overlay_png, audio_path, dest):
    dur = audio_duration(audio_path) + TAIL
    frames = int(dur * FPS)
    vf = (f"[0:v]scale=2160:3840:force_original_aspect_ratio=increase,crop=2160:3840,"
          f"zoompan=z='min(zoom+0.00035,1.18)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
          f"d={frames}:s={W}x{H}:fps={FPS},eq=brightness=-0.12:saturation=0.92[bg];"
          f"[bg][1:v]overlay=0:0[v]")
    subprocess.run(["ffmpeg","-y","-loop","1","-i",bg_img,"-i",overlay_png,"-i",audio_path,
        "-filter_complex",vf,"-map","[v]","-map","2:a","-t",f"{dur:.2f}","-r",str(FPS),
        "-c:v","libx264","-pix_fmt","yuv420p","-c:a","aac","-b:a","192k","-shortest",dest],
        check=True, capture_output=True)

def pick_background(seed):
    bgs = sorted(glob.glob(os.path.join(BG_DIR, "*.jpg")))
    if not bgs:
        raise SystemExit("No backgrounds in backgrounds/")
    return bgs[seed % len(bgs)]      # deterministic: one bg for the whole reel

def build_reel(ayahs, out, bg_seed):
    """ayahs: list of dicts with surah, ayah, text. One background for all."""
    os.makedirs(TMP, exist_ok=True)
    bg = pick_background(bg_seed)
    clips = []
    for a in ayahs:
        s, n = a["surah"], a["ayah"]
        ov = os.path.join(TMP, f"{s:03d}{n:03d}_ov.png")
        aud = os.path.join(TMP, f"{s:03d}{n:03d}.mp3")
        clip = os.path.join(TMP, f"{s:03d}{n:03d}.mp4")
        render_text_overlay(a["text"], s, n, ov)
        fetch_audio(s, n, aud)
        make_clip(bg, ov, aud, clip)
        clips.append(clip)
    listfile = os.path.join(TMP, "concat.txt")
    with open(listfile, "w") as f:
        for c in clips:
            f.write(f"file '{c}'\n")
    subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i",listfile,
        "-c:v","libx264","-pix_fmt","yuv420p","-c:a","aac","-b:a","192k",
        "-r",str(FPS), out], check=True, capture_output=True)
    return out

def build_caption(ayahs, page):
    surahs = []
    for a in ayahs:
        tag = f"{a['surah_en']}"
        if tag not in surahs:
            surahs.append(tag)
    first, last = ayahs[0], ayahs[-1]
    rng = f"{first['surah_en']} {first['ayah']}" + (
        f" – {last['surah_en']} {last['ayah']}" if (first['surah'], first['ayah']) != (last['surah'], last['ayah']) else "")
    body = " | ".join(surahs)
    tags = ("#quran #qurantilawat #yasseraldosari #islam #islamic #recitation "
            "#quranrecitation #muslim #allah #deen #islamicreminder #quranverses "
            "#tilawat #beautifulrecitation #qurandaily")
    return (f"📖 {rng}\n\nالسلام عليكم — Quran, page {page} of 604.\n"
            f"Recitation: Sheikh Yasser Al-Dosari.\n\nFollow to complete the whole Quran with us, one page at a time. 🤍\n\n{tags}")
