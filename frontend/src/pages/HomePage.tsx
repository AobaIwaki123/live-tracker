import { Music2 } from "lucide-react";
// TODO: Import ArtistGrid status hook or state later

export default function HomePage() {
  return (
    <div className="relative w-full">
      {/* Hero Section (DOM Layer) */}
      <section className="relative w-full h-[420px] md:h-[380px] pointer-events-none z-10 flex flex-col justify-center px-12 md:px-16">
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-700 to-purple-500 shadow-lg shadow-purple-400/40 mb-6">
          <Music2 className="h-8 w-8 text-white" />
        </div>

        <div
          className="h-px w-[360px] max-w-full mb-4"
          style={{
            background: "linear-gradient(to right, rgba(167,139,250,0.9), rgba(236,72,153,0.6), transparent)",
            boxShadow: "0 0 8px rgba(167,139,250,0.8)",
          }}
        />

        <h2 className="font-black text-5xl md:text-7xl tracking-tighter bg-gradient-to-br from-white via-purple-200 to-violet-400 bg-clip-text text-transparent drop-shadow-[0_0_28px_rgba(167,139,250,0.6)] mb-3">
          Live Tracker
        </h2>

        <p className="text-xl md:text-2xl font-normal tracking-wide text-violet-300/75 mb-6">
          ライブ日程 追跡ツール
        </p>

        <div className="flex gap-3 flex-wrap pointer-events-auto">
          {["スケジュール自動取得", "Discord 通知"].map((label) => (
            <span
              key={label}
              className="px-4 py-2 rounded-full text-sm font-medium text-violet-200/90 bg-violet-900/40 border border-violet-400/30 backdrop-blur-sm"
            >
              {label}
            </span>
          ))}
        </div>
      </section>

      {/* 
        Note: The actual artist grid will be rendered inside GlobalCanvas in 3D.
        We don't render the DOM Artist Grid here anymore. 
        A transparent spacer or ScrollControls element might be needed here later 
        if we want to drive 3D scrolling via DOM height.
      */}
      <div className="h-[200vh]" /> {/* Placeholder for scroll space */}
    </div>
  );
}
