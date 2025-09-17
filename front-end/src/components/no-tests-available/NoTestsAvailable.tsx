import { EmptyState, Button } from '@instabase.com/pollen';
import { Annotation2 } from '@instabase.com/pollen/illustration';
import styled from 'styled-components';
import { useNavigate } from 'react-router-dom';
import { ROUTES } from '../../constants';

const StyledEmptyState = styled(EmptyState)`
  height: 100%;
`;

export const NoTestsAvailable = () => {
  const navigate = useNavigate();

  const handleCreateTest = () => {
    navigate(ROUTES.CREATE);
  };

  return (
    <StyledEmptyState
      graphic={<Annotation2 style={{ width: '312px', height: 'auto' }}/>}
      title="No tests available"
      description=""
    >
      <Button label="Create new test" intent="secondary" onClick={handleCreateTest}/>
    </StyledEmptyState>
  );
};