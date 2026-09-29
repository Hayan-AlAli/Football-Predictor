interface EmptyStateProps {
  title: string;
  note: string;
}

/** An empty page of the ledger — no fixtures set for this matchweek. */
export default function EmptyState({ title, note }: EmptyStateProps) {
  return (
    <div className="mt-8">
      <div className="plate p-8 text-center">
        <h2 className="font-display text-2xl font-extrabold uppercase text-chalk">{title}</h2>
        <p className="mt-1 font-sans text-sm italic text-chalk-soft">{note}</p>
      </div>
    </div>
  );
}
