const base = import.meta.env.BASE_URL;

export async function fetchSummary() {
  const res = await fetch(`${base}data/summary.json`);
  if (!res.ok) throw new Error(`Failed to load summary.json (${res.status})`);
  return res.json();
}

export async function fetchTopic(slug) {
  const res = await fetch(`${base}data/topics/${slug}.json`);
  if (!res.ok) throw new Error(`Failed to load topic ${slug} (${res.status})`);
  return res.json();
}
