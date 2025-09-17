import React, { useEffect } from 'react';
import { NoTestsAvailable } from '../components/no-tests-available/NoTestsAvailable';
import { ROUTES, TEST_KEYS } from '../constants';
import { Outlet, useMatch, useNavigate } from "react-router";
import { AllTests } from '../components/all-tests/AllTests';
import { FlexContainer, FlexItem, Spinner } from '@instabase.com/pollen';
import styled from 'styled-components';
import { GenericError } from '@instabase.com/pollen/illustration';
import { useTests } from '../api/useTests';

const StyledFlexContainer = styled(FlexContainer)`
  height: 100vh;
`;

export const Tests: React.FC = () => {
  const { data: tests, isLoading, error } = useTests();

  const navigate = useNavigate();
  const match = useMatch('/tests/:name');
  const testName = match?.params?.name;

  useEffect(() => {
    if (tests?.length && !testName) {
      navigate(`${ROUTES.TESTS}/${encodeURIComponent(tests[0][TEST_KEYS.TEST_NAME])}`);
    }
  }, [tests, testName]);

  if (error) {
    return (
      <StyledFlexContainer justify="center" alignItems="center">
        <GenericError />
      </StyledFlexContainer>
    );
  }

  if (isLoading) {
    return (
      <StyledFlexContainer justify="center" alignItems="center">
        <Spinner size={80} />
      </StyledFlexContainer>
    );
  }

  if (!tests?.length) {
    return (
      <NoTestsAvailable />
    );
  }

  return (
    <FlexContainer>
      <AllTests tests={tests} />
      <FlexItem grow={1} shrink={1}>
        <Outlet />
      </FlexItem>
    </FlexContainer>
  )
};

