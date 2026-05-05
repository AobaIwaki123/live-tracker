import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/api/client";

export interface LiveEvent {
  title: string;
  artist: string;
  date: string | null;
  start_time: string;
  venue: string;
  ticket_url: string;
  source_url: string;
  fetch_status: string;
}

export const useEvents = (artistId: string) => {
  return useQuery<LiveEvent[]>({
    queryKey: ["events", artistId],
    queryFn: async () => {
      const response = await apiClient.get(`/artists/${artistId}/events`);
      return response.data;
    },
  });
};
