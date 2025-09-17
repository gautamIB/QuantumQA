import React from 'react';
import { Box, FlexContainer, FlexItem, XSmall, H5, Icon } from '@instabase.com/pollen';
import { STEP_KEYS, STEP_STATUS, TStep } from '../../constants';
import styled from 'styled-components';

const Index = styled(XSmall)`
    background-color: #EAEAEC;
    color: #666974;
    border-radius: 10px;
    padding: 0px 5px;
    margin-top: 3px;
`;

const ErrorBox = styled(Box)`
    background-color: #FFF0F0;
    border-radius: 4px;
    padding: 8px;
`;

const ErrorTitle = styled(H5)`
    font-size: 12px;
`;

const ErrorMessage = styled(XSmall)`
    font-family: monospace;
`;

const StatusIcon = styled(Icon)`
    margin-top: 3px;
`;

export const Steps: React.FC<{ steps: TStep[] }> = ({ steps }) => {
    return (
        <Box mt={4}>
            {steps.map((step: TStep, index: number) => (
                <FlexContainer key={index} gap={2} alignItems="start" justify="start" mb={2}>
                    <Index>{index + 1}</Index>
                    <FlexItem grow={1} shrink={1}>
                        <XSmall>{step[STEP_KEYS.NAME]}</XSmall>
                        {step[STEP_KEYS.ERROR_MESSAGE] && (
                            <ErrorBox mt={2}>
                                <ErrorTitle mb={2}>Reason of failure:</ErrorTitle>
                                <ErrorMessage>{step[STEP_KEYS.ERROR_MESSAGE]}</ErrorMessage>
                            </ErrorBox>
                        )}
                    </FlexItem>
                    <FlexItem>
                        {step[STEP_KEYS.STATUS] === STEP_STATUS.FAILED && (
                            <StatusIcon icon="x-circle-filled" size={16} color="#B10A0A" />
                        )}
                        {step[STEP_KEYS.STATUS] === STEP_STATUS.SUCCESS && (
                            <StatusIcon icon="check-circle-filled" size={16} color="#1E803C" />
                        )}
                        {step[STEP_KEYS.STATUS] === STEP_STATUS.IN_PROGRESS && (
                            <StatusIcon icon="in-progress" size={16} color="#5A52FA" />
                        )}
                    </FlexItem>
                </FlexContainer>
            ))}
        </Box>
    );
};
