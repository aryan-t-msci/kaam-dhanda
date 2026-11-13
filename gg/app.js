'use strict';

/* ------------------------------------------------------------------ config
   Every tunable number lives here. */
const CONFIG = {
  base: { easy: 100, medium: 150, hard: 200 },   // points for a correct answer with no help
  hintMult: 0.75,                                // the hint costs 25%
  moreMult: 0.75,                                // extra lines cost 25% (both together: 56%)
  help: {                                        // what each level allows
    easy: { hint: true, more: true }, medium: { hint: true, more: false }, hard: { hint: false, more: false },
  },
  matchThreshold: 0.8,                           // pre-selects Correct on the reveal; the host decides
  requireVerifiedVideo: false,                   // true = only songs with a verified official video are playable
  eras: { '90s': [1990, 1999], '00s': [2000, 2009], '10s': [2010, 2019], '20s': [2020, 2099] },
  singers: {                                     // display name -> spellings found in the CSV
    'Arijit Singh': ['arijit singh'], 'Shreya Ghoshal': ['shreya ghoshal'],
    'Sunidhi Chauhan': ['sunidhi chauhan'], 'KK': ['kk', 'krishnakumar kunnath'],
    'Shaan': ['shaan'], 'Sonu Nigam': ['sonu nigam'], 'Udit Narayan': ['udit narayan'],
  },
  storageKey: 'gaana-guess-v1',
};
const LEVELS = ['easy', 'medium', 'hard'];
const AVATARS = ['🎤', '🎧', '🎸', '🥁', '🎹', '🎷', '🎺', '🪕', '🦚', '🐯', '🐘', '🦜', '🌶️', '☕', '🪔', '🌙'];
const COLORS = ['#C2185B', '#0B6E6E', '#C77700', '#5B3FA8', '#2E7D32', '#B23A1E', '#1565C0', '#8E2470', '#00838F', '#6D4C41'];
const MAX_PLAYERS = COLORS.length;

let SONGS = [], BY_ID = {}, S = null, draft = null, tick = null;
const $app = document.getElementById('app');
const $bar = document.getElementById('bar');

/* ------------------------------------------------------------------ utils */
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const shuffle = a => { a = [...a]; for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; };
const pick = a => a[Math.floor(Math.random() * a.length)];
const clamp = (n, lo, hi) => Math.min(hi, Math.max(lo, Math.round(+n || 0)));
const cap = s => s[0].toUpperCase() + s.slice(1);
const fmt = s => `${Math.floor(Math.max(0, s) / 60)}:${String(Math.max(0, s) % 60).padStart(2, '0')}`;

const store = {
  load() { try { return JSON.parse(localStorage.getItem(CONFIG.storageKey)); } catch { return null; } },
  save() { try { localStorage.setItem(CONFIG.storageKey, JSON.stringify(S)); } catch { /* private mode: play on without saving */ } },
  clear() { try { localStorage.removeItem(CONFIG.storageKey); } catch { } },
};

/* RFC 4180 CSV: quoted fields may hold commas, quotes ("") and newlines. */
function parseCSV(text) {
  text = text.replace(/^\uFEFF/, '');
  const rows = []; let row = [], f = '', q = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (q) {
      if (c === '"') { if (text[i + 1] === '"') { f += '"'; i++; } else q = false; }
      else f += c;
    } else if (c === '"') q = true;
    else if (c === ',') { row.push(f); f = ''; }
    else if (c === '\n' || c === '\r') {
      if (c === '\r' && text[i + 1] === '\n') i++;
      row.push(f); rows.push(row); row = []; f = '';
    } else f += c;
  }
  if (f || row.length) { row.push(f); rows.push(row); }
  const [head, ...body] = rows;
  return body.filter(r => r.some(x => x.trim()))
    .map(r => Object.fromEntries(head.map((h, i) => [h.trim(), (r[i] ?? '').trim()])));
}

const normName = s => s.toLowerCase().replace(/[^a-z ]/g, '').replace(/\s+/g, ' ').trim();

