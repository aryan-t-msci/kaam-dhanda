#!/usr/bin/env python3
"""
build_lyrics.py - one-time build of songs.csv for Gaana Guess (stdlib only).

    python build_lyrics.py songs_input.csv songs.csv                 # build
    YT_API_KEY=... python build_lyrics.py songs_input.csv songs.csv  # build + find official videos
    python build_lyrics.py --review songs_input.csv                  # export numbered lyrics for review

Review loop: --review writes review/batch_NN.txt (numbered lines, hooks marked, current auto picks).
Line ranges chosen for each song go in selections.json; the build uses them instead of the auto picks:
    {"song_id": {"easy": "4-6", "easy_extra": "15-17", "medium": "10-12,13-14", "hard": "22-24"}}
Ranges are 2-3 lines; comma-separate several to give the game a choice.

Every network stage caches raw results; every decision is re-made from the cache on each
run, so editing input rows or the channel allowlist never costs another API call.
  1. LYRICS   LRCLIB -> lyrics_cache.json        (full lyrics: local only, git-ignored)
  2. YOUTUBE  YouTube Data API search -> youtube_cache.json (top 10 results per song)
  3. FILMS    Wikipedia article summary per film/album -> wiki_cache.json, for an automatic hint
  4. BUILD    caches -> songs.csv: Hinglish snippets (2-3 lines, timestamped) per level,
              official video chosen from allowlisted channels, film-fact hint with titles removed.
              Full lyrics never reach songs.csv.

Input columns: id, title, album, year, singers (;), lead_gender (male|female|duet), composer,
  film_leads (;), levels (; of easy|medium|hard), youtube_id, yt_verified (y|n), yt_offset, duration_s,
  hint_song (optional hand-written hint; must not contain words of the song's title)
  A row with youtube_id filled and yt_verified=y is trusted as-is and never searched.
"""
import csv, html, json, os, re, sys, time, unicodedata
import urllib.error, urllib.parse, urllib.request
from collections import Counter
from difflib import SequenceMatcher

LRCLIB = "https://lrclib.net/api"
YT_SEARCH = "https://www.googleapis.com/youtube/v3/search"
UA = "gaana-guess/1.0 (personal, non-commercial)"      # LRCLIB asks clients to identify themselves
LYRICS_CACHE, YT_CACHE, SELECTIONS = "lyrics_cache.json", "youtube_cache.json", "selections.json"
WIKI_CACHE = "wiki_cache.json"
WIKI_API = "https://en.wikipedia.org/w/api.php"
WIKI_SUMMARY = "https://en.wikipedia.org/api/rest_v1/page/summary/"
SNIP_KEYS = ("easy", "easy_extra", "medium", "hard")
OUT_COLS = ["snippet_easy", "snippet_easy_extra", "snippet_medium", "snippet_hard", "hint_film", "yt_channel", "yt_title",
            "lrclib_id", "lrclib_track", "lrclib_artist", "match_score", "match_status"]
OK, CHECK = 0.80, 0.60                                  # lyric match thresholds
LEVELS = ("easy", "medium", "hard")
MIN_PER_BUCKET = 30
ERAS = {"90s": (1990, 1999), "00s": (2000, 2009), "10s": (2010, 2019), "20s": (2020, 2099)}
SINGERS = {"Arijit Singh": ["arijit singh"], "Shreya Ghoshal": ["shreya ghoshal"],
           "Sunidhi Chauhan": ["sunidhi chauhan"], "KK": ["kk", "krishnakumar kunnath"],
           "Shaan": ["shaan"], "Sonu Nigam": ["sonu nigam"], "Udit Narayan": ["udit narayan"],
           "Alka Yagnik": ["alka yagnik"], "Kumar Sanu": ["kumar sanu"]}

