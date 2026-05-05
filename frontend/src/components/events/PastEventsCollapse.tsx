import { useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";

interface PastEventsCollapseProps {
  count: number;
  children: React.ReactNode;
}

export default function PastEventsCollapse({ count, children }: PastEventsCollapseProps) {
  const [isOpen, setIsOpen] = useState(false);

  if (count === 0) return null;

  return (
    <div className="mt-8">
      <button
        onClick={() => setIsOpen((o) => !o)}
        className="flex w-full items-center gap-2 border-t py-3 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground"
      >
        <span>過去のイベント ({count}件)</span>
        {isOpen ? (
          <ChevronUp className="ml-auto h-4 w-4" />
        ) : (
          <ChevronDown className="ml-auto h-4 w-4" />
        )}
      </button>
      {isOpen && <div className="mt-4 space-y-2">{children}</div>}
    </div>
  );
}