function prepSong(r) {
  const year = +r.year;
  const singers = (r.singers || '').split(';').map(s => s.trim()).filter(Boolean);
  const sn = singers.map(normName);
  return {
    ...r, year, singers,
    era: Object.keys(CONFIG.eras).find(e => year >= CONFIG.eras[e][0] && year <= CONFIG.eras[e][1]),
    singerKeys: Object.keys(CONFIG.singers).filter(k => CONFIG.singers[k].some(a => sn.includes(a))),
    levels: (r.levels || '').split(';').map(s => s.trim()).filter(l => LEVELS.includes(l)),
    leads: (r.film_leads || '').split(';').map(s => s.trim()).filter(Boolean),
    snippets: Object.fromEntries([...LEVELS, 'easy_extra'].map(l => [l, (r['snippet_' + l] || '').split('||').map(s => s.trim()).filter(Boolean)
      .map(x => { const m = x.match(/^(\d+(?:\.\d+)?)\|([\s\S]*)$/); return m ? { t: +m[1], text: m[2].trim() } : { t: null, text: x }; })])),
    verified: !!r.youtube_id && r.yt_verified === 'y',
    playable: r.match_status === 'demo' || !CONFIG.requireVerifiedVideo || (!!r.youtube_id && r.yt_verified === 'y'),
  };
}

/* ------------------------------------------------------------------ guess matching
   Hinglish has no fixed spelling: toh/to, zindagi/jindagi, pyaar/pyar.
   Fold the common variants to one canonical form, then compare by edit distance. */
function canon(s) {
  return s.toLowerCase()
    .replace(/\(.*?\)|\[.*?\]/g, ' ')
    .replace(/[^a-z0-9 ]/g, '')
    .split(/\s+/).filter(Boolean)
    .map(w => w.replace(/ee/g, 'i').replace(/oo/g, 'u').replace(/w/g, 'v').replace(/ph/g, 'f')
      .replace(/q/g, 'k').replace(/z/g, 'j').replace(/(.)\1+/g, '$1').replace(/(.{2,})h$/, '$1'))
    .join('');
}
/* Edit distance that counts a swapped pair of letters (vidoe/video) as one typo, not two. */
function similarity(a, b) {
  if (!a.length || !b.length) return 0;
  let pp = null, prev = Array.from({ length: b.length + 1 }, (_, j) => j);
  for (let i = 1; i <= a.length; i++) {
    const cur = [i];
    for (let j = 1; j <= b.length; j++) {
      cur[j] = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
      if (pp && a[i - 1] === b[j - 2] && a[i - 2] === b[j - 1]) cur[j] = Math.min(cur[j], pp[j - 2] + 1);
    }
    pp = prev; prev = cur;
  }
  return 1 - prev[b.length] / Math.max(a.length, b.length);
}
const isMatch = (guess, title) => similarity(canon(guess), canon(title)) >= CONFIG.matchThreshold;

/* ------------------------------------------------------------------ game rules */
const points = (level, hint, more) =>
  Math.round(CONFIG.base[level] * (hint ? CONFIG.hintMult : 1) * (more ? CONFIG.moreMult : 1));
const pct = m => Math.round((1 - m) * 100);

const pool = (track, choice, level) => SONGS.filter(s =>
  !S.used.includes(s.id) && s.levels.includes(level) && s.snippets[level].length &&
  (track === 'era' ? s.era === choice : s.singerKeys.includes(choice)));

const choicesFor = track => Object.keys(track === 'era' ? CONFIG.eras : CONFIG.singers);
const scoreOf = (pi, round) => S.history.filter(h => h.pi === pi && (round == null || h.round === round))
  .reduce((a, h) => a + h.points, 0);

function hintText(song, t) {
  if (S.track === 'singer') return t.lead ? `The film stars ${t.lead}` : `Released in ${song.year}`;
  return { male: 'Sung by a male lead', female: 'Sung by a female lead', duet: 'A male and female duet' }[song.lead_gender]
    || `Sung by ${song.singers.length} singer${song.singers.length > 1 ? 's' : ''}`;
}

