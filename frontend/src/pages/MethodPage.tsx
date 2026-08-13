import { motion, useReducedMotion } from 'motion/react';
import { useData } from '../lib/data-context';
import { getReducedMotionVariants, headVariants } from '../lib/motion';

const FEATURES = [
  {
    name: 'Club Elo',
    note: 'The live rating of each side at kickoff, taken from ClubElo.',
  },
  {
    name: 'Rolling form — goals',
    note: 'Average goals scored and conceded across each side’s last five matches.',
  },
  {
    name: 'Rolling form — xG',
    note: 'Average expected goals for and against across the last five matches.',
  },
  {
    name: 'Team encoding',
    note: 'A fitted team code for the home and away sides, learned while training.',
  },
  {
    name: 'Home advantage',
    note: 'The structural edge of playing at home, carried by the home-side model.',
  },
];

const PIPELINE = ['Fixtures', 'Features', 'Regressors', 'Poisson', 'Probabilities', 'The ledger'];

/** The Method — the model's section, honest about what it does and does not claim. */
export default function MethodPage() {
  const { season } = useData();
  const reduce = useReducedMotion();
  const variants = reduce ? getReducedMotionVariants(headVariants) : headVariants;

  return (
    <div className="mx-auto max-w-3xl px-4 pb-4">
      <motion.div variants={variants} initial="hidden" animate="show" className="pt-8">
        <h1 className="mt-1 font-sans text-2xl sm:text-3xl font-extrabold uppercase tracking-caps text-ink">
          The Method
        </h1>
        <p className="mt-2 font-serif text-sm italic text-ink-soft sm:text-base">
          How the almanack is printed: the features, the regressors, and the distribution that turns expected
          goals into verdicts.
        </p>
      </motion.div>

      <div className="mt-8 space-y-8">
        {/* I — The model */}
        <section>
          <h2 className="rule-double pt-3 font-sans text-lg font-bold uppercase tracking-caps text-ink">
            <span className="font-mono text-rubric">I.</span> The model
          </h2>
          <p className="mt-3">
            The almanack is printed by two <strong>Random Forest regressors</strong> — one for the home side, one
            for the away side — trained on five seasons of Premier League football. Each regressor estimates its
            side's <strong>expected goals</strong> for a fixture from the features below. The two expectations are
            then expanded into the full outcome line — home win, draw, away win, and the most likely scoreline —
            with a <strong>Poisson distribution</strong> over goals.
          </p>
        </section>

        {/* II — The features */}
        <section>
          <h2 className="rule-double pt-3 font-sans text-lg font-bold uppercase tracking-caps text-ink">
            <span className="font-mono text-rubric">II.</span> The features
          </h2>
          <p className="mt-3">What each prediction is set from — five columns of fact:</p>
          <div className="plate mt-4 overflow-x-auto">
            <table className="w-full border-collapse text-left">
              <thead>
                <tr className="border-b border-paper-line">
                  <th scope="col" className="px-4 py-2.5 font-mono text-[0.6875rem] uppercase tracking-wider-caps text-ink-faint">
                    Feature
                  </th>
                  <th scope="col" className="px-4 py-2.5 font-mono text-[0.6875rem] uppercase tracking-wider-caps text-ink-faint">
                    What it is
                  </th>
                </tr>
              </thead>
              <tbody>
                {FEATURES.map((f) => (
                  <tr key={f.name} className="border-b border-paper-line last:border-b-0">
                    <th scope="row" className="whitespace-nowrap px-4 py-2.5 font-mono text-xs uppercase tracking-widest text-ink">
                      {f.name}
                    </th>
                    <td className="px-4 py-2.5 font-serif text-sm text-ink-soft">{f.note}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-2 font-serif text-xs italic text-ink-faint">
            The trained artifacts are kept as <span className="font-mono not-italic">model_home.pkl</span>,{' '}
            <span className="font-mono not-italic">model_away.pkl</span> and{' '}
            <span className="font-mono not-italic">team_encoder.pkl</span>, retrained through{' '}
            <span className="font-mono not-italic">backend.train_model</span>.
          </p>
        </section>

        {/* III — The press run */}
        <section>
          <h2 className="rule-double pt-3 font-sans text-lg font-bold uppercase tracking-caps text-ink">
            <span className="font-mono text-rubric">III.</span> The press run
          </h2>
          <p className="mt-3">Each morning the press sets the day's fixtures through six stations:</p>
          <ol className="mt-4 flex flex-wrap items-center gap-y-3 font-mono text-xs uppercase tracking-wider-caps">
            {PIPELINE.map((step, i) => (
              <li key={step} className="flex items-center gap-3">
                <span className="chip">
                  <span className="mr-1.5 text-rubric">{String(i + 1).padStart(2, '0')}</span>
                  {step}
                </span>
                {i < PIPELINE.length - 1 && (
                  <span aria-hidden="true" className="text-ink-faint">›</span>
                )}
              </li>
            ))}
          </ol>
          <ul className="mt-4 space-y-1.5 font-serif text-sm text-ink-soft">
            <li>
              <strong className="font-sans">Fixtures</strong> — the day's fixtures are fetched from live match data.
            </li>
            <li>
              <strong className="font-sans">Features</strong> — ELO ratings and the rolling form columns are computed
              for both sides.
            </li>
            <li>
              <strong className="font-sans">Regressors</strong> — both forests estimate the expected goals for their
              side.
            </li>
            <li>
              <strong className="font-sans">Poisson</strong> — the goal distribution is expanded into match outcomes.
            </li>
            <li>
              <strong className="font-sans">Probabilities</strong> — home, draw and away figures are set to paper.
            </li>
            <li>
              <strong className="font-sans">The ledger</strong> — the matchweek's page is printed; every fixture is
              published with its line and the model's call.
            </li>
          </ul>
        </section>

        {/* IV — The record */}
        <section>
          <h2 className="rule-double pt-3 font-sans text-lg font-bold uppercase tracking-caps text-ink">
            <span className="font-mono text-rubric">IV.</span> The record
          </h2>
          <div className="mt-4 border-l-[3px] border-ledger bg-paper-deep p-4 sm:p-5">
            <p className="font-serif text-sm text-ink-soft sm:text-base">
              Probabilities are <strong className="font-sans">model outputs, not bookmakers' odds</strong>. The press
              prints what the data supports and claims no edge. Every verdict is kept against the actual result in
              the <strong className="font-sans">RECORDS</strong> section — hits and misses alike — so the model's
              honest record is a page of this almanack, not a footnote.
            </p>
          </div>
          {season && (
            <p className="mt-3 font-serif text-xs italic text-ink-faint">
              Ledger of record: season {season}.
            </p>
          )}
        </section>
      </div>
    </div>
  );
}
