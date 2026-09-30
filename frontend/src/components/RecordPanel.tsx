import { Link } from 'react-router-dom';
import { headlineBin, useCalibration } from '../lib/calibration';
import { percent } from '../lib/format';

/** "0.55-0.65" → "55–65%". */
function bandLabel(label: string): string {
  const parts = label.split('-').map((v) => Math.round(parseFloat(v) * 100));
  return parts.length === 2 && parts.every((v) => !Number.isNaN(v)) ? `${parts[0]}–${Math.min(parts[1], 100)}%` : label;
}

const LABEL = 'font-mono text-[0.6875rem] tracking-[0.12em] text-chalk-faint';

/** The sidebar: the season record, recent matchweeks, the calibration check and a reading key. */
export default function RecordPanel() {
  const cal = useCalibration();
  const data = cal.status === 'ready' ? cal.data : null;
  const weeks = data ? data.rolling.filter((r) => r.decided > 0).slice(-6) : [];
  const bin = data ? headlineBin(data) : null;
  const correct = data?.accuracy != null ? Math.round(data.accuracy * data.entries) : null;

  return (
    <aside className="flex flex-col gap-5" aria-label="The model's record">
      <section className="plate flex flex-col gap-4 p-6">
        <h2 className={LABEL}>SEASON RECORD</h2>
        {cal.status === 'loading' && <p className="font-mono text-xs text-chalk-faint">Loading the record…</p>}
        {cal.status === 'error' && <p className="text-sm text-chalk-faint">The record could not be loaded.</p>}
        {data && (data.entries === 0 || data.accuracy == null) && (
          <p className="text-sm text-chalk-soft">No decided calls yet — the record fills after the first results come in.</p>
        )}
        {data && data.entries > 0 && data.accuracy != null && (
          <div className="flex flex-col gap-1">
            <span className="font-display text-[5rem] font-black leading-[0.85] text-amber tnum">
              {percent(data.accuracy, 1)}%
            </span>
            <span className="text-[0.9375rem] text-chalk-soft">
              of calls correct{correct != null ? ` · ${correct} of ${data.entries}` : ''}
            </span>
          </div>
        )}

        {weeks.length > 0 && (
          <>
            <div className="h-px bg-line" />
            <h3 className={LABEL}>RECENT CALLS · BLOCKS OF 10</h3>
            <ol className="flex h-[108px] items-end gap-2.5">
              {weeks.map((w) => {
                const acc = w.accuracy ?? 0;
                return (
                  <li key={w.gameweek} className="flex flex-1 flex-col items-center gap-1.5">
                    <span className="font-mono text-micro text-chalk-soft tnum">{w.correct}/{w.decided}</span>
                    <span
                      className={`w-full ${acc >= 0.5 ? 'bg-amber' : 'bg-line-strong'}`}
                      style={{ height: `${Math.max(4, acc * 64)}px` }}
                      aria-hidden="true"
                    />
                    <span className="font-mono text-micro text-chalk-faint">#{w.gameweek}</span>
                  </li>
                );
              })}
            </ol>
          </>
        )}
      </section>

      {bin && (
        <section className="plate flex flex-col gap-3 p-6">
          <h2 className={LABEL}>CALIBRATION</h2>
          <p className="text-base leading-relaxed text-chalk">
            When it says <span className="font-semibold text-amber">{percent(bin.predicted)}%</span>, it has happened{' '}
            <span className="font-semibold text-amber">{percent(bin.actual)}%</span> of the time.
          </p>
          <p className="font-mono text-[0.6875rem] text-chalk-faint">{bin.count} calls in the {bandLabel(bin.label)} band</p>
        </section>
      )}

      <section className="plate flex flex-col gap-3 p-6">
        <h2 className={LABEL}>HOW TO READ A CARD</h2>
        <ul className="flex flex-col gap-2 text-sm leading-snug text-chalk-soft">
          <li><span className="font-semibold text-amber">Amber</span> is always the model's call.</li>
          <li>The light box is the most likely scoreline (Poisson on predicted goals).</li>
          <li>
            <span className="text-chalk" aria-hidden="true">■</span> home{' '}
            <span className="text-draw" aria-hidden="true">■</span> draw{' '}
            <span className="text-signal" aria-hidden="true">■</span> away in the split bar.
          </li>
          <li>ELO, GOALS and xG are the model's inputs — home left, away right.</li>
        </ul>
        <Link to="/method" className="btn-print mt-1 justify-between">
          Turn to the method <span aria-hidden="true">→</span>
        </Link>
      </section>
    </aside>
  );
}
