# morning-news

Private morning news podcast. Feed: https://niklashedstrom.github.io/morning-news-cdf2ca961739/feed.xml

Add an episode: `python3 scripts/build_feed.py add <mp3> <YYYY-MM-DD> <headlines.txt>`

## Swedish audio (GitHub Actions)

The morning-news task pushes `inbox/YYYY-MM-DD.txt` (script, one paragraph per line) and
`inbox/YYYY-MM-DD.headlines.txt`. `.github/workflows/tts.yml` synthesizes it with
`scripts/tts_sv.py` (edge-tts, `sv-SE-SofieNeural`), adds the episode to the feed, moves the
script to `transcripts/` and pushes. Run the workflow manually with no date for a voice test
(MP3 uploaded as an artifact), or with a date to rebuild that episode from `inbox/`.
