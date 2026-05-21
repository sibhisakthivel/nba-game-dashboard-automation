// ============================================================
// DIMER // TERMINAL — wired to live Supabase backend
// Flow: TEAM → PLAYER → STAT → FILTERS → VISUALIZATION
// ============================================================
const { useState, useMemo, useEffect, useRef } = React;

// ---------------------------------------------------------------------------
// Constants (stat definitions, categories, briefing templates)
// ---------------------------------------------------------------------------

const STAT_CATEGORIES = [
  { key: "scoring",    label: "Scoring",    glyph: "▲", stats: ["pts", "tpm"] },
  { key: "playmaking", label: "Playmaking", glyph: "↗", stats: ["ast", "tov"] },
  { key: "rebounding", label: "Rebounding", glyph: "◇", stats: ["reb", "oreb", "dreb"] },
  { key: "combos",     label: "Combos",     glyph: "⧉", stats: ["pa", "pr", "ra", "pra"] },
  { key: "defense",    label: "Defense",    glyph: "◆", stats: ["stl", "blk"] },
];

const STAT_TYPES = [
  { key: "pts",  short: "PTS",     label: "Points",           default: 20.5 },
  { key: "tpm",  short: "3PM",     label: "3-Pointers Made",  default: 1.5  },
  { key: "ast",  short: "AST",     label: "Assists",          default: 5.5  },
  { key: "tov",  short: "TOV",     label: "Turnovers",        default: 2.5  },
  { key: "reb",  short: "REB",     label: "Rebounds",         default: 6.5  },
  { key: "oreb", short: "OREB",    label: "Off Rebounds",     default: 1.5  },
  { key: "dreb", short: "DREB",    label: "Def Rebounds",     default: 5.5  },
  { key: "stl",  short: "STL",     label: "Steals",           default: 1.5  },
  { key: "blk",  short: "BLK",     label: "Blocks",           default: 0.5  },
  { key: "pa",   short: "PTS+AST", label: "Points + Assists", default: 30.5, composite: ["pts","ast"] },
  { key: "pr",   short: "PTS+REB", label: "Points + Rebounds",default: 30.5, composite: ["pts","reb"] },
  { key: "ra",   short: "REB+AST", label: "Rebounds + Assists",default:10.5, composite: ["reb","ast"] },
  { key: "pra",  short: "PRA",     label: "Pts + Reb + Ast",  default: 40.5, composite: ["pts","reb","ast"] },
];

const BRIEFING_TEMPLATES = {
  consistent: {
    thinking: [
      "Loading {{player}} corpus...",
      "Indexing windows · L5 / L10 / L20 / season...",
      "Computing variance band...",
      "Cross-referencing {{stat}} distribution...",
      "Composing analyst brief...",
    ],
    sections: [
      { h: "DIRECTIVE", rows: [
        ["Target",  "{{playerFull}} · {{team}} · {{pos}}"],
        ["Stat",    "{{statLabel}} · reference line {{line}}"],
        ["Sample",  "{{sampleN}} games · window {{window}}"],
      ]},
      { h: "TREND", rows: [
        ["Hit rate",   "<g>{{hitL10}}%</g> over last 10"],
        ["Median",     "{{median}} · vs line {{line}}"],
        ["Volatility", "<g>low</g> · σ {{sigma}}"],
      ]},
      { h: "SPLITS", rows: [
        ["Home",  "<g>{{hitHome}}%</g> · {{nHome}} games"],
        ["Away",  "{{hitAway}}% · {{nAway}} games"],
        ["W / L", "{{hitWin}}% W · {{hitLoss}}% L"],
      ]},
      { h: "NOTES", rows: [
        ["Streak",    "<g>{{streak}}</g> consecutive games over line"],
        ["L5 vs L20", "<g>{{deltaL5L20}}</g> trending"],
      ]},
      { h: "READ", rows: [
        ["Distribution", "<pur>{{distribution}}</pur>"],
        ["Conviction",   "{{confidence}}/100"],
      ]},
    ],
    confidence: 78,
    readout: "stable upper-tail. line sits below median by σ ≈ {{deltaSigma}}",
  },
  fading: {
    thinking: [
      "Loading {{player}} corpus...",
      "Indexing windows · L5 / L10 / L20 / season...",
      "Detecting regression vectors...",
      "Composing analyst brief...",
    ],
    sections: [
      { h: "DIRECTIVE", rows: [
        ["Target",  "{{playerFull}} · {{team}} · {{pos}}"],
        ["Stat",    "{{statLabel}} · reference line {{line}}"],
        ["Sample",  "{{sampleN}} games · window {{window}}"],
      ]},
      { h: "TREND", rows: [
        ["Hit rate",   "<r>{{hitL10}}%</r> over last 10"],
        ["Median",     "{{median}} · vs line {{line}}"],
        ["Volatility", "elevated · σ {{sigma}}"],
      ]},
      { h: "SPLITS", rows: [
        ["Home",  "{{hitHome}}% · {{nHome}} games"],
        ["Away",  "<r>{{hitAway}}%</r> · {{nAway}} games"],
        ["W / L", "{{hitWin}}% W · {{hitLoss}}% L"],
      ]},
      { h: "NOTES", rows: [
        ["Cold streak", "<r>{{coldStreak}}</r> recent games under line"],
        ["L5 vs L20",   "<r>{{deltaL5L20}}</r> regressing"],
      ]},
      { h: "READ", rows: [
        ["Distribution", "<pur>{{distribution}}</pur>"],
        ["Conviction",   "{{confidence}}/100"],
      ]},
    ],
    confidence: 48,
    readout: "line sits above median. expect regression unless usage shifts.",
  },
  neutral: {
    thinking: [
      "Loading {{player}} corpus...",
      "Indexing windows · L5 / L10 / L20 / season...",
      "Cross-referencing {{stat}} distribution...",
      "Composing analyst brief...",
    ],
    sections: [
      { h: "DIRECTIVE", rows: [
        ["Target",  "{{playerFull}} · {{team}} · {{pos}}"],
        ["Stat",    "{{statLabel}} · reference line {{line}}"],
        ["Sample",  "{{sampleN}} games · window {{window}}"],
      ]},
      { h: "TREND", rows: [
        ["Hit rate",   "<y>{{hitL10}}%</y> over last 10"],
        ["Median",     "{{median}} · vs line {{line}}"],
        ["Volatility", "moderate · σ {{sigma}}"],
      ]},
      { h: "SPLITS", rows: [
        ["Home",  "{{hitHome}}% · {{nHome}} games"],
        ["Away",  "{{hitAway}}% · {{nAway}} games"],
        ["W / L", "{{hitWin}}% W · {{hitLoss}}% L"],
      ]},
      { h: "NOTES", rows: [
        ["Variance",  "results split — neither tail dominates"],
        ["L5 vs L20", "{{deltaL5L20}} neutral drift"],
      ]},
      { h: "READ", rows: [
        ["Distribution", "<pur>{{distribution}}</pur>"],
        ["Conviction",   "{{confidence}}/100"],
      ]},
    ],
    confidence: 56,
    readout: "coin-flip output. need filters to surface a real direction.",
  },
};

