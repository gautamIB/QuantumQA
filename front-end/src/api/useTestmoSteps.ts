import { useMutation } from "@tanstack/react-query";
import { API_ENDPOINTS } from "../constants";

export const useTestmoSteps = () => {
    return useMutation({
        mutationFn: (testMoUrl?: string) => fetch(API_ENDPOINTS.GET_TESTMO_STEPS, {
            method: 'POST',
            body: JSON.stringify({
                test_url: testMoUrl,
            }),
            headers: {
                'Content-Type': 'application/json',
            },
        }).then(r => r.text()),
        onError: (error: any) => {
            console.log(error);
        },
    });
};