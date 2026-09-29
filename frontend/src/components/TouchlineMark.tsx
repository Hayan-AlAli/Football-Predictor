/** The Touchline mark: a centre circle with the halfway line drawn through it in amber. */
export default function TouchlineMark({ size = 32, className = '' }: { size?: number; className?: string }) {
  const ring = Math.max(2, Math.round(size / 12));
  const line = Math.max(2, Math.round(size / 11));
  const overhang = Math.round(size / 5);
  const dot = Math.max(4, Math.round(size / 4.5));

  return (
    <span
      aria-hidden="true"
      className={`relative inline-block shrink-0 rounded-full border-chalk ${className}`}
      style={{ width: size, height: size, borderWidth: ring, borderStyle: 'solid' }}
    >
      <span
        className="absolute left-1/2 bg-amber"
        style={{ top: -overhang, bottom: -overhang, width: line, marginLeft: -line / 2 }}
      />
      <span
        className="absolute left-1/2 top-1/2 rounded-full bg-chalk"
        style={{ width: dot, height: dot, marginLeft: -dot / 2, marginTop: -dot / 2 }}
      />
    </span>
  );
}
