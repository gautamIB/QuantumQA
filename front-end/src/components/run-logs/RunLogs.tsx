import styled from "styled-components";
import { GenericError } from '@instabase.com/pollen/illustration';
import { useLogs } from "../../api/useLogs";
import { Box, FlexContainer, FlexItem, Spinner } from "@instabase.com/pollen";

const StyledFlexContainer = styled(FlexContainer)`
  height: 100vh;
`;

const Container = styled(FlexItem)`
  min-height: 100vh;
  max-height: 100vh;
  overflow-y: auto;
  background-color: #F3F3F3;
  width: 100%;
  max-width: calc(100vw - 350px - 48px);
`;

const LogsBox = styled(FlexItem)`
    margin: 12px 12px 0 12px;
    background-color: #1C1E21;
    color: #F1F2F3;
    padding: 20px;
    border-radius: 12px 12px 0 0;
    max-width: 100%;
    font-size: 13px;
    overflow-x: auto;
    pre {
        font-family: monospace;
    }
`;

const LogsContainer = styled(FlexContainer)`
    height: 100%;
`;

export const RunLogs: React.FC<{ runName: string }> = ({ runName }) => {
    const { data, isLoading, error } = useLogs(runName);

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

  return (
    <Container grow={1} shrink={1}>
        <LogsContainer direction="column">
            <LogsBox grow={1} shrink={1}>
                <pre>{data}</pre>
            </LogsBox>
        </LogsContainer>
    </Container>
  );
};