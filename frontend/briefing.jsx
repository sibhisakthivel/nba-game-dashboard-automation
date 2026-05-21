// ============================================================
// AI Co-Pilot Briefing — research-framed terminal output
// ============================================================
const { useState: useStateB, useEffect: useEffectB, useRef: useRefB } = React;

function Briefing({ data, briefId, tickSpeed = 350 }) {
  const [thinkingIdx, setThinkingIdx] = useStateB(-1);
  const [revealedIdx, setRevealedIdx]   = useStateB(-1); // section index revealed
  const [done, setDone]                 = useStateB(false);
  const [meterFill, setMeterFill]       = useStateB(0);
  const timersRef = useRefB([]);

  useEffectB(() => {
    timersRef.current.forEach(clearTimeout);
    timersRef.current = [];
    setThinkingIdx(-1);
    setRevealedIdx(-1);
    setDone(false);
    setMeterFill(0);

    const addTimer = (fn, delay) => {
      const id = setTimeout(fn, delay);
      timersRef.current.push(id);
    };

    let t = 100;
    data.thinking.forEach((_, i) => {
      addTimer(() => setThinkingIdx(i), t);
      t += tickSpeed;
    });

    data.sections.forEach((_, i) => {
      addTimer(() => setRevealedIdx(i), t);
      t += tickSpeed * 0.8;
    });

    addTimer(() => {
      setDone(true);
      setMeterFill(data.confidence);
    }, t);

    return () => timersRef.current.forEach(clearTimeout);
  }, [briefId, tickSpeed]);

  const buildId = String(Math.abs(hashCode(briefId || "default")) % 9999).padStart(4, "0");

  return (
    <div className="briefing scanlines">
      <div className="briefing-head">
        <span className="icon">▣</span>
        DIMER · CO-PILOT BRIEF
        <span style={{ color: "var(--pur-200)" }}>·</span>
        <span style={{ color: "var(--fg-1)" }}>#{buildId}</span>
        <span className="clf">RESEARCH · ANALYTICAL</span>
      </div>

      <div className="briefing-body">
        {/* Loading buffer lines */}
        {data.thinking.slice(0, thinkingIdx + 1).map((line, i) => (
          <div key={"th-" + i} className="buf">
            [LOAD] {line}
            <span className="ok">✓</span>
          </div>
        ))}
        {!done && thinkingIdx < data.thinking.length - 1 && (
          <div className="buf">
            [LOAD] <span className="cursor"></span>
          </div>
        )}

        {data.sections.map((sec, i) => (
          revealedIdx >= i && (
            <div className="sec" key={i}>
              <div className="sec-h"><span className="glyph">▒</span> {sec.h}</div>
              <div className="sec-rows">
                {sec.rows.map(([k, v], j) => (
                  <div className="row" key={k + j}>
                    <span className="k">{k}</span>
                    <span className="v" dangerouslySetInnerHTML={{ __html: v }} />
                  </div>
                ))}
                {sec.h === "READ" && (
                  <div className="row">
                    <span className="k">Meter</span>
                    <span className="v">
                      <div className="verdict-bar">
                        <div className="meter">
                          <div className="fill" style={{ width: `${meterFill}%` }}></div>
                          <div className="ticks"></div>
                        </div>
                      </div>
                    </span>
                  </div>
                )}
              </div>
            </div>
          )
        ))}

        {done && data.readout && (
          <div className="sec no-grid">
            <div className="sec-h"><span className="glyph">▒</span> SUMMARY</div>
            <div style={{ marginTop: 4, color: "var(--fg-0)", fontFamily: "var(--f-mono)", fontSize: 12, lineHeight: 1.6 }}
                 dangerouslySetInnerHTML={{ __html: "// " + data.readout }} />
          </div>
        )}
      </div>

      <div className="briefing-foot">
        <span className="lead">$ dimer-copilot</span>
        <span>·</span>
        <span>v3.1</span>
        <span>·</span>
        <span>brief #{buildId}</span>
        <span className="blink-end">
          <span className="dot"></span>
          {done ? "READY · awaiting next query" : "STREAMING"}
        </span>
      </div>
    </div>
  );
}

function hashCode(s) {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = ((h << 5) - h) + s.charCodeAt(i);
  return h;
}

window.Briefing = Briefing;