// ---------------------------------------------------------------------------
// SVG Icons
// ---------------------------------------------------------------------------
const ICONS = {
  search: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/></svg>,
  filter: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 5h18M6 12h12M10 19h4"/></svg>,
};

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------

const API = "";  // same-origin; set to "http://localhost:8000" for standalone

async function apiFetch(path) {
  const res = await fetch(API + path);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

// ---------------------------------------------------------------------------
// Briefing builder (client-side computation)
// ---------------------------------------------------------------------------

function buildBriefing(player, team, statMeta, statKey, line, games, window_) {
  if (!games || games.length === 0) {
    return {
      thinking: ["No data in current window..."],
      sections: [{ h: "DIRECTIVE", rows: [["Status", "<r>NO SAMPLE — adjust filters</r>"]] }],
      confidence: 0,
      readout: "no games match filters",
    };
  }

  const total = (g) =>
    statMeta.composite
      ? statMeta.composite.reduce((s, k) => s + (g[k] || 0), 0)
      : (g[statKey] || 0);

  const vals = games.map(total).sort((a, b) => a - b);
  const avg  = vals.reduce((s, v) => s + v, 0) / vals.length;
  const median = vals[Math.floor(vals.length / 2)];
  const sigma = Math.sqrt(vals.reduce((s, v) => s + (v - avg) ** 2, 0) / vals.length);

  const hits   = games.filter(g => total(g) > line).length;
  const hitL10 = Math.round((hits / games.length) * 100);

  const home   = games.filter(g => g.ha === "vs");
  const away   = games.filter(g => g.ha === "@");
  const wins   = games.filter(g => g.won);
  const losses = games.filter(g => !g.won);
  const hitPct = (arr) =>
    arr.length ? Math.round(arr.filter(g => total(g) > line).length / arr.length * 100) : 0;

  // Streak detection (games is oldest→newest)
  const recent = [...games].reverse();
  let streak = 0;
  for (const g of recent) { if (total(g) > line) streak++; else break; }
  let coldStreak = 0;
  for (const g of recent) { if (total(g) <= line) coldStreak++; else break; }

  const L5Avg  = games.slice(-5).reduce((s, g) => s + total(g), 0) / Math.max(1, Math.min(5, games.length));
  const L20Avg = games.reduce((s, g) => s + total(g), 0) / games.length;
  const trend  = L5Avg - L20Avg;

  const templateKey = hitL10 >= 65 ? "consistent" : hitL10 <= 40 ? "fading" : "neutral";
  const t = BRIEFING_TEMPLATES[templateKey];

  const sigSafe    = Math.max(0.5, sigma);
  const distSigma  = (median - line) / sigSafe;
  const confidence = Math.max(20, Math.min(92, Math.round(50 + distSigma * 20)));

  let dist;
  if (distSigma >= 0.8)        dist = "right-tailed · clears line consistently";
  else if (distSigma <= -0.8)  dist = "left-tailed · misses line consistently";
  else if (sigma > avg * 0.45) dist = "high-variance · binary outcomes";
  else                         dist = "centered · noise around line";

  const fill = (s) =>
    s
      .replace(/{{player}}/g,     player.last)
      .replace(/{{playerFull}}/g, `${player.first} ${player.last}`)
      .replace(/{{team}}/g,       team.tri)
      .replace(/{{pos}}/g,        player.pos || "—")
      .replace(/{{statLabel}}/g,  statMeta.label)
      .replace(/{{stat}}/g,       statMeta.short)
      .replace(/{{line}}/g,       line)
      .replace(/{{sampleN}}/g,    games.length)
      .replace(/{{window}}/g,     window_)
      .replace(/{{hitL10}}/g,     hitL10)
      .replace(/{{median}}/g,     median.toFixed(1))
      .replace(/{{sigma}}/g,      sigma.toFixed(2))
      .replace(/{{hitHome}}/g,    hitPct(home))
      .replace(/{{nHome}}/g,      home.length)
      .replace(/{{hitAway}}/g,    hitPct(away))
      .replace(/{{nAway}}/g,      away.length)
      .replace(/{{hitWin}}/g,     hitPct(wins))
      .replace(/{{hitLoss}}/g,    hitPct(losses))
      .replace(/{{streak}}/g,     streak)
      .replace(/{{coldStreak}}/g, coldStreak)
      .replace(/{{deltaL5L20}}/g, `${trend >= 0 ? "+" : ""}${trend.toFixed(1)}`)
      .replace(/{{distribution}}/g, dist)
      .replace(/{{confidence}}/g, confidence)
      .replace(/{{deltaSigma}}/g, Math.abs(distSigma).toFixed(1));

  return {
    thinking:   t.thinking.map(fill),
    sections:   t.sections.map(sec => ({
      h:    fill(sec.h),
      rows: sec.rows.map(([k, v]) => [fill(k), fill(v)]),
    })),
    confidence,
    readout: fill(t.readout),
  };
}

// =====================================================================
// TOPBAR
// =====================================================================
function TopBar({ apiOk }) {
  const [now, setNow] = useState(new Date());
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 60000);
    return () => clearInterval(id);
  }, []);

  const days  = ["SUN","MON","TUE","WED","THU","FRI","SAT"];
  const months = ["JAN","FEB","MAR","APR","MAY","JUN","JUL","AUG","SEP","OCT","NOV","DEC"];
  const hh = String(now.getHours()).padStart(2, "0");
  const mm = String(now.getMinutes()).padStart(2, "0");
  const timeStr = `${days[now.getDay()]} · ${months[now.getMonth()]} ${now.getDate()} · ${hh}:${mm}`;

  return (
    <div className="topbar">
      <div className="brand">
        <span className="mark"></span>
        DIMER<span style={{color:"var(--fg-3)"}}>//</span>TERMINAL
        <span className="sub" style={{ marginLeft: 8 }}>v0.5</span>
      </div>
      <div className="search">
        <span style={{ color: "var(--fg-3)", width: 14, display: "inline-flex" }}>{ICONS.search}</span>
        <input placeholder="player · team · stat · query…" readOnly />
        <span className="kbd">⌘K</span>
      </div>
      <div className="status">
        <div className="group">
          <span className={`dot ${apiOk ? "green" : "red"}`}></span>
          SUPABASE · {apiOk ? "LIVE" : "CONNECTING"}
        </div>
        <div className="group"><span className="dot"></span>DIMER-EDGE-V3</div>
        <div className="group" style={{ color: "var(--fg-1)" }}>{timeStr}</div>
      </div>
    </div>
  );
}

