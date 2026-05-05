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
        "shrink-0 inline-flex items-center rounded-full px-2 py-0.5 text-xs font-bold whitespace-nowrap",
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
        "relative flex rounded-xl border bg-card transition-shadow hover:shadow-sm",
        isPast && "opacity-55"
      )}
    >
      {showArtistBar && (
        <div
          className="w-1 shrink-0 rounded-l-xl"
          style={{ backgroundColor: accentColor }}
        />
      )}

      <div className="flex gap-3 p-4 w-full min-w-0">
        {/* Date block */}
        <div className="flex flex-col items-center justify-start min-w-[44px] pt-0.5 text-center">
          <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground leading-none">
            {dateObj ? MONTHS[dateObj.getMonth()] : "---"}
          </span>
          <span
            className="text-2xl font-black leading-tight my-0.5"
            style={{ color: isPast ? undefined : accentColor }}
          >
            {dateObj ? dateObj.getDate() : "--"}
          </span>
          <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground leading-none">
            {dateObj ? DAYS[dateObj.getDay()] : "---"}
          </span>
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <h3 className="font-semibold text-sm leading-snug line-clamp-2 flex-1">{title}</h3>
            <CountdownBadge label={countdown.label} variant={countdown.variant} />
          </div>

          {showArtistBar && artistDisplayName && (
            <div className="flex items-center gap-1.5 mt-1">
              {artistImageUrl && (
                <img
                  src={artistImageUrl}
                  alt={artistDisplayName}
                  className="w-4 h-4 rounded-full object-cover shrink-0"
                />
              )}
              <span className="text-xs text-muted-foreground">{artistDisplayName}</span>
            </div>
          )}

          <div className="flex flex-wrap gap-x-3 gap-y-0.5 mt-1.5 text-xs text-muted-foreground">
            {venue && (
              <span className="flex items-center gap-1">
                <MapPin className="h-3 w-3 shrink-0" />
                {venue}
              </span>
            )}
            {start_time && (
              <span className="flex items-center gap-1">
                <Clock className="h-3 w-3 shrink-0" />
                {start_time}
              </span>
            )}
          </div>

          {(ticket_url || source_url) && (
            <div className="flex flex-wrap gap-2 mt-3">
              {ticket_url && (
                <a
                  href={ticket_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 rounded-md px-2.5 py-1 text-xs font-medium text-white transition-opacity hover:opacity-80"
                  style={{ backgroundColor: accentColor }}
                >
                  <ExternalLink className="h-3 w-3" />
                  チケット
                </a>
              )}
              {source_url && (
                <a
                  href={source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 rounded-md border px-2.5 py-1 text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
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
