import { useData } from '../lib/data-context';
import { lastDecidedWeek, useCalibration } from '../lib/calibration';
import { percent } from '../lib/format';

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <span className="whitespace-nowrap">
      <span className="text-chalk-faint">{label} </span>
      <span className="text-chalk tnum">{value}</span>
    </span>
  );
}

/** The ticker under the masthead: the model's season record at a glance. */
export default function StatsStrip({ gameweek }: { gameweek?: number }) {
  const { gameweeks, season } = useData();
  const cal = useCalibration();
  const data = cal.status === 'ready' ? cal.data : null;
  const last = data ? lastDecidedWeek(data) : null;
  const total = gameweeks.length > 0 ? Math.max(...gameweeks) : null;

  return (
    <section aria-label="Season record" className="border-b border-line bg-panel">
      <div className="scroll-fade mx-auto flex max-w-6xl items-center gap-7 overflow-x-auto py-2.5 pl-4 pr-8 font-mono text-xs tracking-[0.04em] sm:pl-6">
        {gameweek != null && <Stat label="GW" value={total ? `${gameweek} / ${total}` : String(gameweek)} />}
        <Stat label="HIT RATE" value={data?.accuracy != null ? `${percent(data.accuracy, 1)}%` : '—'} />
        <Stat label="LAST 10" value={last ? `${last.correct}/${last.decided}` : '—'} />
        <Stat label="BRIER" value={data?.brier != null ? data.brier.toFixed(3) : '—'} />
        <Stat label="DECIDED" value={data ? String(data.entries) : '—'} />
        {season && <Stat label="SEASON" value={season} />}
      </div>
    </section>
  );
}
