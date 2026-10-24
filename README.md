# motivatio-videos

Vidéos générées automatiquement pour le compte TikTok **@motivativatio** (marque MOTIVATIO).

- `PROCEDURE.md` : la consigne hebdomadaire suivie par Claude (à modifier pour changer le fonctionnement).
- `scripts/` : le moteur vidéo animé (`make_video.py`), le son (`motivatio_audio.py`), les contrôles
  (`check.py`) et le format des scripts (`FORMAT.md`).
- `scripts_videos/` : les scripts de chaque vidéo (JSON).
- `videos/` : les MP4 prêts à publier (1080×1920, 30 i/s).
- `journal/` : la liste des vidéos, les bilans de performance et le suivi commercial.

Générer une vidéo :

```bash
bash scripts/setup.sh
python3 scripts/make_video.py scripts_videos/2026-10-24_prompt-flou-vs-precis.json videos/essai.mp4
```

Ressources gratuites : voix Kokoro v1.1 (Apache 2.0, ≈ 350 Mo téléchargés au premier lancement),
icônes Lucide (ISC), police Poppins (OFL), musique et bruitages composés par calcul (aucun droit).
