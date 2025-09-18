import styled from "styled-components";
import { GenericError } from '@instabase.com/pollen/illustration';
import { useLogs } from "../../api/useLogs";
import { FlexContainer, FlexItem, Spinner } from "@instabase.com/pollen";
import { useEffect, useRef } from "react";

const StyledFlexContainer = styled(FlexContainer)`
  height: 100vh;
`;

const LogsBox = styled(FlexItem)`
    background-color: #1C1E21;
    color: #F1F2F3;
    padding: 20px;
    border-radius: 12px 12px 0 0;
    max-width: 100%;
    font-size: 13px;
    overflow-x: auto;
    margin-top: 12px;
    pre {
      font-family: monospace;
    }
    min-height: calc(100vh - 40px - 24px);
    max-height: calc(100vh - 40px - 24px);
`;

export const RunLogs: React.FC<{ runName: string }> = ({ runName }) => {
    const { data, isLoading, error } = useLogs(runName);

    const containerRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
      containerRef.current?.scrollTo({
        top: containerRef.current?.scrollHeight,
        behavior: 'smooth',
      });
    }, [data]);

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
        <LogsBox grow={1} shrink={1} ref={containerRef}>
            <pre>{data}</pre>
        </LogsBox>
  );
};