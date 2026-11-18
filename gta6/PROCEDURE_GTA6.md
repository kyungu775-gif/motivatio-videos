# Procedure — GTA 6 (international, English) on TikTok @motivativatio

This file is the instruction set for producing GTA 6 videos. It reuses the MOTIVATIO engine
(`scripts/make_video.py`) with `"theme": "gta6"` and `"langue": "en"`. MOTIVATIO files
(`scripts_videos/`, `videos/`, `journal/`, `PROCEDURE.md`) are not touched by this procedure.

## Mode: TEST (drafts only)

- Forbidden: publishing, scheduling for automatic publication, setting `draft` to false,
  editing or deleting any existing Metricool post, touching another GitHub repo, any paid service.
- Every Metricool post: `draft: true`, `autoPublish: false`, `tiktokData.isAigc: true`,
  `privacyOption: "PUBLIC_TO_EVERYONE"`. Serge validates each draft himself.

## Editorial line

- International English, simple sentences (B1 level), no slang that needs local knowledge.
- One verified idea per video. Every factual claim is checked the same day against an official
  source (Rockstar Newswire, support.rockstargames.com, Take-Two investor releases, PlayStation /
  Xbox official pages) and listed in the script's `sources` field with the date.
- Label clearly: confirmed fact / our analysis / rumour (rumours are never presented as facts;
  by default we do not cover them).
- Copyright: no Rockstar footage, artwork, logo, music or characters; no other creators' clips;
  no leaks; no spoilers (endings, story reveals, isolated cutscenes). Visuals = engine graphics only.
  Quotes from Rockstar text: one short quote (under 15 words) per video, attributed.
- Always show "UNOFFICIAL FAN NEWS" (engine brand line) and write "Unofficial fan channel · AI voice"
  in the caption. Never imply a partnership with Rockstar.
- No promises of money, followers or virality. No VPN or location tricks.

## Video format

- 4 to 6 scenes, 70 to 110 words (≈ 25 to 40 s). Scene 1 = hook (title with one `*highlighted*` word).
- Numbers may be written as digits in `texte` only if the `prononciation` field gives the spoken form
  (e.g. `"212": "two hundred twelve"`); `check.py` enforces this.
- Last scene = a question for the comments + "follow for verified GTA 6 news".
- File names: `gta6/scripts/AAAA-MM-JJ_en_slug.json` → `gta6/videos/AAAA-MM-JJ_en_slug.mp4`.
- Reference script: `gta6/scripts/2026-11-18_en_212gb-preload.json`.

## Steps

1. `git fetch origin gta6 && git checkout gta6 && git merge --ff-only FETCH_HEAD`; `bash scripts/setup.sh`.
2. Research: official sources first (see above). Note facts + URLs + date in `sources`.
3. Script: write the JSON, then `python3 scripts/check.py script <json>` until OK.
4. Render: `python3 scripts/make_video.py <json> <mp4>` then `python3 scripts/check.py video <mp4>`.
5. Visual check: `ffmpeg -i <mp4> -vf "fps=2/3,scale=216:-1,tile=8x3" -frames:v 1 planche.png`,
   look at it, fix any cut text or overlap.
6. GitHub: commit only `gta6/`, push branch `gta6`. Check the public link
   `https://raw.githubusercontent.com/kyungu775-gif/motivatio-videos/gta6/gta6/videos/<file>.mp4`
   returns 200 with the same size as the local file.
7. Metricool (brand `7625666`, timezone `Africa/Kinshasa`): check `getScheduledPosts` for the week,
   pick a free slot (best TikTok hour from `getBestTimeToPostByNetwork`, never the same hour as
   another post), create the draft with the raw link, `tiktokData.title` and caption; re-read and
   confirm `draft: true`.
8. Journal: one line per video in `gta6/journal/videos.csv` (with Metricool uuid). Commit and push.
9. Weekly review (with Metricool stats, 30 days): views, average watch time if available,
   likes, comments, shares, follower change. Write the review at the top of `gta6/journal/analyses.md`
   with 3 decisions. Never invent data.

## Metricool Free limits

20 **published** posts per month for the whole brand (drafts do not count) — shared with MOTIVATIO
while both run on the same account. 30 days of statistics history.