// =====================================================================
// BREADCRUMB
// =====================================================================
function Crumb({ team, player, statMeta, line, window_, onJump, teamsCount }) {
  return (
    <div className="crumb">
      <div className={`step ${team ? "done" : "active"}`} onClick={() => onJump("depth-01")}>
        <span className="num">01</span>
        <span>TEAM</span>
        {team && <span className="val">· {team.tri}</span>}
      </div>
      <span className="sep">›</span>
      <div className={`step ${player ? "done" : team ? "active" : ""}`} onClick={() => onJump("depth-02")}>
        <span className="num">02</span>
        <span>PLAYER</span>
        {player && <span className="val">· {player.first[0]}. {player.last}</span>}
      </div>
      <span className="sep">›</span>
      <div className={`step ${player ? "active" : ""}`} onClick={() => onJump("depth-03")}>
        <span className="num">03</span>
        <span>RESEARCH</span>
        {player && statMeta && <span className="val">· {statMeta.short} @ {line} · {window_}</span>}
      </div>
      <div className="right">
        <span className="meta-chip">{teamsCount} TEAMS</span>
        <span className="meta-chip">{STAT_TYPES.length} STATS</span>
        <span className="meta-chip" style={{ color: "var(--pur-100)", borderColor: "var(--pur-500)" }}>
          LIVE · DB
        </span>
      </div>
    </div>
  );
}

// =====================================================================
// DEPTH HEADER
// =====================================================================
function DepthHeader({ num, label, hint, blink }) {
  return (
    <div className="depth-h">
      <span className="num">DEPTH {num}</span>
      <span className="lbl">{label}</span>
      <span className="hint">
        {blink && <span className="blink"></span>}
        {hint}
      </span>
    </div>
  );
}

// =====================================================================
// LOADING SPINNER
// =====================================================================
function Spinner({ label = "LOADING" }) {
  return (
    <div style={{
      padding: "32px 0",
      display: "flex",
      alignItems: "center",
      gap: 10,
      fontFamily: "var(--f-mono)",
      fontSize: 11,
      color: "var(--fg-3)",
      letterSpacing: "0.1em",
    }}>
      <span className="blink" style={{ color: "var(--pur-200)" }}></span>
      {label}
      <span style={{ color: "var(--pur-200)" }}>_</span>
    </div>
  );
}

