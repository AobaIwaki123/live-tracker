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
        "shrink-0 inline-flex items-center rounded-full px-3 py-1 text-xs font-bold whitespace-nowrap",
        variant === "today" && "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
        variant === "soon" && "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400",
        variant === "upcoming" && "bg-secondary text-secondary-foreground",
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
        "relative flex rounded-2xl border bg-card transition-all duration-200 hover:shadow-md hover:border-primary/20",
        isPast && "opacity-60"
      )}
    >
      {showArtistBar && (
        <div
          className="w-1.5 shrink-0 rounded-l-2xl"
          style={{ backgroundColor: accentColor }}
        />
      )}

      <div className="flex gap-5 p-5 w-full min-w-0">
        {/* Date block */}
        <div className="flex flex-col items-center justify-start min-w-[56px] pt-1 text-center">
          <span className="text-xs font-bold uppercase tracking-widest text-muted-foreground leading-none">
            {dateObj ? MONTHS[dateObj.getMonth()] : "---"}
          </span>
          <span
            className="text-3xl font-black leading-none my-1.5"
            style={{ color: isPast ? undefined : accentColor }}
          >
            {dateObj ? dateObj.getDate() : "--"}
          </span>
          <span className="text-xs font-bold uppercase tracking-widest text-muted-foreground leading-none">
            {dateObj ? DAYS[dateObj.getDay()] : "---"}
          </span>
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-3 mb-2">
            <h3 className="font-bold text-lg leading-tight line-clamp-2 flex-1 tracking-tight">{title}</h3>
            <CountdownBadge label={countdown.label} variant={countdown.variant} />
          </div>

          {showArtistBar && artistDisplayName && (
            <div className="flex items-center gap-2 mb-3">
              {artistImageUrl && (
                <img
                  src={artistImageUrl}
                  alt={artistDisplayName}
                  className="w-5 h-5 rounded-full object-cover shrink-0 ring-1 ring-border"
                />
              )}
              <span className="text-sm font-medium text-muted-foreground">{artistDisplayName}</span>
            </div>
          )}

          <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted-foreground">
            {venue && (
              <span className="flex items-center gap-1.5">
                <MapPin className="h-4 w-4 shrink-0 text-muted-foreground/70" />
                {venue}
              </span>
            )}
            {start_time && (
              <span className="flex items-center gap-1.5">
                <Clock className="h-4 w-4 shrink-0 text-muted-foreground/70" />
                {start_time}
              </span>
            )}
          </div>

          {(ticket_url || source_url) && (
            <div className="flex flex-wrap gap-3 mt-4">
              {ticket_url && (
                <a
                  href={ticket_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 rounded-lg px-4 py-1.5 text-sm font-bold text-white transition-all hover:opacity-90 hover:scale-[1.02] active:scale-[0.98] shadow-sm"
                  style={{ backgroundColor: accentColor }}
                >
                  <ExternalLink className="h-3.5 w-3.5" />
                  チケット
                </a>
              )}
              {source_url && (
                <a
                  href={source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 rounded-lg border bg-background px-4 py-1.5 text-sm font-bold text-muted-foreground hover:text-foreground hover:bg-muted transition-all hover:scale-[1.02] active:scale-[0.98]"
                >
                  公式サイト
                </a>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
