# Procédure hebdomadaire — TikTok @motivativatio

Ce fichier est la consigne suivie par la tâche automatique de Claude chaque semaine.
Pour changer le fonctionnement, on modifie ce fichier : la tâche le relit à chaque lancement.

## Mode actuel : VALIDATION (brouillons uniquement)

- Période : du 26/10/2026 au 08/11/2026, puis jusqu'à nouvel ordre de Serge.
- **Interdit** : publier, programmer pour publication, mettre `draft` à false, supprimer ou modifier
  un post Metricool existant, modifier un autre dépôt GitHub que `kyungu775-gif/motivatio-videos`,
  utiliser un service payant.
- Chaque vidéo est créée dans Metricool avec : `draft: true`, `autoPublish: false`,
  `privacyOption: "PUBLIC_TO_EVERYONE"`, `isAigc: true`. Serge valide lui-même dans Metricool.

## Ligne éditoriale

- Langue : français simple, tutoiement, phrases courtes. Public francophone, notamment d'Afrique centrale.
- Thèmes (par ordre de priorité) : intelligence artificielle utile au quotidien, productivité,
  astuces numériques (téléphone, applications gratuites, sécurité en ligne), motivation et habitudes.
- Chaque vidéo apporte **une seule idée concrète et applicable tout de suite**.
- Originalité : ne jamais copier un texte existant. Vérifier `journal/videos.csv` pour ne pas
  répéter un sujet déjà traité.
- Exactitude : toute affirmation factuelle (fonction d'une application, chiffre, prix) est vérifiée
  par une recherche web le jour même. En cas de doute, reformuler sans l'affirmation.
- À éviter : conseils médicaux, financiers ou juridiques personnalisés ; promesses d'argent facile ;
  personnes réelles ; politique ; marques présentées de façon trompeuse ; contenu protégé.

## Format d'une vidéo

- 4 à 6 scènes, 75 à 130 mots au total (≈ 25 à 45 s).
- Scène 1 = accroche de 10 mots maximum (question ou affirmation surprenante).
- Dernière scène = appel à l'action, à varier (s'abonner, commenter, enregistrer, partager).
- Écrire les nombres en lettres dans le texte lu (« deux minutes »), pas dans le titre.
- Une icône Lucide par scène, cohérente avec le texte (liste : `~/.cache/motivatio/lucide/package/icons/`).
- Fichier : `scripts_videos/AAAA-MM-JJ_slug.json`, au format de `scripts_videos/exemple.json`.

## Étapes de la tâche

1. **Accès** : rattacher le dépôt `kyungu775-gif/motivatio-videos` avec l'accès en écriture, le cloner,
   puis lancer `bash scripts/setup.sh`.
2. **Analyse** : lire les statistiques TikTok Metricool des 30 derniers jours
   (vidéos : TKPO01, TKPO03, TKPO05, TKPO07, TKPO08, TKPO09, TKPO10, TKPO13, TKPO15 ;
   compte : TKEV07, TKEV08). Ajouter en tête de `journal/analyses.md` un bilan daté : meilleures et
   pires vidéos, hypothèses, 3 décisions concrètes pour la semaine. S'il n'y a pas encore de données,
   l'écrire simplement.
3. **Idées** : faire quelques recherches web sur l'actualité IA, productivité et numérique,
   choisir 5 sujets en tenant compte du bilan et de `journal/videos.csv`.
4. **Scripts** : écrire les 5 fichiers JSON, puis `python3 scripts/check.py script <fichier>`
   pour chacun ; corriger tant que le contrôle échoue.
5. **Rendu** : `python3 scripts/make_video.py <json> videos/<même-nom>.mp4`, puis
   `python3 scripts/check.py video <mp4>`.
6. **GitHub** : ajouter uniquement `videos/`, `scripts_videos/` et `journal/`, faire un commit, pousser.
   Vérifier chaque lien public :
   `https://raw.githubusercontent.com/kyungu775-gif/motivatio-videos/main/videos/<fichier>.mp4`
   (code 200 et taille identique au fichier local).
7. **Metricool** : marque `7625666`, fuseau `Africa/Kinshasa`. Pour chaque vidéo, créer un brouillon
   TikTok avec le lien public, la légende et le titre TikTok du script. Dates des brouillons : la
   semaine suivante, sur les meilleurs créneaux donnés par Metricool, une vidéo par jour.
8. **Journal** : ajouter une ligne par vidéo dans `journal/videos.csv` (avec l'uuid Metricool),
   faire un commit et pousser.
9. **Rapport** à Serge (court, en français) : les 5 titres, le lien Metricool de chaque brouillon,
   le résumé du bilan, et tout problème rencontré.

## En cas de problème

Ne pas insister au-delà d'une nouvelle tentative. Terminer les vidéos qui peuvent l'être,
puis signaler clairement dans le rapport l'étape bloquée et le message d'erreur exact.

## Limites Metricool Free

20 publications **publiées** par mois au maximum (les brouillons ne comptent pas),
30 jours d'historique de statistiques, 1 marque.
