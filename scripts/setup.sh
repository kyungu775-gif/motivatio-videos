#!/usr/bin/env bash
# Installe tout ce qu'il faut pour générer les vidéos, dans un environnement neuf.
# Idempotent : peut être relancé sans risque. Aucun service payant.
set -euo pipefail
cd "$(dirname "$0")/.."

need() { command -v "$1" >/dev/null 2>&1 || { echo "[motivatio] ERREUR : $1 manquant"; exit 1; }; }
need ffmpeg; need ffprobe; need python3; need npm

python3 -m pip install --quiet --break-system-packages -r scripts/requirements.txt 2>/dev/null \
  || python3 -m pip install --quiet -r scripts/requirements.txt

# Télécharge la voix (≈ 120 Mo) et les icônes au premier lancement
python3 -c "import sys; sys.path.insert(0,'scripts'); import make_video; make_video.ensure_resources()"
echo "[motivatio] environnement prêt"
