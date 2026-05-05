import { Link, useLocation } from "react-router-dom";
import { Music, Sun, Moon, LayoutGrid } from "lucide-react";
import { useDarkMode } from "@/hooks/useDarkMode";
import { cn } from "@/lib/utils";

export default function Navbar() {
  const location = useLocation();
  const { isDark, toggle } = useDarkMode();

  const isHome = location.pathname === "/";

  return (
    <header className="sticky top-0 z-50 border-b bg-background/80 backdrop-blur-xl supports-[backdrop-filter]:bg-background/60">
      <div className="mx-auto max-w-5xl px-4">
        <div className="flex h-16 items-center justify-between gap-4">
          <Link
            to="/"
            className="flex items-center gap-2.5 shrink-0 font-black text-xl hover:opacity-80 transition-all active:scale-95"
          >
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-lg shadow-primary/20">
              <Music className="h-5 w-5" />
            </div>
            <span className="hidden sm:inline tracking-tight">Live Tracker</span>
          </Link>

          <div className="flex items-center gap-2">
            {!isHome && (
              <Link
                to="/"
                className="flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-bold text-muted-foreground hover:text-foreground hover:bg-muted transition-all active:scale-95"
              >
                <LayoutGrid className="h-4 w-4" />
                アーティスト一覧
              </Link>
            )}

            <button
              onClick={toggle}
              className="rounded-xl p-2.5 text-muted-foreground hover:text-foreground hover:bg-muted transition-all active:scale-95 border border-transparent hover:border-border"
              aria-label="テーマを切り替え"
            >
              {isDark ? (
                <Sun className="h-5 w-5 transition-all duration-300 rotate-0 scale-100" />
              ) : (
                <Moon className="h-5 w-5 transition-all duration-300 rotate-0 scale-100" />
              )}
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
