import { useMemo, useLayoutEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, Calendar, Music2, X, Settings } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { useEvents } from "@/hooks/useEvents";
import { useArtists } from "@/hooks/useArtists";
import { applyArtistTheme, clearArtistTheme } from "@/lib/theme";
import { getCountdown } from "@/lib/countdown";
import { useJobProgress, JobProgressDialog } from "@/hooks/useJobProgress";
import EventListItem from "@/components/events/EventListItem";
import MonthSection from "@/components/events/MonthSection";
import PastEventsCollapse from "@/components/events/PastEventsCollapse";
import ArtistEditForm from "@/components/artists/ArtistEditForm";
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
  const { data: artists, mutate: mutateArtists } = useArtists();
  const { data: events, isLoading, error, mutate: mutateEvents } = useEvents(artistId ?? "");
  const [isImageOpen, setIsImageOpen] = useState(false);
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);

  const artist = artists?.find((a) => a.name === artistId);

  const { status, message, isOpen: isJobProgressOpen } = useJobProgress(activeJobId, () => {
    setActiveJobId(null);
    setIsEditOpen(false);
    mutateArtists();
    mutateEvents();
  });

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

  const handleSave = async (data: any) => {
    try {
      const response = await fetch(`/api/artists/${artistId}/update`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      const result = await response.json();
      setActiveJobId(result.job_id);
    } catch (err) {
      console.error("Failed to update artist:", err);
    }
  };

  if (isLoading) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-12">
        <Skeleton className="h-14 w-48 mb-10 rounded-2xl" />
        <Skeleton className="h-80 w-full rounded-[2.5rem] mb-16" />
        <div className="space-y-10">
          {[...Array(4)].map((_, i) => (
            <Skeleton key={i} className="h-40 w-full rounded-[2rem]" />
          ))}
        </div>
      </div>
    );
  }

  if (error || !artist) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-48 text-center">
        <div className="mb-8 inline-flex h-20 w-20 items-center justify-center rounded-3xl bg-destructive/10 text-destructive shadow-xl">
          <Music2 className="h-10 w-10" />
        </div>
        <h2 className="text-3xl font-black mb-6 tracking-tighter">アーティストが見つかりません</h2>
        <Link
          to="/"
          className="inline-flex items-center gap-3 rounded-2xl bg-primary px-8 py-4 text-lg font-black text-primary-foreground shadow-2xl shadow-primary/30 transition-all hover:scale-105 active:scale-95"
        >
          <ArrowLeft className="h-5 w-5" />
          アーティスト一覧に戻る
        </Link>
      </div>
    );
  }

  const themeColor = artist.theme_color || "var(--primary)";

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      {/* Banner */}
      <div
        className="group relative aspect-[21/9] sm:aspect-[21/7] overflow-hidden rounded-[2.5rem] bg-muted mb-8 shadow-2xl shadow-primary/10 transition-all duration-500 hover:shadow-primary/20"
      >
        <img
          src={artist.image_url}
          alt={artist.display_name}
          onClick={() => setIsImageOpen(true)}
          className="h-full w-full object-cover transition-transform duration-700 group-hover:scale-110 cursor-zoom-in"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-black/95 via-black/40 to-transparent transition-opacity group-hover:opacity-90 pointer-events-none" />
        
        {/* Edit Button */}
        <button
          onClick={() => setIsEditOpen(true)}
          className="absolute top-6 right-6 p-3 rounded-2xl bg-white/10 backdrop-blur-xl border border-white/20 text-white opacity-0 group-hover:opacity-100 transition-all hover:bg-white/20 active:scale-95"
        >
          <Settings className="h-6 w-6" />
        </button>

        <div className="absolute bottom-0 left-0 right-0 p-4 sm:p-8 xl:p-10 pointer-events-none">
          <div className="flex flex-row items-end justify-between gap-3">
            <div className="space-y-1 sm:space-y-2 min-w-0">
              <div
                className="hidden sm:inline-block px-3 py-1 rounded-full text-xs font-black uppercase tracking-[0.25em] text-white/90 bg-white/10 backdrop-blur-xl mb-1 sm:mb-2 border border-white/10"
                style={{ backgroundColor: `${themeColor}40` }}
              >
                Artist Profile
              </div>
              <h1
                className="text-3xl sm:text-5xl xl:text-7xl font-black leading-none tracking-tighter drop-shadow-2xl truncate"
                style={{ color: artist.theme_color }}
              >
                {artist.display_name}
              </h1>
            </div>

            <div className="flex flex-wrap gap-2 sm:gap-4 items-center shrink-0">
              {nextCountdown && (
                <div className="px-3 py-2 sm:px-5 sm:py-3 rounded-xl sm:rounded-[1.5rem] bg-white/10 backdrop-blur-2xl border border-white/20 text-white shadow-2xl">
                  <span className="text-[10px] sm:text-xs font-black uppercase tracking-widest text-white/50 block mb-0.5">Next Live</span>
                  <span className="text-base sm:text-xl font-black leading-none">{nextCountdown.label}</span>
                </div>
              )}
              <div className="px-3 py-2 sm:px-5 sm:py-3 rounded-xl sm:rounded-[1.5rem] bg-white/10 backdrop-blur-2xl border border-white/20 text-white shadow-xl">
                <span className="text-[10px] sm:text-xs font-black uppercase tracking-widest text-white/50 block mb-0.5">Upcoming</span>
                <span className="text-base sm:text-xl font-black leading-none">{upcoming.length}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Image Popup */}
      {isImageOpen && (
        <div 
          className="fixed inset-0 z-[100] flex items-center justify-center bg-black/95 backdrop-blur-md p-4 sm:p-10 animate-in fade-in duration-300"
          onClick={() => setIsImageOpen(false)}
        >
          <button 
            className="absolute top-8 right-8 p-4 rounded-full bg-white/10 text-white hover:bg-white/20 transition-colors shadow-2xl border border-white/10"
            onClick={(e) => { e.stopPropagation(); setIsImageOpen(false); }}
          >
            <X className="h-10 w-10" />
          </button>
          <img
            src={artist.image_url}
            alt={artist.display_name}
            className="max-h-[90vh] max-w-[95vw] object-contain rounded-3xl shadow-2xl animate-in zoom-in-95 duration-300 border border-white/10"
          />
        </div>
      )}

      {/* Edit Form */}
      {isEditOpen && artist && (
        <ArtistEditForm 
          artist={artist as any} 
          onSave={handleSave} 
          onCancel={() => setIsEditOpen(false)} 
        />
      )}

      {/* Progress Dialog */}
      <JobProgressDialog isOpen={isJobProgressOpen} status={status} message={message} />

      {/* Event list */}
      {events && events.length > 0 ? (
        <div className="space-y-10">
          <div className="space-y-8">
            {upcomingGroups.map(([key, monthEvents]) => (
              <MonthSection key={key} label={monthLabel(key)}>
                <div className="grid gap-5">
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
            <div className="grid gap-5 mt-6">
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
        <div className="py-48 text-center bg-muted/20 rounded-[3.5rem] border-2 border-dashed border-muted/50 shadow-inner">
          <Calendar className="mx-auto h-24 w-24 text-muted-foreground/30 mb-10" />
          <h3 className="text-4xl font-black mb-6 tracking-tighter">予定されているライブはありません</h3>
          <p className="text-muted-foreground mb-12 text-2xl font-medium">また後ほどチェックしてみてください</p>
          {artist.image_url && (
            <a
              href={String(artist.image_url).startsWith("/img") ? "#" : artist.image_url}
              className="inline-flex items-center gap-4 text-xl font-black text-primary hover:underline underline-offset-[16px] transition-all decoration-[6px]"
            >
              公式サイトを確認する
              <ArrowLeft className="h-6 w-6 rotate-180" />
            </a>
          )}
        </div>
      )}
    </div>
  );
}
