export default function MismatchScoreLabel({ className = "" }) {
  return (
    <span className={`mismatchLabel ${className}`}>
      mismatch score{" "}
      <span className="infoWrap">
        <button
          type="button"
          className="infoIcon"
          aria-label="How mismatch score is calculated"
          aria-describedby="mismatchTip"
        >
          i
        </button>
        <span className="infoTooltip" id="mismatchTip" role="tooltip">
          Shows the log-ratio between Bundestag and talk show coverage for this
          topic. A score of 0 means “equal emphasis”; positive values mean the
          topic is relatively more prominent in Bundestag, negative values mean
          it’s relatively more prominent in talk shows. The log metric is not
          bounded (it can be negative or positive without a fixed min/max).
        </span>
      </span>
    </span>
  );
}
