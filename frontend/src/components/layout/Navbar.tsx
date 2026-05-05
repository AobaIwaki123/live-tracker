import { Link, useLocation } from "react-router-dom";
import { Music, Sun, Moon } from "lucide-react";
import { useArtists } from "@/hooks/useArtists";
import { useDarkMode } from "@/hooks/useDarkMode";
import { cn } from "@/lib/utils";

export default function Navbar() {
  const location = useLocation();
  const { data: artists } = useArtists();
  const { isDark, toggle } = useDarkMode();

  const currentArtistId = location.pathname.startsWith("/artist/")
    ? location.pathname.replace("/artist/", "")
    : null;

  const tabClass = (active: boolean) =>
    cn(
      "rounded-md px-3 py-1.5 text-sm font-medium transition-colors whitespace-nowrap",
      active
        ? "bg-primary text-primary-foreground"
        : "text-muted-foreground hover:text-foreground hover:bg-muted"
    );

  return (
    <header className="sticky top-0 z-50 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="mx-auto max-w-3xl px-4">
        <div className="flex h-14 items-center gap-3">
          <Link
            to="/"
            className="flex items-center gap-1.5 shrink-0 font-semibold hover:opacity-80 transition-opacity"
          >
            <Music className="h-5 w-5" />
            <span>Live Tracker</span>
          </Link>

          <div className="w-px h-5 bg-border shrink-0" />

          <nav className="flex-1 overflow-x-auto scrollbar-none">
            <div className="flex items-center gap-1 min-w-max">
              <Link to="/" className={tabClass(!currentArtistId)}>
                All
              </Link>
              {artists?.map((artist) => (
                <Link
                  key={artist.name}
                  to={`/artist/${artist.name}`}
                  className={tabClass(currentArtistId === artist.name)}
                >
                  {artist.display_name}
                </Link>
              ))}
            </div>
          </nav>

          <button
            onClick={toggle}
            className="shrink-0 rounded-md p-2 text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
            aria-label="テーマを切り替え"
          >
            {isDark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </button>
        </div>
      </div>
    </header>
  );
}
