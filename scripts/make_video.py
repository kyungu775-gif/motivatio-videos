#!/usr/bin/env python3
"""Moteur vidéo MOTIVATIO v2 — vidéos TikTok 9:16 animées, gratuites et hors ligne.

Usage :
    python3 scripts/make_video.py scripts_videos/AAAA-MM-JJ_slug.json videos/AAAA-MM-JJ_slug.mp4

Rendu image par image (30 i/s) : fond animé, animations d'entrée, texte qui se tape, listes et
formules synchronisées sur la voix, couverture du guide avec reflet, sous-titres mot à mot surlignés,
transitions glissées, bruitages et musique lo-fi générés, voix française Kokoro avec minutage
phonème par phonème. Le format du fichier JSON est décrit dans scripts/FORMAT.md.
"""
import functools, hashlib, json, math, os, re, subprocess, sys, tarfile, unicodedata, urllib.request

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import motivatio_audio as son  # noqa: E402

W, H, FPS = 1080, 1920, 30
CACHE = os.path.expanduser(os.environ.get("MOTIVATIO_CACHE", "~/.cache/motivatio"))
MODELES = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/"
VOIX = "ff_siwis"
FONT_DIR = "/usr/share/fonts/truetype/google-fonts"

AMBRE, CORAIL, VERT = (255, 181, 71), (255, 107, 107), (61, 220, 151)
ENCRE, BLANC = (20, 16, 34), (255, 255, 255)
FONDS = [((12, 15, 34), (38, 26, 72)), ((10, 22, 40), (30, 48, 86)), ((18, 14, 38), (52, 30, 80))]
TRANSITION = 0.32       # durée des transitions entre scènes (s)
PAUSE_SCENE = 0.28      # silence entre deux scènes (s)
CAPTION_Y = 1335        # centre des sous-titres (hors zones d'interface TikTok)

# Graphies utilisées pour la voix seulement (les sous-titres gardent le texte original)
PRONONCIATION = [(r"\bIA\b", "i a"), (r"(?i)\bprompts?\b", "prommpte"), (r"(?i)\be-mails?\b", "imèl"),
                 (r"\bMOTIVATIO\b", "Motivatio"), (r"(?i)\bCDF\b", "francs congolais")]
PONCT = set(",.;:!?…—-\"'«»()")


def log(*a):
    print("[motivatio]", *a, flush=True)


# ------------------------------------------------------------------ ressources
def ensure_resources():
    os.makedirs(CACHE, exist_ok=True)
    for local, distant in [("kokoro-v1.1.onnx", "kokoro-v1.0.onnx"), ("voices-v1.1.bin", "voices-v1.0.bin")]:
        p = os.path.join(CACHE, local)
        if not os.path.exists(p) or os.path.getsize(p) < 1_000_000:
            log("téléchargement", distant, "(v1.1, avec minutage)")
            urllib.request.urlretrieve(MODELES + distant, p + ".part"); os.replace(p + ".part", p)
    icons = os.path.join(CACHE, "lucide", "package", "icons")
    if not os.path.isdir(icons):
        log("téléchargement des icônes Lucide (npm)")
        d = os.path.join(CACHE, "lucide"); os.makedirs(d, exist_ok=True)
        out = subprocess.run(["npm", "pack", "lucide-static@1.61.0", "--silent", "--pack-destination", d],
                             capture_output=True, text=True, check=True).stdout.strip().splitlines()[-1]
        with tarfile.open(os.path.join(d, out)) as t:
            t.extractall(d, filter="data")
    return os.path.join(CACHE, "kokoro-v1.1.onnx"), os.path.join(CACHE, "voices-v1.1.bin"), icons


@functools.lru_cache(maxsize=64)
def police(taille, graisse="bold"):
    nom = {"bold": "Poppins-Bold.ttf", "semi": "Poppins-SemiBold.ttf", "medium": "Poppins-Medium.ttf",
           "regular": "Poppins-Regular.ttf"}[graisse]
    p = os.path.join(FONT_DIR, nom)
    if not os.path.exists(p):
        p = os.path.join(FONT_DIR, "Poppins-Bold.ttf" if graisse in ("bold", "semi") else "Poppins-Regular.ttf")
    if not os.path.exists(p):
        p = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    return ImageFont.truetype(p, taille)


ICONS_DIR = None


@functools.lru_cache(maxsize=64)
def icone(nom, taille, couleur=BLANC, trait=1.6):
    import cairosvg, io
    p = os.path.join(ICONS_DIR, f"{nom}.svg")
    if not os.path.exists(p):
        log(f"icône inconnue « {nom} », remplacée par « sparkles »"); p = os.path.join(ICONS_DIR, "sparkles.svg")
    svg = open(p).read().replace("currentColor", "#%02x%02x%02x" % couleur).replace('stroke-width="2"', f'stroke-width="{trait}"')
    return Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg.encode(), output_width=taille, output_height=taille))).convert("RGBA")


