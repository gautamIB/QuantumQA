import React from 'react';
import { Box, FlexContainer, FlexItem, Small, ProgressBar, Icon, XSmall } from '@instabase.com/pollen';

export interface TestProgressProps {
  totalCount: number;
  successCount: number;
  errorCount: number;
}

export const TestProgress: React.FC<TestProgressProps> = ({
  totalCount = 0,
  successCount = 0,
  errorCount = 0,
}) => {
  const percentage = totalCount ? ((successCount + errorCount) / totalCount) * 100 : 0;
  return (
    <Box
      p={4}
      borderRadius="8px"
      maxWidth="400px"
      backgroundColor="#F3F3F3"
    >
      <FlexContainer justify="space-between" alignItems="center" mb={3}>
        <XSmall color="#1C1D20">
          Status: {successCount + errorCount}/{totalCount}
        </XSmall>
        <FlexContainer alignItems="center" gap={2}>
            <FlexContainer alignItems="center" gap={1}>
                <Icon icon="x-circle-filled" size={16} color="#B10A0A" />
                <Small color="#B10A0A">
                    {errorCount}
                </Small>
            </FlexContainer>
            <FlexContainer alignItems="center" gap={1}>
                <Icon icon="check-circle-filled" size={16} color="#1E803C" />
                <Small color="#1E803C">
                    {successCount}
                </Small>
            </FlexContainer>
        </FlexContainer>
      </FlexContainer>      
      <FlexContainer alignItems="center" gap={3}>
        <FlexItem grow={1}>
          <ProgressBar 
            value={percentage} 
            max={100}
            size="medium"
            labelPlacement="right"
          />
        </FlexItem>
      </FlexContainer>
    </Box>
  );
};
