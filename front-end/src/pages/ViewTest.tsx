import React, { useState } from 'react';
import {
  FlexContainer,
  FlexItem,
} from '@instabase.com/pollen';
import { TFormData, TestForm } from '../components/test-form/TestForm';
import { FORM_LABELS, TEST_OPTIONS, TTest } from '../constants';
import { TestTopBar } from '../components/top-bar/TestTopBar';
import { RunTest } from '../components/run-test/RunTest';

export const ViewTest: React.FC<{ test: TTest }> = ({ test }) => {
  const [formData, setFormData] = useState<TFormData>({
    [FORM_LABELS.TEST_NAME]: test.name || '',
    [FORM_LABELS.TEST_TYPE]: test.type || TEST_OPTIONS.TEST_MO,
    [FORM_LABELS.FOLDER_URL]: test.folderUrl || '',
    [FORM_LABELS.DETAILED_STEPS]: test.detailedSteps || '',
  });

  const [isRunTestModalOpen, setIsRunTestModalOpen] = useState(false);

  return (
    <>
      <FlexContainer direction="column">
        <TestTopBar
            testName={test.name}
            handleRun={() => setIsRunTestModalOpen(true)}
        />
        <FlexItem grow={1} shrink={1}>
          <TestForm
            formData={formData}
            setFormData={setFormData}
            isReadOnly={true}
          />
        </FlexItem>
      </FlexContainer>
      {isRunTestModalOpen && (
        <RunTest 
            isOpen={isRunTestModalOpen}
            onClose={() => setIsRunTestModalOpen(false)}
            onRunTest={() => {}}
            testName={test.name}
        />
      )}
    </>
  );
};
