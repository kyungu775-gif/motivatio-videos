#!/usr/bin/env python3
"""Contrôles automatiques avant et après génération.

    python3 scripts/check.py script  scripts_videos/xxx.json   # vérifie le script avant rendu
    python3 scripts/check.py video   videos/xxx.mp4            # vérifie le MP4 produit

Code de sortie 0 = conforme, 1 = problème (détail affiché).
"""
import json, os, subprocess, sys

CACHE = os.path.expanduser(os.environ.get("MOTIVATIO_CACHE", "~/.cache/motivatio"))
ICONS = os.path.join(CACHE, "lucide", "package", "icons")


def check_script(path):
    errs = []
    d = json.load(open(path, encoding="utf-8"))
    titre = d.get("titre", "")
    if not titre or len(titre) > 34:
        errs.append(f"titre absent ou trop long ({len(titre)} car., max 34)")
    scenes = d.get("scenes", [])
    if not 3 <= len(scenes) <= 8:
        errs.append(f"{len(scenes)} scènes (attendu 3 à 8)")
    mots = sum(len(s.get("texte", "").split()) for s in scenes)
    duree = mots / 3.0  # ≈ 3 mots/s mesurés pour cette voix
    if not 45 <= mots <= 150:
        errs.append(f"{mots} mots, soit ≈ {duree:.0f} s (viser 70 à 130 mots, ≈ 23 à 45 s)")
    for i, s in enumerate(scenes, 1):
        if not s.get("texte"):
            errs.append(f"scène {i} sans texte")
        ic = s.get("icone")
        if ic and os.path.isdir(ICONS) and not os.path.exists(os.path.join(ICONS, ic + ".svg")):
            errs.append(f"scène {i} : icône « {ic} » introuvable (voir {ICONS})")
    meta = d.get("tiktok", {})
    if not meta.get("legende"):
        errs.append("légende TikTok absente (champ tiktok.legende)")
    elif len(meta["legende"]) > 2000:
        errs.append("légende TikTok trop longue (> 2000 car.)")
    if not meta.get("titre_tiktok"):
        errs.append("titre TikTok absent (champ tiktok.titre_tiktok, exigé par Metricool)")
    return errs, f"{len(scenes)} scènes, {mots} mots, ≈ {duree:.0f} s"


def check_video(path):
    errs = []
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                          "stream=codec_type,codec_name,width,height,sample_rate,channels:format=duration,size",
                          "-of", "json", path], capture_output=True, text=True)
    if out.returncode:
        return [f"fichier illisible : {out.stderr.strip()}"], ""
    info = json.loads(out.stdout)
    v = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    dur, size = float(info["format"]["duration"]), int(info["format"]["size"])
    if not v or v["codec_name"] != "h264" or (v["width"], v["height"]) != (1080, 1920):
        errs.append("vidéo non conforme (attendu H.264 1080x1920)")
    if not a or a["codec_name"] != "aac":
        errs.append("piste audio absente ou non AAC")
    if not 10 <= dur <= 90:
        errs.append(f"durée {dur:.1f} s hors plage 10–90 s")
    if size > 50 * 1024 * 1024:
        errs.append(f"fichier trop lourd ({size / 1e6:.1f} Mo)")
    return errs, f"{dur:.1f} s, {size / 1e6:.2f} Mo, {v and v['width']}x{v and v['height']}"


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in ("script", "video"):
        sys.exit(__doc__)
    errs, resume = (check_script if sys.argv[1] == "script" else check_video)(sys.argv[2])
    print(("OK " if not errs else "ÉCHEC ") + sys.argv[2] + " — " + resume)
    for e in errs:
        print("  -", e)
    sys.exit(1 if errs else 0)
