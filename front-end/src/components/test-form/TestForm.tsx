import React from 'react';
import { Button, FlexContainer, FlexItem, Input, Select, TextArea } from "@instabase.com/pollen";
import { Box } from "@instabase.com/pollen";
import styled from 'styled-components';
import { TEST_OPTIONS } from "../../constants";
import { FORM_LABELS } from "../../constants";
import { useTestmoSteps } from '../../api/useTestmoSteps';
import { parseYamlFile } from '../../utils/yamlParser';

const FormContainer = styled(Box)`
  width: 690px;
  margin: 24px auto;
`;
  
const TEST_OPTIONS_DESCRIPTION_MAP = {
  [TEST_OPTIONS.TEST_MO]: 'Re use the test-cases already defined in your test-mo',
  [TEST_OPTIONS.END_TO_END_TEST]: 'Test your complete user flow on UI',
  [TEST_OPTIONS.API_TEST]: 'Test your API calls, with YAML a file',
}

export const TEST_OPTIONS_LABEL_MAP = {
  [TEST_OPTIONS.TEST_MO]: 'Test mo',
  [TEST_OPTIONS.END_TO_END_TEST]: 'End to end test',
  [TEST_OPTIONS.API_TEST]: 'API Test',
}
  
export interface TFormData {
  [FORM_LABELS.TEST_NAME]: string;
  [FORM_LABELS.TEST_TYPE]: string;
  [FORM_LABELS.TEST_MO_URL]?: string;
  [FORM_LABELS.STEPS]: string;
  [FORM_LABELS.API_YAML]?: File | null;
}

export const initialFormData: TFormData = {
  [FORM_LABELS.TEST_NAME]: '',
  [FORM_LABELS.TEST_TYPE]: TEST_OPTIONS.TEST_MO,
  [FORM_LABELS.TEST_MO_URL]: '',
  [FORM_LABELS.STEPS]: '',
  [FORM_LABELS.API_YAML]: null,
}

const STEPS_LABEL: Record<TEST_OPTIONS, string> = {
  [TEST_OPTIONS.TEST_MO]: 'Detailed steps from test mo',
  [TEST_OPTIONS.END_TO_END_TEST]: 'Detailed step by step guide to test',
  [TEST_OPTIONS.API_TEST]: 'APIs to be tested',
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
  const { mutateAsync: getTestmoSteps, isLoading } = useTestmoSteps();

  const handleInputChange = (field: keyof TFormData, value: string | File | null) => {
    setFormData((prev: TFormData) => ({
      ...prev,
      [field]: value
    }));
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleInputChange(FORM_LABELS.API_YAML, file);
      const steps = await parseYamlFile(file);
      handleInputChange(FORM_LABELS.STEPS, steps);
    }
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
                  selectedText={(selected: TEST_OPTIONS) => TEST_OPTIONS_LABEL_MAP[selected]}
                  onSelect={(value: string) => handleInputChange(FORM_LABELS.TEST_TYPE, value)}
                  options={Object.keys(TEST_OPTIONS_LABEL_MAP)}
                  placeholder="Select test type"
                  label="Type of test"
                  optionRenderProps={({ value }: { value: TEST_OPTIONS }) => ({
                    label: TEST_OPTIONS_LABEL_MAP[value],
                    description: TEST_OPTIONS_DESCRIPTION_MAP[value],
                  })}
                  fullWidth
                  disabled={isReadOnly}
                />
              </FlexItem>
            </FlexContainer>
            {!isReadOnly && formData[FORM_LABELS.TEST_TYPE] === TEST_OPTIONS.TEST_MO && (
              <FlexContainer gap={2} mt={4} alignItems="flex-end">
                <FlexItem grow={1} shrink={1}>
                  <Input
                    placeholder="https://..."
                    value={formData[FORM_LABELS.TEST_MO_URL]}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleInputChange(FORM_LABELS.TEST_MO_URL, e.target.value)}
                    type="url"
                    label="Test mo's folder URL"
                    fullWidth
                  />
                </FlexItem>
                <FlexItem>
                  <Button
                    intent="primary"
                    label="Get steps"
                    onClick={() => getTestmoSteps(formData[FORM_LABELS.TEST_MO_URL])}
                    loading={isLoading}
                    disabled={!formData[FORM_LABELS.TEST_MO_URL]}
                  />
                </FlexItem>
              </FlexContainer>
            )}
            {!isReadOnly && formData[FORM_LABELS.TEST_TYPE] === TEST_OPTIONS.API_TEST && (
              <FlexContainer gap={2} mt={4} alignItems="flex-end">
                <input
                  type="file"
                  id="file-picker"
                  accept=".yaml,.yml"
                  hidden
                  onChange={handleFileChange}
                />
                <FlexItem grow={1} shrink={1}>
                  <Input
                    placeholder="No file selected"
                    value={formData[FORM_LABELS.API_YAML]?.name || "No file selected"}
                    label="API YAML file"
                    fullWidth
                    disabled
                  />
                </FlexItem>
                <FlexItem>
                  <Button
                    intent="primary"
                    label="Upload"
                    as="label"
                    htmlFor="file-picker"
                  />
                </FlexItem>
              </FlexContainer>
            )}
            <Box mt={4}>
              <TextArea
                placeholder="Enter the steps"
                value={formData[FORM_LABELS.STEPS]}
                onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => handleInputChange(FORM_LABELS.STEPS, e.target.value)}
                rows={25}
                label={STEPS_LABEL[formData[FORM_LABELS.TEST_TYPE] as TEST_OPTIONS]}
                fullWidth
                disabled={formData[FORM_LABELS.TEST_TYPE] !== TEST_OPTIONS.END_TO_END_TEST}
              />
            </Box>
          </FormContainer>
    );
};

