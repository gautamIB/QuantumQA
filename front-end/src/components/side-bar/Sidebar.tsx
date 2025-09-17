import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { 
  Box, 
  FlexContainer, 
  FlexItem,
  IconButton,
  Divider,
  TIconButtonProps,
} from '@instabase.com/pollen';
import { Instabase } from '@instabase.com/pollen/app-icon';
import styled from 'styled-components';
import { ROUTES } from '../../constants';

const StyledSidebar = styled(Box)`
  border-right: 1px solid #DEDEE2;
  padding: 12px 8px;
`;

const StyledIconButton = styled(IconButton)<TIconButtonProps & { isActive?: boolean }>`
  background-color: ${props => props.isActive ? '#EBEBFF' : 'transparent'};
  &:not(:disabled) {
    color: ${props => props.isActive ? '#5A52FA' : '#938E85'};
  }
`;

const Sidebar: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const handleTestsClick = () => {
    navigate(ROUTES.TESTS);
  };

  const handleRunsClick = () => {
    navigate(ROUTES.RUNS);
  };

  return (
    <StyledSidebar
      minWidth="48px"
      minHeight="100vh"
    >
      <FlexContainer 
        direction="column" 
        alignItems="start"
        gap={4}
      >
        <Instabase size={28} />
        <Divider direction="horizontal" size={28} />
        <FlexItem grow={1} shrink={1}>
          <FlexContainer 
            direction="column" 
            alignItems="center" 
            gap={4}
          >
            <StyledIconButton
              icon="list"
              label="Tests"
              onClick={handleTestsClick}
              isActive={location.pathname.includes(ROUTES.TESTS) || location.pathname.includes(ROUTES.CREATE)}
            />
            <StyledIconButton
              icon="run"
              label="Runs"
              onClick={handleRunsClick}
              isActive={location.pathname.includes(ROUTES.RUNS)}
            />
          </FlexContainer>
        </FlexItem>
      </FlexContainer>
    </StyledSidebar>
  );
};

export default Sidebar;
