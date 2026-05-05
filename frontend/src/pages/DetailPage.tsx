import { useParams, Link } from "react-router-dom";
import { useEvents } from "@/hooks/useEvents";
import { useArtists } from "@/hooks/useArtists";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Button, buttonVariants } from "@/components/ui/button";
import { ArrowLeft, Calendar, MapPin, Clock, ExternalLink } from "lucide-react";
import { cn } from "@/lib/utils";

export default function DetailPage() {
  const { artistId } = useParams<{ artistId: string }>();
  const { data: artists } = useArtists();
  const { data: events, isLoading, error } = useEvents(artistId || "");

  const artist = artists?.find((a) => a.name === artistId);

  if (isLoading) {
    return (
      <div className="container py-10">
        <div className="flex items-center gap-4 mb-8">
          <Skeleton className="h-10 w-24" />
          <Skeleton className="h-10 w-48" />
        </div>
        <div className="space-y-4">
          {[...Array(5)].map((_, i) => (
            <Skeleton key={i} className="h-32 w-full rounded-xl" />
          ))}
        </div>
      </div>
    );
  }

  if (error || !artist) {
    return (
      <div className="container py-10 text-center">
        <h1 className="text-2xl font-bold text-destructive">Artist or Events not found</h1>
        <Link to="/">
          <Button variant="outline" className="mt-4">Back to Home</Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="container py-10">
      <header className="mb-10">
        <Link to="/" className="inline-flex items-center text-primary hover:underline mb-6">
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Home
        </Link>
        
        <div className="flex flex-col md:flex-row items-center gap-8">
          <div className="w-32 h-32 md:w-48 md:h-48 rounded-full overflow-hidden border-4 border-muted shadow-lg">
            <img
              src={artist.image_url}
              alt={artist.display_name}
              className="w-full h-full object-cover"
            />
          </div>
          <div className="text-center md:text-left">
            <h1 className="text-4xl md:text-6xl font-bold mb-2">{artist.display_name}</h1>
            <p className="text-xl text-muted-foreground">{events?.length} Upcoming Events</p>
          </div>
        </div>
      </header>

      <div className="space-y-4">
        {events && events.length > 0 ? (
          events.map((event, index) => {
            const dateObj = event.date ? new Date(event.date) : null;
            return (
              <Card key={index} className="overflow-hidden hover:shadow-md transition-shadow">
                <CardContent className="p-6">
                  <div className="flex flex-col md:flex-row gap-6">
                    <div className="flex flex-col items-center justify-center bg-muted/50 rounded-lg p-4 min-w-[100px]">
                      <span className="text-sm font-bold text-muted-foreground uppercase">
                        {dateObj ? dateObj.toLocaleDateString('en-US', { month: 'short' }) : '---'}
                      </span>
                      <span className="text-3xl font-black text-primary">
                        {dateObj ? dateObj.getDate() : '--'}
                      </span>
                      <span className="text-xs font-medium text-muted-foreground">
                        {dateObj ? dateObj.getFullYear() : '????'}
                      </span>
                    </div>

                    <div className="flex-grow">
                      <h3 className="text-xl font-bold mb-3">{event.title}</h3>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-y-2 gap-x-6 text-sm">
                        <div className="flex items-center text-muted-foreground">
                          <MapPin className="mr-2 h-4 w-4 shrink-0" />
                          {event.venue || "Venue TBA"}
                        </div>
                        {event.start_time && (
                          <div className="flex items-center text-muted-foreground">
                            <Clock className="mr-2 h-4 w-4 shrink-0" />
                            {event.start_time}
                          </div>
                        )}
                        <div className="flex items-center">
                          <Badge variant="secondary" className="mt-1">
                            {event.fetch_status}
                          </Badge>
                        </div>
                      </div>
                    </div>

                    <div className="flex flex-col sm:flex-row md:flex-col gap-2 justify-center">
                      {event.ticket_url && (
                        <a
                          href={event.ticket_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className={cn(buttonVariants({ size: "sm" }))}
                        >
                          <ExternalLink className="mr-2 h-4 w-4" />
                          Ticket
                        </a>
                      )}
                      <a
                        href={event.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className={cn(buttonVariants({ variant: "outline", size: "sm" }))}
                      >
                        Source
                      </a>
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })
        ) : (
          <div className="text-center py-20 bg-muted/20 rounded-2xl border-2 border-dashed">
            <Calendar className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium">No events found</h3>
            <p className="text-muted-foreground">Check back later for updates.</p>
          </div>
        )}
      </div>
    </div>
  );
}
