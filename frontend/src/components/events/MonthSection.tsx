interface MonthSectionProps {
  label: string;
  children: React.ReactNode;
}

export default function MonthSection({ label, children }: MonthSectionProps) {
  return (
    <section>
      <div className="flex items-center gap-4 mb-4 px-1">
        <h2 className="text-sm font-black uppercase tracking-[0.2em] text-muted-foreground/80 whitespace-nowrap">
          {label}
        </h2>
        <div className="h-px w-full bg-border/60" />
      </div>
      <div className="space-y-4">{children}</div>
    </section>
  );
}