const ytUrl = (song, start = 0) => song.verified
  ? `https://www.youtube.com/watch?v=${encodeURIComponent(song.youtube_id)}${start ? `&t=${start}s` : ''}`
  : `https://www.youtube.com/results?search_query=${encodeURIComponent(`${song.title} ${song.album} official video`)}`;

/* Start the video ~3s before the lines the player saw (needs timestamped lyrics).
   yt_offset in the CSV corrects for videos with an intro the audio doesn't have. */
const videoStart = (song, snip) => snip.t == null ? 0 : Math.max(0, Math.floor(snip.t + (+song.yt_offset || 0) - 3));

/* ------------------------------------------------------------------ state transitions */
function go(phase) { S.phase = phase; store.save(); render(); window.scrollTo(0, 0); }

function newDraft(n = 3) {
  const av = shuffle(AVATARS);
  return { players: Array.from({ length: n }, (_, i) => ({ name: '', avatar: av[i] })), pool: av, rounds: 5, timer: 60 };
}

function readDraft() {
  document.querySelectorAll('.pname').forEach(el => { draft.players[+el.dataset.i].name = el.value; });
  const r = document.getElementById('rounds'), t = document.getElementById('timer');
  if (r) draft.rounds = clamp(r.value, 1, 50);
  if (t) draft.timer = clamp(t.value, 0, 600);
}

function resizePlayers(n) {
  readDraft();
  n = clamp(n, 1, MAX_PLAYERS);
  while (draft.players.length < n) {
    const taken = draft.players.map(p => p.avatar);
    draft.players.push({ name: '', avatar: draft.pool.find(a => !taken.includes(a)) || pick(AVATARS) });
  }
  draft.players.length = n;
  render();
}

function startGame() {
  readDraft();
  S = {
    players: draft.players.map((p, i) => ({ name: p.name.trim() || `Player ${i + 1}`, avatar: p.avatar, color: COLORS[i] })),
    rounds: draft.rounds, timer: draft.timer, round: 1, track: 'era',
    order: [], oi: 0, turn: null, used: [], history: [], phase: 'round',
  };
  go('round');
}

function beginRound() {
  const t = document.getElementById('timer');
  if (t) S.timer = clamp(t.value, 0, 600);
  S.order = shuffle(S.players.map((_, i) => i));   // fresh random order every round
  S.oi = 0;
  S.turn = { pi: S.order[0], choice: null, level: null };
  go('pick');
}

function startTurn() {
  const t = S.turn, list = pool(S.track, t.choice, t.level);
  if (!list.length) return;
  const song = pick(list);
  Object.assign(t, {
    songId: song.id, snippet: pick(song.snippets[t.level]), lead: song.leads.length ? pick(song.leads) : null,
    extra: t.level === 'easy' && song.snippets.easy_extra.length ? pick(song.snippets.easy_extra) : null,
    hint: false, more: false, answer: '', ok: false, deadline: S.timer ? Date.now() + S.timer * 1000 : 0,
  });
  S.used.push(song.id);                              // never repeats within a game, across both tracks
  go('play');
}

/* One answer per turn. Show answer (or time up) locks in whatever is typed and reveals.
   The fuzzy check only pre-selects Correct / Wrong; the host has the final say. */
function reveal(reason) {
  stopTimer();
  const t = S.turn, el = document.getElementById('guess');
  t.answer = el ? el.value.trim() : '';
  t.ok = !!t.answer && isMatch(t.answer, BY_ID[t.songId].title);
  t.reason = reason;
  S.history.push({ round: S.round, pi: t.pi, songId: t.songId, level: t.level, points: 0 });
  score();
  go('reveal');
}

function score() {
  const t = S.turn;
  t.points = t.ok ? points(t.level, t.hint, t.more) : 0;
  S.history[S.history.length - 1].points = t.points;
}

