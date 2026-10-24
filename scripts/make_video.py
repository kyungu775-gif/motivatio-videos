#!/usr/bin/env python3
"""Générateur de vidéos TikTok 9:16 pour @motivativatio — gratuit et hors ligne.

Usage :
    python3 scripts/make_video.py scripts_videos/AAAA-MM-JJ_slug.json videos/AAAA-MM-JJ_slug.mp4

Entrée JSON :
{
  "titre": "Texte court affiché en haut de la 1re scène (≤ 28 caractères)",
  "vitesse": 1.05,                        # optionnel, débit de la voix
  "scenes": [
    {"texte": "Phrase lue par la voix off.", "icone": "timer", "couleurs": ["#1b1f3b", "#53354a"]},
    ...
  ]
}

Sortie : MP4 H.264 1080x1920 30 i/s, AAC 44,1 kHz stéréo, voix française (Kokoro, voix ff_siwis),
sous-titres incrustés, icônes Lucide (licence ISC), musique générée par calcul (aucun droit).
Les modèles et icônes sont téléchargés automatiquement au premier lancement (dossier ~/.cache/motivatio).
"""
import hashlib, io, json, math, os, subprocess, sys, tarfile, urllib.request

W, H, FPS, SR = 1080, 1920, 30, 24000
CACHE = os.path.expanduser(os.environ.get("MOTIVATIO_CACHE", "~/.cache/motivatio"))
MODEL_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
FONT_DIRS = ["/usr/share/fonts/truetype/google-fonts", "/usr/share/fonts/truetype/dejavu"]
PALETTES = [["#1b1f3b", "#53354a"], ["#0f2027", "#2c5364"], ["#232526", "#414345"], ["#3a1c71", "#d76d77"],
            ["#141e30", "#243b55"], ["#42275a", "#734b6d"], ["#0b486b", "#3b8686"], ["#2c3e50", "#4ca1af"]]


def log(*a):
    print("[motivatio]", *a, flush=True)


def run(cmd):
    r = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if r.returncode:
        raise RuntimeError(f"Échec de {cmd[0]} : {r.stderr[-1500:]}")


# ---------- préparation des ressources (téléchargées une seule fois) ----------
def ensure_resources():
    os.makedirs(CACHE, exist_ok=True)
    for name, fname in [("kokoro.onnx", "kokoro-v1.0.int8.onnx"), ("voices.bin", "voices-v1.0.bin")]:
        p = os.path.join(CACHE, name)
        if not os.path.exists(p) or os.path.getsize(p) < 1_000_000:
            log("téléchargement", fname)
            urllib.request.urlretrieve(MODEL_URL + fname, p + ".part")
            os.replace(p + ".part", p)
    icons = os.path.join(CACHE, "lucide", "package", "icons")
    if not os.path.isdir(icons):
        log("téléchargement des icônes Lucide (npm)")
        d = os.path.join(CACHE, "lucide"); os.makedirs(d, exist_ok=True)
        out = subprocess.run(["npm", "pack", "lucide-static@1.61.0", "--silent", "--pack-destination", d],
                             capture_output=True, text=True, check=True).stdout.strip().splitlines()[-1]
        with tarfile.open(os.path.join(d, out)) as t:
            t.extractall(d, filter="data")
    return os.path.join(CACHE, "kokoro.onnx"), os.path.join(CACHE, "voices.bin"), icons


def font_path():
    for d in FONT_DIRS:
        for f in ("Poppins-Bold.ttf", "DejaVuSans-Bold.ttf"):
            if os.path.exists(os.path.join(d, f)):
                return os.path.join(d, f), d, ("Poppins" if f.startswith("Poppins") else "DejaVu Sans")
    raise RuntimeError("Aucune police grasse trouvée")


def hex2rgb(h):
    h = h.lstrip("#"); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


