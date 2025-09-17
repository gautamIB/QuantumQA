import { useQuery } from "@tanstack/react-query";
import { API_ENDPOINTS, API_KEYS } from "../constants";

export const useLogs = (runName: string) => {
    return useQuery({
        queryKey: [API_KEYS.LOGS, runName],
        queryFn: () => fetch(`${API_ENDPOINTS.GET_RUNS}/${runName}${API_ENDPOINTS.GET_RUN_LOGS}`).then(r => r.text()),
        refetchOnWindowFocus: false,
    });
};