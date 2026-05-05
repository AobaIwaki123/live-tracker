import { useMemo, useLayoutEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, Calendar, Music2 } from "lucide-react";
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
      <div className="mx-auto max-w-4xl px-4 py-8">
        <Skeleton className="h-10 w-32 mb-8 rounded-xl" />
        <Skeleton className="h-64 w-full rounded-3xl mb-12" />
        <div className="space-y-6">
          {[...Array(4)].map((_, i) => (
            <Skeleton key={i} className="h-32 w-full rounded-2xl" />
          ))}
        </div>
      </div>
    );
  }

  if (error || !artist) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-32 text-center">
        <div className="mb-6 inline-flex h-16 w-16 items-center justify-center rounded-full bg-destructive/10 text-destructive">
          <Music2 className="h-8 w-8" />
        </div>
        <h2 className="text-2xl font-black mb-4">アーティストが見つかりません</h2>
        <Link
          to="/"
          className="inline-flex items-center gap-2 rounded-xl bg-primary px-6 py-3 text-sm font-bold text-primary-foreground shadow-lg shadow-primary/20 transition-all hover:scale-105 active:scale-95"
        >
          <ArrowLeft className="h-4 w-4" />
          アーティスト一覧に戻る
        </Link>
      </div>
    );
  }

  const themeColor = artist.theme_color || "hsl(var(--primary))";

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <Link
        to="/"
        className="group inline-flex items-center gap-2 text-sm font-bold text-muted-foreground hover:text-foreground transition-all mb-8 bg-muted/50 px-4 py-2 rounded-xl border border-transparent hover:border-border active:scale-95"
      >
        <ArrowLeft className="h-4 w-4 transition-transform group-hover:-translate-x-1" />
        アーティスト一覧
      </Link>

      {/* Banner */}
      <div className="relative aspect-[21/9] sm:aspect-[21/7] overflow-hidden rounded-3xl bg-muted mb-12 shadow-2xl shadow-primary/5">
        <img
          src={artist.image_url}
          alt={artist.display_name}
          className="h-full w-full object-cover"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/40 to-transparent" />
        <div className="absolute bottom-0 left-0 right-0 p-8 sm:p-10">
          <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-6">
            <div className="space-y-2">
              <div 
                className="inline-block px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest text-white/90 bg-white/10 backdrop-blur-md mb-2"
                style={{ backgroundColor: `${themeColor}40` }}
              >
                Artist Profile
              </div>
              <h1 className="text-4xl sm:text-5xl font-black text-white leading-none tracking-tighter">
                {artist.display_name}
              </h1>
            </div>
            
            <div className="flex flex-wrap gap-4 items-center">
              {nextCountdown && (
                <div className="px-5 py-2.5 rounded-2xl bg-white/10 backdrop-blur-xl border border-white/20 text-white shadow-xl">
                  <span className="text-xs font-bold uppercase tracking-wider text-white/60 block mb-0.5">Next Live</span>
                  <span className="text-lg font-black leading-none">{nextCountdown.label}</span>
                </div>
              )}
              <div className="px-5 py-2.5 rounded-2xl bg-white/10 backdrop-blur-xl border border-white/20 text-white shadow-xl">
                <span className="text-xs font-bold uppercase tracking-wider text-white/60 block mb-0.5">Total Events</span>
                <span className="text-lg font-black leading-none">{upcoming.length}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Event list */}
      {events && events.length > 0 ? (
        <div className="space-y-12">
          <div className="space-y-10">
            {upcomingGroups.map(([key, monthEvents]) => (
              <MonthSection key={key} label={monthLabel(key)}>
                <div className="grid gap-4">
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
                </div>
              </MonthSection>
            ))}
          </div>

          <PastEventsCollapse count={past.length}>
            <div className="grid gap-4 mt-6">
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
            </div>
          </PastEventsCollapse>
        </div>
      ) : (
        <div className="py-32 text-center bg-muted/30 rounded-[2rem] border-2 border-dashed border-muted/50">
          <Calendar className="mx-auto h-16 w-16 text-muted-foreground/40 mb-6" />
          <h3 className="text-2xl font-black mb-2 tracking-tight">予定されているライブはありません</h3>
          <p className="text-muted-foreground mb-8 text-lg">また後ほどチェックしてみてください</p>
          {artist.image_url && (
            <a
              href={String(artist.image_url).startsWith("/img") ? "#" : artist.image_url}
              className="inline-flex items-center gap-2 text-sm font-bold text-primary hover:underline underline-offset-8 transition-all"
            >
              公式サイトを確認する
              <ArrowLeft className="h-4 w-4 rotate-180" />
            </a>
          )}
        </div>
      )}
    </div>
  );
}
