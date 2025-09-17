import { TFormData } from "../components/test-form/TestForm";
import { FORM_LABELS, API_ENDPOINTS, TEST_KEYS } from "../constants";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { API_KEYS } from "../constants";
import { ROUTES } from "../constants";
import { useNavigate } from "react-router-dom";

export const useCreateTest = () => {
    const queryClient = useQueryClient();
    const navigate = useNavigate();

    return useMutation({
        mutationFn: (test: TFormData) => {
          const formData = new FormData();
          formData.append(TEST_KEYS.TEST_NAME, test[FORM_LABELS.TEST_NAME]);
          formData.append(TEST_KEYS.TEST_TYPE, test[FORM_LABELS.TEST_TYPE]);
          formData.append(TEST_KEYS.STEPS, test[FORM_LABELS.STEPS]);
          
          return fetch(API_ENDPOINTS.CREATE_TEST_CONFIGURATION, {
            method: 'POST',
            body: formData,
          });
        },
        onSuccess: async (_response, test: TFormData) => {
          await queryClient.invalidateQueries({ queryKey: [API_KEYS.TEST_CONFIGURATIONS] });
          navigate(`${ROUTES.TESTS}/${test[FORM_LABELS.TEST_NAME]}`);
        },
        onError: (err: any) => {
          console.log(err);
        },
    });
};