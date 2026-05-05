import { Link } from "react-router-dom";
import { useArtists } from "@/hooks/useArtists";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export default function HomePage() {
  const { data: artists, isLoading, error } = useArtists();

  if (isLoading) {
    return (
      <div className="container py-10">
        <h1 className="text-4xl font-bold mb-8 text-center">Favorite Groups</h1>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
          {[...Array(4)].map((_, i) => (
            <Skeleton key={i} className="h-64 w-full rounded-xl" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container py-10 text-center">
        <h1 className="text-2xl font-bold text-destructive">Error loading artists</h1>
        <p className="mt-2 text-muted-foreground">Make sure the backend is running.</p>
      </div>
    );
  }

  return (
    <div className="container py-10">
      <header className="text-center mb-12">
        <h1 className="text-4xl font-bold mb-4">Favorite Groups</h1>
        <p className="text-muted-foreground">クリックして詳細なスケジュールを確認できます。</p>
      </header>

      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
        {artists?.map((artist) => (
          <Link key={artist.name} to={`/artist/${artist.name}`} className="transition-transform hover:scale-105">
            <Card className="overflow-hidden h-full">
              <div className="aspect-[4/3] overflow-hidden">
                <img
                  src={artist.image_url}
                  alt={artist.display_name}
                  className="w-full h-full object-cover"
                />
              </div>
              <CardHeader className="p-4 text-center">
                <CardTitle className="text-xl">{artist.display_name}</CardTitle>
              </CardHeader>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
