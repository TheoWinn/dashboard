import { createClient } from "@supabase/supabase-js";
import fs from "fs/promises";

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

const { data: topics } = await supabase
  .from("topic_summary")
  .select("*");

await fs.writeFile(
  "public/data/summary.json",
  JSON.stringify({
    last_updated: new Date().toISOString(),
    featured_topics: topics
  }, null, 2)
);