function verdictText(t) {
  const help = [t.hint && 'the hint', t.more && 'extra lines'].filter(Boolean).join(' and ');
  if (t.ok) return `Correct${help ? `, with ${help}` : ''}`;
  if (!t.answer) return t.reason === 'time' ? 'Time’s up, no answer entered' : 'No answer entered';
  return t.reason === 'time' ? 'Time’s up. Not this one' : 'Not this one';
}

/* Judging updates the page in place: a full re-render would restart the video. */
function judge(b) {
  S.turn.ok = b.dataset.v === '1';
  score(); store.save();
  document.querySelectorAll('[data-act=judge]').forEach(x =>
    x.setAttribute('aria-pressed', String(S.turn.ok === (x.dataset.v === '1'))));
  const v = document.getElementById('verdict');
  v.textContent = verdictText(S.turn);
  v.className = 'verdict ' + (S.turn.ok ? 'good' : 'miss');
  document.getElementById('pts').textContent = `+${S.turn.points}`;
  renderBar(S.phase);
}

function nextTurn() {
  S.oi++;
  if (S.oi >= S.order.length) return go(S.round >= S.rounds ? 'gameEnd' : 'roundEnd');
  S.turn = { pi: S.order[S.oi], choice: null, level: null };
  go('pick');
}

/* ------------------------------------------------------------------ timer */
function startTimer() {
  stopTimer();
  if (!S.timer || !S.turn.deadline) return;
  const step = () => {
    const left = Math.ceil((S.turn.deadline - Date.now()) / 1000);
    const el = document.getElementById('timer-left');
    if (el) { el.textContent = fmt(left); el.classList.toggle('low', left <= 10); }
    if (left <= 0) reveal('time');
  };
  step();
  tick = setInterval(step, 250);
}
function stopTimer() { clearInterval(tick); tick = null; }

/* ------------------------------------------------------------------ views */
const avatar = (p, cls = '') => `<span class="avatar ${cls}" style="--c:${p.color}" aria-hidden="true">${p.avatar}</span>`;

function viewSetup() {
  const saved = store.load();
  const canResume = saved && saved.phase && saved.phase !== 'setup';
  return `
  <section class="panel setup">
    <h1 class="brand">Gaana Guess</h1>
    <p class="lede">Read two lines. Name the song.</p>
    ${canResume ? `<div class="resume"><span>A saved game is waiting.</span><button class="btn" data-act="resume">Resume game</button></div>` : ''}
    <div class="field"><span id="np-label">Players</span>
      <div class="stepper" role="group" aria-labelledby="np-label">
        <button class="btn" data-act="pdec" aria-label="Remove a player" ${draft.players.length <= 1 ? 'disabled' : ''}>−</button>
        <output aria-live="polite">${draft.players.length}</output>
        <button class="btn" data-act="pinc" aria-label="Add a player" ${draft.players.length >= MAX_PLAYERS ? 'disabled' : ''}>+</button>
      </div></div>
    <ul class="players">${draft.players.map((p, i) => `
      <li>
        <button class="avatar big" data-act="avatar" data-i="${i}" style="--c:${COLORS[i]}" aria-label="Change avatar for player ${i + 1}">${p.avatar}</button>
        <input class="pname" data-i="${i}" maxlength="20" placeholder="Player ${i + 1}" value="${esc(p.name)}" aria-label="Name for player ${i + 1}">
      </li>`).join('')}
    </ul>
    <div class="row">
      <label class="field"><span>Rounds</span>
        <input type="number" id="rounds" min="1" max="50" value="${draft.rounds}"></label>
      <label class="field"><span>Seconds per turn</span>
        <input type="number" id="timer" min="0" max="600" step="5" value="${draft.timer}">
        <small>Set 0 to play without a timer</small></label>
    </div>
    <button class="btn primary big" data-act="start" ${SONGS.length ? '' : 'disabled'}>Start game</button>
    <p class="meta">${SONGS.length} songs loaded</p>
  </section>`;
}

