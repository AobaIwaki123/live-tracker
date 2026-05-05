import { useState } from "react";
import { ChevronDown, ChevronUp, History } from "lucide-react";

interface PastEventsCollapseProps {
  count: number;
  children: React.ReactNode;
}

export default function PastEventsCollapse({ count, children }: PastEventsCollapseProps) {
  const [isOpen, setIsOpen] = useState(false);

  if (count === 0) return null;

  return (
    <div className="mt-16">
      <button
        onClick={() => setIsOpen((o) => !o)}
        className="group flex w-full items-center gap-3 rounded-2xl border bg-muted/30 p-4 text-base font-bold text-muted-foreground transition-all hover:bg-muted hover:text-foreground active:scale-[0.99]"
      >
        <History className="h-5 w-5 text-muted-foreground/60 group-hover:text-primary transition-colors" />
        <span>過去のイベント ({count}件)</span>
        <div className="ml-auto flex h-8 w-8 items-center justify-center rounded-full bg-background/50 group-hover:bg-primary group-hover:text-primary-foreground transition-all">
          {isOpen ? (
            <ChevronUp className="h-4 w-4" />
          ) : (
            <ChevronDown className="h-4 w-4" />
          )}
        </div>
      </button>
      {isOpen && <div className="mt-6 grid gap-4">{children}</div>}
    </div>
  );
}
