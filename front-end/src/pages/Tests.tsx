import React, { useEffect, useState } from 'react';
import { NoTestsAvailable } from '../components/no-tests-available/NoTestsAvailable';
import { ROUTES } from '../constants';
import { Outlet, useMatch, useNavigate } from "react-router";
import { AllTests } from '../components/all-tests/AllTests';
import { FlexContainer, FlexItem } from '@instabase.com/pollen';
import { TESTS } from '../data';
import { TTest } from '../constants';

export const Tests: React.FC = () => {
  const [tests, setTests] = useState<TTest[]>(TESTS);
  const navigate = useNavigate();
  const match = useMatch('/tests/:id');
  const matchParamId = match?.params?.id;

  useEffect(() => {
    if (tests.length && !matchParamId) {
      navigate(`${ROUTES.TESTS}/${tests[0].id}`);
    }
  }, [tests, matchParamId]);

  if (!tests.length) {
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

