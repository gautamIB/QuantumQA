import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Button,
  NavBar,
  H4,
  FlexContainer,
  TButtonProps,
} from '@instabase.com/pollen';
import styled from 'styled-components';
import { ROUTES } from '../../constants';

const StyledButton = styled(Button)<TButtonProps>`
  height: 32px;
  line-height: 32px;
`;

interface CreateTopBarProps {
  handleCreate?: () => void;
  isCreateDisabled?: boolean;
}

export const CreateTopBar: React.FC<CreateTopBarProps> = ({ 
  handleCreate, 
  isCreateDisabled = false 
}) => {
  const navigate = useNavigate();

  const handleCancel = () => {
    navigate(ROUTES.TESTS);
  };

  return (
      <NavBar
        start={
            <H4 weight="bold">
                Create new test
            </H4>
        }
        end={
          <FlexContainer gap={2}>
            <StyledButton
              label="Cancel" 
              onClick={handleCancel} 
              intent="secondary"
            />
            <StyledButton 
              label="Create" 
              onClick={handleCreate} 
              intent="primary"
              disabled={isCreateDisabled}
            />
          </FlexContainer>
        }
      />
  );
};
