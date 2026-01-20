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

function normalizeTimeseries(ts) {
  if (!Array.isArray(ts)) return [];

  return ts
    .map((row) => {
      const rawDate =
        row.window_start ??
        row.date ??
        row.day ??
        row.dt ??
        row.timestamp ??
        row.week ??
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

export default function Topic({ slug, onBack, onSelectTopic }) {
  const [topic, setTopic] = useState(null);
  const [summary, setSummary] = useState(null);
  const [err, setErr] = useState(null);

  useEffect(() => {
    let cancelled = false;

    setTopic(null);
    setErr(null);

    fetchTopic(slug)
      .then((data) => {
        if (!cancelled) setTopic(data);
      })
      .catch((e) => {
        if (!cancelled) setErr(String(e));
      });

    return () => {
      cancelled = true;
    };
  }, [slug]);

  // fetch summary once (for "top other topics")
  useEffect(() => {
    let cancelled = false;

    fetchSummary()
      .then((data) => {
        if (!cancelled) setSummary(data);
      })
      .catch(() => {});

    return () => {
      cancelled = true;
    };
  }, []);

  const mismatchScore = useMemo(() => {
    const ms = topic?.mismatch_score ?? topic?.mismatch ?? topic?.totals?.mismatch_score;
    return Number(ms ?? 0);
  }, [topic]);

  const pieData = useMemo(() => {
    if (!topic) return [];
    return [
      { name: "Bundestag", value: Number(topic?.totals?.bt_share) || 0 },
      { name: "Talk shows", value: Number(topic?.totals?.ts_share) || 0 },
    ].filter((d) => d.value > 0);
  }, [topic]);

  const series = useMemo(() => {
    if (!topic) return [];
    return normalizeTimeseries(topic?.timeseries);
  }, [topic]);

  const topOthers = useMemo(() => {
    if (!summary?.featured_topics?.length) return [];
    return summary.featured_topics
      .filter((t) => t?.slug && t.slug !== slug)
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
              <span>Talk show min</span>
            </div>

            <div className="stat">
              <b>
                <MismatchScoreLabel score={mismatchScore} decimals={3} />
              </b>
              <span>Mismatch score</span>
            </div>

            <div className="stat">
              <b>{Number(topic?.norm_delta ?? 0).toFixed(1)}</b>
              <span>Δ normalized speech time</span>
            </div>
          </div>

          {/* Top 4 other topics */}
          {onSelectTopic && (
            <section className="section" style={{ marginTop: "2rem" }}>
              <h3>Top other topics</h3>
              <div className="grid">
                {topOthers.map((t) => {
                  const otherMismatch = Number(
                    t?.mismatch_score ?? t?.mismatch ?? t?.totals?.mismatch_score ?? 0
                  );

                  return (
                    <button
                      key={t.slug}
                      className="card"
                      type="button"
                      onClick={() => onSelectTopic(t.slug)}
                    >
                      <div className="cardTitle">{t.label}</div>
                      <div className="cardMeta">
                        <span>
                          Mismatch:{" "}
                          <b>
                            <MismatchScoreLabel score={otherMismatch} />
                          </b>
                        </span>
                        <span>
                          Δ norm: <b>{Number(t?.norm_delta ?? 0).toFixed(1)}</b>
                        </span>
                        <span>
                          BT: <b>{Number(t?.bundestag_minutes ?? t?.totals?.bundestag_minutes ?? 0)}</b>{" "}
                          min
                        </span>
                        <span>
                          TV: <b>{Number(t?.talkshow_minutes ?? t?.totals?.talkshow_minutes ?? 0)}</b>{" "}
                          min
                        </span>
                      </div>
                    </button>
                  );
                })}
              </div>
            </section>
          )}

          {/* Charts */}
          <section className="section" style={{ marginTop: "2rem" }}>
            <h3 style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              Time Allocation Share (Bundestag vs Talk shows)
              <span className="infoWrap">
                <span className="infoIcon">?</span>
                <span className="infoTooltip">
                  <strong>Definitions</strong>
                  <br />
                  <br />
                  <strong>bt_normalized_perc</strong>
                  <br />
                  Topic speech time in Bundestag
                  <br />
                  ÷ overall speech time in Bundestag
                  <br />
                  <br />
                  <strong>ts_normalized_perc</strong>
                  <br />
                  Topic speech time in Talkshows
                  <br />
                  ÷ overall speech time in Talkshows
                  <br />
                  <br />
                  <strong>bt_share</strong>
                  <br />
                  bt_normalized_perc
                  <br />
                  ÷ (bt_normalized_perc + ts_normalized_perc)
                  <br />
                  <br />
                  <strong>ts_share</strong>
                  <br />
                  ts_normalized_perc
                  <br />
                  ÷ (bt_normalized_perc + ts_normalized_perc)
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
                    label={(entry) =>
                      `${entry.name}: ${formatPercent(Number(entry.value))}`
                    }
                  >
                    {pieData.map((entry) => (
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

              {pieData.length === 0 && (
                <p className="muted" style={{ marginTop: 8 }}>
                  No share data available to plot.
                </p>
              )}
            </div>
          </section>

          <section className="section" style={{ marginTop: "2rem" }}>
            <h3>Monthly Normalized Attention Share</h3>
            <div className="chartCard" style={{ height: 360 }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart
                  data={series}
                  margin={{ top: 10, right: 20, bottom: 0, left: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" tickMargin={8} />
                  <YAxis tickFormatter={(v) => `${v.toFixed(1)} %`} />
                  <Tooltip formatter={(v) => `${Number(v).toFixed(1)} %`} />
                  <Legend />
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
                    name="Talk shows (normalized %)"
                    stroke={COLORS.talkshow}
                  />
                </LineChart>
              </ResponsiveContainer>

              {series.length === 0 && (
                <p className="muted" style={{ marginTop: 8 }}>
                  No timeseries data available to plot.
                </p>
              )}
            </div>
          </section>

          {/*<h3 style={{ marginTop: "2rem" }}>Timeseries (raw)</h3>
          <pre className="pre">{JSON.stringify(topic?.timeseries ?? [], null, 2)}</pre>*/}
        </>
      )}
    </div>
  );
}
