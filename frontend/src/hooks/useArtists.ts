import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/api/client";

export interface Artist {
  name: string;
  display_name: string;
  image_url: string;
}

export const useArtists = () => {
  return useQuery<Artist[]>({
    queryKey: ["artists"],
    queryFn: async () => {
      const response = await apiClient.get("/artists");
      return response.data;
    },
  });
};
