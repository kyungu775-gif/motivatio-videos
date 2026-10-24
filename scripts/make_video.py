#!/usr/bin/env python3
"""Générateur de vidéos TikTok 9:16 pour @motivativatio (marque MOTIVATIO) — gratuit et hors ligne.

Usage :
    python3 scripts/make_video.py scripts_videos/AAAA-MM-JJ_slug.json videos/AAAA-MM-JJ_slug.mp4

Entrée JSON :
{
  "titre": "Accroche affichée en haut de la 1re scène (≤ 34 caractères)",
  "vitesse": 1.05,                                   # optionnel, débit de la voix
  "scenes": [
    # Visuel au choix, un seul par scène :
    {"texte": "Phrase lue.", "icone": "timer"},                                  # icône Lucide
    {"texte": "Phrase lue.", "carte": {"type": "mauvais", "etiquette": "PROMPT FLOU",
                                        "texte": "Texte affiché à l'écran"}},     # type : mauvais | bon | info
    {"texte": "Phrase lue.", "produit": {"titre": "IA PRATIQUE", "sous_titre": "30 prompts…",
                                          "prix": "12 000 CDF"}}                  # visuel du guide
  ],
  "tiktok": {...}                                    # utilisé par la tâche, pas par ce script
}

Sortie : MP4 H.264 1080x1920 30 i/s, AAC 44,1 kHz stéréo. Voix française Kokoro (ff_siwis),
sous-titres synchronisés phrase par phrase, signature MOTIVATIO, icônes Lucide (licence ISC),
musique générée par calcul (aucun droit). Ressources téléchargées au premier lancement (~/.cache/motivatio).
"""
import hashlib, io, json, math, os, re, subprocess, sys, tarfile, urllib.request

W, H, FPS, SR = 1080, 1920, 30, 24000
CW, CH = int(W * 1.25), int(H * 1.25)          # toile plus grande que l'écran, pour le zoom lent
CACHE = os.path.expanduser(os.environ.get("MOTIVATIO_CACHE", "~/.cache/motivatio"))
MODEL_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
FONT_DIR = "/usr/share/fonts/truetype/google-fonts"
FALLBACK_DIR = "/usr/share/fonts/truetype/dejavu"

# Identité visuelle MOTIVATIO : nuit profonde, accent ambre, vert/corail réservés au bon/mauvais exemple
MARQUE = {
    "fond": [("#0e1226", "#231a45"), ("#0c1a2b", "#1d2f52"), ("#14112b", "#2e1f4f"), ("#0f1b24", "#173a46")],
    "ambre": (255, 181, 71), "vert": (61, 220, 151), "corail": (255, 107, 107), "blanc": (255, 255, 255),
}


def log(*a):
    print("[motivatio]", *a, flush=True)


def run(cmd):
    r = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if r.returncode:
        raise RuntimeError(f"Échec de {cmd[0]} : {r.stderr[-1500:]}")


# ---------- ressources (téléchargées une seule fois) ----------
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


def fonts():
    if os.path.exists(os.path.join(FONT_DIR, "Poppins-Bold.ttf")):
        return {"bold": os.path.join(FONT_DIR, "Poppins-Bold.ttf"),
                "medium": os.path.join(FONT_DIR, "Poppins-Medium.ttf"),
                "regular": os.path.join(FONT_DIR, "Poppins-Regular.ttf"),
                "dir": FONT_DIR, "nom": "Poppins"}
    b = os.path.join(FALLBACK_DIR, "DejaVuSans-Bold.ttf"); r = os.path.join(FALLBACK_DIR, "DejaVuSans.ttf")
    return {"bold": b, "medium": b, "regular": r, "dir": FALLBACK_DIR, "nom": "DejaVu Sans"}


def hex2rgb(h):
    h = h.lstrip("#"); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def icone_png(icons_dir, nom, taille, couleur="#ffffff", trait="1.6"):
    import cairosvg
    from PIL import Image
    p = os.path.join(icons_dir, f"{nom}.svg")
    if not os.path.exists(p):
        log(f"icône inconnue « {nom} », remplacée par « sparkles »"); p = os.path.join(icons_dir, "sparkles.svg")
    svg = open(p).read().replace("currentColor", couleur).replace('stroke-width="2"', f'stroke-width="{trait}"')
    return Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg.encode(), output_width=taille, output_height=taille)))


def wrap(draw, texte, font, largeur):
    lignes, cur = [], ""
    for mot in texte.split():
        test = (cur + " " + mot).strip()
        if draw.textlength(test, font=font) <= largeur:
            cur = test
        else:
            if cur: lignes.append(cur)
            cur = mot
    if cur: lignes.append(cur)
    return lignes


