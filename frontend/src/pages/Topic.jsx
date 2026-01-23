import { useEffect, useMemo, useState } from "react";
import { fetchTopic, fetchSummary } from "../lib/api.js";
import MismatchScoreLabel from "../scripts/MismatchScoreLabel.jsx";

import {
  PieChart,
  Pie,
  Cell,
  Tooltip as ReTooltip,
  Legend,
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";
import { COLORS } from "../lib/colors.js";

// ... (Your helper functions: normalizeTimeseries, formatPercent) ...
function normalizeTimeseries(ts) {
  if (!Array.isArray(ts)) return [];
  return ts
    .map((row) => {
      const rawDate = row.window_start ?? row.date ?? row.day ?? row.dt ?? row.timestamp ?? row.week ?? null;
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

export default function Topic({ slug, onBack, onSelectTopic }) {
  const [topic, setTopic] = useState(null);
  const [summary, setSummary] = useState(null);
  const [err, setErr] = useState(null);

  // ... (Your useEffects for fetching data) ...
  useEffect(() => {
    let cancelled = false;
    setTopic(null);
    setErr(null);
    fetchTopic(slug)
      .then((data) => { if (!cancelled) setTopic(data); })
      .catch((e) => { if (!cancelled) setErr(String(e)); });
    return () => { cancelled = true; };
  }, [slug]);

  useEffect(() => {
    let cancelled = false;
    fetchSummary()
      .then((data) => { if (!cancelled) setSummary(data); })
      .catch(() => {});
    return () => { cancelled = true; };
  }, []);

  const mismatchScore = useMemo(() => {
    const ms = topic?.mismatch_score ?? topic?.mismatch ?? topic?.totals?.mismatch_score;
    return Number(ms ?? 0);
  }, [topic]);

  const pieData = useMemo(() => {
    if (!topic) return [];
    return [
      { name: "Bundestag", value: Number(topic?.totals?.bt_share) || 0 },
      { name: "Talkshows", value: Number(topic?.totals?.ts_share) || 0 },
    ].filter((d) => d.value > 0);
  }, [topic]);

  const series = useMemo(() => {
    if (!topic) return [];
    return normalizeTimeseries(topic?.timeseries);
  }, [topic]);

  // Updated to include the Ignore List
  const topOthers = useMemo(() => {
    if (!summary?.featured_topics?.length) return [];
    
    // Add any topics you want to remove here (must be lowercase)
    const IGNORED_LABELS = [
        "miscellaneous speech fragments", 
        // "other topic name"
    ];

    return summary.featured_topics
      // 1. Remove current topic
      .filter((t) => t?.slug && t.slug !== slug)
      // 2. Remove ignored topics
      .filter((t) => !IGNORED_LABELS.includes(t.label?.toLowerCase()))
      // 3. Take top 4
      .slice(0, 4);
  }, [summary, slug]);

  return (
    <div className="container">
      <button className="back" onClick={onBack} type="button">
        ← Back
      </button>

      {err && <div className="error">Error: {err}</div>}
      {!err && !topic && <p>Loading…</p>}

      {topic && (
        <>
          <h1>{topic?.label}</h1>
          {!!topic?.description && <p className="muted">{topic.description}</p>}

          <div className="stats">
            <div className="stat">
              <b>{Number(topic?.totals?.bundestag_minutes ?? 0)}</b>
              <span>Bundestag min</span>
            </div>

            <div className="stat">
              <b>{Number(topic?.totals?.talkshow_minutes ?? 0)}</b>
              <span>Talkshow min</span>
            </div>

            {/* === 1. MISMATCH SCORE WITH TOOLTIP === */}
            <div className="stat">
              <b>
                <MismatchScoreLabel score={mismatchScore} decimals={3} />
              </b>
              
              <span style={{ display: 'flex', alignItems: 'center', gap: '4px', cursor: 'help' }}>
                Mismatch score
                
                {/* The Wrapper */}
                <span className="infoWrap" style={{ position: 'relative' }}>
                  
                  {/* The Transparent 'i' Icon */}
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
                  
                  {/* The Tooltip Box */}
                  <span 
                    className="infoTooltip" 
                    style={{ 
                      position: 'absolute',
                      top: '24px', 
                      left: '50%', 
                      transform: 'translateX(-50%)',
                      zIndex: 50,
                      width: '240px', 
                      fontSize: '0.75rem',
                      lineHeight: '1.4',
                      fontWeight: 'normal',
                      textAlign: 'left',
                      color: '#fff',
                      backgroundColor: '#1f2937', 
                      padding: '12px',
                      borderRadius: '6px',
                      boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
                      whiteSpace: 'normal',
                      textTransform: 'none' 
                    }}
                  >
                    <div style={{ marginBottom: '12px' }}>
                      We compare normalized attention shares.
                      A score of <span style={{ fontFamily: '"Times New Roman", serif', fontStyle: 'italic' }}>x</span> means 
                      one side gave this topic <b style={{ fontFamily: '"Times New Roman", serif' }}>2<sup style={{ fontSize: '0.6em' }}>x</sup></b> times more attention.
                    </div>

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
                          color: COLORS.bundestag, 
                          fontStyle: 'italic'
                        }}>
                          share_BT
                        </span>
                        <span style={{ 
                          paddingTop: '1px', 
                          color: COLORS.talkshow, 
                          fontStyle: 'italic'
                        }}>
                          share_TV
                        </span>
                      </div>
                    </div>
                  </span>
                </span>
              </span>
            </div>

            {/* === 2. DELTA STAT WITH TOOLTIP === */}
            <div className="stat">
              <b>{Number(topic?.norm_delta ?? 0).toFixed(1)}</b>
              
              <span style={{ display: 'flex', alignItems: 'center', gap: '4px', cursor: 'help' }}>
                Δ normalized speech time
                
                {/* The Wrapper */}
                <span className="infoWrap" style={{ position: 'relative' }}>
                  
                  {/* The Transparent 'i' Icon */}
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
                  
                  {/* The Tooltip Box */}
                  <span 
                    className="infoTooltip" 
                    style={{ 
                      position: 'absolute',
                      top: '24px', 
                      left: '50%', 
                      transform: 'translateX(-50%)',
                      zIndex: 50,
                      width: '240px', 
                      fontSize: '0.75rem',
                      lineHeight: '1.4',
                      fontWeight: 'normal',
                      textAlign: 'left',
                      color: '#fff',
                      backgroundColor: '#1f2937', 
                      padding: '12px',
                      borderRadius: '6px',
                      boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
                      whiteSpace: 'normal',
                      textTransform: 'none'
                    }}
                  >
                    <div style={{ marginBottom: '12px' }}>
                      <strong>The "Volume" Gap:</strong><br/>
                      While the Mismatch Score shows the <i>ratio</i> (multiplier), this Delta shows the simple arithmetic difference in percentage points.
                      A Delta of 8 means this topic consumed 8 percentage points more of the total available time in one institution compared to the other.
                      High Deltas indicate 'Mainstream' disagreements, while High Mismatch Scores often highlight 'Niche' obsessions.
                    </div>

                    {/* Formula Block */}
                    <div style={{ 
                      fontFamily: '"Times New Roman", Times, serif', 
                      fontSize: '1rem', 
                      textAlign: 'center' 
                    }}>
                      <span style={{ fontStyle: 'italic' }}>Δ</span>
                      {' = '}
                      <span style={{ color: COLORS.bundestag, fontStyle: 'italic' }}>share_BT</span>
                      {' - '}
                      <span style={{ color: COLORS.talkshow, fontStyle: 'italic' }}>share_TV</span>
                    </div>
                  </span>
                </span>
              </span>
            </div>
          </div>

          {/* Charts Section 1: Pie Chart */}
          <section className="section" style={{ marginTop: "2rem" }}>
            <h3 style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              Time Allocation Share (Bundestag vs Talkshows)
              <span className="infoWrap">
                <span className="infoIcon">?</span>
                <span className="infoTooltip">
                  <strong>Intuition: </strong>
                  Read these graphs as 'Out of the entire time that this topic was talked about in general, X % came from the Bundestag and Y % came from Talkshows'
                </span>
              </span>
            </h3>

            <div className="chartCard" style={{ height: 320 }}>
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={pieData}
                    dataKey="value"
                    nameKey="name"
                    innerRadius={60}
                    outerRadius={95}
                    paddingAngle={2}
                    isAnimationActive={false}
                    label={(entry) => `${entry.name}: ${formatPercent(Number(entry.value))}`}
                  >
                    {pieData.map((entry) => (
                      <Cell key={entry.name} fill={entry.name === "Bundestag" ? COLORS.bundestag : COLORS.talkshow} />
                    ))}
                  </Pie>
                  <ReTooltip formatter={(v) => formatPercent(Number(v))} />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
              {pieData.length === 0 && <p className="muted" style={{ marginTop: 8 }}>No share data available to plot.</p>}
            </div>
          </section>

          {/* Charts Section 2: Line Chart */}
          <section className="section" style={{ marginTop: "2rem" }}>
            <h3>Monthly Normalized Attention Share</h3>
            <div className="chartCard" style={{ height: 360 }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={series} margin={{ top: 10, right: 20, bottom: 0, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" tickMargin={8} />
                  <YAxis tickFormatter={(v) => `${v.toFixed(1)} %`} />
                  <Tooltip formatter={(v) => `${Number(v).toFixed(1)} %`} />
                  <Legend />
                  <Line type="monotone" dataKey="bt_normalized_perc" dot={false} strokeWidth={2} isAnimationActive={false} name="Bundestag (normalized %)" stroke={COLORS.bundestag} />
                  <Line type="monotone" dataKey="ts_normalized_perc" dot={false} strokeWidth={2} isAnimationActive={false} name="Talkshows (normalized %)" stroke={COLORS.talkshow} />
                </LineChart>
              </ResponsiveContainer>
              {series.length === 0 && <p className="muted" style={{ marginTop: 8 }}>No timeseries data available to plot.</p>}
            </div>
          </section>

          {/* Top 4 other topics (Standard Cards - NO Tooltip) */}
          {onSelectTopic && (
            <section className="section" style={{ marginTop: "2rem" }}>
              <h3>Top other topics</h3>
              <div className="grid">
                {topOthers.map((t) => {
                  const otherMismatch = Number(t?.mismatch_score ?? t?.mismatch ?? t?.totals?.mismatch_score ?? 0);
                  return (
                    <button key={t.slug} className="card" type="button" onClick={() => onSelectTopic(t.slug)}>
                      <div className="cardTitle">{t.label}</div>
                      <div className="cardMeta">
                        <span>
                          Mismatch:{" "}
                          <b><MismatchScoreLabel score={otherMismatch} /></b>
                        </span>
                        <span>Δ norm: <b>{Number(t?.norm_delta ?? 0).toFixed(1)}</b></span>
                        <span>BT: <b>{Number(t?.bundestag_minutes ?? t?.totals?.bundestag_minutes ?? 0)}</b> min</span>
                        <span>TV: <b>{Number(t?.talkshow_minutes ?? t?.totals?.talkshow_minutes ?? 0)}</b> min</span>
                      </div>
                    </button>
                  );
                })}
              </div>
            </section>
          )}

        </>
      )}
    </div>
  );
}