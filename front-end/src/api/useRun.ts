import { useQuery } from "@tanstack/react-query";
import { API_ENDPOINTS, API_KEYS } from "../constants";

export const useRun = (runName: string) => {
    return useQuery({
        queryKey: [API_KEYS.RUN, runName],
        queryFn: () => fetch(`${API_ENDPOINTS.GET_RUNS}/${runName}`).then(r => r.json()),
        refetchOnWindowFocus: false,
    });
};