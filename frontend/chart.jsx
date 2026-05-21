// ============================================================
// Chart component — stacked bars, prop line, hoverable
// ============================================================
const { useState, useMemo } = React;

function PerfChart({ games, statKey, line, statTypeMeta }) {
  const [hover, setHover] = useState(null);

  // For composite stats (PRA, P+A, etc), break into segments.
  // For single stats, single segment.
  const composite = statTypeMeta.composite || null;

  // Build rendered series
  const series = useMemo(() => {
    return games.map((g, i) => {
      let total = 0;
      let segs = [];
      if (composite) {
        composite.forEach((k, idx) => {
          const v = g[k] || 0;
          total += v;
          segs.push({ key: k, value: v, primary: idx === 0 });
        });
      } else {
        const v = g[statKey] || 0;
        total = v;
        segs = [{ key: statKey, value: v, primary: true }];
      }
      const hit = total > line;
      return { ...g, total, segs, hit, idx: i };
    });
  }, [games, statKey, line, composite]);

  // y-axis scaling
  const maxVal = Math.max(...series.map(s => s.total), line) * 1.18;
  const yTicks = useMemo(() => {
    const step = Math.ceil(maxVal / 8 / 5) * 5;
    const ticks = [];
    for (let v = 0; v <= maxVal; v += step) ticks.push(v);
    return ticks;
  }, [maxVal]);

  const linePct = ((line / maxVal) * 100);
  // chart has bars area = height - 30 (axis space). The line is positioned relative to bars area.
  // We'll position via bottom percentage inside .bars

  return (
    <div className="chart">
      <div className="yaxis">
        {yTicks.map((t, i) => <div key={i}>{t}</div>)}
      </div>
      <div className="bars" style={{ position: "relative" }}>
        {yTicks.map((t, i) => (
          <div
            key={"gl-" + i}
            className="gridline"
            style={{ bottom: `${(t / maxVal) * 100}%` }}
          />
        ))}
        {/* prop line */}
        <div className="line" style={{ bottom: `${linePct}%` }}>
          <div className="label">{line}</div>
        </div>

        {series.map((s, i) => {
          const heightPct = (s.total / maxVal) * 100;
          const cls = s.hit ? "over" : "under";
          return (
            <div
              key={s.date + "-" + i}
              className={`bar-col ${cls} ${hover === i ? "active" : ""}`}
              onMouseEnter={() => setHover(i)}
              onMouseLeave={() => setHover(null)}
            >
              <div
                className="bar-stack"
                style={{ height: `${heightPct}%` }}
              >
                {hover === i && (
                  <Tooltip game={s} statKey={statKey} composite={composite} line={line} />
                )}
                <div className="bar-total">{s.total}</div>
                {s.segs.map((seg, si) => {
                  const segPct = (seg.value / s.total) * 100;
                  const segCls = `seg ${cls}${si > 0 ? " secondary" : ""}`;
                  return (
                    <div
                      key={seg.key + si}
                      className={segCls}
                      style={{ flex: `${seg.value}` }}
                    >
                      {seg.value >= 4 && segPct > 14 ? (
                        <span>{seg.value} {labelFor(seg.key)}</span>
                      ) : null}
                    </div>
                  );
                })}
              </div>
              <div className="bar-label">
                <div>{s.date}</div>
                <div><span className="opp">{s.ha}{s.opp}</span></div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function labelFor(k) {
  const map = { pts: "PTS", ast: "AST", reb: "REB", tpm: "3PM", stl: "STL", blk: "BLK", to: "TOV" };
  return map[k] || k.toUpperCase();
}

function Tooltip({ game, statKey, composite, line }) {
  return (
    <div className="tooltip">
      <div className="ttl">{game.date}  {game.ha} {game.opp}</div>
      <div className="row"><span className="k">RESULT</span><span>{game.result}</span></div>
      <div className="row"><span className="k">MIN</span><span>{game.min}</span></div>
      {composite ? composite.map(k => (
        <div className="row" key={k}><span className="k">{labelFor(k)}</span><span>{game[k]}</span></div>
      )) : (
        <div className="row"><span className="k">{labelFor(statKey)}</span><span>{game[statKey]}</span></div>
      )}
      <div className="row">
        <span className="k">VS LINE</span>
        <span style={{ color: game.total > line ? "var(--green)" : "var(--red)" }}>
          {game.total > line ? "+" : ""}{(game.total - line).toFixed(1)}
        </span>
      </div>
    </div>
  );
}

window.PerfChart = PerfChart;
