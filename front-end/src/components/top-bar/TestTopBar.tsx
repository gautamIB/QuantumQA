import React from 'react';
import {
  Button,
  NavBar,
  H4,
  TButtonProps,
} from '@instabase.com/pollen';
import styled from 'styled-components';

const StyledButton = styled(Button)<TButtonProps>`
  height: 32px;
  line-height: 32px;
`;

interface TestTopBarProps {
  testName: string;
  handleRun?: () => void;
}

export const TestTopBar: React.FC<TestTopBarProps> = ({
  testName,
  handleRun, 
}) => {

  return (
      <NavBar
        start={
            <H4 weight="bold">
                {testName}
            </H4>
        }
        end={
            <StyledButton 
              label="Run" 
              onClick={handleRun} 
              intent="primary"
            />
        }
      />
  );
};
