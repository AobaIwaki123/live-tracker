import { Link, useLocation } from "react-router-dom";
import { Music, ArrowLeft } from "lucide-react";

export default function Navbar() {
  const location = useLocation();
  const isHome = location.pathname === "/";

  return (
    <header className="sticky top-0 z-50 bg-white/70 backdrop-blur-2xl supports-[backdrop-filter]:bg-white/60 border-b border-purple-100/80 shadow-[0_1px_20px_rgba(147,112,219,0.08)]">
      <div className="mx-auto max-w-5xl px-4">
        <div className="flex h-20 items-center justify-between gap-4">
          <Link
            to="/"
            className="flex items-center gap-3 shrink-0 font-black text-2xl hover:opacity-80 transition-all active:scale-95"
          >
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-500 to-purple-700 text-white shadow-lg shadow-purple-400/30">
              <Music className="h-6 w-6" />
            </div>
            <span className="tracking-tighter bg-gradient-to-r from-violet-700 to-purple-500 bg-clip-text text-transparent">
              Live Tracker
            </span>
          </Link>

          <div className="flex items-center gap-3">
            {!isHome && (
              <Link
                to="/"
                className="flex items-center gap-2.5 rounded-2xl bg-secondary px-4 py-2.5 text-base font-black text-secondary-foreground hover:bg-violet-600 hover:text-white transition-all active:scale-95 shadow-sm border border-border"
              >
                <ArrowLeft className="h-5 w-5 shrink-0" />
                <span className="hidden sm:inline">アーティスト一覧</span>
              </Link>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}

