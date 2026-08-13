interface EmptyStateProps {
  title: string;
  note: string;
}

/** An empty page of the ledger — no fixtures set for this matchweek. */
export default function EmptyState({ title, note }: EmptyStateProps) {
  return (
    <div className="mt-8">
      <div className="plate p-8 text-center">
        <h2 className="font-sans text-lg font-bold uppercase tracking-caps text-ink">{title}</h2>
        <p className="mt-1 font-serif text-sm italic text-ink-soft">{note}</p>
      </div>
    </div>
  );
}
