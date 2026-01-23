import { useEffect, useMemo, useState } from "react";
import MismatchScoreLabel from "../scripts/MismatchScoreLabel.jsx";
import { fetchSummary } from "../lib/api.js";


import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Tooltip as ReTooltip,
  Legend,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
} from "recharts";

import { COLORS } from "../lib/colors.js";

function normalizeTimeseries(ts) {
  if (!Array.isArray(ts)) return [];

  return ts
    .map((row) => {
      // use the start of the window as the x-axis "date"
      const rawDate =
        row.window_start ??
        row.date ??
        row.day ??
        row.dt ??
        row.timestamp ??
        null;

      return {
        date: rawDate ? String(rawDate) : "",
        bt_normalized_perc: Number(row.bt_normalized_perc) || 0,
        ts_normalized_perc: Number(row.ts_normalized_perc) || 0,
      };
    })
    .filter((d) => d.date)
    .sort((a, b) => new Date(a.date) - new Date(b.date));
}

function formatPercent(v) {
  if (typeof v !== "number" || Number.isNaN(v)) return "";
  return `${v.toFixed(1)} %`;
}

function formatGermanDateTime(isoString) {
  if (!isoString) return "";
  const date = new Date(isoString);

  return new Intl.DateTimeFormat("de-DE", {
    timeZone: "Europe/Berlin",
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

export default function Landing({ onSelectTopic }) {
  const INTRO_KEY = "mismatch_intro_seen_v1";

  const [summary, setSummary] = useState(null);
  const [err, setErr] = useState(null);

  const [showIntro, setShowIntro] = useState(false);

  useEffect(() => {
    const seen = sessionStorage.getItem(INTRO_KEY) === "1";
    if (!seen) setShowIntro(true);
  }, []);

  const closeIntro = () => {
    sessionStorage.setItem(INTRO_KEY, "1");
    setShowIntro(false);
  };

  useEffect(() => {
    fetchSummary()
      .then(setSummary)
      .catch((e) => setErr(String(e)));
  }, []);

  // 1. Calculate the Hero
  const rawHero = summary?.hero_topic;
  // Safety check: is the API-provided hero the "bad" topic?
  const isBadHero = rawHero?.label?.toLowerCase() === "miscellaneous speech fragments";

  // If bad, try to grab the first valid topic from the list. Otherwise use rawHero.
  const hero = isBadHero && summary?.featured_topics?.length 
    ? summary.featured_topics.find(t => t.label?.toLowerCase() !== "miscellaneous speech fragments")
    : rawHero;

  // 2. Calculate the Grid (Top Others)
  const topOthers = useMemo(() => {
    if (!summary?.featured_topics?.length) return [];
    
    const heroSlug = hero?.slug;
    
    // Add any topics you want to remove here (make sure to use lowercase)
    const IGNORED_LABELS = [
        "miscellaneous speech fragments", 
        "parliamentary debate discourse" 
    ];

    return summary.featured_topics
      // 1. Remove the Hero
      .filter((t) => t?.slug && t.slug !== heroSlug)
      // 2. Remove ANY topic that is in our ignored list
      .filter((t) => !IGNORED_LABELS.includes(t.label?.toLowerCase()))
      // 3. Take the top 16 of what remains
      .slice(0, 19);
      
  }, [summary, hero?.slug]);

  if (err) {
    return (
      <div className="container">
        <div className="error">Error: {err}</div>
      </div>
    );
  }

  if (!summary) {
    return (
      <div className="container">
        <p>Loading…</p>
      </div>
    );
  }

  if (!hero) {
    return (
      <div className="container">
        <h1>Mismatch Barometer</h1>
        <p className="muted">
          Last updated: {formatGermanDateTime(summary.last_updated)}
        </p>
        <div className="error">No hero_topic found in summary.json</div>
      </div>
    );
  }

  const heroPie = [
    { name: "Bundestag", value: Number(hero.bt_share) || 0 },
    { name: "Talkshows", value: Number(hero.ts_share) || 0 },
  ].filter((d) => d.value > 0);

  const heroSeries = normalizeTimeseries(hero.timeseries);

return (
  <div className="container">
    {showIntro && (
    <div className="modalBackdrop modalFadeIn" onClick={closeIntro} style={{ 
      display: 'flex', 
      alignItems: 'center', 
      justifyContent: 'center',
      zIndex: 100 
    }}>
      <div
        className="modalCard"
        role="dialog"
        aria-modal="true"
        onClick={(e) => e.stopPropagation()}
        style={{
          maxWidth: "850px",
          width: "90%",
          padding: 0,
          borderRadius: "16px",
          overflow: "hidden",
          display: "flex",
          flexDirection: "row", // Side-by-side layout
          boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.25)",
          flexWrap: "wrap" // Wraps on mobile
        }}
      >
        
        {/* 1. Visual Side (Illustration) */}
        <div style={{
          flex: "1 1 300px",
          background: "linear-gradient(135deg, #f9fafb 0%, #f3f4f6 100%)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: "3rem",
          borderRight: "1px solid #e5e7eb"
        }}>
          {/* Custom SVG Illustration: TV vs Podium */}
          <svg width="200" height="180" viewBox="0 0 200 180" fill="none" xmlns="http://www.w3.org/2000/svg">
            {/* Connecting "Tension" Line */}
            <path d="M100 60 L100 120" stroke="#d1d5db" strokeWidth="2" strokeDasharray="6 4" />
            <circle cx="100" cy="90" r="16" fill="white" stroke="#d1d5db" strokeWidth="2" />
            <text x="100" y="96" textAnchor="middle" fontSize="18" fontWeight="bold" fill="#9ca3af">vs</text>

            {/* Talkshow Side (Left/Top) */}
            <g transform="translate(10, 20)">
              <rect x="0" y="0" width="80" height="60" rx="8" fill={COLORS.talkshow} opacity="0.9" />
              <rect x="5" y="5" width="70" height="50" rx="4" fill="white" opacity="0.2" />
              <path d="M25 75 L35 60 H45 L55 75" stroke={COLORS.talkshow} strokeWidth="4" strokeLinecap="round" />
              {/* Screen "Noise" Lines */}
              <path d="M20 30 H60 M20 40 H50" stroke="white" strokeWidth="3" strokeLinecap="round" opacity="0.8"/>
            </g>

            {/* Bundestag Side (Right/Bottom) */}
            <g transform="translate(110, 100)">
              <path d="M10 60 L10 10 L70 10 L70 60" stroke={COLORS.bundestag} strokeWidth="4" fill="white" />
              <path d="M0 10 H80 M5 60 H75" stroke={COLORS.bundestag} strokeWidth="4" strokeLinecap="round" />
              <path d="M40 25 V45" stroke={COLORS.bundestag} strokeWidth="4" strokeLinecap="round" />
              <circle cx="40" cy="20" r="4" fill={COLORS.bundestag} /> {/* Mic Head */}
            </g>
          </svg>
        </div>

        {/* 2. Content Side */}
        <div style={{
          flex: "1 1 300px",
          padding: "3rem",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          background: "white"
        }}>
          <h2 id="introTitle" style={{ 
            fontSize: "1.75rem", 
            marginBottom: "1rem", 
            color: "#111827",
            lineHeight: 1.2
          }}>
            Welcome to the <br/>
            <span style={{ color: COLORS.talkshow }}>Mismatch</span> Barometer
          </h2>

          <p id="introText" style={{ 
            fontSize: "1.05rem", 
            lineHeight: 1.6, 
            color: "#4b5563",
            marginBottom: "2rem" 
          }}>
            Remember when the European Parliament started talking about banning

            conventional names for vegan substitutes?<br/><br/> Yeah, that was pretty wild,

            right?<br/><br/> How come that politicians seem to talk about

            arbitrary stuff, whilst the public is interested in vastly different

            things?
            <br/><br/>
            We analyzed thousands of minutes of{' '}
            <span style={{ color: COLORS.bundestag, fontWeight: 600 }}>Bundestag protocols</span>
            {' '}and{' '}
            <span style={{ color: COLORS.talkshow, fontWeight: 600 }}>Talkshows</span>
            {' '}to find out:
            <br />
            <i style={{ display: 'block', marginTop: '8px', color: '#111827' }}>
              <b>Who</b> is giving <b>what</b> more attention?
            </i>
          </p>

          <button 
            className="btn" 
            type="button" 
            onClick={closeIntro}
            style={{
              alignSelf: "flex-start",
              padding: "12px 24px",
              fontSize: "1rem",
              background: "#111827",
              color: "white",
              border: "none",
              borderRadius: "8px",
              cursor: "pointer",
              transition: "transform 0.2s"
            }}
            onMouseOver={(e) => e.currentTarget.style.transform = "scale(1.02)"}
            onMouseOut={(e) => e.currentTarget.style.transform = "scale(1)"}
          >
            Find out for yourself &rarr;
          </button>
        </div>

      </div>
    </div>
  )}

    <header className="hero">
      <h1 className="heroTitle">Mismatch Barometer</h1>

      <p className="muted">
        Last updated: {formatGermanDateTime(summary.last_updated)}
      </p>

      <div className="heroCard">
        <h2>{hero.label}</h2>
        {!!hero.headline && <p className="headline">{hero.headline}</p>}

        <div className="metricRow">
          <div className="metric">
            <div className="metricValue">{hero.bundestag_minutes}</div>
            <div className="metricLabel">minutes in Bundestag</div>
          </div>

          <div className="metric">
            <div className="metricValue">{hero.talkshow_minutes}</div>
            <div className="metricLabel">minutes in Talkshows</div>
          </div>

          <div className="metric">
            <div className="metricValue">
              {/* The Score/Gauge */}
              <MismatchScoreLabel score={hero.mismatch_score ?? 0} decimals={1} />
            </div>
            
            {/* The Label with the Info Tooltip */}
            <div 
              className="metricLabel" 
              style={{ 
                display: 'flex', 
                alignItems: 'center', 
                justifyContent: 'center', // Centers it in the hero metric column
                gap: '4px', 
                cursor: 'help' 
              }}
            >
              Mismatch score
              
              <span className="infoWrap" style={{ position: 'relative' }}>
                {/* Transparent 'i' Icon */}
                <span 
                  className="infoIcon" 
                  style={{ 
                    width: '12px', 
                    height: '12px', 
                    fontSize: '9px', 
                    lineHeight: '11px',
                    backgroundColor: 'transparent',
                    border: '1px solid #9ca3af',
                    color: '#9ca3af',
                    borderRadius: '50%',
                    textAlign: 'center',
                    display: 'inline-block',
                    verticalAlign: 'middle'
                  }}
                >
                  i
                </span>
                
                {/* The Tooltip Dropdown */}
                <span 
                  className="infoTooltip" 
                  style={{ 
                    position: 'absolute',
                    top: '24px', // Drops down
                    left: '50%', 
                    transform: 'translateX(-50%)',
                    zIndex: 50,
                    width: '220px', 
                    fontSize: '0.75rem',
                    lineHeight: '1.4',
                    fontWeight: 'normal',
                    textAlign: 'left',
                    color: '#fff',
                    backgroundColor: '#1f2937', 
                    padding: '8px 12px',
                    borderRadius: '6px',
                    boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
                    whiteSpace: 'normal',
                    textTransform: 'none' // Resets any uppercase from metricLabel
                  }}
                >
                  <strong>Calculation:</strong><br/>
                  We compare normalized attention shares. The attention shares are calculated with the normalized speech time for a given topic in percentages.
                  A score of <b>X</b> means one side gave this topic <b>X</b> times more relative attention than the other. <br/><br/>
                  {/* Styled Formula Block */}
                  {/* 1. Definition Formula */}
                  <div style={{ 
                    fontFamily: '"Times New Roman", Times, serif', 
                    fontSize: '1rem', 
                    textAlign: 'center',
                    marginBottom: '8px'
                  }}>
                    <span style={{ fontStyle: 'italic' }}>share</span>
                    {' = '}
                    
                    {/* Visual Fraction */}
                    <div style={{ display: 'inline-flex', flexDirection: 'column', verticalAlign: 'middle', margin: '0 4px' }}>
                      <span style={{ borderBottom: '1px solid rgba(255,255,255,0.5)', paddingBottom: '1px', fontStyle: 'italic' }}>
                        topic_time
                      </span>
                      <span style={{ paddingTop: '1px', fontStyle: 'italic' }}>
                        total_time
                      </span>
                    </div>
                  </div>

                  {/* 2. Ratio Formula */}
                  <div style={{ 
                    fontFamily: '"Times New Roman", Times, serif', 
                    fontSize: '1rem', 
                    textAlign: 'center' 
                  }}>
                    <span style={{ fontStyle: 'normal' }}>Ratio</span>
                    {' = '}
                    
                    {/* Visual Fraction */}
                    <div style={{ display: 'inline-flex', flexDirection: 'column', verticalAlign: 'middle', margin: '0 4px' }}>
                      <span style={{ 
                        borderBottom: '1px solid rgba(255,255,255,0.5)', 
                        paddingBottom: '1px', 
                        color: COLORS.bundestag, // Blue
                        fontStyle: 'italic'
                      }}>
                        share_BT
                      </span>
                      <span style={{ 
                        paddingTop: '1px', 
                        color: COLORS.talkshow, // Orange
                        fontStyle: 'italic'
                      }}>
                        share_TV
                      </span>
                    </div>
                  </div>
                </span>
              </span>
            </div>
          </div>
        </div>

        <button
          className="btn"
          type="button"
          onClick={() => onSelectTopic?.(hero.slug)}
        >
          Explore this topic
        </button>


          <div className="heroCharts">
            <div className="chartCard" style={{ height: 220 }}>
              <h4 style={{ margin: "0 0 8px" }}>Time split</h4>

              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={heroPie}
                    dataKey="value"
                    nameKey="name"
                    innerRadius={45}
                    outerRadius={75}
                    paddingAngle={2}
                    isAnimationActive={false}
                    label={false //(entry) =>
                      //`${entry.name}: ${formatPercent(Number(entry.value))}` 
                    }
                  >
                    {heroPie.map((entry) => (
                      <Cell
                        key={entry.name}
                        fill={
                          entry.name === "Bundestag"
                            ? COLORS.bundestag
                            : COLORS.talkshow
                        }
                      />
                    ))}
                  </Pie>

                  <ReTooltip formatter={(v) => formatPercent(Number(v))} />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>

              {heroPie.length === 0 && (
                <p className="muted" style={{ marginTop: 8 }}>
                  No share data available.
                </p>
              )}
            </div>

            <div className="chartCard" style={{ height: 220 }}>
              <h4 style={{ margin: "0 0 8px" }}>Monthly Normalized Attention Share</h4>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart
                    data={heroSeries}
                    margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" />

                    {/* Y axis as percentages */}
                    <YAxis tickFormatter={(v) => `${v.toFixed(1)} %`} />

                    {/* Tooltip as percentages */}
                    <Tooltip formatter={(v) => `${Number(v).toFixed(1)} %`} />

                    <Line
                      type="monotone"
                      dataKey="bt_normalized_perc"
                      dot={false}
                      strokeWidth={2}
                      isAnimationActive={false}
                      name="Bundestag (normalized %)"
                      stroke={COLORS.bundestag}
                    />
                    <Line
                      type="monotone"
                      dataKey="ts_normalized_perc"
                      dot={false}
                      strokeWidth={2}
                      isAnimationActive={false}
                      name="Talkshows (normalized %)"
                      stroke={COLORS.talkshow}
                    />
                  </LineChart>
                </ResponsiveContainer>
              {heroSeries.length === 0 && (
                <p className="muted" style={{ marginTop: 8 }}>
                  No timeseries available.
                </p>
              )}
            </div>
          </div>
        </div>
      </header>
          <section className="section">
        <h3>Overall snapshot</h3>
        <div className="stats">
          <div className="stat">
            <b>{summary.overall_stats?.total_topics ?? "—"} Topics</b>
            <span>in total </span>
          </div>
         <div className="stat">
            <b>
              {summary.overall_stats?.avg_abs_mismatch
                ? `${Math.pow(2, Number(summary.overall_stats.avg_abs_mismatch)).toFixed(1)}x`
                : "—"}
            </b>
            <span>average mismatch</span>
          </div>
          <div className="stat">
          <b style={{ color: COLORS.bundestag }}>
            {summary.overall_stats?.topics_more_parliament ?? "—"} Topics
          </b>
          <span> more attention in the Bundestag</span>
        </div>

        <div className="stat">
          <b style={{ color: COLORS.talkshow }}>
            {summary.overall_stats?.topics_more_talkshows ?? "—"} Topics
          </b>
          <span> more attention in Talkshows</span>
        </div>
        </div>
      </section>

      <section className="section">
        <h3>Top other topics</h3>
        <p className="muted">
          Twenty more topics with the largest normalized attention gap.
        </p>

        <div className="grid">
          {topOthers.map((t) => (
            <button
              key={t.slug}
              className="card"
              type="button"
              onClick={() => onSelectTopic?.(t.slug)}
            >
              <div className="cardTitle">{t.label}</div>
              <div className="cardMeta">
                <span>
                  <MismatchScoreLabel score={t.mismatch_score} decimals={1} />
                </span>
                {/*<span>
                  Δ norm: <b>{Number(t.norm_delta ?? 0).toFixed(1)}</b>
                </span>
                <span>
                  BT: <b>{t.bundestag_minutes}</b> min
                </span>
                <span>
                  TV: <b>{t.talkshow_minutes}</b> min
                </span>*/}
              </div>
            </button>
                ))}
        </div>

        {topOthers.length === 0 && (
          <p className="muted">No additional topics available.</p>
        )}
      </section>

      
    </div>
  );
}