# ---------- visuels ----------
def fond(couleurs, chemin, icons_dir, font, titre=None, icone=None):
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    w, h = int(W * 1.25), int(H * 1.25)
    a, b = np.array(hex2rgb(couleurs[0]), float), np.array(hex2rgb(couleurs[1]), float)
    y = np.linspace(0, 1, h)[:, None, None]
    img = (a * (1 - y) + b * y).repeat(w, axis=1)
    yy, xx = np.mgrid[0:h, 0:w]
    halo = np.exp(-(((xx - w * .5) / (w * .42)) ** 2 + ((yy - h * .36) / (h * .22)) ** 2))[..., None]
    im = Image.fromarray(np.clip(img + halo * 70, 0, 255).astype(np.uint8)).convert("RGBA")
    svg_path = os.path.join(icons_dir, f"{icone}.svg") if icone else None
    if svg_path and not os.path.exists(svg_path):
        log(f"icône inconnue « {icone} », remplacée par « sparkles »")
        svg_path = os.path.join(icons_dir, "sparkles.svg")
    if svg_path:
        import cairosvg
        svg = open(svg_path).read().replace("currentColor", "#ffffff").replace('stroke-width="2"', 'stroke-width="1.6"')
        ic = Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg.encode(), output_width=520, output_height=520)))
        disque = Image.new("RGBA", im.size, (0, 0, 0, 0)); dd = ImageDraw.Draw(disque)
        cx, cy, r = w // 2, int(h * .36), 430
        dd.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(255, 255, 255, 34), outline=(255, 255, 255, 90), width=6)
        im = Image.alpha_composite(im, disque)
        im.alpha_composite(ic, (cx - 260, cy - 260))
    if titre:
        d = ImageDraw.Draw(im); size = 70
        f = ImageFont.truetype(font, size)
        while d.textlength(titre.upper(), font=f) > 980 and size > 40:
            size -= 4; f = ImageFont.truetype(font, size)
        tw = d.textlength(titre.upper(), font=f)
        y0 = int(h * .12)
        d.rounded_rectangle((w // 2 - tw / 2 - 50, y0 - 60, w // 2 + tw / 2 + 50, y0 + 60), 60, fill=(0, 0, 0, 110))
        d.text((w // 2, y0), titre.upper(), font=f, fill=(255, 255, 255, 255), anchor="mm")
    im.convert("RGB").save(chemin)


def musique(duree, chemin, graine):
    """Nappe d'accords douce, générée par calcul : aucun droit d'auteur."""
    import numpy as np, soundfile as sf
    progressions = [
        [[220, 277.18, 329.63], [196, 246.94, 293.66], [174.61, 220, 261.63], [196, 246.94, 293.66]],
        [[261.63, 329.63, 392], [220, 261.63, 329.63], [174.61, 220, 261.63], [196, 246.94, 293.66]],
        [[196, 246.94, 293.66], [164.81, 196, 246.94], [130.81, 164.81, 196], [146.83, 185, 220]],
    ]
    accords = progressions[graine % len(progressions)]
    t = np.arange(int(duree * SR)) / SR
    sig = np.zeros_like(t); seg = 4.0
    for i, acc in enumerate(accords * (int(duree // (seg * 4)) + 2)):
        m = (t >= i * seg) & (t < (i + 1) * seg + 1)
        if not m.any():
            continue
        tt = t[m] - i * seg
        env = np.minimum(1, tt / 1.2) * np.minimum(1, np.maximum(0, (seg + 1 - tt)) / 1.5)
        for f in acc:
            sig[m] += env * (np.sin(2 * np.pi * f * tt) + .3 * np.sin(4 * np.pi * f * tt)) / 6
    sig *= np.minimum(1, t / 2) * np.minimum(1, (duree - t) / 2)
    sf.write(chemin, (sig * .35).astype(np.float32), SR)


def ass_time(s):
    return f"{int(s // 3600)}:{int(s % 3600 // 60):02d}:{s % 60:05.2f}"


# ---------- assemblage ----------
def main(entree, sortie):
    import numpy as np, soundfile as sf
    from kokoro_onnx import Kokoro
    data = json.load(open(entree, encoding="utf-8"))
    if not data.get("scenes"):
        raise ValueError("Le script ne contient aucune scène")
    model, voices, icons = ensure_resources()
    font, fontdir, fontname = font_path()
    graine = int(hashlib.md5(data["titre"].encode()).hexdigest(), 16)
    tmp = os.path.abspath(os.path.splitext(sortie)[0] + "_tmp"); os.makedirs(tmp, exist_ok=True)
    os.makedirs(os.path.dirname(os.path.abspath(sortie)), exist_ok=True)
    k = Kokoro(model, voices)
    voix, clips, events, t0 = [], [], [], 0.0
    pause = np.zeros(int(SR * .35), np.float32)
    for i, sc in enumerate(data["scenes"]):
        a, _ = k.create(sc["texte"], voice="ff_siwis", speed=data.get("vitesse", 1.05), lang="fr-fr")
        a = np.concatenate([a.astype(np.float32), pause]); d = len(a) / SR
        voix.append(a)
        mots = sc["texte"].split(); blocs = [" ".join(mots[j:j + 3]) for j in range(0, len(mots), 3)]
        total = sum(len(b) for b in blocs); parle = d - .35; t = t0
        for b in blocs:
            db = parle * len(b) / total; events.append((t, t + db, b)); t += db
        couleurs = sc.get("couleurs") or PALETTES[(graine + i) % len(PALETTES)]
        img = os.path.join(tmp, f"bg{i}.png")
        fond(couleurs, img, icons, font, data["titre"] if i == 0 else None, sc.get("icone"))
        clip = os.path.join(tmp, f"c{i}.mp4"); n = math.ceil(d * FPS)
        zoom = "min(zoom+0.0006,1.15)" if i % 2 == 0 else "if(eq(on,0),1.15,max(zoom-0.0006,1.0))"
        run(["ffmpeg", "-y", "-loop", "1", "-i", img, "-vf",
             f"zoompan=z='{zoom}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={n}:s={W}x{H}:fps={FPS},format=yuv420p",
             "-frames:v", str(n), "-c:v", "libx264", "-preset", "veryfast", clip])
        clips.append(clip); t0 += d
        log(f"scène {i + 1}/{len(data['scenes'])} prête ({d:.1f} s)")
    sf.write(os.path.join(tmp, "voix.wav"), np.concatenate(voix), SR)
    musique(t0, os.path.join(tmp, "musique.wav"), graine)
    ass = os.path.join(tmp, "subs.ass")
    with open(ass, "w", encoding="utf-8") as f:
        f.write("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n[V4+ Styles]\n"
                "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
                f"Style: Main,{fontname},104,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,7,3,2,80,80,520,1\n\n"
                "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
        for s, e, txt in events:
            f.write(f"Dialogue: 0,{ass_time(s)},{ass_time(e)},Main,,0,0,0,,{{\\fad(60,60)}}{txt.upper()}\n")
    liste = os.path.join(tmp, "liste.txt")
    open(liste, "w").write("".join(f"file '{c}'\n" for c in clips))
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", liste,
         "-i", os.path.join(tmp, "voix.wav"), "-i", os.path.join(tmp, "musique.wav"),
         "-filter_complex", f"[0:v]ass={ass}:fontsdir={fontdir}[v];[1:a][2:a]amix=inputs=2:duration=first:weights='1 0.6',loudnorm=I=-14:TP=-1.5[a]",
         "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2", "-movflags", "+faststart", "-t", f"{t0:.2f}", sortie])
    subprocess.run(["rm", "-rf", tmp])
    log(f"OK {sortie} — {t0:.1f} s")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