function viewRound() {
  const track = (v, title, sub) => `
    <button class="track ${S.track === v ? 'on' : ''}" data-act="track" data-v="${v}" aria-pressed="${S.track === v}">
      <strong>${title}</strong><span>${sub}</span></button>`;
  return `
  <section class="panel">
    <h2>Round ${S.round} of ${S.rounds}</h2>
    <p>Pick the track for this round. Everyone plays it once, in a random order.</p>
    <div class="tracks">
      ${track('era', 'By era', '90s, 00s, 10s or 20s')}
      ${track('singer', 'By singer', 'Arijit, Shreya, Sunidhi, KK, Shaan, Sonu, Udit')}
    </div>
    <label class="field narrow"><span>Seconds per turn</span>
      <input type="number" id="timer" min="0" max="600" step="5" value="${S.timer}">
      <small>Set 0 to play without a timer</small></label>
    <button class="btn primary big" data-act="beginRound">Start round ${S.round}</button>
  </section>`;
}

function helpLabel(l) {
  const h = CONFIG.help[l];
  return h.hint && h.more ? 'Hint and extra lines available' : h.hint ? 'Hint available' : 'No help';
}

function viewPick() {
  const t = S.turn, p = S.players[t.pi];
  const chip = (act, v, label, n, on) =>
    `<button class="chip ${on ? 'on' : ''}" data-act="${act}" data-v="${esc(v)}" aria-pressed="${on}" ${n === 0 ? 'disabled' : ''}>
      ${label}${n != null ? `<small>${n} left</small>` : ''}</button>`;
  const ready = t.choice && t.level && pool(S.track, t.choice, t.level).length;
  return `
  <section class="panel">
    <p class="turnof">${avatar(p)} <span>${esc(p.name)}, you’re up</span></p>
    <h2>${S.track === 'era' ? 'Choose an era' : 'Choose a singer'}</h2>
    <div class="chips">${choicesFor(S.track).map(c =>
      chip('choice', c, esc(c), t.level ? pool(S.track, c, t.level).length : null, t.choice === c)).join('')}</div>
    <h2>Choose difficulty</h2>
    <div class="chips">${LEVELS.map(l =>
      chip('level', l, `${cap(l)} <em>${CONFIG.base[l]} points</em><span class="allows">${helpLabel(l)}</span>`,
        t.choice ? pool(S.track, t.choice, l).length : null, t.level === l)).join('')}</div>
    <button class="btn primary big" data-act="play" ${ready ? '' : 'disabled'}>Show my lines</button>
  </section>`;
}

function viewPlay() {
  const t = S.turn, p = S.players[t.pi], song = BY_ID[t.songId], h = CONFIG.help[t.level];
  const lines = snip => snip.text.split(' / ').map(l => `<span class="ln">${esc(l)}</span>`).join('');
  return `
  <section class="panel play">
    <div class="playhead">
      <p class="turnof">${avatar(p)} <span>${esc(p.name)}</span><span class="tag">${esc(t.choice)}</span><span class="tag">${cap(t.level)}</span></p>
      ${S.timer ? `<span id="timer-left" class="timer" role="timer">${fmt(S.timer)}</span>` : ''}
    </div>
    <blockquote class="lyric">${lines(t.snippet)}</blockquote>
    ${t.more ? `<blockquote class="lyric extra" aria-label="Extra lines">${lines(t.extra)}</blockquote>` : ''}
    ${t.hint ? `<p class="hint">${esc(hintText(song, t))}</p>` : ''}
    <label class="answer-field"><span>Your answer</span>
      <input id="guess" autocomplete="off" spellcheck="false" enterkeyhint="done" placeholder="Type the song name"></label>
    <p class="tries">A correct answer now scores ${points(t.level, t.hint, t.more)}.</p>
    <div class="actions">
      ${h.hint ? `<button class="btn" data-act="hint" ${t.hint ? 'disabled' : ''}>${t.hint ? 'Hint shown' : `Show a hint (−${pct(CONFIG.hintMult)}%)`}</button>` : ''}
      ${h.more && t.extra ? `<button class="btn" data-act="more" ${t.more ? 'disabled' : ''}>${t.more ? 'Extra lines shown' : `Show more lines (−${pct(CONFIG.moreMult)}%)`}</button>` : ''}
    </div>
    <button class="btn primary big" data-act="show">Show answer</button>
  </section>`;
}

