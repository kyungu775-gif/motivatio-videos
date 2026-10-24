# motivatio-videos

Vidéos générées automatiquement pour le compte TikTok **@motivativatio**.

- `PROCEDURE.md` : la consigne hebdomadaire suivie par Claude (à modifier pour changer le fonctionnement).
- `scripts/` : le générateur (voix française Kokoro, sous-titres, icônes Lucide, musique générée).
- `scripts_videos/` : les scripts de chaque vidéo (JSON).
- `videos/` : les MP4 prêts à publier (1080×1920).
- `journal/` : la liste des vidéos et les bilans de performance.

Générer une vidéo :

```bash
bash scripts/setup.sh
python3 scripts/make_video.py scripts_videos/exemple.json videos/exemple.mp4
```

Ressources gratuites utilisées : voix Kokoro (licence Apache 2.0), icônes Lucide (licence ISC),
musique composée par calcul (aucun droit).
