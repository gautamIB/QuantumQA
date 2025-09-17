import { useQuery } from "@tanstack/react-query";
import { API_ENDPOINTS, API_KEYS } from "../constants";
import { RUNS } from "../data";

export const useRuns = () => {
    return useQuery({
        queryKey: [API_KEYS.RUNS],
        queryFn: () => {
            // return { runs: RUNS }
            return fetch(API_ENDPOINTS.GET_RUNS).then(r => r.json())
        },
        refetchOnWindowFocus: false,
    });
};