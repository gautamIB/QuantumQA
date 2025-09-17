import React, { useState, useEffect } from 'react';
import {
  FlexContainer,
  FlexItem,
} from '@instabase.com/pollen';
import { TFormData, TestForm, initialFormData } from '../components/test-form/TestForm';
import { FORM_LABELS, TEST_KEYS, TEST_OPTIONS, TTest } from '../constants';
import { TestTopBar } from '../components/top-bar/TestTopBar';
import { RunTest } from '../components/run-test/RunTest';
import styled from 'styled-components';

const Container = styled(FlexContainer)`
  min-height: 100vh;
  max-height: 100vh;
  overflow-y: auto;
`;

export const ViewTest: React.FC<{ test: TTest }> = ({ test }) => {
  const [formData, setFormData] = useState<TFormData>(initialFormData);

  useEffect(() => {
    setFormData({
      [FORM_LABELS.TEST_NAME]: test[TEST_KEYS.TEST_NAME] || '',
      [FORM_LABELS.TEST_TYPE]: test[TEST_KEYS.TEST_TYPE] || TEST_OPTIONS.TEST_MO,
      [FORM_LABELS.TEST_MO_URL]: test[TEST_KEYS.TEST_MO_URL] || '',
      [FORM_LABELS.STEPS]: test[TEST_KEYS.STEPS] || '',
    });
  }, [test]);

  const [isRunTestModalOpen, setIsRunTestModalOpen] = useState(false);

  return (
    <>
      <Container direction="column">
        <TestTopBar
          testName={test[TEST_KEYS.TEST_NAME]}
          handleRun={() => setIsRunTestModalOpen(true)}
        />
        <FlexItem grow={1} shrink={1}>
          <TestForm
            formData={formData}
            setFormData={setFormData}
            isReadOnly={true}
          />
        </FlexItem>
      </Container>
      {isRunTestModalOpen && (
        <RunTest 
            isOpen={isRunTestModalOpen}
            onClose={() => setIsRunTestModalOpen(false)}
            onRunTest={() => {}}
            testName={test[TEST_KEYS.TEST_NAME]}
        />
      )}
    </>
  );
};
