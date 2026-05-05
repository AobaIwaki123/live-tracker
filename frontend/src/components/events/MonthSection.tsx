interface MonthSectionProps {
  label: string;
  children: React.ReactNode;
}

export default function MonthSection({ label, children }: MonthSectionProps) {
  return (
    <section>
      <div className="flex items-center gap-6 mb-8 px-2">
        <h2 className="text-xl font-black uppercase tracking-[0.3em] text-muted-foreground/50 whitespace-nowrap">
          {label}
        </h2>
        <div className="h-px w-full bg-gradient-to-r from-border/80 to-transparent" />
      </div>
      <div className="space-y-6">{children}</div>
    </section>
  );
}
