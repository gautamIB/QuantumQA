import { API_ENDPOINTS, TEST_KEYS } from "../constants";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { API_KEYS } from "../constants";
import { ROUTES } from "../constants";
import { useNavigate } from "react-router-dom";
import { RunTestFormData } from "../components/run-test/RunTest";
import { TTest } from "../constants";

export const useRunTest = () => {
    const queryClient = useQueryClient();
    const navigate = useNavigate();

    return useMutation({
        mutationFn: async ({formData, test}: {formData: RunTestFormData, test: TTest}) => {
          const credentials: any = {
            username: formData.userName,
            password: formData.password,
          };
          if (formData.apiKey) {
            credentials.token = formData.apiKey;
          }
          const response = await fetch(API_ENDPOINTS.CREATE_RUN, {
            method: 'POST',
            body: JSON.stringify({
                env: formData.testUrl,
                credentials,
                test_file_path: test[TEST_KEYS.FILE_PATH],
                test_type: test[TEST_KEYS.TEST_TYPE],
                run_name: formData.runName,
                options: {
                    headless: false,
                    timeout: 300,
                    retry_count: 1,
                },
            }),
            headers: {
              'Content-Type': 'application/json',
            },
          });
          if (!response.ok) {
            throw new Error('Failed to create run');
          }
          return response.json();
        },
        onSuccess: async (_response, { formData }: {formData: RunTestFormData}) => {
          await queryClient.invalidateQueries({ queryKey: [API_KEYS.RUNS] });
          navigate(`${ROUTES.RUNS}/${formData.runName}`);
        },
        onError: (err: any) => {
          console.log(err);
        },
    });
};