# ---------- visuels ----------
def fond_base(i, graine):
    import numpy as np
    from PIL import Image
    c0, c1 = MARQUE["fond"][(graine + i) % len(MARQUE["fond"])]
    a, b = np.array(hex2rgb(c0), float), np.array(hex2rgb(c1), float)
    y = np.linspace(0, 1, CH)[:, None, None]
    img = (a * (1 - y) + b * y).repeat(CW, axis=1)
    yy, xx = np.mgrid[0:CH, 0:CW]
    hx = .3 if i % 2 else .7
    halo = np.exp(-(((xx - CW * hx) / (CW * .5)) ** 2 + ((yy - CH * .3) / (CH * .25)) ** 2))[..., None]
    img = img + halo * np.array(MARQUE["ambre"], float) * .16
    grain = np.random.default_rng(graine + i).normal(0, 3, (CH, CW, 1))   # léger grain, évite les bandes
    return Image.fromarray(np.clip(img + grain, 0, 255).astype(np.uint8)).convert("RGBA")


def dessine_icone(im, icons_dir, nom):
    from PIL import Image, ImageDraw
    cx, cy, r = CW // 2, int(CH * .36), 400
    calque = Image.new("RGBA", im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(calque)
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(255, 255, 255, 26), outline=MARQUE["ambre"] + (150,), width=6)
    im = Image.alpha_composite(im, calque)
    ic = icone_png(icons_dir, nom, 480)
    im.alpha_composite(ic, (cx - 240, cy - 240))
    return im