# Official label channels. A video counts as verified only if its channel title is here.
# The build prints unlisted channels it saw; check one on YouTube before adding it.
OFFICIAL_CHANNELS = {
    "T-Series", "Sony Music India", "Zee Music Company", "YRF", "Saregama Music",
    "Tips Official", "Eros Now Music", "Shemaroo Filmi Gaane", "Times Music",
    "Universal Music India", "Venus", "Speed Records", "Junglee Music",
}
# Versions that aren't the song players know, or whose timestamps won't line up.
NOT_THE_SONG = re.compile(r"\b(reprise|unplugged|cover|remix|lo-?fi|slowed|reverb|8d|teaser|trailer|"
                          r"promo|making|jukebox|karaoke|instrumental|mashup|live|version)\b", re.I)

# ---------------------------------------------------------------- Devanagari -> Hinglish
CONS = {"क": "k", "ख": "kh", "ग": "g", "घ": "gh", "ङ": "n", "च": "ch", "छ": "chh", "ज": "j",
        "झ": "jh", "ञ": "n", "ट": "t", "ठ": "th", "ड": "d", "ढ": "dh", "ण": "n", "त": "t",
        "थ": "th", "द": "d", "ध": "dh", "न": "n", "प": "p", "फ": "ph", "ब": "b", "भ": "bh",
        "म": "m", "य": "y", "र": "r", "ल": "l", "व": "v", "श": "sh", "ष": "sh", "स": "s",
        "ह": "h", "\ue000": "gy"}                       # \ue000 = placeholder for ज्ञ
NUKTA = {"क": "q", "ख": "kh", "ग": "g", "ज": "z", "ड": "d", "ढ": "dh", "फ": "f"}
VOWELS = {"अ": "a", "आ": "aa", "इ": "i", "ई": "ee", "उ": "u", "ऊ": "oo", "ए": "e", "ऐ": "ai",
          "ओ": "o", "औ": "au", "ऋ": "ri", "ऑ": "o", "ऍ": "e"}
MATRAS = {"ा": "aa", "ि": "i", "ी": "ee", "ु": "u", "ू": "oo", "े": "e", "ै": "ai", "ो": "o",
          "ौ": "au", "ृ": "ri", "ॉ": "o", "ॅ": "e"}
VIRAMA, NUKTA_SIGN, ANUSVARA, CHANDRABINDU, VISARGA = "्", "़", "ं", "ँ", "ः"
DEVA_RUN = re.compile(r"[\u0900-\u097f\ue000]+")


COMMON = {"में": "mein", "वो": "woh", "वह": "woh", "यह": "yeh"}   # spellings convention beats rules


def _word(w):
    """One Devanagari word -> casual Hinglish. Units are [consonant, vowel, is_schwa, coda]."""
    if w in COMMON:
        return COMMON[w]
    w = unicodedata.normalize("NFD", w).replace("ज्ञ", "\ue000")   # NFD splits precomposed nukta letters
    units, i = [], 0
    while i < len(w):
        c, nxt = w[i], (w[i + 1] if i + 1 < len(w) else "")
        if c in CONS:
            r = CONS[c]
            if nxt == NUKTA_SIGN:
                r, i = NUKTA.get(c, r), i + 1
                nxt = w[i + 1] if i + 1 < len(w) else ""
            if nxt in MATRAS:
                units.append([r, MATRAS[nxt], False, ""]); i += 1
            elif nxt == VIRAMA:
                units.append([r, "", False, ""]); i += 1
            else:
                units.append([r, "a", True, ""])           # inherent schwa
        elif c in VOWELS:
            units.append(["", VOWELS[c], False, ""])
        elif c == ANUSVARA and units:
            units[-1][3] = "n"                           # a real nasal consonant: forms a cluster
        elif c == CHANDRABINDU and units:
            units[-1][3] = "~"                           # nasalised vowel only: no consonant
        elif c == VISARGA and units:
            units[-1][3] += "h"
        i += 1
    if not units:
        return ""
    n = len(units)
    # 1) word-final schwa deletion: दिल -> dil, इश्क़ -> ishq
    if n > 1 and units[-1][2] and not units[-1][3]:
        units[-1][1:3] = ["", False]
    # 2) medial schwa deletion, right to left, in V C(a) C V context: समझना -> samajhna.
    #    Anusvara before it is a consonant, so deleting would make a 3-consonant cluster (ज़िंदगी stays
    #    zindagi); chandrabindu only nasalises the vowel, so deletion still applies (चाँदनी -> chaandni).
    for k in range(n - 2, 0, -1):
        u, prev, nxt = units[k], units[k - 1], units[k + 1]
        if u[2] and not u[3] and prev[1] and not prev[3].startswith("n") and nxt[1]:
            u[1:3] = ["", False]
    # 3) Hinglish convention: long vowels short at word end (mera, meri, tu), kept before nasal (hoon, haan)
    last = units[-1]
    if not last[2]:                                      # consonant + matra, or a bare vowel (आई -> aai)
        if last[1] == "ee":
            last[1] = "i"
        elif last[1] in ("aa", "oo") and not last[3]:
            last[1] = {"aa": "a", "oo": "u"}[last[1]]
    out = []
    for k, (c, v, _, coda) in enumerate(units):
        coda = coda.replace("~", "n")
        if coda.startswith("n") and k + 1 < n and units[k + 1][0][:1] in ("p", "b", "m"):
            coda = "m" + coda[1:]                          # अंबर -> ambar
        out.append(c + v + coda)
    return "".join(out)


