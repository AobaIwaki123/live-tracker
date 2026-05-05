export type CountdownVariant = "today" | "soon" | "upcoming" | "past" | "unknown";

export interface Countdown {
  label: string;
  variant: CountdownVariant;
}

export function getCountdown(dateStr: string | null): Countdown {
  if (!dateStr) return { label: "日付未定", variant: "unknown" };

  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const eventDate = new Date(dateStr);
  eventDate.setHours(0, 0, 0, 0);

  const diffDays = Math.round(
    (eventDate.getTime() - today.getTime()) / (1000 * 60 * 60 * 24)
  );

  if (diffDays === 0) return { label: "TODAY", variant: "today" };
  if (diffDays === 1) return { label: "明日", variant: "soon" };
  if (diffDays > 1 && diffDays <= 7) return { label: `${diffDays}日後`, variant: "soon" };
  if (diffDays > 7) return { label: `${diffDays}日後`, variant: "upcoming" };
  return { label: `${Math.abs(diffDays)}日前`, variant: "past" };
}