def dessine_carte(im, icons_dir, f, carte):
    from PIL import Image, ImageDraw, ImageFont
    typ = carte.get("type", "info")
    couleur = {"mauvais": MARQUE["corail"], "bon": MARQUE["vert"]}.get(typ, MARQUE["ambre"])
    ic_nom = {"mauvais": "circle-x", "bon": "circle-check"}.get(typ, "sparkles")
    larg, x0 = 1080, (CW - 1080) // 2
    d = ImageDraw.Draw(im)
    size = 52
    while True:
        fb = ImageFont.truetype(f["regular"], size)
        lignes = wrap(d, carte["texte"], fb, larg - 120)
        if len(lignes) <= 9 or size <= 36: break
        size -= 4
    lh = int(size * 1.38)
    haut = 130 + len(lignes) * lh + 70
    y0 = max(int(CH * .36) - haut // 2, int(CH * .12) + 110)
    calque = Image.new("RGBA", im.size, (0, 0, 0, 0)); dc = ImageDraw.Draw(calque)
    dc.rounded_rectangle((x0 + 10, y0 + 18, x0 + larg + 10, y0 + haut + 18), 44, fill=(0, 0, 0, 90))      # ombre
    dc.rounded_rectangle((x0, y0, x0 + larg, y0 + haut), 44, fill=(255, 255, 255, 236))
    dc.rounded_rectangle((x0, y0, x0 + 16, y0 + haut), 8, fill=couleur + (255,))                         # liseré
    im = Image.alpha_composite(im, calque); d = ImageDraw.Draw(im)
    ic = icone_png(icons_dir, ic_nom, 64, "#%02x%02x%02x" % couleur, "2.4")
    im.alpha_composite(ic, (x0 + 60, y0 + 42))
    fe = ImageFont.truetype(f["bold"], 40)
    d.text((x0 + 144, y0 + 74), carte.get("etiquette", "").upper(), font=fe, fill=couleur + (255,), anchor="lm")
    y = y0 + 130
    for l in lignes:
        d.text((x0 + 60, y), l, font=fb, fill=(24, 22, 38, 255)); y += lh
    return im


def dessine_produit(im, f, prod):
    from PIL import Image, ImageDraw, ImageFont
    import numpy as np
    bw, bh = 640, 860
    x0, y0 = (CW - bw) // 2, int(CH * .36) - bh // 2 - 40
    # couverture : dégradé ambre → corail
    t = np.linspace(0, 1, bh)[:, None, None]
    grad = (np.array(MARQUE["ambre"], float) * (1 - t) + np.array(MARQUE["corail"], float) * t).repeat(bw, axis=1)
    couv = Image.fromarray(grad.astype(np.uint8)).convert("RGBA")
    masque = Image.new("L", (bw, bh), 0); ImageDraw.Draw(masque).rounded_rectangle((0, 0, bw, bh), 30, fill=255)
    ombre = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(ombre).rounded_rectangle((x0 + 18, y0 + 26, x0 + bw + 18, y0 + bh + 26), 30, fill=(0, 0, 0, 110))
    im = Image.alpha_composite(im, ombre)
    im.paste(couv, (x0, y0), masque)
    d = ImageDraw.Draw(im)
    d.rectangle((x0 + 26, y0, x0 + 40, y0 + bh), fill=(0, 0, 0, 40))                                       # dos
    d.text((x0 + 80, y0 + 90), "MOTIVATIO", font=ImageFont.truetype(f["bold"], 30), fill=(30, 20, 40, 220))
    ft = ImageFont.truetype(f["bold"], 96)
    y = y0 + 230
    for l in wrap(d, prod.get("titre", "").upper(), ft, bw - 140):
        d.text((x0 + 80, y), l, font=ft, fill=(20, 16, 34, 255)); y += 104
    fs = ImageFont.truetype(f["medium"], 42)
    y += 30
    for l in wrap(d, prod.get("sous_titre", ""), fs, bw - 160):
        d.text((x0 + 80, y), l, font=fs, fill=(20, 16, 34, 230)); y += 56
    if prod.get("detail"):
        d.text((x0 + 80, y0 + bh - 90), prod["detail"], font=ImageFont.truetype(f["medium"], 34), fill=(20, 16, 34, 200))
    if prod.get("prix"):
        fp = ImageFont.truetype(f["bold"], 58)
        tw = d.textlength(prod["prix"], font=fp)
        py = y0 + bh + 90
        d.rounded_rectangle((CW // 2 - tw / 2 - 50, py - 52, CW // 2 + tw / 2 + 50, py + 52), 52, fill=(255, 255, 255, 245))
        d.text((CW // 2, py), prod["prix"], font=fp, fill=(20, 16, 34, 255), anchor="mm")
    return im


def scene_image(chemin, sc, i, graine, icons_dir, f, titre=None):
    from PIL import ImageDraw, ImageFont
    im = fond_base(i, graine)
    if sc.get("carte"):
        im = dessine_carte(im, icons_dir, f, sc["carte"])
    elif sc.get("produit"):
        im = dessine_produit(im, f, sc["produit"])
    elif sc.get("icone"):
        im = dessine_icone(im, icons_dir, sc["icone"])
    if titre:
        d = ImageDraw.Draw(im); size = 68
        ft = ImageFont.truetype(f["bold"], size)
        while d.textlength(titre.upper(), font=ft) > 1000 and size > 40:
            size -= 4; ft = ImageFont.truetype(f["bold"], size)
        tw = d.textlength(titre.upper(), font=ft); y0 = int(CH * .155)
        d.rounded_rectangle((CW // 2 - tw / 2 - 46, y0 - 58, CW // 2 + tw / 2 + 46, y0 + 58), 58, fill=MARQUE["ambre"] + (255,))
        d.text((CW // 2, y0), titre.upper(), font=ft, fill=(20, 16, 34, 255), anchor="mm")
    im.convert("RGB").save(chemin)


# ---------- son ----------
def musique(duree, chemin, graine):
    """Nappe d'accords douce et pulsation légère, générées par calcul : aucun droit d'auteur."""
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
        if not m.any(): continue
        tt = t[m] - i * seg
        env = np.minimum(1, tt / 1.2) * np.minimum(1, np.maximum(0, (seg + 1 - tt)) / 1.5)
        for fq in acc:
            sig[m] += env * (np.sin(2 * np.pi * fq * tt) + .3 * np.sin(4 * np.pi * fq * tt)) / 6
    # pulsation douce (basse sur chaque temps à 100 bpm) pour donner du rythme
    beat = 60 / 100; ph = (t % beat)
    sig += .12 * np.sin(2 * np.pi * 55 * ph) * np.exp(-ph * 9)
    sig *= np.minimum(1, t / 1.5) * np.minimum(1, (duree - t) / 2)
    sf.write(chemin, (sig * .33).astype(np.float32), SR)


def ass_time(s):
    return f"{int(s // 3600)}:{int(s % 3600 // 60):02d}:{s % 60:05.2f}"


def phrases(texte):
    return [p for p in re.split(r"(?<=[.!?…:])\s+", texte.strip()) if p]


# ---------- assemblage ----------
def main(entree, sortie):
    import numpy as np, soundfile as sf
    from kokoro_onnx import Kokoro
    data = json.load(open(entree, encoding="utf-8"))
    if not data.get("scenes"):
        raise ValueError("Le script ne contient aucune scène")
    model, voices, icons = ensure_resources()
    f = fonts()
    graine = int(hashlib.md5(data["titre"].encode()).hexdigest(), 16) % 10_000
    tmp = os.path.abspath(os.path.splitext(sortie)[0] + "_tmp"); os.makedirs(tmp, exist_ok=True)
    os.makedirs(os.path.dirname(os.path.abspath(sortie)), exist_ok=True)
    k = Kokoro(model, voices)
    vitesse = data.get("vitesse", 1.05)
    voix, clips, events, t0 = [], [], [], 0.0
    pause_phrase = np.zeros(int(SR * .18), np.float32)
    pause_scene = np.zeros(int(SR * .30), np.float32)
    for i, sc in enumerate(data["scenes"]):
        debut_scene = t0
        # synthèse phrase par phrase : le minutage exact de chaque phrase cale les sous-titres
        for j, ph in enumerate(phrases(sc["texte"])):
            a, _ = k.create(ph, voice="ff_siwis", speed=vitesse, lang="fr-fr")
            a = a.astype(np.float32); parle = len(a) / SR
            mots = ph.split(); blocs = [" ".join(mots[x:x + 3]) for x in range(0, len(mots), 3)]
            total = sum(len(b) + 2 for b in blocs); t = t0
            for b in blocs:
                db = parle * (len(b) + 2) / total; events.append((t, t + db, b)); t += db
            voix.append(a); t0 += parle
            voix.append(pause_phrase); t0 += len(pause_phrase) / SR
        voix.append(pause_scene); t0 += len(pause_scene) / SR
        d = t0 - debut_scene
        img = os.path.join(tmp, f"bg{i}.png")
        scene_image(img, sc, i, graine, icons, f, data["titre"] if i == 0 else None)
        clip = os.path.join(tmp, f"c{i}.mp4"); n = math.ceil(d * FPS)
        vit = "0.0009" if (sc.get("carte") or sc.get("produit")) else "0.0006"
        zoom = f"min(zoom+{vit},1.12)" if i % 2 == 0 else f"if(eq(on,0),1.12,max(zoom-{vit},1.0))"
        run(["ffmpeg", "-y", "-loop", "1", "-i", img, "-vf",
             f"zoompan=z='{zoom}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={n}:s={W}x{H}:fps={FPS},format=yuv420p",
             "-frames:v", str(n), "-c:v", "libx264", "-preset", "veryfast", clip])
        clips.append((clip, d))
        log(f"scène {i + 1}/{len(data['scenes'])} prête ({d:.1f} s)")
    sf.write(os.path.join(tmp, "voix.wav"), np.concatenate(voix), SR)
    musique(t0, os.path.join(tmp, "musique.wav"), graine)
    ass = os.path.join(tmp, "subs.ass")
    with open(ass, "w", encoding="utf-8") as fh:
        fh.write("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nWrapStyle: 0\n\n[V4+ Styles]\n"
                 "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
                 f"Style: Main,{f['nom']},96,&H00FFFFFF,&H00FFFFFF,&H00261014,&H96000000,-1,0,0,0,100,100,0,0,1,8,2,2,110,140,500,1\n"
                 f"Style: Marque,{f['nom']},32,&H40FFFFFF,&H40FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,8,0,1,0,0,8,0,0,150,1\n\n"
                 "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
        fh.write(f"Dialogue: 0,{ass_time(0)},{ass_time(t0)},Marque,,0,0,0,,MOTIVATIO\n")
        # barre de progression ambre en haut de l'écran (s'allonge pendant toute la vidéo)
        fh.write(f"Dialogue: 1,{ass_time(0)},{ass_time(t0)},Marque,,0,0,0,,{{\\an7\\pos(0,0)\\1c&H47B5FF&\\1a&H00&\\bord0\\shad0\\clip(0,0,0,12)\\t(0,{int(t0 * 1000)},\\clip(0,0,1080,12))\\p1}}m 0 0 l 1080 0 1080 12 0 12{{\\p0}}\n")
        for s, e, txt in events:
            fh.write(f"Dialogue: 2,{ass_time(s)},{ass_time(e)},Main,,0,0,0,,{{\\fad(50,40)\\fscx92\\fscy92\\t(0,90,\\fscx100\\fscy100)}}{txt.upper()}\n")
    liste = os.path.join(tmp, "liste.txt")
    open(liste, "w").write("".join(f"file '{c}'\n" for c, _ in clips))
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", liste,
         "-i", os.path.join(tmp, "voix.wav"), "-i", os.path.join(tmp, "musique.wav"),
         "-filter_complex", f"[0:v]ass={ass}:fontsdir={f['dir']}[v];[1:a][2:a]amix=inputs=2:duration=first:weights='1 0.55',loudnorm=I=-14:TP=-1.5[a]",
         "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2", "-movflags", "+faststart", "-t", f"{t0:.2f}", sortie])
    subprocess.run(["rm", "-rf", tmp])
    log(f"OK {sortie} — {t0:.1f} s")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
