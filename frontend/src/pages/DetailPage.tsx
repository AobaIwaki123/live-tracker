import { useMemo, useLayoutEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, Calendar } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { useEvents } from "@/hooks/useEvents";
import { useArtists } from "@/hooks/useArtists";
import { applyArtistTheme, clearArtistTheme } from "@/lib/theme";
import { getCountdown } from "@/lib/countdown";
import EventListItem from "@/components/events/EventListItem";
import MonthSection from "@/components/events/MonthSection";
import PastEventsCollapse from "@/components/events/PastEventsCollapse";
import type { LiveEvent } from "@/hooks/useEvents";

const MONTH_LABELS = ["1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月", "10月", "11月", "12月"];

function groupByMonth(events: LiveEvent[]): [string, LiveEvent[]][] {
  const map = new Map<string, LiveEvent[]>();
  for (const event of events) {
    const key = event.date
      ? `${new Date(event.date).getFullYear()}-${String(new Date(event.date).getMonth() + 1).padStart(2, "0")}`
      : "undated";
    if (!map.has(key)) map.set(key, []);
    map.get(key)!.push(event);
  }
  return [...map.entries()];
}

function monthLabel(key: string): string {
  if (key === "undated") return "日付未定";
  const [year, month] = key.split("-");
  return `${year}年${MONTH_LABELS[parseInt(month, 10) - 1]}`;
}

export default function DetailPage() {
  const { artistId } = useParams<{ artistId: string }>();
  const { data: artists } = useArtists();
  const { data: events, isLoading, error } = useEvents(artistId ?? "");

  const artist = artists?.find((a) => a.name === artistId);

  useLayoutEffect(() => {
    if (artist?.theme_color) applyArtistTheme(artist.theme_color);
    return () => clearArtistTheme();
  }, [artist?.theme_color]);

  const today = useMemo(() => {
    const d = new Date();
    d.setHours(0, 0, 0, 0);
    return d;
  }, []);

  const { upcoming, past } = useMemo(() => {
    if (!events) return { upcoming: [] as LiveEvent[], past: [] as LiveEvent[] };
    const upcoming = events.filter((e) => !e.date || new Date(e.date) >= today);
    const past = events.filter((e) => !!e.date && new Date(e.date) < today);
    return { upcoming, past };
  }, [events, today]);

  const upcomingGroups = useMemo(() => groupByMonth(upcoming), [upcoming]);

  const nextEvent = upcoming.find((e) => e.date);
  const nextCountdown = nextEvent ? getCountdown(nextEvent.date) : null;

  if (isLoading) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-8">
        <Skeleton className="h-4 w-24 mb-6" />
        <Skeleton className="h-40 w-full rounded-xl mb-8" />
        <div className="space-y-3">
          {[...Array(4)].map((_, i) => (
            <Skeleton key={i} className="h-24 w-full rounded-xl" />
          ))}
        </div>
      </div>
    );
  }

  if (error || !artist) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-20 text-center">
        <h2 className="text-base font-semibold text-destructive mb-4">アーティストが見つかりません</h2>
        <Link
          to="/"
          className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          トップに戻る
        </Link>
      </div>
    );
  }

  const themeColor = artist.theme_color || "hsl(var(--primary))";

  return (
    <div className="mx-auto max-w-3xl px-4 py-6">
      <Link
        to="/"
        className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors mb-5"
      >
        <ArrowLeft className="h-4 w-4" />
        すべてのイベント
      </Link>

      {/* Banner */}
      <div className="relative aspect-[16/5] overflow-hidden rounded-xl bg-muted mb-6">
        <img
          src={artist.image_url}
          alt={artist.display_name}
          className="h-full w-full object-cover"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/30 to-transparent" />
        <div className="absolute bottom-0 left-0 right-0 p-5">
          <h1 className="text-2xl font-bold text-white leading-tight mb-1.5">
            {artist.display_name}
          </h1>
          <div className="flex flex-wrap gap-3 text-sm text-white/75">
            {nextCountdown && (
              <span>次のライブまで {nextCountdown.label}</span>
            )}
            {upcoming.length > 0 && (
              <span>直近 {upcoming.length} 件</span>
            )}
          </div>
        </div>
      </div>

      {/* Event list */}
      {events && events.length > 0 ? (
        <>
          <div className="space-y-8">
            {upcomingGroups.map(([key, monthEvents]) => (
              <MonthSection key={key} label={monthLabel(key)}>
                {monthEvents.map((event, i) => (
                  <EventListItem
                    key={`${event.artist}-${i}`}
                    title={event.title}
                    date={event.date}
                    venue={event.venue}
                    start_time={event.start_time}
                    ticket_url={event.ticket_url}
                    source_url={event.source_url}
                    themeColor={themeColor}
                  />
                ))}
              </MonthSection>
            ))}
          </div>

          <PastEventsCollapse count={past.length}>
            {past.map((event, i) => (
              <EventListItem
                key={`past-${i}`}
                title={event.title}
                date={event.date}
                venue={event.venue}
                start_time={event.start_time}
                ticket_url={event.ticket_url}
                source_url={event.source_url}
                themeColor={themeColor}
              />
            ))}
          </PastEventsCollapse>
        </>
      ) : (
        <div className="py-20 text-center">
          <Calendar className="mx-auto h-10 w-10 text-muted-foreground mb-3" />
          <h3 className="font-medium mb-1">イベント情報なし</h3>
          <p className="text-sm text-muted-foreground mb-4">次のスクレイプ後に更新されます</p>
          {artist.image_url && (
            <a
              href={String(artist.image_url).startsWith("/img") ? "#" : ""}
              className="text-sm text-muted-foreground hover:text-foreground underline underline-offset-4 transition-colors"
            >
              公式サイトを確認する
            </a>
          )}
        </div>
      )}
    </div>
  );
}
