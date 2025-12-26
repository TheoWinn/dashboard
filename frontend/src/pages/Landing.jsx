import { useEffect, useState } from "react";
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
} from "recharts";

function normalizeTimeseries(ts) {
  if (!Array.isArray(ts)) return [];
  return ts
    .map((row) => {
      const date = row.date ?? row.day ?? row.dt ?? row.timestamp ?? null;

      const bundestag =
        row.bundestag_minutes ?? row.bt_minutes ?? row.bundestag ?? row.bt ?? 0;

      const talkshow =
        row.talkshow_minutes ?? row.tv_minutes ?? row.talkshow ?? row.tv ?? 0;

      const mismatch =
        row.mismatch_score ??
        row.mismatch ??
        Math.abs(Number(talkshow) - Number(bundestag));

      return {
        date: String(date ?? ""),
        bundestag_minutes: Number(bundestag) || 0,
        talkshow_minutes: Number(talkshow) || 0,
        mismatch_score: Number(mismatch) || 0,
      };
    })
    .filter((d) => d.date);
}

function formatMinutes(v) {
  if (typeof v !== "number" || Number.isNaN(v)) return "";
  return `${v} min`;
}

export default function Landing({ onSelectTopic }) {
  const [summary, setSummary] = useState(null);
  const [err, setErr] = useState(null);

  useEffect(() => {
    fetchSummary()
      .then(setSummary)
      .catch((e) => setErr(String(e)));
  }, []);

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

  const hero = summary.hero_topic;

  const heroPie = [
    { name: "Bundestag", value: Number(hero.bundestag_minutes) || 0 },
    { name: "Talk shows", value: Number(hero.talkshow_minutes) || 0 },
  ].filter((d) => d.value > 0);

  const heroSeries = normalizeTimeseries(hero.timeseries);

  return (
    <div className="container">
      <header className="hero">
        <h1>Mismatch Barometer</h1>
        <p className="muted">Last updated: {summary.last_updated}</p>

        <div className="heroCard">
          <h2>{hero.label}</h2>
          <p className="headline">{hero.headline}</p>

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
              <div className="metricValue">{hero.mismatch_score}</div>
              <div className="metricLabel">mismatch score</div>
            </div>
          </div>

          <button className="btn" onClick={() => onSelectTopic(hero.slug)}>
            Explore this topic
          </button>

          {/* HERO CHARTS */}
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
                  />
                  <ReTooltip formatter={(v) => formatMinutes(Number(v))} />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>

              {heroPie.length === 0 && (
                <p className="muted" style={{ marginTop: 8 }}>
                  No minutes available.
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
                  <XAxis dataKey="date" hide />
                  <YAxis hide />
                  <Tooltip
                    formatter={(value, name) => {
                      if (name === "bundestag_minutes")
                        return [value, "Bundestag"];
                      if (name === "talkshow_minutes")
                        return [value, "Talk shows"];
                      if (name === "mismatch_score") return [value, "Mismatch"];
                      return [value, name];
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="bundestag_minutes"
                    dot={false}
                    strokeWidth={2}
                    isAnimationActive={false}
                    name="Bundestag"
                  />
                  <Line
                    type="monotone"
                    dataKey="talkshow_minutes"
                    dot={false}
                    strokeWidth={2}
                    isAnimationActive={false}
                    name="Talk shows"
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
        <h3>Explore topics</h3>
        <p className="muted">
          Click a topic to see daily attention over time and overall time
          allocation.
        </p>

        <div className="grid">
          {summary.featured_topics.map((t) => (
            <button
              key={t.slug}
              className="card"
              onClick={() => onSelectTopic(t.slug)}
              type="button"
            >
              <div className="cardTitle">{t.label}</div>
              <div className="cardMeta">
                <span>
                  Mismatch: <b>{t.mismatch_score}</b>
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
      </section>

      <section className="section">
        <h3>Overall snapshot</h3>
        <div className="stats">
          <div className="stat">
            <b>{summary.overall_stats.total_topics}</b>
            <span>Total topics</span>
          </div>
          <div className="stat">
            <b>{summary.overall_stats.avg_abs_mismatch}</b>
            <span>Avg |mismatch|</span>
          </div>
          <div className="stat">
            <b>{summary.overall_stats.topics_more_parliament}</b>
            <span>More Bundestag</span>
          </div>
          <div className="stat">
            <b>{summary.overall_stats.topics_more_talkshows}</b>
            <span>More talk shows</span>
          </div>
        </div>
      </section>
    </div>
  );
}
