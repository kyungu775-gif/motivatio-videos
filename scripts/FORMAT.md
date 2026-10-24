# Format d'un script vidéo (JSON)

Un fichier par vidéo dans `scripts_videos/AAAA-MM-JJ_slug.json`. Contrôle : `python3 scripts/check.py script <fichier>`.

```json
{
  "titre": "Tu utilises *mal* ChatGPT ?",
  "vitesse": 1.06,
  "mots_cles": ["rôle", "objectif", "GUIDE"],
  "scenes": [ { "texte": "Phrase lue par la voix.", "<visuel>": { } } ],
  "tiktok": { "titre_tiktok": "…", "legende": "…", "sujet": "…", "accroche": "…" }
}
```

- `titre` : accroche affichée en grand au début (46 caractères max, 2 lignes). Les mots entre
  `*étoiles*` ressortent sur fond ambre.
- `vitesse` : débit de la voix (1.0 à 1.1).
- `mots_cles` : mots toujours surlignés en ambre dans les sous-titres.
- `texte` : ce que dit la voix. Nombres en lettres. Les sous-titres sont créés automatiquement,
  mot par mot, à partir de ce texte.

## Visuels (un seul par scène)

| Clé | Usage | Exemple |
|---|---|---|
| `icone` (+ `label` optionnel) | Idée simple, introduction | `"icone": "file-text", "label": "Méthode en 3 étapes"` |
| `carte` | Montrer un prompt qui se tape à l'écran | `"carte": {"type": "mauvais" \| "bon" \| "info", "etiquette": "Prompt flou", "texte": "…", "badge": "Trop vague"}` |
| `liste` | 2 à 5 points qui apparaissent quand la voix les prononce | `"liste": {"style": "coche" \| "croix", "titre": "…", "items": [{"texte": "Les dates", "mot": "dates"}]}` |
| `formule` | 2 à 5 mots-clés qui surgissent au moment où ils sont dits | `"formule": ["Rôle", "Objectif", "Public", "Format"]` |
| `produit` | Le guide en dernière scène, avec prix et appel à l'action | `"produit": {"titre": "IA Pratique", "sous_titre": "…", "detail": "Guide PDF · 19 pages", "prix": "12 000 CDF", "cta": "Écris GUIDE en commentaire", "mot_cta": "GUIDE"}` |

Pour `liste`, le champ `mot` doit être un mot réellement prononcé dans `texte` de la scène :
l'élément apparaît à ce moment précis. Les icônes viennent de Lucide
(`~/.cache/motivatio/lucide/package/icons/`, nom du fichier sans `.svg`).

## Ce que le moteur fait automatiquement

Voix française avec minutage phonème par phonème, sous-titres mot à mot avec le mot prononcé en
ambre, fond animé aux couleurs MOTIVATIO, transitions glissées, texte tapé à l'écran, coches et
badges animés, couverture du guide avec reflet, musique lo-fi qui s'efface sous la voix,
bruitages (transition, apparition, frappe, validation), mixage et normalisation à −14 LUFS.
