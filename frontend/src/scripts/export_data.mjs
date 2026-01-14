import dotenv from "dotenv";
import path from "path";
import { fileURLToPath } from "url";

import { createClient } from "@supabase/supabase-js";
import fs from "fs/promises";

// --- Robust .env loading (repo-root/.env) ---
// export-data.mjs is at: repo-root/Frontend/scripts/export-data.mjs
// repo-root/.env is:    repo-root/.env
// so: scripts -> Frontend (..) -> repo-root (..) -> .env
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

dotenv.config({
  path: path.join(__dirname, "..", "..", "..", ".env"),
});

// Optional: fail fast if env vars are missing
if (!process.env.SUPABASE_URL) {
  throw new Error(
    "SUPABASE_URL is missing. Expected it in repo-root/.env (two levels above Frontend/scripts)."
  );
}
if (!process.env.SUPABASE_ANON_KEY) {
  throw new Error(
    "SUPABASE_ANON_KEY is missing. Expected it in repo-root/.env."
  );
}

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_ANON_KEY // use ONLY in CI/scripts, never in browser
);

const OUT_DIR = "public/data";
const TOPICS_DIR = path.join(OUT_DIR, "topics");

function makeSlug(topicId) {
  return `t-${topicId}`;
}

// Postgres interval often comes back as a string like:
// "01:23:45", "00:05:12.345", or sometimes "1 day 02:03:04"
function intervalToMinutes(v) {
  if (v == null) return 0;

  const s = String(v).trim();
  if (!s) return 0;

  let days = 0;
  let timePart = s;

  const dayMatch = s.match(/(\d+)\s+day[s]?\s+(.*)/i);
  if (dayMatch) {
    days = Number(dayMatch[1]) || 0;
    timePart = dayMatch[2] || "0:0:0";
  }

  const parts = timePart.split(":");
  if (parts.length < 2) return 0;

  const h = Number(parts[0]) || 0;
  const m = Number(parts[1]) || 0;

  // seconds part can include decimals
  const secPart = parts[2] ?? "0";
  const sec = Number(String(secPart).split(".")[0]) || 0;

  const totalSeconds = days * 86400 + h * 3600 + m * 60 + sec;
  return Math.round(totalSeconds / 60);
}

function safeText(v) {
  if (v == null) return "";
  return String(v);
}

function safeNum(v) {
  const n = Number(v);
  return Number.isFinite(n) ? n : 0;
}