def to_hinglish(text):
    if not text:
        return text
    text = text.replace("॥", ".").replace("।", ".")
    text = text.translate(str.maketrans("०१२३४५६७८९", "0123456789"))
    return DEVA_RUN.sub(lambda m: _word(m.group()), text)   # timestamps / Latin text untouched

# ---------------------------------------------------------------- matching
def norm(s):
    s = to_hinglish(s or "").lower()
    s = re.sub(r"\(.*?\)|\[.*?\]|\b(feat|ft)\b.*", " ", s)  # drop (From "Film"), feat. ...
    return " ".join(re.sub(r"[^a-z0-9 ]+", " ", s).split())


def sim(a, b):
    return SequenceMatcher(None, norm(a), norm(b)).ratio()


def artist_sim(a, b):
    """Bollywood tracks credit several singers differently per source: best pairwise match wins."""
    split = lambda s: [x for x in re.split(r",|&|/|\band\b", s or "") if x.strip()]
    return max((sim(x, y) for x in split(a) for y in split(b)), default=0.0)


def fold(s):
    """Spelling-insensitive key: chaandni == chandni, poochha == pucha."""
    return re.sub(r"(.)\1+", r"\1", norm(s).replace("ee", "i").replace("oo", "u"))


class QuotaExceeded(Exception):
    pass


def get_json(url, headers=None):
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code == 403 and "quota" in e.read().decode("utf-8", "ignore").lower():
                raise QuotaExceeded()
            if e.code != 429 and e.code < 500:
                raise
        except (urllib.error.URLError, TimeoutError):
            pass
        time.sleep(2 * 2 ** attempt)                      # back off: 2s, 4s, 8s
    return None


def api(path, **params):
    q = urllib.parse.urlencode({k: v for k, v in params.items() if v not in (None, "")})
    return get_json(f"{LRCLIB}/{path}?{q}")


def split_list(s):
    return [x.strip() for x in (s or "").split(";") if x.strip()]


