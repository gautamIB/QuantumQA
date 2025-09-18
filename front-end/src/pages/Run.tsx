import { useMatch } from "react-router-dom";
import { RunDetails } from "../components/run-details/RunDetails";
import { ROUTES, RUN_KEYS } from "../constants";
import { GenericError } from "@instabase.com/pollen/illustration";
import { FlexContainer, FlexItem, Tabs } from "@instabase.com/pollen";
import styled from "styled-components";
import { RunLogs } from "../components/run-logs/RunLogs";
import { useRun } from "../api/useRun";
import { RunGif } from "../components/run-gif/RunGif";

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
  padding: 12px 12px 0 12px;
`;

export const Run: React.FC = () => {
  const match = useMatch(`${ROUTES.RUNS}/:name`);
  const runName = match?.params?.name;

  const { data, isLoading, error } = useRun(runName);

  if (!runName) {
    return (
      <StyledFlexContainer justify="center" alignItems="center">
          <GenericError />
      </StyledFlexContainer>
    );
  }

  const tabs = [
    {
      id:  "logs",
      label: "Detailed logs",
      render: () => <RunLogs runName={runName} />,
    },
    {
      id:  "gif",
      label: "GIF",
      render: () => <RunGif gifUrl={data?.[RUN_KEYS.GIF_FILE_PATH]} />,
      disabled: !data?.[RUN_KEYS.GIF_FILE_PATH],
    },
  ];

  return (
    <FlexContainer>
      <RunDetails run={data} error={error} isLoading={isLoading} />
      <Container grow={1} shrink={1}>
        <Tabs tabs={tabs} />
      </Container>
    </FlexContainer>
  );
};