import { useQuery } from "@tanstack/react-query";
import { API_ENDPOINTS, API_KEYS } from "../constants";

export const useTests = () => {
    return useQuery({
        queryKey: [API_KEYS.TEST_CONFIGURATIONS],
        queryFn: () => fetch(API_ENDPOINTS.GET_TEST_CONFIGURATIONS).then(r => r.json()),
        staleTime: 1000 * 60,
        refetchOnWindowFocus: false,
        onError: (err: any) => {
            console.log(err);
        },
    });
};