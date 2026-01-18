export default function MismatchScoreLabel({
  score,
  decimals = 3,
  text = `Shows the log-ratio between Bundestag and talk show coverage for this topic.
A score of 0 means “equal emphasis”; positive values mean the topic is relatively more prominent in Bundestag, negative values mean it’s relatively more prominent in talk shows.
The log metric is not bounded (it can be negative or positive without a fixed min/max).`,
}) {
  const n = Number(score);
  const hasScore = Number.isFinite(n);
  const tooltipId = "mismatch-tooltip";

  return (
    <span
      className="mismatchInline"
      style={{ display: "inline-flex", alignItems: "center", gap: 8 }}
    >
      <span style={{ fontVariantNumeric: "tabular-nums" }}>
        {hasScore ? n.toFixed(decimals) : "—"}
      </span>

      <span className="mismatchValue" style={{ fontVariantNumeric: "tabular-nums" }}>
        {hasScore ? n.toFixed(decimals) : "—"}
      </span>

      <span className="infoWrap" style={{ position: "relative", display: "inline-flex" }}>
        <button
          type="button"
          aria-describedby={tooltipId}
          className="infoIcon"
          style={{
            width: 18,
            height: 18,
            borderRadius: "50%",
            border: "1px solid currentColor",
            background: "transparent",
            fontSize: 12,
            lineHeight: "16px",
            padding: 0,
            cursor: "pointer",
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          i
        </button>

        <span
          id={tooltipId}
          role="tooltip"
          className="infoTooltip"
          style={{
            display: "none",
            position: "absolute",
            top: "120%",
            left: "50%",
            transform: "translateX(-50%)",
            width: 300,
            padding: 12,
            borderRadius: 10,
            background: "white",
            color: "#111",
            boxShadow: "0 8px 30px rgba(0,0,0,0.15)",
            zIndex: 50,
            textAlign: "left",
            whiteSpace: "pre-line",
          }}
        >
          {text}
        </span>
      </span>

      <style>{`
        .infoWrap:hover .infoTooltip,
        .infoWrap:focus-within .infoTooltip {
          display: block !important;
        }
      `}</style>
    </span>
  );
}
