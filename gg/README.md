# Gaana Guess

A pass-the-laptop Bollywood song quiz for 1–10 players. Read the lines, name the song,
then watch the official video from the moment those lines are sung.
Plain HTML, CSS and JavaScript: no build step, no dependencies, runs on GitHub Pages as-is.

## Play it locally
```
python -m http.server
```
Open http://localhost:8000. (Opening `index.html` directly won't work: browsers block
loading `songs.csv` from `file://`.)

## Put it on GitHub Pages (builds the real song list for you)
This folder lives in `gg/` of the repo; the workflow lives at the repo root in
`.github/workflows/deploy.yml` (GitHub only runs workflows from there).

1. Upload this folder's files into `gg/`.
2. **Settings → Pages → Source: GitHub Actions.**
3. **Actions → Build songs and deploy** runs on every push to `gg/`, or on demand (Run workflow). It fetches lyrics (LRCLIB) and film facts (Wikipedia) on GitHub's servers,
   builds `songs.csv`, and publishes only the four game files.
4. The run summary shows the build report: lyric matches, hint coverage, songs per bucket.

## Demo round
"Try the demo round" plays **13 extra songs that are not part of the main game**: one per era
(90s, 00s, 10s, 20s) and one per Track 2 singer, difficulty rotating easy, medium, hard.
Nothing is random (same songs, lines and turn order on every device and every visit).

- Songs: `demo_input.csv` (built to `demo.csv`). The main game only ever reads `songs.csv`.
- Each slot (`demo_slot` 1–13) has a main song (`demo_rank` 1) and, for most slots, a backup (rank 2),
  used only if the main song's lyrics aren't found. A slot with no usable song is skipped.
- Slot order and levels: `DEMO_SLOTS` at the top of `app.js`.

## Hints
- `hint_song` (in `songs_input.csv`): a hand-written fact about the song itself. Edit freely;
  the build drops any hint that contains a word of the song's title.
- `hint_film` (built): the most story-specific sentence of the film's Wikipedia intro (who it follows,
  where it's set, what it's based on), with every name of the film removed, e.g. "Starring Shah Rukh
  Khan and Kajol, the film follows Raj and Simran, two young non-resident Indians who fall in love
  during a vacation through Europe with their friends." Box-office and award sentences are skipped.
- The game shows the song hint if there is one, else the film hint, else a basic fallback.

## Build the song list locally (optional)
The bundled `songs.csv` is demo data (invented titles and lines) so the game works out of the box.

1. Fill `songs_input.csv` (columns explained at the top of `build_lyrics.py`).
2. Build: `python build_lyrics.py songs_input.csv songs.csv`
3. Read the report: review `check` lyric matches, and the per-bucket table (anything under 30 is flagged).
4. Commit `songs.csv`. Cache files and `review/` hold full lyrics and stay on your machine (git-ignored).

### Choosing which lines are shown (optional, per batch)
`python build_lyrics.py --review songs_input.csv` writes `review/batch_NN.txt`: each song's lines
numbered, hooks marked `[H]`, and the automatic picks. Section choices go into `selections.json`
as line ranges (2–3 lines each, never touching a hook); the next build uses them instead of the
automatic picks. Invalid ranges are reported and fall back to the automatic pick.

If you edit a CSV in Excel, save as **CSV UTF-8 (Comma delimited)**.

## How scoring works
One answer per turn. Show answer (or the timer) locks in what's typed; the reveal shows it beside
the right answer and the host taps Correct or Wrong.

| Level | Points | Help allowed |
|---|---|---|
| Easy | 100 | Hint and extra lines (each −25%; both = 56) |
| Medium | 150 | Hint (−25% = 113) |
| Hard | 200 | None |

All numbers are in the `CONFIG` block at the top of `app.js`.

## Credits
Lyric excerpts: LRCLIB, a community-contributed lyrics database. Film facts: adapted from Wikipedia (CC BY-SA). Songs and videos belong to their
labels; the reveal links to them on YouTube.
Personal, non-commercial use.
