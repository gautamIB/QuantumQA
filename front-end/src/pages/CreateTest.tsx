import React, { useState } from 'react';
import { CreateTopBar } from '../components/top-bar/CreateTopBar';
import {
  FlexContainer,
  FlexItem,
} from '@instabase.com/pollen';
import { TFormData, TestForm } from '../components/test-form/TestForm';
import { FORM_LABELS, TEST_OPTIONS } from '../constants';

const initialFormData: TFormData = {
  [FORM_LABELS.TEST_NAME]: '',
  [FORM_LABELS.TEST_TYPE]: TEST_OPTIONS.TEST_MO,
  [FORM_LABELS.FOLDER_URL]: '',
  [FORM_LABELS.DETAILED_STEPS]: '',
}

export const CreateTest: React.FC = () => {
  
  const [formData, setFormData] = useState<TFormData>(initialFormData);

  const handleCreateTest = () => {
    // TODO: Implement actual test creation logic
    console.log('Creating test with data:', formData);
    
    // Reset form
    setFormData(initialFormData);
  };

  const isFormValid = formData[FORM_LABELS.TEST_NAME].trim().length > 0;

  return (
      <FlexContainer direction="column">
        <CreateTopBar
          handleCreate={handleCreateTest}
          isCreateDisabled={!isFormValid}
        />
        <FlexItem grow={1} shrink={1}>
          <TestForm
            formData={formData}
            setFormData={setFormData}
          />
        </FlexItem>
      </FlexContainer>
  );
};
