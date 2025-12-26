import { useEffect, useState } from "react";
import { fetchSummary } from "../lib/api.js";

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
        </div>
      </header>

      <section className="section">
        <h3>Explore topics</h3>
        <p className="muted">
          Click a topic to see daily attention over time and overall time allocation.
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
