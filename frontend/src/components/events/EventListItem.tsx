import { MapPin, Clock, ExternalLink } from "lucide-react";
import { cn } from "@/lib/utils";
import { getCountdown } from "@/lib/countdown";

const MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"];
const DAYS = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"];

interface EventListItemProps {
  title: string;
  date: string | null;
  venue: string | null;
  start_time: string | null;
  ticket_url: string | null;
  source_url: string | null;
  themeColor?: string;
  showArtistBar?: boolean;
  artistDisplayName?: string;
  artistImageUrl?: string;
}

function CountdownBadge({ label, variant }: { label: string; variant: string }) {
  return (
    <span
      className={cn(
        "shrink-0 inline-flex items-center rounded-full px-4 py-1.5 text-sm font-black whitespace-nowrap shadow-sm",
        variant === "today" && "bg-red-500 text-white animate-pulse",
        variant === "soon" && "bg-orange-500 text-white",
        variant === "upcoming" && "bg-secondary text-secondary-foreground border border-border",
        variant === "past" && "bg-muted text-muted-foreground",
        variant === "unknown" && "bg-muted text-muted-foreground"
      )}
    >
      {label}
    </span>
  );
}

export default function EventListItem({
  title,
  date,
  venue,
  start_time,
  ticket_url,
  source_url,
  themeColor,
  showArtistBar = false,
  artistDisplayName,
  artistImageUrl,
}: EventListItemProps) {
  const dateObj = date ? new Date(date) : null;
  const countdown = getCountdown(date);
  const isPast = countdown.variant === "past";
  const accentColor = themeColor || "hsl(var(--primary))";

  return (
    <div
      className={cn(
        "relative flex rounded-[2rem] border bg-card transition-all duration-300 hover:shadow-xl hover:border-primary/30 group/item",
        isPast && "opacity-60 grayscale-[0.5]"
      )}
    >
      {showArtistBar && (
        <div
          className="w-2 shrink-0 rounded-l-[2rem]"
          style={{ backgroundColor: accentColor }}
        />
      )}

      <div className="flex flex-col sm:flex-row gap-4 p-6 sm:p-8 w-full min-w-0">
        {/* Date block */}
        <div className="flex flex-row sm:flex-col items-center justify-center sm:justify-start gap-2 sm:gap-1 min-w-[60px] text-center border-b sm:border-b-0 sm:border-r border-border pb-3 sm:pb-0 sm:pr-4">
          <span
            className="text-4xl font-black leading-none"
            style={{ color: isPast ? undefined : accentColor }}
          >
            {dateObj ? dateObj.getDate() : "--"}
          </span>
          <span className="text-sm font-black uppercase tracking-[0.2em] text-muted-foreground/60 leading-none">
            {dateObj ? DAYS[dateObj.getDay()] : "---"}
          </span>
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0 flex flex-col justify-center">
          <div className="flex flex-col xl:flex-row items-start xl:items-start justify-between gap-2 mb-6">
            <h3 className="font-black text-2xl leading-tight line-clamp-2 tracking-tighter group-hover/item:text-primary transition-colors">{title}</h3>
            <CountdownBadge label={countdown.label} variant={countdown.variant} />
          </div>

          {showArtistBar && artistDisplayName && (
            <div className="flex items-center gap-2.5 mb-4 bg-muted/40 w-fit px-3 py-1.5 rounded-full border border-border/50">
              {artistImageUrl && (
                <img
                  src={artistImageUrl}
                  alt={artistDisplayName}
                  className="w-6 h-6 rounded-full object-cover shrink-0 ring-2 ring-background shadow-sm"
                />
              )}
              <span className="text-base font-black text-muted-foreground/80">{artistDisplayName}</span>
            </div>
          )}

          <div className="flex items-center justify-between gap-x-4 gap-y-2 flex-wrap">
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
              {venue && (
                <span className="flex items-center gap-2 text-lg text-muted-foreground font-medium">
                  <MapPin className="h-5 w-5 shrink-0 text-primary/60" />
                  {venue}
                </span>
              )}
              {start_time && (
                <span className="flex items-center gap-2 text-lg text-muted-foreground font-medium">
                  <Clock className="h-5 w-5 shrink-0 text-primary/60" />
                  {start_time}
                </span>
              )}
            </div>
            {(ticket_url || source_url) && (
              <div className="flex items-center gap-2 shrink-0">
                {ticket_url && (
                  <a
                    href={ticket_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-black text-white transition-all hover:opacity-90 hover:scale-105 active:scale-95 shadow-md shadow-primary/20"
                    style={{ backgroundColor: accentColor }}
                  >
                    <ExternalLink className="h-3.5 w-3.5" />
                    チケット予約
                  </a>
                )}
                {source_url && (
                  <a
                    href={source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 rounded-xl border bg-background px-4 py-2 text-sm font-black text-muted-foreground hover:text-foreground hover:bg-muted transition-all hover:scale-105 active:scale-95 border-border shadow-sm"
                  >
                    詳細・公式サイト
                  </a>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
