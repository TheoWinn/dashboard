import { useEffect, useMemo, useState } from "react";
import { fetchTopic } from "../lib/api.js";
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

/**
 * Adjust this to match your API timeseries shape.
 * Expected output shape:
 * [{ date: "2025-12-01", bundestag_minutes: 12, talkshow_minutes: 30, mismatch_score: 18 }, ...]
 */
function normalizeTimeseries(ts) {
  if (!Array.isArray(ts)) return [];

  // Common possibilities:
  // - { date, bundestag_minutes, talkshow_minutes }
  // - { day, bt_minutes, tv_minutes }
  // - { date, bundestag, talkshow }
  return ts
    .map((row) => {
      const date =
        row.date ?? row.day ?? row.dt ?? row.timestamp ?? row.week ?? null;

      const bundestag =
        row.bundestag_minutes ??
        row.bt_minutes ??
        row.bundestag ??
        row.bt ??
        0;

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

export default function Topic({ slug, onBack }) {
  const [topic, setTopic] = useState(null);
  const [err, setErr] = useState(null);

  useEffect(() => {
    setTopic(null);
    setErr(null);

    fetchTopic(slug)
      .then(setTopic)
      .catch((e) => setErr(String(e)));
  }, [slug]);

  const pieData = useMemo(() => {
    if (!topic) return [];
    return [
      { name: "Bundestag", value: Number(topic.totals?.bundestag_minutes) || 0 },
      { name: "Talk shows", value: Number(topic.totals?.talkshow_minutes) || 0 },
    ].filter((d) => d.value > 0);
  }, [topic]);

  const series = useMemo(() => {
    if (!topic) return [];
    return normalizeTimeseries(topic.timeseries);
  }, [topic]);

  return (
    <div className="container">
      <button className="back" onClick={onBack} type="button">
        ← Back
      </button>

      {err && <div className="error">Error: {err}</div>}
      {!err && !topic && <p>Loading…</p>}

      {topic && (
        <>
          <h1>{topic.label}</h1>
          <p className="muted">{topic.description}</p>

          <div className="stats">
            <div className="stat">
              <b>{topic.totals.bundestag_minutes}</b>
              <span>Bundestag min</span>
            </div>
            <div className="stat">
              <b>{topic.totals.talkshow_minutes}</b>
              <span>Talk show min</span>
            </div>
            <div className="stat">
              <b>{topic.mismatch_score}</b>
              <span>Mismatch score</span>
            </div>
          </div>

          {/* Charts */}
          <section className="section" style={{ marginTop: "2rem" }}>
            <h3>Mismatch split (Bundestag vs Talk shows)</h3>
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
                    label={(entry) => `${entry.name}: ${entry.value}`}
                  >
                    {/* Colors are optional; remove Cells to use defaults */}
                    <Cell />
                    <Cell />
                  </Pie>
                  <ReTooltip formatter={(v) => formatMinutes(Number(v))} />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
              {pieData.length === 0 && (
                <p className="muted" style={{ marginTop: 8 }}>
                  No minutes available to plot.
                </p>
              )}
            </div>
          </section>

          <section className="section" style={{ marginTop: "2rem" }}>
            <h3>Daily attention over time</h3>
            <div className="chartCard" style={{ height: 360 }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={series} margin={{ top: 10, right: 20, bottom: 0, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" tickMargin={8} />
                  <YAxis tickFormatter={(v) => `${v}`} />
                  <Tooltip
                    formatter={(value, name) => {
                      if (name === "mismatch_score") return [value, "Mismatch"];
                      if (name === "bundestag_minutes") return [value, "Bundestag"];
                      if (name === "talkshow_minutes") return [value, "Talk shows"];
                      return [value, name];
                    }}
                  />
                  <Legend />

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

                  {/* Optional: mismatch as third line */}
                  <Line
                    type="monotone"
                    dataKey="mismatch_score"
                    dot={false}
                    strokeWidth={2}
                    isAnimationActive={false}
                    name="Mismatch"
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

          {/* Keep your debug output if you want */}
          <h3 style={{ marginTop: "2rem" }}>Timeseries (raw)</h3>
          <pre className="pre">{JSON.stringify(topic.timeseries, null, 2)}</pre>
        </>
      )}
    </div>
  );
}
