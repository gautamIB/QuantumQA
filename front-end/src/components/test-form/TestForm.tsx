import React from 'react';
import { FlexContainer, FlexItem, Input, Select, TextArea } from "@instabase.com/pollen";
import { Box } from "@instabase.com/pollen";
import styled from 'styled-components';
import { TEST_OPTIONS } from "../../constants";
import { FORM_LABELS } from "../../constants";

const FormContainer = styled(Box)`
  width: 690px;
  margin: 24px auto;
`;
  
const TEST_OPTIONS_MAP = {
    [TEST_OPTIONS.TEST_MO]: 'Re use the test-cases already defined in your test-mo',
    [TEST_OPTIONS.END_TO_END_TEST]: 'Test your complete user flow on UI',
    [TEST_OPTIONS.API_TEST]: 'Test your API calls, with YAML a file',
}
  
export interface TFormData {
    [FORM_LABELS.TEST_NAME]: string;
    [FORM_LABELS.TEST_TYPE]: string;
    [FORM_LABELS.FOLDER_URL]: string;
    [FORM_LABELS.DETAILED_STEPS]: string;
  }
  


export const TestForm = ({
    formData,
    setFormData,
    isReadOnly = false,
}: {
    formData: TFormData;
    setFormData: React.Dispatch<React.SetStateAction<TFormData>>;
    isReadOnly?: boolean;
}) => {

  const handleInputChange = (field: keyof TFormData, value: string) => {
    setFormData((prev: TFormData) => ({
      ...prev,
      [field]: value
    }));
  };
    return (
        <FormContainer>
            <FlexContainer gap={5}>
              {!isReadOnly && (
                <FlexItem grow={1} shrink={1}>
                    <Input
                    placeholder="Some name"
                    value={formData[FORM_LABELS.TEST_NAME]}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleInputChange(FORM_LABELS.TEST_NAME, e.target.value)}
                    label="Test name"
                    required
                    fullWidth
                    />
                </FlexItem>
              )}
              <FlexItem grow={1} shrink={1}>
                <Select
                  selected={formData[FORM_LABELS.TEST_TYPE]}
                  onSelect={(value: string) => handleInputChange(FORM_LABELS.TEST_TYPE, value)}
                  options={Object.keys(TEST_OPTIONS_MAP)}
                  placeholder="Select test type"
                  label="Type of test"
                  optionRenderProps={({ value }: { value: TEST_OPTIONS }) => ({
                    label: value,
                    description: TEST_OPTIONS_MAP[value],
                  })}
                  fullWidth
                  disabled={isReadOnly}
                />
              </FlexItem>
            </FlexContainer>
            <Box mt={4}>
              <Input
                placeholder="https://..."
                value={formData[FORM_LABELS.FOLDER_URL]}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleInputChange(FORM_LABELS.FOLDER_URL, e.target.value)}
                type="url"
                label="Test mo's folder URL"
                fullWidth
                disabled={isReadOnly}
              />
            </Box>
            <Box mt={4}>
              <TextArea
                placeholder="Enter the steps"
                value={formData[FORM_LABELS.DETAILED_STEPS]}
                onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => handleInputChange(FORM_LABELS.DETAILED_STEPS, e.target.value)}
                rows={20}
                label="Detailed steps from test mo."
                fullWidth
                disabled={formData[FORM_LABELS.TEST_TYPE] === TEST_OPTIONS.TEST_MO || isReadOnly}
              />
            </Box>
          </FormContainer>
    );
};