// =====================================================================
// DEPTH 01 — TEAM SELECT
// =====================================================================
function Depth01({ teams, activeTri, onSelect, loading }) {
  const [query, setQuery] = useState("");
  const [conf, setConf]   = useState("all");

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return teams.filter(t => {
      if (conf !== "all" && t.conf !== conf) return false;
      if (!q) return true;
      return (
        t.tri.toLowerCase().includes(q) ||
        t.city.toLowerCase().includes(q) ||
        t.name.toLowerCase().includes(q) ||
        t.div.toLowerCase().includes(q)
      );
    });
  }, [teams, query, conf]);

  const grouped = useMemo(() => {
    const map = {};
    filtered.forEach(t => {
      map[t.conf] = map[t.conf] || {};
      map[t.conf][t.div] = map[t.conf][t.div] || [];
      map[t.conf][t.div].push(t);
    });
    return map;
  }, [filtered]);

  const divOrder = {
    East: ["Atlantic","Central","Southeast"],
    West: ["Northwest","Pacific","Southwest"],
  };

  return (
    <section className="depth" id="depth-01">
      <DepthHeader num="01" label="Select Team" hint="30 NBA FRANCHISES · CONF · DIV" blink />
      <div className="shelf">
        <div className="field">
          <span className="icon">{ICONS.search}</span>
          <input
            placeholder="search teams · city · division…"
            value={query}
            onChange={e => setQuery(e.target.value)}
          />
          <span className="kbd">⌘T</span>
        </div>
        <span className={`filter-pill ${conf === "all" ? "active" : ""}`} onClick={() => setConf("all")}>ALL</span>
        <span className={`filter-pill ${conf === "East" ? "active" : ""}`} onClick={() => setConf("East")}>EAST</span>
        <span className={`filter-pill ${conf === "West" ? "active" : ""}`} onClick={() => setConf("West")}>WEST</span>
        <span className="right">// {filtered.length} matching</span>
      </div>

      {loading ? (
        <Spinner label="LOADING TEAMS FROM SUPABASE" />
      ) : (
        ["East","West"].map(c => grouped[c] && (
          <div className="conf-block" key={c}>
            <div className="conf-head">
              {c === "East" ? "EASTERN" : "WESTERN"} CONFERENCE
              <span className="count">{Object.values(grouped[c]).flat().length} TEAMS</span>
            </div>
            {divOrder[c].map(d => grouped[c][d] && (
              <div className="div-row" key={d}>
                <div className="div-label">
                  <span className="icon">▸</span>
                  <span>{d.toUpperCase()}</span>
                  <span className="num">DIVISION</span>
                </div>
                <div className="div-teams">
                  {grouped[c][d].map(t => (
                    <TeamCard
                      key={t.tri}
                      team={t}
                      active={activeTri === t.tri}
                      onClick={() => t.hasData && onSelect(t.tri)}
                    />
                  ))}
                </div>
              </div>
            ))}
          </div>
        ))
      )}
    </section>
  );
}

function TeamCard({ team, active, onClick }) {
  return (
    <div
      className={`team-card ${active ? "active" : ""} ${!team.hasData ? "no-data" : ""}`}
      onClick={onClick}
      title={team.hasData ? undefined : "No data indexed for this team"}
    >
      <div className="tri">{team.tri}</div>
      <div className="nm">{team.name}</div>
      <div className="ros">
        {team.hasData ? "INDEXED · LIVE" : "INDEX PENDING"}
      </div>
    </div>
  );
}

