import { teamShort } from '../lib/teams';
import type { Match } from '../types';

const LEAGUE_ROWS: Array<{
  label: string;
  key: 'home_rolling_goals' | 'away_rolling_goals' | 'home_rolling_xg' | 'away_rolling_xg';
  avgKey: 'league_avg_goals' | 'league_avg_xg';
}> = [
  { label: 'Rolling goals — home', key: 'home_rolling_goals', avgKey: 'league_avg_goals' },
  { label: 'Rolling goals — away', key: 'away_rolling_goals', avgKey: 'league_avg_goals' },
  { label: 'Rolling xG — home', key: 'home_rolling_xg', avgKey: 'league_avg_xg' },
  { label: 'Rolling xG — away', key: 'away_rolling_xg', avgKey: 'league_avg_xg' },
];

function Delta({ value, avg }: { value: number; avg: number }) {
  const diff = value - avg;
  const cls = Math.abs(diff) < 0.05 ? 'text-ink-faint' : diff > 0 ? 'text-ledger' : 'text-rubric';
  return (
    <span className={`font-mono text-[0.6875rem] tnum ${cls}`}>
      {Math.abs(diff) < 0.05 ? '≈' : diff > 0 ? '▲' : '▼'} {Math.abs(diff).toFixed(2)}
    </span>
  );
}

/** The model's inputs for one fixture: why it prints what it prints. */
export default function FeatureReveal({ match }: { match: Match }) {
  const f = match.prediction?.features;
  if (!f) return null;
  const home = typeof match.home_team === 'string' ? match.home_team : match.home_team?.name ?? '';
  const away = typeof match.away_team === 'string' ? match.away_team : match.away_team?.name ?? '';

  return (
    <section className="rule-double mt-5 pt-4" aria-label="Model inputs for this fixture">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h4 className="font-mono text-[0.6875rem] uppercase tracking-wider-caps text-ink-faint">
          Why the model says so · feature inputs
        </h4>
        <span className="font-serif text-[0.6875rem] italic text-ink-faint">
          live club rating and rolling form, against the league average
        </span>
      </div>

      <div className="mt-3 space-y-1.5">
        <div className="grid grid-cols-[1fr_auto] gap-x-3 sm:grid-cols-[8rem_1fr_1fr_1fr]">
          <span className="font-mono text-[0.625rem] uppercase tracking-widest text-ink-faint">Club rating</span>
          <span className="hidden sm:block text-right font-mono text-[0.625rem] uppercase tracking-widest text-ink-faint">{teamShort(home)}</span>
          <span className="hidden sm:block text-center font-mono text-[0.625rem] uppercase tracking-widest text-ink-faint">gap</span>
          <span className="hidden sm:block text-right font-mono text-[0.625rem] uppercase tracking-widest text-ink-faint">{teamShort(away)}</span>
        </div>
        <div className="grid grid-cols-[1fr_auto] items-center gap-x-3 border-t border-paper-line pt-1.5 sm:grid-cols-[8rem_1fr_1fr_1fr]">
          <span className="font-mono text-[0.6875rem] uppercase tracking-wider-caps text-ink-soft">Elo</span>
          <span className="text-right font-mono text-sm text-ink tnum">{f.home_elo}</span>
          <span className="text-center font-mono text-[0.6875rem] text-ink-faint tnum">
            {f.elo_gap >= 0 ? `+${f.elo_gap}` : f.elo_gap}
          </span>
          <span className="text-right font-mono text-sm text-ink tnum">{f.away_elo}</span>
        </div>

        {LEAGUE_ROWS.map((row) => (
          <div
            key={row.key}
            className="grid grid-cols-[1fr_auto] items-center gap-x-3 border-t border-paper-line pt-1.5 sm:grid-cols-[8rem_1fr_1fr_1fr]"
          >
            <span className="font-mono text-[0.6875rem] uppercase tracking-wider-caps text-ink-soft">
              {row.label}
            </span>
            <span className="text-right font-mono text-sm text-ink tnum">{f[row.key].toFixed(2)}</span>
            <span className="text-center font-mono text-[0.6875rem] text-ink-faint tnum">
              avg {f[row.avgKey].toFixed(2)}
            </span>
            <span className="text-right">
              <Delta value={f[row.key]} avg={f[row.avgKey]} />
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}