def load_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_json(path, obj):
    with open(path + ".tmp", "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(path + ".tmp", path)                      # atomic: never a half-written file


def save_csv(path, cols, rows):
    with open(path + ".tmp", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, restval="", extrasaction="ignore")
        w.writeheader(); w.writerows(rows)
    os.replace(path + ".tmp", path)

# ---------------------------------------------------------------- stage 1: lyrics
def lookup(row):
    t, singers, dur, album = row.get("title"), split_list(row.get("singers")), row.get("duration_s"), row.get("album")
    a, lead = ", ".join(singers), (singers[0] if singers else "")
    cands = []
    if album and dur:                                    # exact-signature endpoint
        hit = api("get", track_name=t, artist_name=lead, album_name=album, duration=dur)
        cands = [hit] if hit else []
    if not cands:
        cands = api("search", track_name=t, artist_name=lead) or []
    if not cands:                                        # free text catches artist-credit mismatches
        cands = api("search", q=f"{t} {lead}") or []
    best, best_s = None, 0.0
    for c in cands[:15]:
        ts, as_ = sim(t, c.get("trackName")), artist_sim(a, c.get("artistName"))
        # Film name disambiguates the many Bollywood songs that share a title
        s = (0.5 * ts + 0.3 * as_ + 0.2 * sim(album, c.get("albumName"))) if album and c.get("albumName") \
            else (0.6 * ts + 0.4 * as_)
        if dur and c.get("duration") and abs(float(dur) - c["duration"]) > 10:
            s -= 0.15
        if not c.get("plainLyrics"):
            s -= 0.30
        if c.get("syncedLyrics"):
            s += 0.02                                    # timestamps let the video start at the lines
        if s > best_s:
            best, best_s = c, s
    return best, best_s


def lyrics_stage(rows, cache):
    todo = [r for r in rows if r.get("id") and r["id"] not in cache]
    for i, row in enumerate(todo, 1):
        try:
            best, s = lookup(row)
        except Exception as e:                           # one bad response must not stop an unattended build
            print(f"  lyrics [{i}/{len(todo)}] error      {row.get('title')}: {e}")
            continue
        if best and s >= CHECK:
            cache[row["id"]] = {"status": "ok" if s >= OK else "check", "score": round(s, 2),
                                "id": best.get("id"), "track": best.get("trackName", ""),
                                "artist": best.get("artistName", ""),
                                "plain": best.get("plainLyrics") or "", "synced": best.get("syncedLyrics") or ""}
        status = cache.get(row["id"], {}).get("status", "not_found")   # not_found isn't cached: retried next run
        print(f"  lyrics [{i}/{len(todo)}] {status:<10} {row.get('title')}")
        if i % 10 == 0:
            save_json(LYRICS_CACHE, cache)
        time.sleep(0.4)                                  # polite to a free, volunteer-run API
    save_json(LYRICS_CACHE, cache)

# ---------------------------------------------------------------- stage 2: youtube
def youtube_stage(rows, cache, key):
    todo = [r for r in rows if r.get("id") and r["id"] not in cache
            and not (r.get("youtube_id") and r.get("yt_verified") == "y")]
    print(f"\nYouTube: {len(todo)} songs to search (each search costs 100 of the 10,000 free daily units)")
    for i, row in enumerate(todo, 1):
        q = f"{row.get('title')} {row.get('album')} song"
        url = YT_SEARCH + "?" + urllib.parse.urlencode(
            {"part": "snippet", "type": "video", "maxResults": 10, "q": q,
             "regionCode": "IN", "relevanceLanguage": "hi", "key": key})
        try:
            res = get_json(url)
        except QuotaExceeded:
            print("  Daily YouTube quota used up. Progress is saved: run again tomorrow to continue.")
            break
        cache[row["id"]] = [{"video": it["id"]["videoId"], "channel": html.unescape(it["snippet"]["channelTitle"]),
                             "title": html.unescape(it["snippet"]["title"])}
                            for it in (res or {}).get("items", []) if it.get("id", {}).get("videoId")]
        print(f"  youtube [{i}/{len(todo)}] {len(cache[row['id']])} results  {row.get('title')}")
        if i % 10 == 0:
            save_json(YT_CACHE, cache)
    save_json(YT_CACHE, cache)


def pick_video(row, items):
    """Best official upload of this song: allowlisted channel, title names the song, not a variant."""
    best, best_s, t, film = None, 0.0, fold(row.get("title")), fold(row.get("album"))
    for it in items:
        if it["channel"] not in OFFICIAL_CHANNELS or NOT_THE_SONG.search(it["title"]):
            continue
        vt = fold(it["title"])
        s = 0.7 if t and t in vt else 0.7 * SequenceMatcher(None, t, vt).ratio()
        s += 0.3 if film and film in vt else 0.0
        if s > best_s:
            best, best_s = it, s
    return best if best_s >= 0.6 else None

# ---------------------------------------------------------------- stage 3: film facts (Wikipedia)
def film_key(row):
    return f"{row.get('album', '')}|{row.get('year', '')}"


def wiki_stage(rows, cache):
    """One Wikipedia lookup per film/album: search, then take the article summary if it is about
    a film or album from that year. Misses are cached too (delete the key to retry)."""
    films = sorted({film_key(r) for r in rows if r.get("album")} - set(cache))
    print(f"\nFilm facts: {len(films)} films/albums to look up on Wikipedia")
    for i, key in enumerate(films, 1):
        album, year = key.rsplit("|", 1)
        found = {}
        try:
            res = get_json(WIKI_API + "?" + urllib.parse.urlencode(
                {"action": "query", "list": "search", "srsearch": f"{album} {year} film", "srlimit": 3,
                 "format": "json"})) or {}
            for hit in res.get("query", {}).get("search", []):
                summ = get_json(WIKI_SUMMARY + urllib.parse.quote(hit["title"].replace(" ", "_"))) or {}
                text = summ.get("extract", "")
                if year in text and re.search(r"\b(film|soundtrack|album)\b", text) and \
                        SequenceMatcher(None, fold(album), fold(hit["title"])).ratio() >= 0.5:
                    found = {"page": hit["title"], "extract": text}
                    break
        except Exception as e:
            print(f"  film [{i}/{len(films)}] error {album}: {e}")
            continue
        cache[key] = found
        if i % 20 == 0:
            save_json(WIKI_CACHE, cache)
        time.sleep(0.1)
    save_json(WIKI_CACHE, cache)


def title_words(title):
    return {w for w in fold(title).split() if len(w) >= 4}


def leaks(hint, title):
    return bool(title_words(title) & set(fold(hint).split()))


STORY = re.compile(r"\b(follows|story|revolves|centres|centers|about|based on|remake|adaptation|set in|set against|tells|depicts|chronicles|narrates|plot|journey|falls? in love|struggles?)\b", re.I)
STATS = re.compile(r"\b(box office|grossed|grossing|crore|budget|award|Filmfare|National Film|nominat|released (on|in|theatrically)|premiered|commercial|critical|critics|soundtrack|cinematography|edited by|principal photography)\b", re.I)


def strip_names(text, row, wiki):
    """Remove every name of the film from a sentence so the hint never gives the title away."""
    text = re.sub(r",?\s*(also|better|simply|popularly) known (as|by)[^,]*,", ",", text)
    page = wiki.get("page", "")
    for name in sorted({row.get("album", ""), page, re.sub(r"\s*\(.*\)$", "", page)}, key=len, reverse=True):
        if name:
            text = re.sub(re.escape(name), "the film", text, flags=re.I)
    text = re.sub(r"\bthe film,?\s+the film\b", "the film", text, flags=re.I)
    return re.sub(r"\s{2,}", " ", text).replace(" ,", ",").strip(" ,")


def film_hint(wiki, row):
    """
    The most story-specific sentence of the film's Wikipedia intro: who it follows, where it is set,
    what it is based on. Box-office, award and release sentences score down. Falls back to the
    first sentence (genre, year, director) only when no sentence tells the story.
    """
    text = (wiki or {}).get("extract", "")
    if not text:
        return ""
    text = re.sub(r"\s*\([^)]*\)", "", text)                          # (transl. ...) first, so 'transl.' can't split
    sentences = [x.strip().rstrip(".") for x in re.split(r"(?<=[a-z0-9])\.\s+(?=[A-Z])", text) if x.strip()]
    title = row.get("title", "")

    def score(i, x):
        sc = 3 * len(STORY.findall(x)) - 4 * len(STATS.findall(x))
        sc += 1 if 50 <= len(x) <= 230 else -1
        return sc - (2 if i == 0 else 0)                              # the first sentence is the generic one

    ranked = sorted(enumerate(sentences), key=lambda ix: score(*ix), reverse=True)
    for i, x in ranked:
        if score(i, x) < 1 and i != 0:
            continue
        h = strip_names(x, row, wiki)
        if i == 0:                                                    # generic fallback: "From a 1995 ... film by ..."
            h = re.sub(r"^\W*(the film\s+)?(is|was)\s+(an?|the)\s+", lambda m: f"From {m.group(3)} ", h, flags=re.I)
            h = re.sub(r",?\s*(and\s+)?(co-)?produced by\b.*$", "", h)
            if not h.lower().startswith("from "):
                continue
        h = re.sub(r"\bIndian Hindi[- ]language\b", "Hindi", h)
        if len(h) > 240:                                              # long: drop a leading "Set in ..., during ...," clause
            m = re.match(r"^[^,]{0,140}(,[^,]{0,140})?,\s+(the film|it)\s", h, flags=re.I)
            if m:
                h = h[m.start(2):]
        h = h[0].upper() + h[1:] if h else h
        if len(h) > 260:                                              # still long: cut at a clause boundary
            cut = max(h.rfind(", ", 0, 260), h.rfind(" and ", 0, 260))
            h = h[:cut] if cut > 90 else h[:260].rsplit(" ", 1)[0]
        if h and not leaks(h, title):
            return h + "."
    return ""

# ---------------------------------------------------------------- stage 4: build
LRC_LINE = re.compile(r"\[(\d+):(\d+(?:\.\d+)?)\](.*)")


def structure(plain, synced, title):
    """
    Number the song's lines and mark hooks.
      lines   = [(n, stanza_index, text)], n is 1-based over non-empty lines (the review numbering)
      hook(n) = line repeated anywhere, containing the title, or under 3 words -> never shown
      times   = folded line text -> first timestamp in the synced lyrics
    """
    stanzas = [[l.strip() for l in st.splitlines() if l.strip()] for st in re.split(r"\n\s*\n", plain.strip())]
    stanzas = [st for st in stanzas if st]
    if len(stanzas) == 1:                                # no blank lines in source: chunk by 4
        flat = stanzas[0]
        stanzas = [flat[i:i + 4] for i in range(0, len(flat), 4)]
    lines = [(0, si, l) for si, st in enumerate(stanzas) for l in st]
    lines = [(n, si, l) for n, (_, si, l) in enumerate(lines, 1)]
    counts = Counter(fold(l) for _, _, l in lines)
    t = fold(title)
    hooks = {n for n, _, l in lines if counts[fold(l)] > 1 or (t and t in fold(l)) or len(norm(l).split()) < 3}
    times = {}
    for row in (synced or "").splitlines():
        m = LRC_LINE.match(row.strip())
        if m:
            times.setdefault(fold(m.group(3)), int(m.group(1)) * 60 + float(m.group(2)))
    return lines, hooks, times


def auto_picks(lines, hooks, per_level=3):
    """
    Default sections when a song hasn't been reviewed. Windows of 2-3 consecutive non-hook lines:
      easy       = mukhda (first stanza)
      easy_extra = antara lines only, so the extra help is never the hook or the title
      medium     = first antara;   hard = later antaras
    """
    windows, run, last_si = [], [], None
    for n, si, _ in lines + [(None, None, None)]:
        if n is not None and n not in hooks and si == last_si:
            run.append(n)
        else:
            windows += [(last_si, run[k:k + 3]) for k in range(0, len(run), 3) if len(run[k:k + 3]) >= 2]
            run = [n] if n is not None and n not in hooks else []
        last_si = si

    def pool(cond):
        ws = [w for si, w in windows if cond(si)]
        return [w for w in ws if len(w) == 3] or ws      # prefer 3-line snippets
    easy = pool(lambda si: si == 0) or pool(lambda si: si <= 1)
    medium = pool(lambda si: si in (1, 2))
    hard = pool(lambda si: si >= 3) or pool(lambda si: si >= 2)
    medium = medium or easy or hard
    hard = hard or medium
    extra = [w for w in pool(lambda si: si >= 1) if w not in easy]
    spread = lambda xs: xs[::max(1, len(xs) // per_level)][:per_level]
    return {k: spread(v) for k, v in zip(SNIP_KEYS, (easy, extra, medium, hard))}


def parse_ranges(spec, n_lines, hooks=frozenset()):
    """'4-6,10-11' -> [[4,5,6],[10,11]]; rejects ranges outside the song, not 2-3 lines long, or touching a hook."""
    out = []
    for part in str(spec or "").split(","):
        m = re.fullmatch(r"\s*(\d+)\s*-\s*(\d+)\s*", part)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            if 1 <= a < b <= n_lines and 2 <= b - a + 1 <= 3 and not hooks & set(range(a, b + 1)):
                out.append(list(range(a, b + 1)))
    return out


def snippet_columns(plain, synced, title, chosen=None):
    """Snippet strings per level: 'seconds|line / line / line' joined by ' || '."""
    lines, hooks, times = structure(plain, synced, title)
    text = {n: l for n, _, l in lines}
    picks, bad = auto_picks(lines, hooks), []
    for k in SNIP_KEYS:
        if chosen and chosen.get(k):
            r = parse_ranges(chosen[k], len(lines), hooks)
            if r:
                picks[k] = r
            else:
                bad.append(k)

    def fmt(w):
        sec = times.get(fold(text[w[0]]))
        return (f"{sec:.1f}|" if sec is not None else "") + " / ".join(text[n] for n in w)
    return {k: " || ".join(fmt(w) for w in picks[k]) for k in SNIP_KEYS}, bad


def export_review(rows, lyr, size=25):
    """Numbered lyrics for choosing sections by line number. Local only (review/ is git-ignored)."""
    os.makedirs("review", exist_ok=True)
    songs = [r for r in rows if lyr.get(r.get("id"), {}).get("plain")]
    for b in range(0, len(songs), size):
        path = f"review/batch_{b // size + 1:02d}.txt"
        with open(path, "w", encoding="utf-8") as f:
            f.write("Pick 2-3 line ranges per level by line number. [H] = hook, never shown.\n"
                    "easy: well-known, not the hook | easy_extra: antara, not easily solved | "
                    "medium: less-heard | hard: deep cut\n\n")
            for r in songs[b:b + size]:
                c = lyr[r["id"]]
                lines, hooks, _ = structure(to_hinglish(c["plain"]), "", r.get("title", ""))
                auto = auto_picks(lines, hooks)
                f.write(f"=== {r['id']} | {r.get('title')} | {r.get('album')} ({r.get('year')}) | levels: {r.get('levels')}\n")
                f.write("auto: " + "  ".join(f"{k}={','.join(f'{w[0]}-{w[-1]}' for w in auto[k])}" for k in SNIP_KEYS) + "\n")
                last = None
                for n, si, l in lines:
                    if last is not None and si != last:
                        f.write("\n")
                    f.write(f"{n:>3}{' [H]' if n in hooks else '    '} {l}\n")
                    last = si
                f.write("\n")
        print("wrote", path)


def build_stage(rows, lyr, yt, sel, wiki):
    unlisted = Counter()
    for row in rows:
        row["hint_film"] = film_hint(wiki.get(film_key(row)), row)
        if row.get("hint_song") and leaks(row["hint_song"], row.get("title", "")):
            print(f"  hint_song for {row.get('id')} contains a word of its title; not used")
            row["hint_song"] = ""
        c = lyr.get(row.get("id"))
        if c:
            row.update(lrclib_id=c["id"], lrclib_track=c["track"], lrclib_artist=c["artist"],
                       match_score=f"{c['score']:.2f}", match_status=c["status"])
            if c["plain"]:
                cols, bad = snippet_columns(to_hinglish(c["plain"]), to_hinglish(c.get("synced", "")),
                                            row.get("title", ""), sel.get(row["id"]))
                row.update({f"snippet_{k}": v for k, v in cols.items()})
                if bad:
                    print(f"  selections.json: invalid range for {row['id']} {bad}; auto pick used")
        else:
            row["match_status"] = "not_found"
        if row.get("youtube_id") and row.get("yt_verified") == "y":
            continue                                     # trusted manual entry
        items = yt.get(row.get("id"), [])
        unlisted.update(it["channel"] for it in items if it["channel"] not in OFFICIAL_CHANNELS)
        v = pick_video(row, items)
        row.update(youtube_id=v["video"] if v else "", yt_channel=v["channel"] if v else "",
                   yt_title=v["title"] if v else "", yt_verified="y" if v else "n")
    return unlisted


REQUIRE_VERIFIED_VIDEO = False                          # keep in step with requireVerifiedVideo in app.js


def playable(r, lvl=None):
    video = not REQUIRE_VERIFIED_VIDEO or (r.get("youtube_id") and r.get("yt_verified") == "y")
    ok = video and r.get("match_status") in ("ok", "check")
    return ok and (lvl is None or (r.get(f"snippet_{lvl}") and lvl in split_list(r.get("levels"))))


def coverage(rows):
    sn = lambda r: [" ".join(re.sub(r"[^a-z ]", "", s.lower()).split()) for s in split_list(r.get("singers"))]
    print(f"\nPlayable songs per bucket (minimum {MIN_PER_BUCKET}" + (", verified video required" if REQUIRE_VERIFIED_VIDEO else "") + "):")
    for label, groups in (("Era", ERAS), ("Singer", SINGERS)):
        print(f"\n  {label:<16}" + "".join(f"{l:>8}" for l in LEVELS) + "   unique")
        for g in groups:
            if label == "Era":
                lo, hi = ERAS[g]
                inb = lambda r: r.get("year", "").isdigit() and lo <= int(r["year"]) <= hi
            else:
                inb = lambda r, g=g: any(a in sn(r) for a in SINGERS[g])
            cells = [sum(1 for r in rows if inb(r) and playable(r, l)) for l in LEVELS]
            uniq = sum(1 for r in rows if inb(r) and playable(r))
            print(f"  {g:<16}" + "".join(f"{n:>7}{'!' if n < MIN_PER_BUCKET else ' '}" for n in cells) + f"{uniq:>9}")
    total = [r for r in rows if playable(r)]
    duets = sum(1 for r in total if sum(any(a in sn(r) for a in v) for v in SINGERS.values()) > 1)
    print(f"\n  Unique playable songs: {len(total)} of {len(rows)} ({duets} count for two Track 2 singers)")
    print("  ! = below minimum. Add songs to that bucket or widen their 'levels'.")


def main(src, dst=None, review=False):
    with open(src, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        sys.exit("Input CSV has no rows.")
    lyr, yt, sel, wiki = load_json(LYRICS_CACHE), load_json(YT_CACHE), load_json(SELECTIONS), load_json(WIKI_CACHE)
    print("Lyrics:")
    lyrics_stage(rows, lyr)
    if review:
        return export_review(rows, lyr)
    key = os.environ.get("YT_API_KEY")
    if key:
        youtube_stage(rows, yt, key)
    else:
        print("\nYouTube: skipped (set YT_API_KEY to find official videos). Unverified songs get a YouTube search link.")
    wiki_stage(rows, wiki)
    unlisted = build_stage(rows, lyr, yt, sel, wiki)
    print(f"Reviewed sections used for {sum(1 for r in rows if r.get('id') in sel)} songs; the rest use auto picks.")
    cols = list(rows[0].keys()) + [c for c in OUT_COLS if c not in rows[0]]
    save_csv(dst, cols, rows)
    print("\nLyrics match:", dict(Counter(r.get("match_status", "") for r in rows)))
    print("Videos verified:", sum(r.get("yt_verified") == "y" for r in rows), "of", len(rows))
    print("Hints: song-specific", sum(bool(r.get("hint_song")) for r in rows), "| film facts",
          sum(bool(r.get("hint_film")) for r in rows), "| neither", sum(not (r.get("hint_song") or r.get("hint_film")) for r in rows))
    if unlisted:
        print("Channels seen but not on the allowlist (verify before adding to OFFICIAL_CHANNELS):")
        for ch, n in unlisted.most_common(12):
            print(f"  {n:>4}  {ch}")
    print("Wrong match? Delete that id from the cache file, fix the input row, re-run.")
    coverage(rows)


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) == 2 and args[0] == "--review":
        main(args[1], review=True)
    elif len(args) == 2:
        main(args[0], args[1])
    else:
        sys.exit(__doc__)