function viewReveal() {
  const t = S.turn, p = S.players[t.pi], song = BY_ID[t.songId];
  const last = S.oi >= S.order.length - 1;
  const start = videoStart(song, t.snippet);
  return `
  <section class="panel reveal">
    <h2 class="title">${esc(song.title)}</h2>
    <p class="sub">${esc(song.album)}${song.year ? `, ${song.year}` : ''}</p>

    ${t.answer ? `<div class="judge">
      <h3>${esc(p.name)} answered</h3>
      <div class="judgerow"><span class="said">“${esc(t.answer)}”</span>
        <span class="seg" role="group" aria-label="Verdict">
          <button data-act="judge" data-v="1" aria-pressed="${t.ok}">Correct</button>
          <button data-act="judge" data-v="0" aria-pressed="${!t.ok}">Wrong</button>
        </span></div>
    </div>` : ''}
    <p id="verdict" class="verdict ${t.points ? 'good' : 'miss'}">${verdictText(t)}</p>
    <p id="pts" class="pts">+${t.points}</p>

    ${song.verified ? `
    <div class="video"><iframe src="https://www.youtube-nocookie.com/embed/${encodeURIComponent(song.youtube_id)}?start=${start}&autoplay=1&rel=0"
      title="${esc(song.title)}, official video" allow="autoplay; encrypted-media; picture-in-picture" allowfullscreen></iframe></div>
    <p class="credit">Official upload${song.yt_channel ? ` by ${esc(song.yt_channel)}` : ''}, played via YouTube.
      <a href="${ytUrl(song, start)}" target="_blank" rel="noopener">Open on YouTube</a></p>`
    : song.match_status === 'demo' ? '<p class="credit">Demo song: no video.</p>'
    : `<p class="credit"><a class="btn yt" href="${ytUrl(song)}" target="_blank" rel="noopener">Find it on YouTube</a></p>`}

    <dl>
      <dt>Singers</dt><dd>${esc(song.singers.join(', '))}</dd>
      <dt>Music</dt><dd>${esc(song.composer || 'Not listed')}</dd>
      ${song.leads.length ? `<dt>Starring</dt><dd>${esc(song.leads.join(', '))}</dd>` : ''}
    </dl>
    <button class="btn primary big" data-act="next">${last ? 'See the round scores' : `Next: ${esc(S.players[S.order[S.oi + 1]].name)}`}</button>
  </section>`;
}

function board(showRound) {
  const rows = S.players.map((p, i) => ({ ...p, total: scoreOf(i), now: scoreOf(i, S.round) }))
    .sort((a, b) => b.total - a.total);
  return `
  <table class="board">
    <thead><tr><th scope="col">Rank</th><th scope="col">Player</th>${showRound ? '<th scope="col" class="num">This round</th>' : ''}<th scope="col" class="num">Total</th></tr></thead>
    <tbody>${rows.map(r => `
      <tr class="${r.total > 0 && r.total === rows[0].total ? 'lead' : ''}">
        <td>${1 + rows.filter(x => x.total > r.total).length}</td>
        <td>${avatar(r, 'sm')} ${esc(r.name)}</td>
        ${showRound ? `<td class="num">+${r.now}</td>` : ''}
        <td class="num">${r.total}</td></tr>`).join('')}
    </tbody>
  </table>`;
}

function viewRoundEnd() {
  return `
  <section class="panel">
    <h2>Scores after round ${S.round} of ${S.rounds}</h2>
    ${board(true)}
    <button class="btn primary big" data-act="nextRound">Set up round ${S.round + 1}</button>
  </section>`;
}

function viewGameEnd() {
  const top = Math.max(...S.players.map((_, i) => scoreOf(i)));
  const winners = S.players.filter((_, i) => scoreOf(i) === top);
  return `
  <section class="panel">
    <h1 class="brand">${top > 0 ? `${winners.map(w => esc(w.name)).join(' & ')} ${winners.length > 1 ? 'tie' : 'wins'}` : 'Game over'}</h1>
    ${board(true)}
    <div class="actions">
      <button class="btn primary" data-act="extraRound">Play one more round</button>
      <button class="btn ghost" data-act="newGame">New game</button>
    </div>
  </section>`;
}

