export function MeterBar({ value, tone = 'ink' }: { value: number; tone?: 'ink' | 'rubric' }) {
  const pct = Math.min(100, Math.max(0, value * 100));
  return (
    <span className="inline-block h-2 flex-1 bg-raised border border-line overflow-hidden" aria-hidden="true">
      <span
        className={`block h-full ${tone === 'rubric' ? 'bg-amber' : 'bg-chalk'}`}
        style={{ width: `${pct}%` }}
      />
    </span>
  );
}

export function SvgLineChart({
  points,
  width = 520,
  height = 160,
  strokeClass = 'stroke-signal',
}: {
  points: Array<{ x: string; y: number }>;
  width?: number;
  height?: number;
  strokeClass?: string;
}) {
  if (points.length === 0) return null;
  const ys = points.map((p) => p.y);
  const min = Math.min(...ys);
  const max = Math.max(...ys);
  const span = Math.max(max - min, 1);
  const pad = span * 0.1;
  const lo = min - pad;
  const hi = max + pad;
  const stepX = points.length > 1 ? width / (points.length - 1) : 0;
  const coords = points.map((p, i) => ({
    x: i * stepX,
    y: height - ((p.y - lo) / (hi - lo)) * height,
  }));
  const line = coords.map((c, i) => `${i === 0 ? 'M' : 'L'}${c.x.toFixed(1)},${c.y.toFixed(1)}`).join(' ');
  const first = coords[0];
  const last = coords[coords.length - 1];
  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="none"
      className="h-40 w-full overflow-visible"
      role="img"
      aria-label="Trend chart"
    >
      <line x1={0} y1={first.y} x2={width} y2={first.y} className="stroke-line" strokeWidth={1} vectorEffect="non-scaling-stroke" />
      <line x1={0} y1={last.y} x2={width} y2={last.y} className="stroke-line" strokeWidth={1} vectorEffect="non-scaling-stroke" />
      <path d={line} fill="none" className={strokeClass} strokeWidth={2} vectorEffect="non-scaling-stroke" />
      {/* A zero-length round-capped stroke: stays a circle under the non-uniform stretch */}
      <line
        x1={last.x}
        y1={last.y}
        x2={last.x}
        y2={last.y}
        className="stroke-chalk"
        strokeWidth={7}
        strokeLinecap="round"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}

export function CalibrationCurve({
  bins,
  width = 520,
  height = 160,
}: {
  bins: Array<{ label: string; count: number; predicted: number; actual: number }>;
  width?: number;
  height?: number;
}) {
  if (bins.length === 0) return null;
  const padX = 24;
  const padY = 16;
  const x = (v: number) => padX + v * (width - padX * 2);
  const y = (v: number) => height - padY - v * (height - padY * 2);
  const diagonal = `M${x(0)},${y(0)} L${x(1)},${y(1)}`;
  const line = bins
    .map((b, i) => `${i === 0 ? 'M' : 'L'}${x(b.predicted).toFixed(1)},${y(b.actual).toFixed(1)}`)
    .join(' ');
  const axis = 'font-mono text-micro text-chalk-faint tnum';
  return (
    <figure className="flex gap-2">
      {/* Axis labels live in HTML so they stay one size however wide the chart is drawn */}
      <div className={`flex flex-col justify-between pb-6 ${axis}`} aria-hidden="true">
        <span>100%</span>
        <span>0%</span>
      </div>
      <div className="min-w-0 flex-1">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="block w-full"
          role="img"
          aria-label="Calibration curve: predicted probability versus actual win rate"
        >
          <path d={diagonal} fill="none" className="stroke-line-strong" strokeWidth={1} strokeDasharray="3 3" vectorEffect="non-scaling-stroke" />
          <path d={line} fill="none" className="stroke-amber" strokeWidth={2} vectorEffect="non-scaling-stroke" />
          {bins.map((b) => (
            <circle key={b.label} cx={x(b.predicted)} cy={y(b.actual)} r={3.5} className="fill-chalk" />
          ))}
        </svg>
        <div className={`mt-1 flex justify-between ${axis}`} aria-hidden="true">
          <span>0% predicted</span>
          <span>100%</span>
        </div>
      </div>
    </figure>
  );
}