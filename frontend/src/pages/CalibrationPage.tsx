import { useEffect, useState } from 'react';
import { motion, useReducedMotion } from 'motion/react';
import Press from '../components/Press';
import OfflineSlate from '../components/OfflineSlate';
import EmptyState from '../components/EmptyState';
import { CalibrationCurve, SvgLineChart } from '../lib/charts';
import { getCalibration } from '../api/matches';
import { percent } from '../lib/format';
import { getReducedMotionVariants, headVariants } from '../lib/motion';
import type { CalibrationData } from '../types';

type LoadState =
  | { status: 'loading' }
  | { status: 'error' }
  | { status: 'ready'; data: CalibrationData };

export default function CalibrationPage() {
  const [state, setState] = useState<LoadState>({ status: 'loading' });
  const [reloadKey, setReloadKey] = useState(0);
  const reduce = useReducedMotion();
  const headV = reduce ? getReducedMotionVariants(headVariants) : headVariants;

  useEffect(() => {
    let cancelled = false;
    getCalibration()
      .then((data) => { if (!cancelled) setState({ status: 'ready', data }); })
      .catch(() => { if (!cancelled) setState({ status: 'error' }); });
    return () => { cancelled = true; };
  }, [reloadKey]);

  if (state.status === 'loading') return <div className="mx-auto max-w-5xl px-4 pb-4"><Press /></div>;
  if (state.status === 'error') {
    return (
      <div className="mx-auto max-w-5xl px-4 pb-4">
        <OfflineSlate
          message="The calibration ledger could not be read. Check that the press (FastAPI) is running."
          onRetry={() => {
            setState({ status: 'loading' });
            setReloadKey((k) => k + 1);
          }}
        />
      </div>
    );
  }

  const { data } = state;

  return (
    <div className="mx-auto max-w-5xl px-4 pb-4">
      <motion.div variants={headV} initial="hidden" animate="show" className="pt-8">
        <h1 className="font-sans text-2xl sm:text-3xl font-extrabold uppercase tracking-caps text-ink">
          Calibration &amp; the record
        </h1>
        <p className="mt-1.5 font-serif text-sm italic text-ink-soft sm:text-base">
          When the model says 60%, does it win six in ten? The record, kept honestly — misses included.
        </p>
      </motion.div>

      {data.entries === 0 ? (
        <div className="mt-8">
          <EmptyState
            title="The calibration ledger is blank"
            note="No decided verdicts recorded yet. The evening press compares predictions against results; once it has, the calibration ledger fills."
          />
        </div>
      ) : (
        <>
          <div className="mt-6 grid gap-4 sm:grid-cols-3">
            <div className="plate p-4">
              <h3 className="font-mono text-[0.6875rem] uppercase tracking-wider-caps text-ink-faint">Overall accuracy</h3>
              <p className="mt-1 font-mono text-3xl font-semibold text-ink tnum">
                {data.accuracy != null ? percent(data.accuracy) : '—'}
              </p>
              <p className="mt-1 font-serif text-xs italic text-ink-faint">{data.entries} decided verdicts</p>
            </div>
            <div className="plate p-4">
              <h3 className="font-mono text-[0.6875rem] uppercase tracking-wider-caps text-ink-faint">Brier score</h3>
              <p className="mt-1 font-mono text-3xl font-semibold text-ink tnum">
                {data.brier != null ? data.brier.toFixed(3) : '—'}
              </p>
              <p className="mt-1 font-serif text-xs italic text-ink-faint">lower is better; a perfect forecaster scores 0</p>
            </div>
            <div className="plate p-4">
              <h3 className="font-mono text-[0.6875rem] uppercase tracking-wider-caps text-ink-faint">Honesty note</h3>
              <p className="mt-1 font-serif text-sm italic text-ink-soft">
                This ledger shows every miss. A prediction is only as credible as its record of being wrong.
              </p>
            </div>
          </div>

          {data.bins.length > 0 && (
            <section className="rule-double mt-10 pt-4">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <h2 className="font-mono text-xl font-semibold text-rubric">Calibration curve</h2>
                <span className="font-mono text-[0.6875rem] uppercase tracking-wider-caps text-ink-faint">
                  predicted probability vs actual win rate
                </span>
              </div>
              <div className="mt-4">
                <CalibrationCurve bins={data.bins} />
              </div>
              <p className="mt-2 font-serif text-xs italic text-ink-faint">
                The dashed line is perfect calibration — on it, 60% predicted wins exactly six in ten.
              </p>
              <div className="mt-4 flex flex-wrap gap-2">
                {data.bins.map((b) => (
                  <span key={b.label} className="font-mono text-[0.625rem] uppercase tracking-widest text-ink-soft">
                    {b.label} · n={b.count} · {percent(b.predicted)} → {percent(b.actual)}
                  </span>
                ))}
              </div>
            </section>
          )}

          {data.rolling.length > 0 && (
            <section className="rule-double mt-10 pt-4">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <h2 className="font-mono text-xl font-semibold text-rubric">By matchweek</h2>
                <span className="font-mono text-[0.6875rem] uppercase tracking-wider-caps text-ink-faint">
                  decided verdicts per matchweek, rolling
                </span>
              </div>
              <div className="mt-4">
                <SvgLineChart
                  points={data.rolling.map((r) => ({ x: `GW ${r.gameweek}`, y: r.accuracy ?? 0 }))}
                />
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                {data.rolling.map((r) => (
                  <span key={r.gameweek} className="chip">
                    GW {r.gameweek} · {r.correct}/{r.decided}
                    {r.accuracy != null ? ` · ${percent(r.accuracy)}` : ''}
                  </span>
                ))}
              </div>
            </section>
          )}
        </>
      )}
    </div>
  );
}