# ------------------------------------------------------------------ outils
def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def out_cubic(x):
    x = clamp(x); return 1 - (1 - x) ** 3


def out_back(x):
    x = clamp(x); c1 = 1.70158; c3 = c1 + 1
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


def in_out(x):
    x = clamp(x); return 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2


def norm(mot):
    s = unicodedata.normalize("NFD", mot.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]", "", s)


def wrap(texte, font, largeur):
    d = ImageDraw.Draw(Image.new("L", (1, 1)))
    lignes, cur = [], ""
    for mot in texte.split():
        test = (cur + " " + mot).strip()
        if d.textlength(test, font=font) <= largeur:
            cur = test
        else:
            if cur: lignes.append(cur)
            cur = mot
    if cur: lignes.append(cur)
    return lignes


def avec_alpha(img, a):
    if a >= 0.999: return img
    im = img.copy()
    im.putalpha(im.getchannel("A").point(lambda v: int(v * a)))
    return im


def coller(frame, img, cx, cy, echelle=1.0, alpha=1.0, dx=0, rot=0.0):
    """Colle img centrée en (cx+dx, cy), avec échelle, transparence et rotation, en restant dans le cadre."""
    if alpha <= 0.01 or echelle <= 0.01: return
    im = img
    if abs(echelle - 1) > 0.004:
        im = im.resize((max(1, int(im.width * echelle)), max(1, int(im.height * echelle))), Image.BILINEAR)
    if abs(rot) > 0.05:
        im = im.rotate(rot, resample=Image.BICUBIC, expand=True)
    im = avec_alpha(im, alpha)
    x, y = int(cx + dx - im.width / 2), int(cy - im.height / 2)
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(W, x + im.width), min(H, y + im.height)
    if x1 <= x0 or y1 <= y0: return
    if (x0, y0, x1, y1) != (x, y, x + im.width, y + im.height):
        im = im.crop((x0 - x, y0 - y, x1 - x, y1 - y))
    frame.alpha_composite(im, (x0, y0))


