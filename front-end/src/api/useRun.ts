import { useQuery, useQueryClient } from "@tanstack/react-query";
import { API_ENDPOINTS, API_KEYS, RUN_KEYS, RUN_STATUS } from "../constants";
import { useRef } from "react";

export const useRun = (runName?: string) => {
    const refetchTimeout = useRef<NodeJS.Timeout | null>(null);
    const queryClient = useQueryClient();
    return useQuery({
        queryKey: [API_KEYS.RUN, runName],
        queryFn: async () => {
            const response = await fetch(`${API_ENDPOINTS.GET_RUNS}/${runName}`);
            if (!response.ok) {
                throw new Error('Failed to get run');
            }
            return response.json();
        },
        onSuccess: (data) => {
            if (data[RUN_KEYS.STATUS] === RUN_STATUS.IN_PROGRESS) {
                refetchTimeout.current = setTimeout(() => {
                    queryClient.invalidateQueries({ queryKey: [API_KEYS.RUN, runName] });
                    queryClient.invalidateQueries({ queryKey: [API_KEYS.LOGS, runName] });
                }, 1000);
            } else {
                if (refetchTimeout.current) {
                    clearTimeout(refetchTimeout.current);
                }
            }
        },
        refetchOnWindowFocus: false,
        enabled: !!runName,
    });
};