import { useMemo } from "react";
import { Calendar } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { useAllEvents, type AllEvent } from "@/hooks/useAllEvents";
import EventListItem from "@/components/events/EventListItem";
import MonthSection from "@/components/events/MonthSection";
import PastEventsCollapse from "@/components/events/PastEventsCollapse";

const MONTH_LABELS = ["1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月", "10月", "11月", "12月"];

function groupByMonth(events: AllEvent[]): [string, AllEvent[]][] {
  const map = new Map<string, AllEvent[]>();
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

export default function HomePage() {
  const { data: events, isLoading, error } = useAllEvents();

  const today = useMemo(() => {
    const d = new Date();
    d.setHours(0, 0, 0, 0);
    return d;
  }, []);

  const { upcoming, past } = useMemo(() => {
    if (!events) return { upcoming: [] as AllEvent[], past: [] as AllEvent[] };
    const upcoming = events.filter((e) => !e.date || new Date(e.date) >= today);
    const past = events.filter((e) => !!e.date && new Date(e.date) < today);
    return { upcoming, past };
  }, [events, today]);

  const upcomingGroups = useMemo(() => groupByMonth(upcoming), [upcoming]);

  if (isLoading) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-8 space-y-3">
        {[...Array(6)].map((_, i) => (
          <Skeleton key={i} className="h-24 w-full rounded-xl" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-20 text-center">
        <h2 className="text-base font-semibold text-destructive mb-3">バックエンドに接続できません</h2>
        <code className="text-sm bg-muted px-4 py-2 rounded-lg inline-block">
          uv run uvicorn src.web.app:app --reload
        </code>
      </div>
    );
  }

  if (!events || events.length === 0) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-24 text-center">
        <Calendar className="mx-auto h-10 w-10 text-muted-foreground mb-3" />
        <h3 className="font-medium mb-1">イベント情報なし</h3>
        <p className="text-sm text-muted-foreground">次のスクレイプ後に更新されます</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
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
                themeColor={event.theme_color}
                showArtistBar={true}
                artistDisplayName={event.display_name}
                artistImageUrl={event.image_url}
              />
            ))}
          </MonthSection>
        ))}
      </div>

      <PastEventsCollapse count={past.length}>
        {past.map((event, i) => (
          <EventListItem
            key={`past-${event.artist}-${i}`}
            title={event.title}
            date={event.date}
            venue={event.venue}
            start_time={event.start_time}
            ticket_url={event.ticket_url}
            source_url={event.source_url}
            themeColor={event.theme_color}
            showArtistBar={true}
            artistDisplayName={event.display_name}
            artistImageUrl={event.image_url}
          />
        ))}
      </PastEventsCollapse>
    </div>
  );
}
