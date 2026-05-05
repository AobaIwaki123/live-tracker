import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/api/client";

export interface AllEvent {
  title: string;
  artist: string;
  display_name: string;
  date: string | null;
  start_time: string | null;
  venue: string | null;
  ticket_url: string | null;
  source_url: string | null;
  theme_color: string;
  image_url: string;
}

export const useAllEvents = () => {
  return useQuery<AllEvent[]>({
    queryKey: ["all-events"],
    queryFn: async () => {
      const response = await apiClient.get("/events");
      return response.data;
    },
  });
};