// =====================================================================
// DEPTH 02 — PLAYER SELECT
// =====================================================================
function Depth02({ team, players, activeId, onSelect, loading }) {
  const [query, setQuery] = useState("");

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return players;
    return players.filter(p =>
      p.first.toLowerCase().includes(q) ||
      p.last.toLowerCase().includes(q) ||
      p.pos.toLowerCase().includes(q)
    );
  }, [players, query]);

  if (!team) return null;

  return (
    <section className="depth" id="depth-02">
      <DepthHeader
        num="02"
        label="Select Player"
        hint={`${team.city.toUpperCase()} · ${team.name.toUpperCase()} ROSTER`}
      />
      <div className="roster-wrap">
        <div className="roster-meta">
          <div className="tri-big">{team.tri}</div>
          <div className="nm-big">{team.city} {team.name}</div>
          <div className="meta-row">
            {team.conf === "East" ? "EASTERN" : "WESTERN"}
            <span className="sep">·</span>
            {team.div.toUpperCase()} DIV
          </div>
          <div className="stats-row">
            <div className="stat"><span className="k">ROSTER</span><span className="v">{players.length}</span></div>
            <div className="stat"><span className="k">INDEXED</span><span className="v">{players.length}</span></div>
            <div className="stat">
              <span className="k">CORPUS</span>
              <span className="v">{players.reduce((s, p) => s + (p.games || 0), 0).toLocaleString()}</span>
            </div>
            <div className="stat"><span className="k">SOURCE</span><span className="v">DB</span></div>
          </div>
        </div>

        <div>
          <div className="shelf">
            <div className="field">
              <span className="icon">{ICONS.search}</span>
              <input
                placeholder="search roster · name…"
                value={query}
                onChange={e => setQuery(e.target.value)}
              />
            </div>
            <span className="right">// {filtered.length} player{filtered.length !== 1 ? "s" : ""}</span>
          </div>

          {loading ? (
            <Spinner label="LOADING ROSTER" />
          ) : filtered.length === 0 && players.length === 0 ? (
            <div className="roster-empty">
              <div className="glyph">▣</div>
              No roster indexed for {team.tri}.<br />
              Ingestion pipeline pending for this franchise.
            </div>
          ) : filtered.length === 0 ? (
            <div className="roster-empty">
              <div className="glyph">∅</div>
              No players matching "{query}"
            </div>
          ) : (
            <table className="roster-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th style={{ textAlign: "right" }}>PPG</th>
                  <th style={{ textAlign: "right" }}>APG</th>
                  <th style={{ textAlign: "right" }}>RPG</th>
                  <th style={{ textAlign: "right" }}>MIN</th>
                  <th style={{ textAlign: "right" }}>GP</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map(p => (
                  <tr
                    key={p.id}
                    className={activeId === p.id ? "active" : ""}
                    onClick={() => onSelect(p.id)}
                  >
                    <td className="name">{p.first} {p.last}</td>
                    <td className="metric"><strong>{p.stats.pts.toFixed(1)}</strong></td>
                    <td className="metric">{p.stats.ast.toFixed(1)}</td>
                    <td className="metric">{p.stats.reb.toFixed(1)}</td>
                    <td className="metric">{p.stats.min > 0 ? p.stats.min.toFixed(1) : "—"}</td>
                    <td className="metric" style={{ color: "var(--fg-3)" }}>{p.games}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </section>
  );
}

// =====================================================================
// DEPTH 03 — RESEARCH
// =====================================================================
function Depth03(props) {
  return (
    <section className="depth" id="depth-03">
      <DepthHeader num="03" label="Research" hint={`TARGET · ${props.player.first} ${props.player.last}`} blink />

      <Hero
        player={props.player} team={props.team}
        statMeta={props.statMeta} line={props.line}
        hitRate={props.hitRate} hitCount={props.hitCount} totalGames={props.totalGames}
        onLine={props.onLine}
      />

      <div style={{ height: 16 }} />

      <StatCategoryGrid
        categories={STAT_CATEGORIES}
        statTypes={STAT_TYPES}
        active={props.statKey}
        onChange={props.onStat}
        player={props.player}
      />

      <div style={{ height: 16 }} />

      <FilterBar
        window_={props.window_}
        onWindow={props.onWindow}
        chips={props.chips}
        onToggle={props.onToggle}
      />

      <div style={{ height: 16 }} />

      {props.gamesLoading ? (
        <Spinner label="LOADING GAME LOG FROM DB" />
      ) : (
        <>
          <TerminalChartCard
            games={props.games} statMeta={props.statMeta} statKey={props.statKey}
            line={props.line} hitRate={props.hitRate} hitCount={props.hitCount}
            totalGames={props.totalGames} window_={props.window_}
            player={props.player}
          />

          <div style={{ height: 16 }} />

          {props.briefing && (
            <Briefing data={props.briefing} briefId={props.briefId} tickSpeed={props.briefSpeed} />
          )}

          <div style={{ height: 16 }} />

          <SupportingGrid
            player={props.player} games={props.games}
            statKey={props.statKey} statMeta={props.statMeta} line={props.line}
          />
        </>
      )}
    </section>
  );
}

// =====================================================================
// HERO
// =====================================================================
function Hero({ player, team, statMeta, line, hitRate, hitCount, totalGames, onLine }) {
  const hitCls = hitRate >= 60 ? "green" : hitRate >= 45 ? "yellow" : "red";
  const [val, setVal] = useState(line);
  useEffect(() => setVal(line), [line]);

  const commit = (v) => {
    const n = parseFloat(v);
    if (Number.isFinite(n) && n >= 0) onLine(Math.round(n * 2) / 2);
  };

  return (
    <div className="hero">
      <div className="hero-photo">
        {player.initials}
        <div className="ghost"></div>
        <div className="placeholder-note">// photo slot</div>
      </div>
      <div className="hero-info">
        <div className="hero-name">
          <span>{player.first} {player.last}</span>
          <span className="team-tag">{team.tri}</span>
        </div>
        <div className="hero-meta">
          <span>{team.city} {team.name}</span>
          {player.stats.min > 0 && (
            <><span className="sep">·</span><span>{player.stats.min.toFixed(1)} MIN/G</span></>
          )}
          <span className="sep">·</span>
          <span>{player.games} GAMES</span>
          <span className="sep">·</span>
          <span style={{ color: "var(--pur-100)" }}>LIVE · DB CORPUS</span>
        </div>
        <div className="hero-tag">
          <span className="dot"></span>
          ANALYZING · {statMeta.label.toUpperCase()} · REFERENCE LINE {line}
        </div>
      </div>
      <div className="hero-prop">
        <div className="hero-line">
          <span className="lbl">// REFERENCE LINE · {statMeta.short}</span>
          <div className="line-input" style={{ marginTop: 4 }}>
            <span className="lbl">OVER</span>
            <button className="num-btn" onClick={() => commit(val - 0.5)} title="-0.5">−</button>
            <input
              type="number"
              step="0.5"
              value={val}
              onChange={e => setVal(e.target.value)}
              onBlur={e => commit(e.target.value)}
              onKeyDown={e => { if (e.key === "Enter") e.target.blur(); }}
            />
            <button className="num-btn" onClick={() => commit((parseFloat(val) || 0) + 0.5)} title="+0.5">+</button>
          </div>
        </div>
        <div className={`hero-hit ${hitCls}`}>
          <div className="num">{hitRate}<span style={{ fontSize: 16 }}>%</span></div>
          <div className="meta">
            <div><strong>{hitCount}/{totalGames}</strong> OVER</div>
            <div>L{totalGames} HIT RATE</div>
          </div>
        </div>
      </div>
    </div>
  );
}

// =====================================================================
// STAT CATEGORY GRID
// =====================================================================
function StatCategoryGrid({ categories, statTypes, active, onChange, player }) {
  return (
    <div className="cat-grid" style={{ gridTemplateColumns: `repeat(${categories.length}, 1fr)` }}>
      {categories.map(cat => {
        const hasActive = cat.stats.includes(active);
        return (
          <div className={`cat-card ${hasActive ? "has-active" : ""}`} key={cat.key}>
            <div className="cat-h">
              <span className="glyph">{cat.glyph}</span>
              {cat.label}
            </div>
            <div className="cat-pills">
              {cat.stats.map(sKey => {
                const meta = statTypes.find(s => s.key === sKey);
                if (!meta) return null;
                const avg = meta.composite
                  ? meta.composite.reduce((s, k) => s + (player.stats[k] || 0), 0)
                  : (player.stats[sKey] || 0);
                return (
                  <div
                    key={sKey}
                    className={`cat-pill ${active === sKey ? "active" : ""}`}
                    onClick={() => onChange(sKey)}
                  >
                    <span className="stat">{meta.short}</span>
                    <span className="line">{avg.toFixed(1)} /g</span>
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// =====================================================================
// FILTER BAR
// =====================================================================
function FilterBar({ window_, onWindow, chips, onToggle }) {
  const windows = [
    { k: "L5", l: "L5" }, { k: "L10", l: "L10" }, { k: "L20", l: "L20" },
    { k: "H2H", l: "H2H" }, { k: "SZN", l: "SEASON" },
  ];
  const haGroup  = [{ k: "home", l: "HOME" }, { k: "away", l: "AWAY" }];
  const wlGroup  = [{ k: "win", l: "W" }, { k: "loss", l: "L" }];
  const count = Object.values(chips).filter(Boolean).length;

  return (
    <div className="filter-bar">
      <span className="lbl">// Window</span>
      <div className="window-group">
        {windows.map(w => (
          <button
            key={w.k}
            className={`window-btn ${window_ === w.k ? "active" : ""}`}
            onClick={() => onWindow(w.k)}
          >{w.l}</button>
        ))}
      </div>
      <span className="sep-v"></span>
      <span className="lbl">// Venue</span>
      {haGroup.map(c => (
        <span key={c.k} className={`chip ${chips[c.k] ? "active" : ""}`} onClick={() => onToggle(c.k)}>{c.l}</span>
      ))}
      <span className="sep-v"></span>
      <span className="lbl">// Result</span>
      {wlGroup.map(c => (
        <span key={c.k} className={`chip ${chips[c.k] ? "active" : ""}`} onClick={() => onToggle(c.k)}>{c.l}</span>
      ))}
      <span className="chip" style={{ marginLeft: "auto", borderColor: "var(--pur-400)", color: "var(--pur-100)" }}>
        {ICONS.filter} ADV {count > 0 && <span className="chip-count">{count}</span>}
      </span>
    </div>
  );
}

// =====================================================================
// TERMINAL CHART CARD
// =====================================================================
function TerminalChartCard({ games, statMeta, statKey, line, hitRate, hitCount, totalGames, window_, player }) {
  const hitCls = hitRate >= 60 ? "green" : hitRate >= 45 ? "yellow" : "red";
  const slug = player.last.toLowerCase().replace(/[^a-z]/g, "");
  return (
    <div className="term-chart-card scanlines">
      <div className="term-bar">
        <div className="dots"><span></span><span></span><span></span></div>
        <span>dimer@terminal</span>
        <span style={{ color: "var(--fg-4)" }}>:</span>
        <span className="pwd">~/{player.team.toLowerCase()}/{slug}/{statKey}</span>
        <span className="right">{window_} · BARS [{games.length}]</span>
      </div>
      <div className="term-chart">
        <div className="term-chart-head">
          <span className="prompt">$</span>
          <span className="cmd">plot</span>
          <span className="arg">--player={player.id}</span>
          <span className="arg">--stat={statKey}</span>
          <span className="arg">--line={line}</span>
          <span className="arg">--window={window_.toLowerCase()}</span>
          <span className="right">
            <span style={{ color: "var(--fg-3)" }}>hit_rate =</span>
            <span className={`hit-pct ${hitCls}`}>{hitRate}%</span>
            <span style={{ color: "var(--fg-3)" }}>({hitCount}/{totalGames})</span>
          </span>
        </div>
        {games.length === 0 ? (
          <div style={{
            padding: "32px 0",
            textAlign: "center",
            fontFamily: "var(--f-mono)",
            fontSize: 11,
            color: "var(--fg-3)",
          }}>
            // NO GAMES MATCH CURRENT FILTERS
          </div>
        ) : (
          <PerfChart
            key={`${statKey}-${window_}-${player.id}-${line}`}
            games={games}
            statKey={statKey}
            line={line}
            statTypeMeta={statMeta}
          />
        )}
      </div>
      <div className="term-foot">
        <span className="legend"><span className="swatch over"></span> OVER LINE</span>
        <span className="legend"><span className="swatch under"></span> UNDER LINE</span>
        <span className="legend"><span className="swatch line"></span> LINE {line}</span>
        <span className="right">LIVE DB · {games.length} BARS</span>
      </div>
    </div>
  );
}

// =====================================================================
// SUPPORTING GRID
// =====================================================================
function SupportingGrid({ player, games, statKey, statMeta, line }) {
  const total = (g) =>
    statMeta.composite
      ? statMeta.composite.reduce((s, k) => s + (g[k] || 0), 0)
      : (g[statKey] || 0);

  const vals   = games.map(total).sort((a, b) => a - b);
  const avg    = vals.length ? vals.reduce((s, v) => s + v, 0) / vals.length : 0;
  const median = vals.length ? vals[Math.floor(vals.length / 2)] : 0;
  const max    = vals.length ? vals[vals.length - 1] : 0;
  const min    = vals.length ? vals[0] : 0;
  const sigma  = vals.length
    ? Math.sqrt(vals.reduce((s, v) => s + (v - avg) ** 2, 0) / vals.length)
    : 0;

  const home   = games.filter(g => g.ha === "vs");
  const away   = games.filter(g => g.ha === "@");
  const wins   = games.filter(g => g.won);
  const losses = games.filter(g => !g.won);

  const hitPct = (arr) =>
    arr.length ? Math.round(arr.filter(g => total(g) > line).length / arr.length * 100) : 0;
  const avgArr = (arr) =>
    arr.length ? arr.reduce((s, g) => s + total(g), 0) / arr.length : 0;

  const splits = [
    { k: "HOME",   n: home.length,   hit: hitPct(home),   avg: avgArr(home) },
    { k: "AWAY",   n: away.length,   hit: hitPct(away),   avg: avgArr(away) },
    { k: "WINS",   n: wins.length,   hit: hitPct(wins),   avg: avgArr(wins) },
    { k: "LOSSES", n: losses.length, hit: hitPct(losses), avg: avgArr(losses) },
  ];

  return (
    <div className="support-strip">
      {/* Distribution */}
      <div className="s-card">
        <div className="s-h"><span className="glyph">▦</span> Distribution · {statMeta.short}</div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 14 }}>
          {[
            ["AVG",    avg.toFixed(1)],
            ["MEDIAN", median.toFixed(1)],
            ["MAX",    max],
            ["MIN",    min],
            ["σ",      sigma.toFixed(1)],
            ["RANGE",  `${min}–${max}`],
            ["LINE",   line],
            ["Δ MED",  (median - line).toFixed(1)],
          ].map(([k, v]) => (
            <div key={k} style={{ display: "flex", flexDirection: "column", gap: 2 }}>
              <span style={{
                fontFamily: "var(--f-mono)", fontSize: 10,
                color: "var(--fg-3)", letterSpacing: "0.1em", textTransform: "uppercase",
              }}>{k}</span>
              <span style={{
                fontFamily: "var(--f-mono)", fontSize: 16, fontWeight: 700,
                color: k === "Δ MED"
                  ? ((median - line) >= 0 ? "var(--green)" : "var(--red)")
                  : "var(--fg-0)",
              }}>{v}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Splits */}
      <div className="s-card">
        <div className="s-h"><span className="glyph">▥</span> Splits · vs line {line}</div>
        {splits.map(s => (
          <div className="def-row" key={s.k}>
            <div className="stat">{s.k} <span style={{ color: "var(--fg-4)" }}>· {s.n}g</span></div>
            <div className={`rank ${s.hit >= 60 ? "good" : s.hit >= 45 ? "mid" : "bad"}`}>{s.hit}%</div>
            <div className="val">{s.avg.toFixed(1)}</div>
          </div>
        ))}
      </div>

      {/* Game log */}
      <div className="s-card">
        <div className="s-h"><span className="glyph">▤</span> Game Log · {games.length}g</div>
        <div style={{ maxHeight: 200, overflowY: "auto" }}>
          <table style={{ width: "100%", fontFamily: "var(--f-mono)", fontSize: 11, borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ color: "var(--fg-3)", fontSize: 9, letterSpacing: "0.08em" }}>
                <th style={{ textAlign: "left", padding: "4px 0", textTransform: "uppercase" }}>Date</th>
                <th style={{ textAlign: "left", padding: "4px 0", textTransform: "uppercase" }}>Opp</th>
                <th style={{ textAlign: "left", padding: "4px 0", textTransform: "uppercase" }}>WL</th>
                <th style={{ textAlign: "right", padding: "4px 0", textTransform: "uppercase" }}>{statMeta.short}</th>
                <th style={{ textAlign: "right", padding: "4px 0", textTransform: "uppercase" }}>Δ</th>
              </tr>
            </thead>
            <tbody>
              {[...games].reverse().map((g, i) => {
                const v = total(g);
                const delta = v - line;
                return (
                  <tr key={g.game_id || i} style={{ borderBottom: "1px solid var(--line-1)" }}>
                    <td style={{ padding: "4px 0", color: "var(--fg-2)" }}>{g.date}</td>
                    <td style={{ padding: "4px 0", color: "var(--fg-1)" }}>{g.ha}{g.opp}</td>
                    <td style={{ padding: "4px 0", color: g.won ? "var(--green)" : "var(--red)" }}>{g.result}</td>
                    <td style={{ padding: "4px 0", textAlign: "right", color: "var(--fg-0)", fontWeight: 600 }}>{v}</td>
                    <td style={{
                      padding: "4px 0", textAlign: "right", fontWeight: 600,
                      color: delta >= 0 ? "var(--green)" : "var(--red)",
                    }}>
                      {delta >= 0 ? "+" : ""}{delta.toFixed(1)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// =====================================================================
// TWEAK DEFAULTS
// =====================================================================
const TWEAK_DEFAULTS = {
  theme: "violet",
  scanlines: true,
  glow: true,
  density: "regular",
  briefSpeed: 240,
};

// =====================================================================
// MAIN APP
// =====================================================================
function App() {
  const [t, setTweak] = useTweaks(TWEAK_DEFAULTS);

  // Remote data
  const [teams,    setTeams]   = useState([]);
  const [players,  setPlayers] = useState([]);
  const [allGames, setAllGames]= useState([]);

  // Loading flags
  const [teamsLoading,  setTeamsLoading]  = useState(true);
  const [playersLoading,setPlayersLoading]= useState(false);
  const [gamesLoading,  setGamesLoading]  = useState(false);
  const [apiOk,         setApiOk]         = useState(false);

  // Selections
  const [teamTri,  setTeamTri]  = useState(null);
  const [playerId, setPlayerId] = useState(null);
  const [statKey,  setStatKey]  = useState("pts");
  const [window_,  setWindow_]  = useState("L10");
  const [line,     setLine]     = useState(29.5);
  const [chips,    setChips]    = useState({});

  // Load teams on mount
  useEffect(() => {
    apiFetch("/api/teams")
      .then(data => { setTeams(data); setApiOk(true); setTeamsLoading(false); })
      .catch(() => { setTeamsLoading(false); });
  }, []);

  // Load players when team changes
  useEffect(() => {
    if (!teamTri) return;
    setPlayersLoading(true);
    setPlayers([]);
    setPlayerId(null);
    setAllGames([]);
    apiFetch(`/api/teams/${teamTri}/players`)
      .then(data => { setPlayers(data); setPlayersLoading(false); })
      .catch(() => setPlayersLoading(false));
  }, [teamTri]);

  // Load game log when player changes
  useEffect(() => {
    if (!playerId) return;
    setGamesLoading(true);
    setAllGames([]);
    apiFetch(`/api/players/${playerId}/games`)
      .then(data => { setAllGames(data); setGamesLoading(false); })
      .catch(() => setGamesLoading(false));
  }, [playerId]);

  // Derived
  const team     = teams.find(x => x.tri === teamTri) || null;
  const player   = players.find(p => p.id === String(playerId)) || null;
  const statMeta = STAT_TYPES.find(s => s.key === statKey);

  // Reset line when stat or player changes
  useEffect(() => {
    if (!player || !statMeta) return;
    const avg = statMeta.composite
      ? statMeta.composite.reduce((s, k) => s + (player.stats[k] || 0), 0)
      : (player.stats[statKey] || 0);
    const newLine = Math.max(0.5, Math.round(avg * 2) / 2 - 0.5);
    setLine(newLine);
  }, [statKey, playerId]); // eslint-disable-line

  // Filter games (allGames is newest first)
  const games = useMemo(() => {
    if (!statMeta) return [];
    let logs = [...allGames];
    if      (window_ === "L5")  logs = logs.slice(0, 5);
    else if (window_ === "L10") logs = logs.slice(0, 10);
    else if (window_ === "L20") logs = logs.slice(0, 20);
    else if (window_ === "H2H") {
      const opp = logs[0]?.opp;
      if (opp) logs = logs.filter(g => g.opp === opp);
    }
    // else SZN = all games
    if (chips.home) logs = logs.filter(g => g.ha === "vs");
    if (chips.away) logs = logs.filter(g => g.ha === "@");
    if (chips.win)  logs = logs.filter(g => g.won);
    if (chips.loss) logs = logs.filter(g => !g.won);
    return [...logs].reverse(); // oldest → newest for chart
  }, [allGames, window_, chips, statMeta]);

  // Hit rate
  const totals  = games.map(g => statMeta
    ? (statMeta.composite
      ? statMeta.composite.reduce((s, k) => s + (g[k] || 0), 0)
      : (g[statKey] || 0))
    : 0);
  const hits    = totals.filter(v => v > line).length;
  const hitRate = games.length ? Math.round((hits / games.length) * 100) : 0;

  // AI briefing
  const briefId  = `${playerId}-${statKey}-${window_}-${line}`;
  const briefing = useMemo(() => {
    if (!player || !team || !statMeta || games.length === 0) return null;
    return buildBriefing(player, team, statMeta, statKey, line, games, window_);
  }, [briefId]); // eslint-disable-line

  // Theme class
  useEffect(() => {
    document.documentElement.className =
      `theme-${t.theme} density-${t.density}` +
      (t.scanlines ? "" : " no-scan") +
      (t.glow ? "" : " no-glow");
    document.body.classList.add("v2");
  }, [t.theme, t.scanlines, t.glow, t.density]);

  const onJump = (id) => {
    const el = document.getElementById(id);
    if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  return (
    <div className="depth-app">
      <TopBar apiOk={apiOk} />
      <Crumb
        team={team} player={player}
        statMeta={statMeta} line={line} window_={window_}
        onJump={onJump} teamsCount={teams.length}
      />

      <Depth01
        teams={teams}
        activeTri={teamTri}
        loading={teamsLoading}
        onSelect={(tri) => {
          setTeamTri(tri);
          setTimeout(() => onJump("depth-02"), 280);
        }}
      />

      {teamTri && (
        <Depth02
          team={team || { tri: teamTri, city: teamTri, name: "", conf: "?", div: "?" }}
          players={players}
          activeId={playerId}
          loading={playersLoading}
          onSelect={(id) => {
            setPlayerId(id);
            setTimeout(() => onJump("depth-03"), 280);
          }}
        />
      )}

      {player && statMeta && (
        <Depth03
          player={player} team={team}
          statMeta={statMeta} line={line} onLine={setLine}
          statKey={statKey} onStat={(k) => { setStatKey(k); setChips({}); }}
          window_={window_} onWindow={setWindow_}
          chips={chips} onToggle={(k) => setChips(c => ({ ...c, [k]: !c[k] }))}
          games={games} gamesLoading={gamesLoading}
          hitRate={hitRate} hitCount={hits} totalGames={games.length}
          briefing={briefing} briefId={briefId} briefSpeed={t.briefSpeed}
        />
      )}

      <TweaksPanel>
        <TweakSection label="Theme" />
        <TweakSelect
          label="Accent" value={t.theme}
          options={["violet","cyan","amber","magenta","toxic"]}
          onChange={(v) => setTweak("theme", v)}
        />
        <TweakRadio
          label="Density" value={t.density}
          options={["regular","compact"]}
          onChange={(v) => setTweak("density", v)}
        />
        <TweakSection label="Atmosphere" />
        <TweakToggle label="Scanlines"    value={t.scanlines}  onChange={(v) => setTweak("scanlines", v)} />
        <TweakToggle label="Accent glow"  value={t.glow}       onChange={(v) => setTweak("glow", v)} />
        <TweakSlider
          label="Briefing tick" value={t.briefSpeed}
          min={120} max={700} step={20} unit="ms"
          onChange={(v) => setTweak("briefSpeed", v)}
        />
      </TweaksPanel>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
