import React, { useState } from 'react';
import { CreateTopBar } from '../components/top-bar/CreateTopBar';
import {
  FlexContainer,
  FlexItem,
} from '@instabase.com/pollen';
import { TFormData, TestForm, initialFormData } from '../components/test-form/TestForm';
import { FORM_LABELS } from '../constants';
import { useCreateTest } from '../api/useCreateTest';
import styled from 'styled-components';

const Container = styled(FlexContainer)`
  min-height: 100vh;
  max-height: 100vh;
  overflow-y: auto;
`;

export const CreateTest: React.FC = () => {
  const { mutateAsync: createTest, isLoading } = useCreateTest();
  const [formData, setFormData] = useState<TFormData>(initialFormData);

  const handleCreateTest = async () => {
    await createTest(formData);
    // Reset form
    setFormData(initialFormData);
  };

  const isFormInvalid = !formData[FORM_LABELS.TEST_NAME] || !formData[FORM_LABELS.STEPS];

  return (
      <Container direction="column">
        <CreateTopBar
          handleCreate={handleCreateTest}
          isDisabled={isFormInvalid || isLoading}
        />
        <FlexItem grow={1} shrink={1}>
          <TestForm
            formData={formData}
            setFormData={setFormData}
          />
        </FlexItem>
      </Container>
  );
};
