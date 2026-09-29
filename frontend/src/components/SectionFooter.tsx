import { useData } from '../lib/data-context';
import TouchlineMark from './TouchlineMark';

/** The desk's footer: imprint, method line, and the not-betting-advice note. */
export default function SectionFooter() {
  const { season } = useData();

  return (
    <footer className="mt-10 border-t border-line bg-ground-deep">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-3 px-4 py-6 sm:px-6">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <p className="flex items-center gap-2.5 font-mono text-[0.6875rem] uppercase tracking-wider-caps text-chalk-soft">
            <TouchlineMark size={16} />
            Touchline {season && `· Premier League ${season}`}
          </p>
          <p className="font-mono text-[0.6875rem] uppercase tracking-wider-caps text-chalk-faint">
            Random Forest + Poisson · five seasons of data · live club Elo
          </p>
        </div>
        <p className="text-xs italic text-chalk-faint">
          Model outputs are not betting advice. Every miss is kept in the Records section.
        </p>
      </div>
    </footer>
  );
}
