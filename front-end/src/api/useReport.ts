import { useQuery } from "@tanstack/react-query";
import { API_ENDPOINTS, API_KEYS } from "../constants";

export const useReport = (runName: string) => {
    return useQuery({
        queryKey: [API_KEYS.REPORT, runName],
        queryFn: () => fetch(`${API_ENDPOINTS.GET_RUNS}/${runName}${API_ENDPOINTS.GET_RUN_REPORT}`).then(r => r.json()),
        refetchOnWindowFocus: false,
    });
};