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

## Put it on GitHub Pages
1. Push this folder to a GitHub repo (files at the repo root).
2. Repo **Settings → Pages → Build and deployment**: Source = *Deploy from a branch*,
   Branch = `main`, folder = `/ (root)`. Save.
3. After a minute it's live at `https://<username>.github.io/<repo>/`.

## Build the real song list
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

### Official videos (optional)
Without a key, the reveal shows a "Find it on YouTube" link. To embed the official video instead:
get a free YouTube Data API key (Google Cloud Console → enable **YouTube Data API v3** → Credentials),
then build with `YT_API_KEY=your_key python build_lyrics.py songs_input.csv songs.csv`
(PowerShell: `$env:YT_API_KEY="your_key"; python ...`). About 100 songs a day fit the free quota;
progress is saved. Only allowlisted label channels count. To make verified video a hard requirement,
set `requireVerifiedVideo: true` in `app.js` and `REQUIRE_VERIFIED_VIDEO = True` in the build script.
If a video starts in the wrong place, set `yt_offset` (seconds, can be negative) and rebuild.

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
Lyric excerpts: LRCLIB, a community-contributed lyrics database. Songs and videos belong to their
labels and are played from official YouTube channels through YouTube's embedded player.
Personal, non-commercial use.
