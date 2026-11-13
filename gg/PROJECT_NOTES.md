# Gaana Guess — project notes (portable context for any session / LLM)

## Goal
Bollywood song-guessing party game, 5–10 players. Hindi songs only.
Players see a 2–3 line Hinglish lyric snippet and name the song.

## Game spec (agreed)
- Setup: 1–10 players (target 5–10), name + emoji avatar each, number of rounds, seconds per turn (0 = off).
- Round = every player plays once; play order reshuffled every round.
- Track chosen per round for the whole group; switchable between rounds; scores carry over.
  - Track 1 "By era": 90s / 00s / 10s / 20s (1990–99, 2000–09, 2010–19, 2020+).
  - Track 2 "By singer": Arijit Singh, Shreya Ghoshal, Sunidhi Chauhan, KK, Shaan, Sonu Nigam, Udit Narayan.
    Credited lead only (duets count for both singers; chorus doesn't).
- Each player picks era/singer + difficulty on their own turn.
- One answer per turn (3-guess mechanic removed). Points = base[level] × 0.75 if hint × 0.75 if extra lines.
  Base: easy 100, medium 150, hard 200.
- Help by level: easy = hint + "more lines" (antara lines, never hook/title); medium = hint only; hard = none.
- Hint: Track 1 = lead gender (male / female / duet). Track 2 = one lead actor of the film.
- Show answer (or time up) locks in the typed answer and reveals. Reveal shows typed answer beside the
  correct one with Correct / Wrong; fuzzy match (Hinglish folding + Damerau edit distance) only pre-selects.
- Reveal: title, film/album, year, singers, composer, film leads. Verified official video is embedded from
  ~3s before the snippet (LRCLIB timestamps + yt_offset); otherwise a YouTube search link.
- No song repeats within a game across both tracks. "Play one more round" at game end.
- Game state saved in localStorage (survives refresh).

## Data rules
- All songs famous. Difficulty = popularity tier + which lyric section is shown.
- Minimum 30 playable songs per (era × level) and (singer × level); curate ~40 to absorb LRCLIB misses.
- A famous song may sit in 2 levels (different lyric section) to cover thin buckets (KK, Shaan, 20s).
- Snippets: 2–3 lines (3 preferred). easy = mukhda non-hook lines; medium = first antara; hard = later antaras.
- Lyrics: Claude never writes or edits lyric text. The script fetches them; `--review` exports numbered
  lines; Claude returns line ranges only (selections.json), which the build applies. Musixmatch API is
  the planned fallback source if the first real run leaves buckets short.
  Hook (repeated / contains title / <3 words) never shown.
- YouTube: embedding needs no key; the key only finds/verifies IDs. Web search can't find YouTube IDs
  reliably (tested). For now: link fallback, requireVerifiedVideo=false. Target: only songs with a verified official upload are playable (lyrical / audio uploads fine; jukeboxes,
  reprises, covers, remixes, trailers rejected). Verified = channel on OFFICIAL_CHANNELS allowlist,
  found via YouTube Data API at build time (free key, ~100 searches/day, resumable), or a manual
  youtube_id with yt_verified=y.
- Duets count for both singers in Track 2, but the unique song total must stay large (report shows it).

## Architecture
- Static site: index.html + style.css + app.js + songs.csv. No build step; GitHub Pages from branch root.
- build_lyrics.py (stdlib), 3 stages: LRCLIB → lyrics_cache.json; YouTube search → youtube_cache.json
  (raw top-10, so allowlist edits re-select for free); build → songs.csv with snippets only. Caches git-ignored.
- Gaana / JioSaavn not used (no official API, no CORS, unofficial wrappers decrypt streams).

## Song list (songs_input.csv)
- 388 unique songs, metadata only (title, film, year, singers, composer, film leads), written by Claude from
  its own knowledge: spot-check before relying on details. Variety singers in 90s–10s (Kumar Sanu, Lucky Ali,
  Javed Ali, Roop Kumar Rathod, Neeraj Shridhar, Atif Aslam, Mohit Chauhan, Rahat Fateh Ali Khan, Kailash Kher,
  Abhijeet, Hariharan, Sukhwinder Singh, Papon...).
- Tiers: A biggest hits = easy;medium;hard, B big hits = easy;medium, C known-but-less-heard = medium;hard.
  B also plays hard in the 90s, the 20s and for Udit. Every Sonu, KK, Shaan and Sunidhi song plays at all
  levels (fewer famous songs available).
- Known thin bucket: Shaan (22 songs max). Real per-bucket counts come from the build report after LRCLIB.

## Deploy
- .github/workflows/deploy.yml: on push to main, runs build_lyrics.py on GitHub (LRCLIB reachable there),
  caches lyrics in the Actions cache, deploys index.html/app.js/style.css/songs.csv to Pages.
  Pages source must be "GitHub Actions". Optional secret YT_API_KEY enables official-video lookup.

## Constraints
- Simplest code that works; no unnecessary dependencies.
- CSV UTF-8; Excel users save as "CSV UTF-8".

## Status
- [x] build_lyrics.py: transliteration, matching, cache, snippets, bucket coverage report (tested offline)
- [x] Frontend v3 (single answer, per-level help, judge on reveal, video or link), scripted playthrough 19/19
- [x] Build: review export + selections.json, easy_extra pool, transliteration 31/31 regression words
- [x] Demo songs.csv (invented data) so the game runs now
- [x] songs_input.csv: 388 songs across 90s–20s, variety singers included
- [x] GitHub Actions build + deploy (tested with a mocked full-size run: 388 songs, error-tolerant)
- [ ] YouTube verification via build (needs user's API key)
- [ ] First real run on GitHub: read the build report; add songs to any bucket under 30 (Shaan expected)
