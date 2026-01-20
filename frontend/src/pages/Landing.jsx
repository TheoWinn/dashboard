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

      const bundestag =
        row.bundestag_minutes ??
        row.bt_minutes ??
        row.bundestag ??
        row.bt ??
        0;

      const talkshow =
        row.talkshow_minutes ??
        row.tv_minutes ??
        row.talkshow ??
        row.tv ??
        0;

      // you could also use norm_delta here if you prefer
      const mismatch =
        row.mismatch_score ??
        row.norm_delta ??
        Math.abs(Number(talkshow) - Number(bundestag));

      return {
        // keep full ISO string so the tooltip can show it nicely
        date: rawDate ? String(rawDate) : "",
        bundestag_minutes: Number(bundestag) || 0,
        talkshow_minutes: Number(talkshow) || 0,
        mismatch_score: Number(mismatch) || 0,
        // keep the original window info around for richer tooltips later
        window_start: row.window_start ?? null,
        window_end: row.window_end ?? null,
      };
    })
    .filter((d) => d.date);
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

  const hero = summary?.hero_topic;

  const topOthers = useMemo(() => {
    if (!summary?.featured_topics?.length) return [];
    const heroSlug = hero?.slug;
    return summary.featured_topics
      .filter((t) => t?.slug && t.slug !== heroSlug)
      .slice(0, 20);
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
    { name: "Talk shows", value: Number(hero.ts_share) || 0 },
  ].filter((d) => d.value > 0);

  const heroSeries = normalizeTimeseries(hero.timeseries);

return (
  <div className="container">
    {showIntro && (
      <div className="modalBackdrop modalFadeIn" onClick={closeIntro}>
        <div
          className="modalCard"
          role="dialog"
          aria-modal="true"
          aria-labelledby="introTitle"
          aria-describedby="introText"
          onClick={(e) => e.stopPropagation()}
        >
          <h2 id="introTitle">Welcome to the Mismatch Barometer</h2>

          <p id="introText">
            Remember when the European Parliament started talking about banning
            conventional names for vegan substitues? Yeah, that was pretty wild,
            and somewhat weird? How come that politicians seem to talk about
            arbitrary stuff, whilst the public is interested in vastly different
            things? With this dashboard, we are trying to seek out which other
            topic mismatches are present between the Bundestag and German
            talkshows.
          </p>

          <button className="btn" type="button" onClick={closeIntro}>
            Check out dashboard
          </button>
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
            <div className="metricLabel">minutes in talk shows</div>
          </div>

          <div className="metric">
            <div className="metricValue">
              <MismatchScoreLabel score={hero.mismatch_score ?? 0} decimals={3} />
            </div>
            <div className="metricLabel">mismatch score</div>
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
                    label={(entry) =>
                      `${entry.name}: ${formatPercent(Number(entry.value))}`
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
              <h4 style={{ margin: "0 0 8px" }}>Daily attention</h4>

              <ResponsiveContainer width="100%" height="100%">
                <LineChart
                  data={heroSeries}
                  margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date"/>
                  <YAxis />
                  <Tooltip />
                  <Line
                    type="monotone"
                    dataKey="bundestag_minutes"
                    dot={false}
                    strokeWidth={2}
                    isAnimationActive={false}
                    name="Bundestag"
                    stroke={COLORS.bundestag}
                  />
                  <Line
                    type="monotone"
                    dataKey="talkshow_minutes"
                    dot={false}
                    strokeWidth={2}
                    isAnimationActive={false}
                    name="Talk shows"
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
                  Mismatch: <b>{Number(t.mismatch_score ?? 0).toFixed(3)}</b>
                </span>
                <span>
                  Δ norm: <b>{Number(t.norm_delta ?? 0).toFixed(1)}</b>
                </span>
                <span>
                  BT: <b>{t.bundestag_minutes}</b> min
                </span>
                <span>
                  TV: <b>{t.talkshow_minutes}</b> min
                </span>
              </div>
            </button>
          ))}
        </div>

        {topOthers.length === 0 && (
          <p className="muted">No additional topics available.</p>
        )}
      </section>

      <section className="section">
        <h3>Overall snapshot</h3>
        <div className="stats">
          <div className="stat">
            <b>{summary.overall_stats?.total_topics ?? "—"}</b>
            <span>Total topics</span>
          </div>
          <div className="stat">
            <b>{summary.overall_stats?.avg_abs_mismatch ?? "—"}</b>
            <span>Avg |mismatch|</span>
          </div>
          <div className="stat">
            <b>{summary.overall_stats?.topics_more_parliament ?? "—"}</b>
            <span>More Bundestag</span>
          </div>
          <div className="stat">
            <b>{summary.overall_stats?.topics_more_talkshows ?? "—"}</b>
            <span>More talk shows</span>
          </div>
        </div>
      </section>
    </div>
  );
}


