import { useMatch } from "react-router-dom";
import { RunDetails } from "../components/run-details/RunDetails";
import { ROUTES } from "../constants";
import { GenericError } from "@instabase.com/pollen/illustration";
import { FlexContainer } from "@instabase.com/pollen";
import styled from "styled-components";
import { RunLogs } from "../components/run-logs/RunLogs";

const StyledFlexContainer = styled(FlexContainer)`
  height: 100vh;
`;

export const Run: React.FC = () => {
  const match = useMatch(`${ROUTES.RUNS}/:name`);
  const runName = match?.params?.name;

  if (!runName) {
    return (
      <StyledFlexContainer justify="center" alignItems="center">
          <GenericError />
      </StyledFlexContainer>
    );
  }
  return (
    <FlexContainer>
      <RunDetails runName={runName} />
      <RunLogs runName={runName} />
    </FlexContainer>
  );
};