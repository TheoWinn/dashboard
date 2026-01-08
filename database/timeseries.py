import pandas as pd
import numpy as np

df = pd.read_csv("../topicmodelling/data/raw_topics/topics_representations_2025.csv", encoding="utf-8", low_memory=False)

df["date"] = pd.to_datetime(df["date"], format="%Y-%m-%d", errors="coerce")
start = pd.Timestamp("2025-01-01")
end   = pd.Timestamp("2025-01-29")
period = df[df["date"].between(start, end, inclusive="left")]
period["speech_duration"] = np.where(
    period["source"].eq("bundestag"),
    period["transcript_end"].astype(float) - period["transcript_start"].astype(float),
    np.where(
        period["source"].eq("talkshow"),
        period["end"].astype(float) - period["start"].astype(float),
        np.nan, 
    ),
)


tmp = period.assign(
    speech_duration_bt=np.where(period["source"].eq("bundestag"), period["speech_duration"], 0.0),
    speech_duration_ts=np.where(period["source"].eq("talkshow"),  period["speech_duration"], 0.0),
)

g = tmp.groupby("topic", as_index=False)[["speech_duration_bt", "speech_duration_ts"]].sum()

td = pd.to_timedelta(g["speech_duration_bt"], unit="s") 
h = (td.dt.total_seconds() // 3600).astype("Int64")
m = ((td.dt.total_seconds() % 3600) // 60).astype("Int64")
sec = (td.dt.total_seconds() % 60)

g["speech_duration_bt"] = (
    h.map(lambda x: f"{x:03d}" if pd.notna(x) else None)
    + ":" + m.map(lambda x: f"{x:02d}" if pd.notna(x) else None)
    + ":" + sec.map(lambda x: f"{x:06.3f}" if pd.notna(x) else None)
)

td = pd.to_timedelta(g["speech_duration_ts"], unit="s") 
h = (td.dt.total_seconds() // 3600).astype("Int64")
m = ((td.dt.total_seconds() % 3600) // 60).astype("Int64")
sec = (td.dt.total_seconds() % 60)

g["speech_duration_ts"] = (
    h.map(lambda x: f"{x:03d}" if pd.notna(x) else None)
    + ":" + m.map(lambda x: f"{x:02d}" if pd.notna(x) else None)
    + ":" + sec.map(lambda x: f"{x:06.3f}" if pd.notna(x) else None)
)
print(g)