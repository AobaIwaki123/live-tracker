import { useState } from "react";
import { Settings, Download, Plus } from "lucide-react";
import { useArtists } from "@/hooks/useArtists";
import ArtistCreateForm from "@/components/artists/ArtistCreateForm";
import { Skeleton } from "@/components/ui/skeleton";

interface SettingsPageProps {
  onJobStart: (jobId: string) => void;
  isProcessing: boolean;
}

export default function SettingsPage({ onJobStart, isProcessing }: SettingsPageProps) {
  const { data: artists, isLoading } = useArtists();
  const [isCreateOpen, setIsCreateOpen] = useState(false);

  const handleSave = async (data: any) => {
    setIsCreateOpen(false);
    try {
      const response = await fetch("/api/artists/create", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      const result = await response.json();
      onJobStart(result.job_id);
    } catch (err) {
      console.error("Failed to create artist:", err);
    }
  };

  const handleDownload = () => {
    window.open("/api/admin/config/artists.yaml", "_blank");
  };

  if (isLoading) {
    return (
      <div className="p-8 space-y-6">
        <Skeleton className="h-12 w-64 rounded-2xl" />
        {[...Array(5)].map((_, i) => (
          <Skeleton key={i} className="h-24 w-full rounded-3xl" />
        ))}
      </div>
    );
  }

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-6 mb-12">
        <div className="flex items-center gap-4">
          <div className="h-14 w-14 flex items-center justify-center rounded-[1.5rem] bg-violet-100 text-violet-600 shadow-inner">
            <Settings className="h-8 w-8" />
          </div>
          <div>
            <h1 className="text-4xl font-black tracking-tighter">Settings</h1>
            <p className="text-muted-foreground font-medium">システム設定と管理</p>
          </div>
        </div>

        <button
          onClick={handleDownload}
          className="flex items-center justify-center gap-3 rounded-2xl bg-secondary px-6 py-4 text-lg font-black text-secondary-foreground hover:bg-primary hover:text-white transition-all active:scale-95 shadow-sm border border-border group"
        >
          <Download className="h-5 w-5 transition-transform group-hover:-translate-y-1" />
          artists.yaml を保存
        </button>
      </div>

      <div className="grid gap-8">
        {/* Create Card */}
        <button
          onClick={() => setIsCreateOpen(true)}
          disabled={isProcessing}
          className="group relative flex flex-col items-center justify-center p-12 rounded-[3rem] bg-gradient-to-br from-violet-500 to-purple-700 text-white shadow-2xl shadow-purple-200 transition-all hover:scale-[1.02] active:scale-[0.98] disabled:opacity-60 disabled:cursor-not-allowed disabled:hover:scale-100 disabled:active:scale-100"
        >
          <div className="mb-6 rounded-3xl bg-white/20 p-6 backdrop-blur-xl group-hover:scale-110 transition-transform">
            <Plus className="h-12 w-12" />
          </div>
          <h2 className="text-3xl font-black tracking-tighter mb-2">アーティストを新規追加</h2>
          <p className="text-white/70 font-medium text-lg text-center">
            名前、カラー、URLを入力して新しく登録します
          </p>
        </button>

        {/* List Section */}
        <div className="space-y-4">
          <h2 className="text-xl font-black uppercase tracking-widest text-muted-foreground ml-2 mb-4">
            Registered Artists ({artists?.length})
          </h2>
          <div className="grid gap-3">
            {artists?.map((artist) => (
              <div
                key={artist.name}
                className="flex items-center gap-5 p-5 rounded-[2rem] bg-muted/30 border border-border shadow-sm"
              >
                <div className="h-12 w-12 shrink-0 overflow-hidden rounded-xl border border-border bg-white shadow-sm">
                  <img
                    src={artist.image_url}
                    alt={artist.display_name}
                    className="h-full w-full object-cover"
                  />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <div 
                      className="h-2.5 w-2.5 rounded-full" 
                      style={{ backgroundColor: artist.theme_color || "#888888" }} 
                    />
                    <h3 className="font-black tracking-tight truncate">
                      {artist.display_name}
                    </h3>
                  </div>
                  <p className="text-xs font-mono text-muted-foreground/60">ID: {artist.name}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {isCreateOpen && (
        <ArtistCreateForm
          onSave={handleSave}
          onCancel={() => setIsCreateOpen(false)}
        />
      )}
    </div>
  );
}
