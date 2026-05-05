import { Link } from "react-router-dom";
import { Music2, ChevronRight } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { useArtists } from "@/hooks/useArtists";

export default function HomePage() {
  const { data: artists, isLoading, error } = useArtists();

  if (isLoading) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-12">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {[...Array(6)].map((_, i) => (
            <Skeleton key={i} className="aspect-[4/3] w-full rounded-2xl" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-24 text-center">
        <h2 className="text-xl font-bold text-destructive mb-4">バックエンドに接続できません</h2>
        <code className="text-sm bg-muted px-4 py-2 rounded-lg inline-block">
          uv run uvicorn src.web.app:app --reload
        </code>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-12">
      <header className="mb-12 text-center">
        <h1 className="text-4xl font-black tracking-tight mb-4 bg-gradient-to-br from-foreground to-foreground/60 bg-clip-text text-transparent">
          アーティスト
        </h1>
        <p className="text-lg text-muted-foreground max-w-lg mx-auto">
          ライブ情報をチェックしたいアーティストを選択してください。
        </p>
      </header>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-8">
        {artists?.map((artist) => (
          <Link
            key={artist.name}
            to={`/artist/${artist.name}`}
            className="group relative flex flex-col overflow-hidden rounded-2xl bg-card border shadow-sm transition-all duration-300 hover:-translate-y-1 hover:shadow-xl hover:border-primary/20"
          >
            <div className="aspect-[16/10] overflow-hidden">
              <img
                src={artist.image_url}
                alt={artist.display_name}
                className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-110"
              />
              <div 
                className="absolute inset-0 opacity-20 group-hover:opacity-10 transition-opacity" 
                style={{ backgroundColor: artist.theme_color }}
              />
            </div>
            
            <div className="flex flex-1 items-center justify-between p-6">
              <div className="flex items-center gap-3">
                <div 
                  className="w-1.5 h-6 rounded-full shrink-0"
                  style={{ backgroundColor: artist.theme_color || "var(--primary)" }}
                />
                <h3 className="text-xl font-bold group-hover:text-primary transition-colors">
                  {artist.display_name}
                </h3>
              </div>
              <ChevronRight className="h-5 w-5 text-muted-foreground group-hover:text-primary transition-colors" />
            </div>
          </Link>
        ))}

        {!artists || artists.length === 0 && (
          <div className="col-span-full py-24 text-center bg-muted/30 rounded-3xl border-2 border-dashed">
            <Music2 className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-xl font-bold mb-2">アーティストが登録されていません</h3>
            <p className="text-muted-foreground">config/artists.yaml を確認してください</p>
          </div>
        )}
      </div>
    </div>
  );
}