def ombre_portee(img, rayon=28, decal=(0, 22), opacite=150, avec_image=True):
    """Ombre douce sous une image RGBA (retourne une image plus grande, l'image étant centrée)."""
    m = rayon * 2
    out = Image.new("RGBA", (img.width + 2 * m, img.height + 2 * m), (0, 0, 0, 0))
    a = img.getchannel("A").point(lambda v: v * opacite // 255)
    out.paste(Image.new("RGBA", img.size, (0, 0, 0, 255)), (m + decal[0], m + decal[1]), a)
    out = out.filter(ImageFilter.GaussianBlur(rayon))
    if avec_image:
        out.alpha_composite(img, (m, m))
    return out


def pilule(texte, taille, fond, couleur, pad=(40, 18), graisse="bold", icone_nom=None):
    f = police(taille, graisse)
    tw = int(ImageDraw.Draw(Image.new("L", (1, 1))).textlength(texte, font=f))
    iw = int(taille * 1.05) if icone_nom else 0
    w, h = tw + iw + 2 * pad[0] + (14 if icone_nom else 0), int(taille * 1.25) + 2 * pad[1]
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, h - 1), h // 2, fill=fond)
    x = pad[0]
    if icone_nom:
        ic = icone(icone_nom, iw, couleur[:3], 2.6); im.alpha_composite(ic, (x, (h - iw) // 2)); x += iw + 14
    d.text((x, h // 2), texte, font=f, fill=couleur, anchor="lm")
    return im


# ------------------------------------------------------------------ voix et minutage
def prononce(mot):
    for motif, rempl in PRONONCIATION:
        mot = re.sub(motif, rempl, mot)
    return mot


def synthese(k, texte, vitesse):
    """Retourne (audio 24 kHz, [{'mot', 'debut', 'fin'}]) avec un minutage mot par mot."""
    jetons = texte.split()
    mots = []
    for j in jetons:
        if mots and all(c in PONCT for c in j):
            mots[-1] += " " + j
        else:
            mots.append(j)
    tts = [prononce(m) for m in mots]
    audio, sr, tim = k.create_timed(" ".join(tts), voice=VOIX, speed=vitesse, lang="fr-fr", trim=False)
    groupes, cur = [], []
    for t in tim:
        if t.phoneme == " ":
            if cur: groupes.append(cur); cur = []
        else:
            cur.append(t)
    if cur: groupes.append(cur)
    comptes = [max(1, len(k.tokenizer.phonemize(m, "fr-fr").split())) for m in tts]
    res = []
    if sum(comptes) == len(groupes):
        i = 0
        for m, c in zip(mots, comptes):
            g = [p for grp in groupes[i:i + c] for p in grp]
            sons = [p for p in g if p.phoneme not in PONCT and p.end > p.start] or g
            res.append({"mot": m, "debut": sons[0].start, "fin": sons[-1].end}); i += c
    else:
        log(f"minutage approximatif ({sum(comptes)} groupes attendus, {len(groupes)} obtenus)")
        d0 = tim[0].start if tim else 0.05; d1 = tim[-1].end if tim else len(audio) / sr
        poids = [len(norm(m)) + 1 for m in mots]; tot = sum(poids); t = d0
        for m, p in zip(mots, poids):
            dt = (d1 - d0) * p / tot; res.append({"mot": m, "debut": t, "fin": t + dt * 0.92}); t += dt
    fin = max(r["fin"] for r in res) + 0.12
    audio = audio[:int(min(len(audio), fin * sr))]
    return audio.astype(np.float32), res


def temps_du_mot(mots, cible, apres=0.0, dernier=False):
    """Moment où la voix prononce `cible` (premier après `apres`, ou dernière occurrence)."""
    c = norm(cible.split()[0]) if cible and cible.split() else ""
    trouves = [m["debut"] for m in mots if m["debut"] >= apres - 1e-6 and c and norm(m["mot"]).startswith(c)]
    if not trouves:
        return None
    return trouves[-1] if dernier else trouves[0]


# ------------------------------------------------------------------ éléments visuels
class Element:
    def __init__(self, sc, dur, mots, titre):
        self.sc, self.dur, self.mots, self.titre = sc, dur, mots, titre
        self.sons = []          # (t, type) relatifs au début de la scène
        self.haut = 520 if titre else 300   # haut de la zone libre

    def dessine(self, frame, u, dx, a):
        pass


class Icone(Element):
    def __init__(self, *args):
        super().__init__(*args)
        nom = self.sc["icone"]
        taille = 560
        im = Image.new("RGBA", (taille + 160, taille + 160), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        c = im.width // 2; r = taille // 2
        d.ellipse((c - r, c - r, c + r, c + r), outline=AMBRE + (200,), width=10)
        im = im.filter(ImageFilter.GaussianBlur(26))
        d = ImageDraw.Draw(im)
        d.ellipse((c - r, c - r, c + r, c + r), fill=(255, 255, 255, 24), outline=AMBRE + (210,), width=5)
        ic = icone(nom, 290); im.alpha_composite(ic, (c - 145, c - 145))
        self.img = im
        self.label = pilule(self.sc["label"].upper(), 44, AMBRE + (255,), ENCRE) if self.sc.get("label") else None
        self.cy = max(self.haut + 330, 740)
        self.sons.append((0.05, "pop"))

    def dessine(self, frame, u, dx, a):
        e = out_back(u / 0.5)
        flotte = 10 * math.sin(2 * math.pi * u / 2.8)
        coller(frame, self.img, W / 2, self.cy + flotte, 0.6 + 0.4 * e, a * clamp(u / 0.2), dx)
        if self.label:
            el = out_cubic((u - 0.25) / 0.35)
            coller(frame, self.label, W / 2, self.cy + 330 + 30 * (1 - el), 1, a * el, dx)


class Carte(Element):
    """Carte de prompt : le texte se tape à l'écran, puis un badge juge le prompt."""

    def __init__(self, *args):
        super().__init__(*args)
        c = self.sc["carte"]
        self.texte = c["texte"]; self.type = c.get("type", "info")
        self.couleur = {"mauvais": CORAIL, "bon": VERT}.get(self.type, AMBRE)
        larg = 940; marge = 56
        taille = 64 if len(self.texte) < 70 else 54 if len(self.texte) < 140 else 48
        while True:
            self.f = police(taille, "regular")
            self.lignes = wrap(self.texte, self.f, larg - 2 * marge)
            if len(self.lignes) <= 8 or taille <= 36: break
            taille -= 3
        self.lh = int(taille * 1.42)
        haut_carte = 136 + len(self.lignes) * self.lh + 60
        base = Image.new("RGBA", (larg, haut_carte), (0, 0, 0, 0)); d = ImageDraw.Draw(base)
        teinte = tuple(int(255 * 0.86 + v * 0.14) for v in self.couleur) + (255,)
        d.rounded_rectangle((0, 0, larg - 1, haut_carte - 1), 40, fill=teinte)
        d.rounded_rectangle((0, 104, larg - 1, haut_carte - 1), 40, fill=(255, 255, 255, 255))
        d.rectangle((0, 104, larg - 1, 160), fill=(255, 255, 255, 255))
        d.line((0, 104, larg, 104), fill=self.couleur + (90,), width=2)
        ic_nom = {"mauvais": "message-square-x", "bon": "message-square-text"}.get(self.type, "sparkles")
        base.alpha_composite(icone(ic_nom, 54, self.couleur, 2.4), (marge, 25))
        fonce = tuple(int(v * 0.72) for v in self.couleur)
        d.text((marge + 74, 52), c.get("etiquette", "").upper(), font=police(38, "bold"), fill=fonce, anchor="lm")
        self.base = base
        self.marge = marge
        self.w, self.h = larg, haut_carte
        top = max(self.haut, 780 - haut_carte // 2)
        self.cy = top + haut_carte / 2
        self.t_type = 0.38
        nb = len(self.texte)
        self.d_type = clamp(nb / 40, 0.8, max(0.8, self.dur * 0.55))
        self.t_badge = self.t_type + self.d_type + 0.2
        self.badge = None
        if self.type in ("mauvais", "bon"):
            txt = c.get("badge") or ("Trop vague" if self.type == "mauvais" else "Précis")
            self.badge = pilule(txt.upper(), 42, self.couleur + (255,), ENCRE if self.type == "bon" else BLANC,
                                icone_nom="x" if self.type == "mauvais" else "check")
            self.sons.append((self.t_badge, "erreur" if self.type == "mauvais" else "ding"))
        self.sons.append((0.02, "pop"))
        t = self.t_type
        while t < self.t_type + self.d_type:
            self.sons.append((t, "tick")); t += 0.065

    def dessine(self, frame, u, dx, a):
        e = out_cubic(u / 0.4)
        img = self.base.copy(); d = ImageDraw.Draw(img)
        n = int(len(self.texte) * clamp((u - self.t_type) / self.d_type))
        reste, y = n, 136
        x_fin, y_fin = self.marge, y
        for ligne in self.lignes:
            if reste <= 0: break
            part = ligne[:reste]
            d.text((self.marge, y), part, font=self.f, fill=ENCRE)
            x_fin, y_fin = self.marge + d.textlength(part, font=self.f), y
            reste -= len(ligne) + 1; y += self.lh
        if u < self.t_type + self.d_type + 0.6 and int(u * 2.4) % 2 == 0:
            d.rectangle((x_fin + 4, y_fin + 6, x_fin + 10, y_fin + self.lh - 14), fill=self.couleur)
        coller(frame, ombre_portee_cache(self, img), W / 2, self.cy + 70 * (1 - e), 0.94 + 0.06 * e, a * e, dx)
        if self.badge and u >= self.t_badge:
            eb = out_back((u - self.t_badge) / 0.35)
            secousse = 8 * math.sin(u * 60) * max(0, 1 - (u - self.t_badge) / 0.3) if self.type == "mauvais" else 0
            coller(frame, self.badge, W / 2 + self.w / 2 - self.badge.width / 2 - 10 + secousse,
                   self.cy - self.h / 2 - 6, eb, a, dx, rot=-6 if self.type == "mauvais" else 4)


def ombre_portee_cache(obj, img):
    """L'ombre ne dépend que de la forme de la carte : calculée une fois, puis le contenu est recollé dessus."""
    if not hasattr(obj, "_ombre"):
        obj._ombre = ombre_portee(obj.base, 30, (0, 24), 120, avec_image=False)
        obj._marge = (obj._ombre.width - obj.base.width) // 2
    out = obj._ombre.copy()
    out.alpha_composite(img, (obj._marge, obj._marge))
    return out


class Liste(Element):
    """Étapes qui apparaissent une à une, synchronisées sur la voix ; chaque étape se coche."""

    def __init__(self, *args):
        super().__init__(*args)
        L = self.sc["liste"]
        self.titre_liste = pilule(L["titre"].upper(), 42, (255, 255, 255, 30), AMBRE) if L.get("titre") else None
        items = L["items"]
        croix = L.get("style") == "croix"      # « croix » : éléments à retirer / défauts ; sinon coches vertes
        coul, ic_nom, son_ok = (CORAIL, "x", "pop") if croix else (VERT, "check", "ding")
        self.rows = []
        f = police(54, "semi")
        larg = 940
        hauteurs = [44 + len(wrap(it["texte"] if isinstance(it, dict) else it, f, larg - 160)) * 70 + 22 for it in items]
        bloc = sum(hauteurs) + 30 * (len(items) - 1) + (110 if self.titre_liste else 0)
        self.y_titre = max(self.haut, 780 - bloc // 2) + 34
        y = self.y_titre - 34 + (110 if self.titre_liste else 0)
        t_prec = 0.15
        for i, it in enumerate(items):
            txt = it["texte"] if isinstance(it, dict) else it
            mot = it.get("mot") if isinstance(it, dict) else None
            lignes = wrap(txt, f, larg - 160)
            h = hauteurs[i]
            vide = Image.new("RGBA", (larg, h), (0, 0, 0, 0)); d = ImageDraw.Draw(vide)
            d.rounded_rectangle((0, 0, larg - 1, h - 1), 30, fill=(255, 255, 255, 26), outline=(255, 255, 255, 50), width=2)
            for j, l in enumerate(lignes):
                d.text((140, 44 + j * 70), l, font=f, fill=BLANC)
            coche = vide.copy(); dc = ImageDraw.Draw(coche)
            dc.ellipse((40, h // 2 - 32, 104, h // 2 + 32), fill=coul)
            coche.alpha_composite(icone(ic_nom, 44, ENCRE, 3.2), (50, h // 2 - 22))
            d.ellipse((40, h // 2 - 32, 104, h // 2 + 32), outline=(255, 255, 255, 140), width=4)
            t = temps_du_mot(self.mots, mot, t_prec) if mot else None
            if t is None:
                t = 0.25 + i * max(0.5, (self.dur * 0.7 - 0.25) / max(1, len(items)))
            t_prec = t
            self.rows.append({"vide": vide, "coche": coche, "y": y + h / 2, "t": max(0.05, t - 0.15)})
            self.sons.append((max(0.05, t - 0.15), "pop")); self.sons.append((t + 0.35, son_ok))
            y += h + 26

    def dessine(self, frame, u, dx, a):
        if self.titre_liste:
            coller(frame, self.titre_liste, W / 2, self.y_titre, 1, a * out_cubic(u / 0.3), dx)
        for r in self.rows:
            if u < r["t"]: continue
            e = out_cubic((u - r["t"]) / 0.35)
            img = r["coche"] if u >= r["t"] + 0.35 else r["vide"]
            ec = out_back((u - r["t"] - 0.35) / 0.25) if u >= r["t"] + 0.35 else 1
            coller(frame, img, W / 2 - 120 * (1 - e), r["y"], 0.97 + 0.03 * ec, a * e, dx)


class Formule(Element):
    """Mots-clés qui apparaissent au moment exact où la voix les prononce."""

    def __init__(self, *args):
        super().__init__(*args)
        mots = self.sc["formule"]
        self.chips = []
        n = len(mots)
        h_chip, gap = 118, 64
        total = n * h_chip + (n - 1) * gap
        y = max(self.haut, 780 - total // 2) + h_chip / 2
        t_prec = 0.0
        for i, m in enumerate(mots):
            fond = AMBRE + (255,) if i % 2 == 0 else (255, 255, 255, 245)
            img = pilule(m.upper(), 62, fond, ENCRE, pad=(56, 20))
            t = temps_du_mot(self.mots, m, t_prec)
            if t is None: t = 0.2 + i * 0.55
            t_prec = t
            self.chips.append({"img": img, "y": y, "t": max(0, t - 0.06)})
            self.sons.append((max(0, t - 0.06), "pop"))
            y += h_chip + gap
        self.plus = pilule("+", 54, (0, 0, 0, 0), AMBRE, pad=(10, 0))

    def dessine(self, frame, u, dx, a):
        for i, c in enumerate(self.chips):
            if u < c["t"]: continue
            e = out_back((u - c["t"]) / 0.38)
            coller(frame, c["img"], W / 2, c["y"], 0.5 + 0.5 * e, a * clamp((u - c["t"]) / 0.15), dx)
            if i > 0:
                coller(frame, self.plus, W / 2, c["y"] - 91, 1, a * clamp((u - c["t"]) / 0.2), dx)


class Produit(Element):
    """Couverture du guide qui monte, reflet lumineux, prix puis appel à l'action synchronisé."""

    def __init__(self, *args):
        super().__init__(*args)
        p = self.sc["produit"]
        bw, bh = 560, 760
        t = np.linspace(0, 1, bh)[:, None, None]
        grad = (np.array(AMBRE, float) * (1 - t) + np.array(CORAIL, float) * t).repeat(bw, axis=1)
        couv = Image.fromarray(grad.astype(np.uint8)).convert("RGBA")
        masque = Image.new("L", (bw, bh), 0); ImageDraw.Draw(masque).rounded_rectangle((0, 0, bw - 1, bh - 1), 26, fill=255)
        couv.putalpha(masque)
        d = ImageDraw.Draw(couv)
        d.rectangle((24, 0, 38, bh), fill=(0, 0, 0, 38))
        d.text((76, 74), "MOTIVATIO", font=police(28, "bold"), fill=ENCRE + (210,))
        y = 200
        for l in wrap(p.get("titre", "").upper(), police(92, "bold"), bw - 130):
            d.text((76, y), l, font=police(92, "bold"), fill=ENCRE); y += 98
        y += 26
        for l in wrap(p.get("sous_titre", ""), police(38, "medium"), bw - 140):
            d.text((76, y), l, font=police(38, "medium"), fill=ENCRE + (235,)); y += 52
        if p.get("detail"):
            d.text((76, bh - 84), p["detail"], font=police(30, "medium"), fill=ENCRE + (200,))
        self.couv = couv
        self.ombre = ombre_portee(couv, 34, (16, 30), 170)
        bande = Image.new("L", (160, bh * 2), 0); db = ImageDraw.Draw(bande)
        for x in range(160):
            db.line((x, 0, x, bh * 2), fill=int(150 * math.sin(math.pi * x / 159) ** 2))
        self.bande = bande.rotate(18, expand=True)
        self.prix = pilule(p.get("prix", ""), 58, (255, 255, 255, 250), ENCRE, pad=(52, 16)) if p.get("prix") else None
        self.cta = pilule(p.get("cta", "Écris GUIDE en commentaire"), 46, AMBRE + (255,), ENCRE,
                          icone_nom="message-circle", pad=(40, 16))
        self.cy = (self.haut + 40 if self.titre else 300) + bh / 2 * 0.88
        self.t_prix = 0.75
        tc = temps_du_mot(self.mots, p.get("mot_cta", "GUIDE"), dernier=True)
        self.t_cta = tc - 0.1 if tc is not None else self.dur * 0.6
        self.sons += [(0.0, "whoosh"), (0.55, "brillance"), (self.t_prix, "pop"), (self.t_cta, "pop")]

    def dessine(self, frame, u, dx, a):
        e = out_cubic(u / 0.55)
        couv = self.couv
        tb = (u - 0.5) / 0.9
        if 0 <= tb <= 1:
            couv = couv.copy()
            reflet = Image.new("RGBA", couv.size, (255, 255, 255, 0))
            x = int(-260 + tb * (couv.width + 360))
            masque = Image.new("L", couv.size, 0)
            masque.paste(self.bande, (x, -self.bande.height // 4))
            reflet.putalpha(Image.fromarray(np.minimum(np.array(masque), np.array(couv.getchannel("A"))).astype(np.uint8)))
            couv.alpha_composite(reflet)
        ech = (0.82 + 0.06 * e) + 0.012 * math.sin(2 * math.pi * u / 3)
        y = self.cy + 160 * (1 - e)
        coller(frame, self.ombre, W / 2, y + 8, ech, a * e * 0.95, dx, rot=-3)
        coller(frame, couv, W / 2, y, ech, a * e, dx, rot=-3)
        bas = y + self.couv.height * ech / 2
        if self.prix and u >= self.t_prix:
            coller(frame, self.prix, W / 2, bas + 70, out_back((u - self.t_prix) / 0.35), a, dx)
        if u >= self.t_cta:
            pulse = 1 + 0.03 * math.sin(2 * math.pi * (u - self.t_cta) / 0.9)
            coller(frame, self.cta, W / 2, bas + 175, out_back((u - self.t_cta) / 0.35) * pulse, a, dx)


class Titre(Element):
    """Accroche de la 1re scène : les mots surgissent un par un. Les mots entre *étoiles* sont en ambre."""

    def __init__(self, sc, dur, mots, titre):
        super().__init__(sc, dur, mots, titre)
        brut = titre.split()
        f = police(84, "bold")
        self.mots_img = []
        lignes, cur, largeur = [], [], 0
        sp = 24
        dans_accent = False
        for m in brut:
            debut_acc = m.startswith("*")
            accent = dans_accent or debut_acc
            dans_accent = accent and not m.endswith("*")
            txt = m.strip("*").upper()
            w = int(ImageDraw.Draw(Image.new("L", (1, 1))).textlength(txt, font=f))
            if cur and largeur + sp + w > 940:
                lignes.append(cur); cur, largeur = [], 0
            cur.append((txt, accent, w)); largeur += (sp if largeur else 0) + w
        if cur: lignes.append(cur)
        y = 290
        k = 0
        for ligne in lignes:
            total = sum(w for _, _, w in ligne) + sp * (len(ligne) - 1)
            x = (W - total) / 2
            for txt, accent, w in ligne:
                im = Image.new("RGBA", (w + 40, 130), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
                if accent:
                    d.rounded_rectangle((0, 8, w + 39, 122), 22, fill=AMBRE)
                d.text((20, 65), txt, font=f, fill=ENCRE if accent else BLANC, anchor="lm",
                       stroke_width=0 if accent else 6, stroke_fill=ENCRE)
                self.mots_img.append({"img": im, "cx": x + w / 2, "cy": y, "t": 0.05 + 0.09 * k})
                x += w + sp; k += 1
            y += 120

    def dessine(self, frame, u, dx, a):
        for m in self.mots_img:
            if u < m["t"]: continue
            e = out_back((u - m["t"]) / 0.32)
            coller(frame, m["img"], m["cx"], m["cy"] + 20 * (1 - e), 0.6 + 0.4 * e, a * clamp((u - m["t"]) / 0.12), dx)


TYPES = [("carte", Carte), ("liste", Liste), ("formule", Formule), ("produit", Produit), ("icone", Icone)]


# ------------------------------------------------------------------ décor et sous-titres
def fond_video(graine):
    rng = np.random.default_rng(graine)
    c0, c1 = FONDS[graine % len(FONDS)]
    bw, bh = W + 240, H + 320
    y = np.linspace(0, 1, bh)[:, None, None]
    img = (np.array(c0, float) * (1 - y) + np.array(c1, float) * y).repeat(bw, axis=1)
    yy, xx = np.mgrid[0:bh, 0:bw]
    for (px, py, rx, ry, col, k) in [(.78, .22, .45, .2, AMBRE, .2), (.15, .7, .5, .25, (120, 80, 255), .16),
                                     (.6, .95, .4, .15, CORAIL, .1)]:
        g = np.exp(-(((xx - bw * px) / (bw * rx)) ** 2 + ((yy - bh * py) / (bh * ry)) ** 2))[..., None]
        img = img + g * np.array(col, float) * k
    img += rng.normal(0, 2.4, (bh, bw, 1))
    fond = np.clip(img, 0, 255).astype(np.uint8)
    part = Image.new("RGBA", (W, H * 2), (0, 0, 0, 0)); d = ImageDraw.Draw(part)
    for _ in range(46):
        x, y, r = rng.uniform(0, W), rng.uniform(0, H * 2), rng.uniform(2, 7)
        d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 230, 190, int(rng.uniform(25, 85))))
    part = part.filter(ImageFilter.GaussianBlur(1.6))
    return fond, part


def morceaux_sous_titres(mots):
    """Découpe en groupes de 1 à 3 mots, coupés à la ponctuation, pour un affichage dynamique."""
    groupes, cur = [], []
    for m in mots:
        cur.append(m)
        long = sum(len(x["mot"]) for x in cur) + len(cur)
        if len(cur) == 3 or long >= 17 or m["mot"][-1] in ",.;:!?…":
            groupes.append(cur); cur = []
    if cur: groupes.append(cur)
    out = []
    for i, g in enumerate(groupes):
        fin = g[-1]["fin"] + 0.25
        if i + 1 < len(groupes): fin = min(max(fin, groupes[i + 1][0]["debut"] - 0.02), groupes[i + 1][0]["debut"] - 0.02)
        out.append({"mots": g, "debut": g[0]["debut"] - 0.04, "fin": fin})
    return out


def dessine_sous_titre(frame, morceau, t, mots_cles):
    f = police(80, "bold")
    d0 = ImageDraw.Draw(frame)
    textes = [m["mot"].upper() for m in morceau["mots"]]
    largeurs = [d0.textlength(x, font=f) for x in textes]
    sp = 22; total = sum(largeurs) + sp * (len(textes) - 1)
    taille = 80
    while total > 940 and taille > 52:
        taille -= 6; f = police(taille, "bold")
        largeurs = [d0.textlength(x, font=f) for x in textes]; total = sum(largeurs) + sp * (len(textes) - 1)
    img = Image.new("RGBA", (int(total) + 60, 170), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    x = 30
    for m, txt, w in zip(morceau["mots"], textes, largeurs):
        actif = m["debut"] <= t < m["fin"] + 0.08
        cle = norm(m["mot"]) in mots_cles
        couleur = AMBRE if (actif or cle) else BLANC
        lift = -8 * (1 - clamp((t - m["debut"]) / 0.12)) if actif else 0
        d.text((x, 85 + lift), txt, font=f, fill=couleur, anchor="lm", stroke_width=9, stroke_fill=ENCRE)
        x += w + sp
    e = out_back((t - morceau["debut"]) / 0.16)
    coller(frame, img, W / 2, CAPTION_Y, 0.85 + 0.15 * e, clamp((t - morceau["debut"]) / 0.08))


# ------------------------------------------------------------------ assemblage
def main(entree, sortie):
    global ICONS_DIR
    from kokoro_onnx import Kokoro
    data = json.load(open(entree, encoding="utf-8"))
    if not data.get("scenes"):
        raise ValueError("Le script ne contient aucune scène")
    modele, voix, ICONS_DIR = ensure_resources()
    graine = int(hashlib.md5(data["titre"].encode()).hexdigest(), 16) % 10_000
    k = Kokoro(modele, voix)
    vitesse = data.get("vitesse", 1.05)
    mots_cles = {norm(x) for x in data.get("mots_cles", [])}

    # 1. voix et minutage
    scenes, pistes, t0 = [], [], 0.0
    for i, sc in enumerate(data["scenes"]):
        audio, mots = synthese(k, sc["texte"], vitesse)
        parle = len(audio) / 24000
        dur = parle + PAUSE_SCENE + (0.9 if i == len(data["scenes"]) - 1 else 0)
        scenes.append({"sc": sc, "debut": t0, "dur": dur, "mots": mots})
        pistes.append(np.concatenate([audio, np.zeros(int((dur - parle) * 24000), np.float32)]))
        t0 += dur
        log(f"voix scène {i + 1}/{len(data['scenes'])} : {parle:.1f} s")
    total = t0
    voix_audio = np.concatenate(pistes)

    # 2. plan visuel
    evenements = []
    for i, s in enumerate(scenes):
        titre = data["titre"] if i == 0 else None
        cls = next((c for key, c in TYPES if s["sc"].get(key)), None)
        s["elements"] = []
        if titre:
            s["elements"].append(Titre(s["sc"], s["dur"], s["mots"], titre))
        if cls:
            s["elements"].append(cls(s["sc"], s["dur"], s["mots"], titre))
        for el in s["elements"]:
            evenements += [(s["debut"] + t, typ) for t, typ in el.sons]
        if i > 0:
            evenements.append((s["debut"] - 0.12, "whoosh"))
    sous_titres = []
    for s in scenes:
        for m in morceaux_sous_titres([dict(x, debut=x["debut"] + s["debut"], fin=x["fin"] + s["debut"]) for x in s["mots"]]):
            sous_titres.append(m)

    # 3. son : voix, musique, bruitages
    tmp = os.path.abspath(os.path.splitext(sortie)[0] + "_tmp"); os.makedirs(tmp, exist_ok=True)
    os.makedirs(os.path.dirname(os.path.abspath(sortie)), exist_ok=True)
    import soundfile as sf
    sf.write(os.path.join(tmp, "voix.wav"), voix_audio, 24000)
    sf.write(os.path.join(tmp, "musique.wav"), son.musique(total, graine), son.SR)
    sf.write(os.path.join(tmp, "sfx.wav"), son.bruitages(total, evenements, graine), son.SR)

    # 4. images
    fond, particules = fond_video(graine)
    marque = Image.new("RGBA", (420, 60), (0, 0, 0, 0)); dm = ImageDraw.Draw(marque)
    dm.text((210, 30), "M O T I V A T I O", font=police(28, "bold"), fill=(255, 255, 255, 150), anchor="mm")
    nb = int(math.ceil(total * FPS))
    filtre = (
        "[1:a]aresample=44100,highpass=f=75,equalizer=f=220:t=q:w=1:g=-2,equalizer=f=3400:t=q:w=1.2:g=3,"
        "acompressor=threshold=-20dB:ratio=3:attack=5:release=90:makeup=2,asplit=2[v][vsc];"
        "[2:a]volume=0.42[m];[m][vsc]sidechaincompress=threshold=0.02:ratio=10:attack=15:release=350[md];"
        "[3:a]volume=0.6[s];[v][md][s]amix=inputs=3:duration=first:normalize=0,alimiter=limit=0.95,"
        "loudnorm=I=-14:TP=-1.5:LRA=11[a]")
    proc = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
         "-i", os.path.join(tmp, "voix.wav"), "-i", os.path.join(tmp, "musique.wav"), "-i", os.path.join(tmp, "sfx.wav"),
         "-filter_complex", filtre, "-map", "0:v", "-map", "[a]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2", "-movflags", "+faststart",
         "-t", f"{total:.3f}", sortie], stdin=subprocess.PIPE)
    i_st = 0
    for n in range(nb):
        t = n / FPS
        ox = int(120 + 90 * math.sin(2 * math.pi * t / 15)); oy = int(160 + 130 * math.sin(2 * math.pi * t / 21))
        frame = Image.fromarray(fond[oy:oy + H, ox:ox + W]).convert("RGBA")
        py = int((t * 28) % H)
        frame.alpha_composite(particules.crop((0, H - py, W, 2 * H - py)))
        # scène courante (et précédente pendant la transition)
        idx = max(j for j, s in enumerate(scenes) if s["debut"] <= t + 1e-9)
        s = scenes[idx]; u = t - s["debut"]
        if idx > 0 and u < TRANSITION:
            e = in_out(u / TRANSITION)
            p = scenes[idx - 1]
            for el in p["elements"]:
                el.dessine(frame, p["dur"] + u, -e * 300, 1 - e)
            for el in s["elements"]:
                el.dessine(frame, u, (1 - e) * 300, e)
        else:
            for el in s["elements"]:
                el.dessine(frame, u, 0, 1)
        while i_st < len(sous_titres) and sous_titres[i_st]["fin"] <= t:
            i_st += 1
        if i_st < len(sous_titres) and sous_titres[i_st]["debut"] <= t:
            dessine_sous_titre(frame, sous_titres[i_st], t, mots_cles)
        frame.alpha_composite(marque, ((W - marque.width) // 2, 150))
        ImageDraw.Draw(frame).rectangle((0, 0, int(W * t / total), 7), fill=AMBRE)
        proc.stdin.write(frame.convert("RGB").tobytes())
        if n % (FPS * 5) == 0:
            log(f"images {n}/{nb}")
    proc.stdin.close()
    if proc.wait():
        raise RuntimeError("échec de l'encodage ffmpeg")
    if not os.environ.get("MOTIVATIO_GARDER_TMP"):
        subprocess.run(["rm", "-rf", tmp])
    log(f"OK {sortie} — {total:.1f} s")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