function renderBar(phase) {
  if (!S || phase === 'setup') { $bar.innerHTML = ''; return; }
  $bar.innerHTML = `
    <span class="barbrand">Gaana Guess</span>
    <span class="barround">Round ${S.round}/${S.rounds}, ${S.track === 'era' ? 'by era' : 'by singer'}</span>
    <ul class="mini">${S.players.map((p, i) => `<li title="${esc(p.name)}">${avatar(p, 'sm')}<b>${scoreOf(i)}</b></li>`).join('')}</ul>
    <button class="btn link quit" data-act="newGame">Quit</button>`;
}

function render() {
  const views = { setup: viewSetup, round: viewRound, pick: viewPick, play: viewPlay, reveal: viewReveal, roundEnd: viewRoundEnd, gameEnd: viewGameEnd };
  const phase = S ? S.phase : 'setup';
  $app.innerHTML = views[phase]();
  renderBar(phase);
  if (phase === 'play') { startTimer(); document.getElementById('guess')?.focus(); } else stopTimer();
}

/* ------------------------------------------------------------------ events */
/* Taking help re-renders the play screen; keep what the player already typed. */
function keepTyped(fn) {
  const typed = document.getElementById('guess')?.value || '';
  fn(); store.save(); render();
  const el = document.getElementById('guess');
  if (el) { el.value = typed; el.focus(); }
}

const actions = {
  resume: () => { S = store.load(); render(); },
  avatar: b => { readDraft(); const p = draft.players[+b.dataset.i]; p.avatar = AVATARS[(AVATARS.indexOf(p.avatar) + 1) % AVATARS.length]; render(); },
  pdec: () => resizePlayers(draft.players.length - 1),
  pinc: () => resizePlayers(draft.players.length + 1),
  start: startGame,
  track: b => { S.track = b.dataset.v; store.save(); render(); },
  beginRound,
  choice: b => { S.turn.choice = b.dataset.v; store.save(); render(); },
  level: b => { S.turn.level = b.dataset.v; store.save(); render(); },
  play: startTurn,
  hint: () => keepTyped(() => { S.turn.hint = true; }),
  more: () => keepTyped(() => { S.turn.more = true; }),
  show: () => reveal('shown'),
  judge,
  next: nextTurn,
  nextRound: () => { S.round++; go('round'); },
  extraRound: () => { S.rounds++; S.round++; go('round'); },
  newGame: () => {
    if (S && S.phase !== 'gameEnd' && !confirm('Quit this game? Scores will be cleared.')) return;
    stopTimer(); store.clear(); S = null; draft = newDraft(); render();
  },
};

document.addEventListener('click', e => {
  const b = e.target.closest('[data-act]');
  if (b && !b.disabled) actions[b.dataset.act]?.(b);
});
document.addEventListener('keydown', e => {
  if (e.key === 'Enter' && e.target.id === 'guess') reveal('shown');
});

/* ------------------------------------------------------------------ boot */
(async function init() {
  try {
    const res = await fetch('songs.csv', { cache: 'no-cache' });
    if (!res.ok) throw new Error(res.status);
    SONGS = parseCSV(await res.text()).map(prepSong).filter(s => s.id && s.title && s.playable);
    BY_ID = Object.fromEntries(SONGS.map(s => [s.id, s]));
  } catch {
    $app.innerHTML = `
      <section class="panel">
        <h2>The song list didn’t load</h2>
        <p>Browsers block loading <code>songs.csv</code> when <code>index.html</code> is opened straight from your files.
        In the project folder run <code>python -m http.server</code>, then open <code>http://localhost:8000</code>.
        On GitHub Pages it loads on its own.</p>
      </section>`;
    return;
  }
  draft = newDraft();
  render();
})();
