interface MonthSectionProps {
  label: string;
  children: React.ReactNode;
}

export default function MonthSection({ label, children }: MonthSectionProps) {
  return (
    <section>
      <h2 className="text-xs font-bold uppercase tracking-widest text-muted-foreground mb-2 px-1">
        {label}
      </h2>
      <div className="space-y-2">{children}</div>
    </section>
  );
}
