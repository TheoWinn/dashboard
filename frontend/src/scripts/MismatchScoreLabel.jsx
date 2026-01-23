import { COLORS } from "../lib/colors.js";

export default function MismatchGauge({ 
  score, 
  decimals = 1,
  maxScoreCap = 4 // score of ±4 (16x difference) = Edge of the meter
}) {
  const n = Number(score);

  if (!Number.isFinite(n)) return <span>—</span>;

  // 1. Math: Map the score (-4 to +4) to a percentage (0% to 100%)
  // -4 (Talkshow Max) => 0%
  //  0 (Neutral)      => 50%
  // +4 (Bundestag Max) => 100%
  const clampedScore = Math.max(-maxScoreCap, Math.min(n, maxScoreCap));
  const positionPercent = ((clampedScore + maxScoreCap) / (maxScoreCap * 2)) * 100;

  // 2. Determine Active State
  const absScore = Math.abs(n);
  const isBundestag = n > 0;
  const isNeutral = absScore < 0.1; 

  const rawMultiplier = Math.pow(2, absScore);
  const labelText = `${rawMultiplier.toFixed(decimals)}x ${isBundestag ? "Bundestag" : "Talkshows"}`;

  // 3. Colors
  // We use a CSS gradient for the background track
  const trackGradient = `linear-gradient(90deg, ${COLORS.talkshow} 0%, #e5e7eb 50%, ${COLORS.bundestag} 100%)`;
  
  // The needle color matches the dominant side (or dark gray if neutral)
  const needleColor = isNeutral 
    ? '#374151' 
    : (isBundestag ? COLORS.bundestag : COLORS.talkshow);

  return (
    <div style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: '6px' }}>
      
      {/* The Meter Track */}
      <div style={{ 
        position: 'relative', 
        height: '10px', 
        background: trackGradient,
        borderRadius: '5px',
        width: '100%',
        boxShadow: 'inset 0 1px 2px rgba(0,0,0,0.1)' // Adds depth like a thermometer tube
      }}>
        
        {/* Center Tick (Optional: helps read the middle) 
        <div style={{
          position: 'absolute',
          left: '50%',
          top: 0,
          bottom: 0,
          width: '1px',
          background: 'rgba(255,255,255,0.6)',
        }} /> */ }

        {/* The Sliding Needle / Marker */}
        <div style={{
          position: 'absolute',
          top: '-3px', // Extend slightly above track
          bottom: '-3px', // Extend slightly below track
          left: `${positionPercent}%`,
          width: '4px',
          marginLeft: '-2px', // Center the needle on the exact percentage
          background: '#fff',
          border: `2px solid ${needleColor}`,
          borderRadius: '4px',
          boxShadow: '0 1px 3px rgba(0,0,0,0.3)',
          transition: 'left 0.5s cubic-bezier(0.4, 0, 0.2, 1)',
          zIndex: 10
        }} />
      </div>

      {/* Text Label Below */}
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', // Center the text for a clean look
        fontSize: '0.75rem', 
        fontWeight: 600, 
        color: '#6b7280' 
      }}>
        <span style={{ color: needleColor, transition: 'color 0.3s ease' }}>
          {isNeutral ? "Balanced coverage" : labelText}
        </span>
      </div>

    </div>
  );
}