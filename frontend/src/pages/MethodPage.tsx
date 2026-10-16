import { motion } from 'motion/react';
import { useData } from '../lib/data-context';
import { useMotionVariants } from '../lib/motion';

const FEATURES = [
  {
    name: 'Attack strength',
    note: 'How many goals each club creates, fitted from every result it has played.',
  },
  {
    name: 'Defence strength',
    note: 'How many goals each club concedes, fitted the same way.',
  },
  {
    name: 'Expected goals (xG)',
    note: 'Results count three parts xG to one part goals: chance quality says more about a side than a few finishes.',
  },
  {
    name: 'Recency',
    note: 'A match five months old counts half as much as one played this week.',
  },
  {
    name: 'Home advantage',
    note: 'One league-wide boost to the home side’s scoring, fitted with the rest.',
  },
];

const PIPELINE = ['Results', 'Strengths', 'Expected goals', 'Scorelines', 'Probabilities', 'The ledger'];

/** The Method — the model's section, honest about what it does and does not claim. */
export default function MethodPage() {
  const { season } = useData();
  const { head: variants } = useMotionVariants();

  return (
    <div className="method-prose mx-auto max-w-3xl px-4 pb-4">
      <motion.div variants={variants} initial="hidden" animate="show" className="pt-8">
        <h1 className="mt-1 font-display text-[2.75rem] sm:text-[3.5rem] font-black uppercase leading-[0.9] text-chalk">
          The Method
        </h1>
        <p className="mt-2 font-sans text-sm italic text-chalk-soft sm:text-base">
          How the predictions are made: the club strengths, the results they are fitted to, and the distribution
          that turns expected goals into verdicts.
        </p>
      </motion.div>

      <div className="mt-8 space-y-8">
        {/* I — The model */}
        <section>
          <h2 className="rule-double pt-3 font-display text-2xl font-extrabold uppercase text-chalk">
            <span className="font-mono text-chalk-faint">I.</span> The model
          </h2>
          <p className="mt-3">
            Every prediction comes from a <strong>Dixon-Coles model</strong>: each club gets an attack and a
            defence strength, fitted to every Premier League result since 2020 with recent matches counting most.
            A fixture's <strong>expected goals</strong> follow from the two clubs' strengths and home advantage, and
            a <strong>Poisson distribution</strong> over goals — corrected for how often low scores like 0-0 and
            1-1 really happen — gives the full outcome line: home win, draw, away win and the likeliest scoreline.
            Replayed week by week over two and a half seasons, it beat the random forest it replaced, goals-only
            versions of itself and Elo alone.
          </p>
        </section>

        {/* II — The features */}
        <section>
          <h2 className="rule-double pt-3 font-display text-2xl font-extrabold uppercase text-chalk">
            <span className="font-mono text-chalk-faint">II.</span> The features
          </h2>
          <p className="mt-3">What each prediction is set from:</p>
          <div className="plate mt-4 overflow-x-auto">
            <table className="w-full border-collapse text-left">
              <thead>
                <tr className="border-b border-line">
                  <th scope="col" className="px-4 py-2.5 font-mono text-[0.6875rem] uppercase tracking-wider-caps text-chalk-faint">
                    Feature
                  </th>
                  <th scope="col" className="px-4 py-2.5 font-mono text-[0.6875rem] uppercase tracking-wider-caps text-chalk-faint">
                    What it is
                  </th>
                </tr>
              </thead>
              <tbody>
                {FEATURES.map((f) => (
                  <tr key={f.name} className="border-b border-line last:border-b-0">
                    <th scope="row" className="whitespace-nowrap px-4 py-2.5 font-mono text-xs uppercase tracking-widest text-chalk">
                      {f.name}
                    </th>
                    <td className="px-4 py-2.5 font-sans text-sm text-chalk-soft">{f.note}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-2 font-sans text-xs italic text-chalk-faint">
            xG comes from Understat. The model refits whenever new results arrive; the comparison behind it reruns
            with <span className="font-mono not-italic">python -m backend.backtest</span>.
          </p>
        </section>

        {/* III — The press run */}
        <section>
          <h2 className="rule-double pt-3 font-display text-2xl font-extrabold uppercase text-chalk">
            <span className="font-mono text-chalk-faint">III.</span> The press run
          </h2>
          <p className="mt-3">Twice a day the press sets the coming fixtures through six stations:</p>
          <ol className="mt-4 space-y-3 sm:flex sm:flex-wrap sm:items-center sm:gap-y-3 sm:gap-x-1 font-mono text-xs uppercase tracking-wider-caps">
            {PIPELINE.map((step, i) => (
              <li key={step} className="flex items-center gap-3">
                <span className="chip">
                  <span className="mr-1.5 text-chalk-faint">{String(i + 1).padStart(2, '0')}</span>
                  {step}
                </span>
                {i < PIPELINE.length - 1 && (
                  <span aria-hidden="true" className="text-chalk-faint hidden sm:inline">›</span>
                )}
              </li>
            ))}
          </ol>
          <ul className="mt-4 space-y-1.5 font-sans text-sm text-chalk-soft">
            <li>
              <strong className="font-sans">Results</strong> — the latest scores come in from live match data, with
              each match's xG from Understat.
            </li>
            <li>
              <strong className="font-sans">Strengths</strong> — every club's attack and defence are refitted.
            </li>
            <li>
              <strong className="font-sans">Expected goals</strong> — each fixture's goals for both sides follow from
              the two clubs' strengths.
            </li>
            <li>
              <strong className="font-sans">Scorelines</strong> — the goal distribution is expanded into every
              scoreline, and from there into match outcomes.
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
          <h2 className="rule-double pt-3 font-display text-2xl font-extrabold uppercase text-chalk">
            <span className="font-mono text-chalk-faint">IV.</span> The record
          </h2>
          <div className="mt-4 border border-line-strong bg-panel p-4 sm:p-5">
            <p className="font-sans text-sm text-chalk-soft sm:text-base">
              Probabilities are <strong className="font-sans">model outputs, not bookmakers' odds</strong>. The press
              prints what the data supports and claims no edge. Every verdict is kept against the actual result in
              the <strong className="font-sans">RECORDS</strong> section — hits and misses alike — so the model's
              honest record is a page of this almanack, not a footnote.
            </p>
          </div>
          {season && (
            <p className="mt-3 font-sans text-xs italic text-chalk-faint">
              Ledger of record: season {season}.
            </p>
          )}
        </section>
      </div>
    </div>
  );
}