async function main() {
  await fs.rm(TOPICS_DIR, { recursive: true, force: true });
  await fs.mkdir(TOPICS_DIR, { recursive: true });
  // Pull from dashboard schema
  const { data: rows, error } = await supabase
    .schema("dashboard")
    .from("topics_view")
    .select(
      [
        "topic_id",
        "topic_label",
        "topic_keywords",
        "topic_duration_bt",
        "topic_duration_ts",
        "mismatch_ppoints",
        "mismatch_log_ratio",
        "bt_share",
        "ts_share",
        "bt_normalized_perc",
        "ts_normalized_perc"
      ].join(",")
    );

  if (error) throw error;
  console.log(
    "DEBUG keys in first row:",
    rows?.[0] ? Object.keys(rows[0]) : "(no rows)"
  );
  console.log(
    "DEBUG first row shares:",
    rows?.[0]?.bt_share,
    rows?.[0]?.ts_share
  );

  const n = rows?.length ?? 0;
  const nBtNonNull = (rows ?? []).filter((r) => r.bt_share != null).length;
  const nTsNonNull = (rows ?? []).filter((r) => r.ts_share != null).length;
  console.log(
    `DEBUG rows=${n}  bt_share non-null=${nBtNonNull}  ts_share non-null=${nTsNonNull}`
  );

  const topics = (rows ?? []).map((r) => {
    const bundestag_minutes = intervalToMinutes(r.topic_duration_bt);
    const talkshow_minutes = intervalToMinutes(r.topic_duration_ts);

    // Pick ONE mismatch metric to expose in the UI:
    // - mismatch_ppoints is easy to interpret (-100..100)
    const mismatch_score = safeNum(r.mismatch_ppoints);
    const bt_norm = safeNum(r.bt_normalized_perc);
    const ts_norm = safeNum(r.ts_normalized_perc);
    const norm_delta = Math.abs(bt_norm - ts_norm);

    return {
      topic_id: r.topic_id,
      slug: makeSlug(r.topic_id),
      label: safeText(r.topic_label) || `Topic ${r.topic_id}`,
      keywords: safeText(r.topic_keywords),
      bundestag_minutes,
      talkshow_minutes,
      mismatch_score,
      bt_share: safeNum(r.bt_share),
      ts_share: safeNum(r.ts_share),
      bt_normalized_perc: safeNum(r.bt_normalized_perc),
      ts_normalized_perc: safeNum(r.ts_normalized_perc),
      norm_delta
    };
  });

  // Choose "featured" topics shown on landing:
  // Here: top 20 by delta between normalized speechtime
  const featured_topics = [...topics]
    .sort((a, b) => (b.norm_delta ?? 0) - (a.norm_delta ?? 0))
    .slice(0, 20)
    .map((t) => ({
      slug: t.slug,
      label: t.label,
      bundestag_minutes: t.bundestag_minutes,
      talkshow_minutes: t.talkshow_minutes,
      mismatch_score: t.mismatch_score,
      bt_share: t.bt_share,
      ts_share: t.ts_share,
      bt_normalized_perc: t.bt_normalized_perc,
      ts_normalized_perc: t.ts_normalized_perc,
      norm_delta: t.norm_delta,
    }));

  // Hero topic: biggest absolute mismatch
  const hero =
    [...topics].sort((a, b) => (b.norm_delta ?? 0) - (a.norm_delta ?? 0))[0] ??
    null;

  // Overall stats (landing bottom section)
  const total_topics = topics.length;

  const avg_abs_mismatch =
    total_topics === 0
      ? 0
      : Math.round(
          (topics.reduce((acc, t) => acc + Math.abs(t.mismatch_score), 0) /
            total_topics) *
            100
        ) / 100;

  const topics_more_parliament = topics.filter((t) => t.mismatch_score > 0).length;
  const topics_more_talkshows = topics.filter((t) => t.mismatch_score < 0).length;

  // Write per-topic JSONs (Topic.jsx)
  for (const t of topics) {
    const topicJson = {
      slug: t.slug,
      label: t.label,
      description: t.keywords ? `Keywords: ${t.keywords}` : "",
      mismatch_score: t.mismatch_score,
      totals: {
        bundestag_minutes: t.bundestag_minutes,
        talkshow_minutes: t.talkshow_minutes,
        bt_share: t.bt_share,
        ts_share: t.ts_share,
        bt_normalized_perc: t.bt_normalized_perc,
        ts_normalized_perc: t.ts_normalized_perc
      },
      timeseries: [], // intentionally empty for now
    };

    await fs.writeFile(
      path.join(TOPICS_DIR, `${t.slug}.json`),
      JSON.stringify(topicJson, null, 2),
      "utf-8"
    );
  }

  // Write summary JSON (Landing.jsx)
  const summaryJson = {
    last_updated: new Date().toISOString(),
    hero_topic: hero
      ? {
          slug: hero.slug,
          label: hero.label,
          headline: hero.keywords ? `Keywords: ${hero.keywords}` : "",
          bundestag_minutes: hero.bundestag_minutes,
          talkshow_minutes: hero.talkshow_minutes,
          mismatch_score: hero.mismatch_score,
          bt_share: hero.bt_share,
          ts_share: hero.ts_share,
          bt_normalized_perc: hero.bt_normalized_perc,
          ts_normalized_perc: hero.ts_normalized_perc,
          norm_delta: hero.norm_delta,
          timeseries: [], // intentionally empty for now
        }
      : null,
    featured_topics,
    overall_stats: {
      total_topics,
      avg_abs_mismatch,
      topics_more_parliament,
      topics_more_talkshows,
    },
  };

  await fs.mkdir(OUT_DIR, { recursive: true });
  await fs.writeFile(
    path.join(OUT_DIR, "summary.json"),
    JSON.stringify(summaryJson, null, 2),
    "utf-8"
  );

  console.log(
    `✅ Exported ${topics.length} topics → ${OUT_DIR}/summary.json and ${TOPICS_DIR}/*.json`
  );
}

main().catch((e) => {
  console.error("❌ Export failed:", e);
  process.exit(1);
});
