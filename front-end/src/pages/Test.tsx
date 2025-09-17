import React from 'react';
import { useMatch } from 'react-router-dom';
import { ViewTest } from './ViewTest';
import { ROUTES, TEST_KEYS, TTest } from '../constants';
import { useTests } from '../api/useTests';
import { GenericError } from '@instabase.com/pollen/illustration';
import styled from 'styled-components';
import { FlexContainer } from '@instabase.com/pollen';

const StyledFlexContainer = styled(FlexContainer)`
  height: 100vh;
`;

export const Test: React.FC = () => {
    const { data: tests } = useTests();
    const match = useMatch(`${ROUTES.TESTS}/:name`);

    if (match?.params?.name && tests?.length) {
        const test = tests.find((test: TTest) => test[TEST_KEYS.TEST_NAME] === decodeURI(match.params.name as string));
        if (test) {
            return (
                <ViewTest test={test} />
            );
        }
        return (
            <StyledFlexContainer justify="center" alignItems="center">
                <GenericError />
            </StyledFlexContainer>
        );
    }
    return null;
};

