import { useEffect, useState } from "react";
import { fetchTopic } from "../lib/api.js";

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

          <h3 style={{ marginTop: "2rem" }}>Timeseries (mock)</h3>
          <pre className="pre">{JSON.stringify(topic.timeseries, null, 2)}</pre>
        </>
      )}
    </div>
  );
}
