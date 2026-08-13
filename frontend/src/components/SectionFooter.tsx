import { useData } from '../lib/data-context';

/** The colophon — the almanack's imprint. */
export default function SectionFooter() {
  const { season } = useData();

  return (
    <footer className="mx-auto w-full max-w-5xl px-4 pb-10 pt-6">
      <div className="rule-double pt-4">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <p className="font-mono text-[0.6875rem] uppercase tracking-wider-caps text-ink-soft">
            Printed by the Football Predictor {season && `· Season ${season}`}
          </p>
          <p className="font-mono text-[0.6875rem] uppercase tracking-wider-caps text-ink-faint">
            Random Forest regressors · five seasons of Premier League · live club Elo
          </p>
        </div>
        <p className="mt-3 font-serif text-xs italic text-ink-faint">
          Model outputs are not betting advice. The model's honest record is kept in the RECORDS section.
        </p>
      </div>
    </footer>
  );
}
