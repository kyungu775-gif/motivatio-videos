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
- Un seul visuel par scène : une icône Lucide (`icone`), une carte de texte (`carte`, pour montrer un
  prompt à l'écran : type `mauvais`, `bon` ou `info`), ou le visuel du guide (`produit`).
  Liste des icônes : `~/.cache/motivatio/lucide/package/icons/`. Modèle complet :
  `scripts_videos/2026-10-24_prompt-flou-vs-precis.json`.
- Fichier : `scripts_videos/AAAA-MM-JJ_slug.json`.

## Campagne en cours : guide IA PRATIQUE

- Produit : « IA PRATIQUE — 30 prompts pour gagner du temps », guide PDF de 19 pages,
  10 prompts études, 10 emploi, 10 projets. Prix : 12 000 CDF.
  Lien officiel, le seul à utiliser : https://vcixxduw.mychariow.co/prd_2un4krca
- Chaque semaine, **2 vidéos sur 5** sont des vidéos de campagne. Les 3 autres sont 100 % conseils.
- Vidéo de campagne : d'abord une astuce gratuite, complète et utilisable sans acheter ;
  le guide n'apparaît que dans la dernière scène (visuel `produit`), une seule fois, sans pression.
  Champ Metricool obligatoire en plus : `tiktokData.commercialContentOwnBrand: true`.
- Interdit : faux témoignages, faux chiffres de ventes, promesse d'emploi, de note ou de revenu,
  fausse urgence (« dernières places », « prix qui augmente demain »).
- Ne jamais décrire le contenu précis du guide au-delà de ce qui est écrit ci-dessus.
- Appel à l'action : « Écris GUIDE en commentaire ».
  **lien_bio_confirme : non** — tant que cette ligne dit « non », ne jamais écrire ni dire
  « lien dans la bio ». Serge la passera à « oui » quand le lien du profil TikTok sera vérifié.

## Étapes de la tâche

1. **Accès** : si `/home/claude/motivatio-videos` existe déjà, faire `git fetch origin main` puis
   `git merge --ff-only FETCH_HEAD`. Sinon, rattacher le dépôt `kyungu775-gif/motivatio-videos`
   (accès en écriture) et le cloner. Puis lancer `bash scripts/setup.sh`.
2. **Analyse** : lire les statistiques TikTok Metricool des 30 derniers jours
   (vidéos : TKPO01, TKPO03, TKPO05, TKPO07, TKPO08, TKPO09, TKPO10, TKPO13, TKPO15 ;
   compte : TKEV07, TKEV08, TKEV09). Ajouter en tête de `journal/analyses.md` un bilan daté :
   meilleures et pires vidéos, vidéos de campagne comparées aux vidéos conseils, hypothèses,
   3 décisions concrètes pour la semaine. Ajouter une ligne à `journal/suivi_commercial.csv` avec les
   colonnes mesurables par Metricool ; laisser vides les colonnes que seul Serge connaît (clics,
   visites Chariow, commandes, chiffre d'affaires). Ne jamais deviner ni estimer une vente.
   S'il n'y a pas encore de données, l'écrire simplement.
3. **Idées** : lire avec getScheduledPosts les posts déjà présents du mardi au samedi de la semaine.
   Nombre de vidéos à créer = 5 moins le nombre de posts déjà présents sur ces jours (jamais moins
   de 0), pour rester sous la limite de Metricool Free. Faire quelques recherches web sur l'actualité
   IA, productivité et numérique, puis choisir les sujets en tenant compte du bilan, de
   `journal/videos.csv` et de la répartition campagne / conseils ci-dessus.
4. **Scripts** : écrire les 5 fichiers JSON, puis `python3 scripts/check.py script <fichier>`
   pour chacun ; corriger tant que le contrôle échoue.
5. **Rendu** : `python3 scripts/make_video.py <json> videos/<même-nom>.mp4`, puis
   `python3 scripts/check.py video <mp4>`.
6. **GitHub** : ajouter uniquement `videos/`, `scripts_videos/` et `journal/`, faire un commit, pousser.
   Vérifier chaque lien public :
   `https://raw.githubusercontent.com/kyungu775-gif/motivatio-videos/main/videos/<fichier>.mp4`
   (code 200 et taille identique au fichier local).
7. **Metricool** : marque `7625666`, fuseau `Africa/Kinshasa`. Pour chaque vidéo, créer un brouillon
   TikTok avec le lien public, la légende et le titre TikTok du script. Dates des brouillons : du
   mardi au samedi de la semaine en cours, une vidéo par jour, sur le meilleur créneau du jour donné
   par Metricool (getBestTimeToPostByNetwork). Champs obligatoires : `draft: true`,
   `autoPublish: false`, `tiktokData.title`, `tiktokData.isAigc: true`.
   Après création, relire avec getScheduledPosts et vérifier que chaque brouillon a `draft: true`.
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
