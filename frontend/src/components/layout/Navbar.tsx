import { Link, useLocation } from "react-router-dom";
import { Music, LayoutGrid, ArrowLeft } from "lucide-react";
import { cn } from "@/lib/utils";

export default function Navbar() {
  const location = useLocation();
  const isHome = location.pathname === "/";

  return (
    <header className="sticky top-0 z-50 border-b bg-background/60 backdrop-blur-2xl supports-[backdrop-filter]:bg-background/40">
      <div className="mx-auto max-w-5xl px-4">
        <div className="flex h-20 items-center justify-between gap-4">
          <Link
            to="/"
            className="flex items-center gap-3 shrink-0 font-black text-2xl hover:opacity-80 transition-all active:scale-95"
          >
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-primary text-primary-foreground shadow-xl shadow-primary/20">
              <Music className="h-6 w-6" />
            </div>
            <span className="hidden xs:inline tracking-tighter">Live Tracker</span>
          </Link>

          <div className="flex items-center gap-3">
            {!isHome && (
              <Link
                to="/"
                className="flex items-center gap-2.5 rounded-2xl bg-secondary px-5 py-2.5 text-base font-black text-secondary-foreground hover:bg-primary hover:text-primary-foreground transition-all active:scale-95 shadow-sm border border-border"
              >
                <ArrowLeft className="h-5 w-5" />
                <span>アーティスト一覧</span>
              </Link>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}

