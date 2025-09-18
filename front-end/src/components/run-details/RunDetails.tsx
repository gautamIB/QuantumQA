import React from 'react';
import { Box, FlexContainer, H5, IconButton, Spinner } from '@instabase.com/pollen';
import { GenericError } from '@instabase.com/pollen/illustration';
import styled from 'styled-components';
import { TestProgress } from '../test-progress/TestProgress';
import { useNavigate } from 'react-router-dom';
import { RUN_KEYS, ROUTES, TRun } from '../../constants';
import { Steps } from '../steps/Steps';

const Container = styled(Box)`
  padding: 12px;
  background: white;
  min-height: 100vh;
  max-height: 100vh;
  overflow-y: auto;
  width: 350px;
  min-width: 350px;
  border-right: 1px solid #DEDEE2;
`;

const StyledFlexContainer = styled(FlexContainer)`
  height: 100vh;
`;

export const RunDetails: React.FC<{ run: TRun, error: any, isLoading: boolean }> = ({ run, error, isLoading }) => {

  const navigate = useNavigate();
  const onLeftArrowClick = () => {
    navigate(ROUTES.RUNS);
  };

  if (error) {
    return (
      <Container>
        <StyledFlexContainer justify="center" alignItems="center">
          <GenericError />
        </StyledFlexContainer>
      </Container>
    );
  }

  if (isLoading) {
    return (
      <Container>
        <StyledFlexContainer justify="center" alignItems="center">
          <Spinner size={40} />
        </StyledFlexContainer>
      </Container>
    );
  }

  return (
    <Container>
        <FlexContainer mb={3} alignItems="center" gap={2}>
          <IconButton icon="arrow-left" onClick={onLeftArrowClick} label="Back" />
          <H5>Run name</H5>
        </FlexContainer>
        <TestProgress
          totalCount={run[RUN_KEYS.TOTAL_COUNT]}
          successCount={run[RUN_KEYS.SUCCESS_COUNT]}
          errorCount={run[RUN_KEYS.FAILED_COUNT]}
          skippedCount={run[RUN_KEYS.SKIPPED_COUNT]}
        />
        {run[RUN_KEYS.STEPS] && (
          <Steps steps={run[RUN_KEYS.STEPS]} />
        )}
    </Container>
  );
};
