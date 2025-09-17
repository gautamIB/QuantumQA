import React, { useMemo, useState } from 'react';
import { Box, FlexContainer, H5, Input, Small, TableGrid, Icon, XSmall, Spinner, EmptyState, Link } from '@instabase.com/pollen';
import { RUN_KEYS, RUN_STATUS, TRun, TEST_OPTIONS, ROUTES } from '../constants';
import styled from 'styled-components';
import { useRuns } from '../api/useRuns';
import { GenericError } from '@instabase.com/pollen/illustration';
import { TEST_OPTIONS_LABEL_MAP } from '../components/test-form/TestForm';
import { useNavigate } from 'react-router-dom';

const SuccessChip = styled(Box)`
  background-color: #E9F5DA;
  color: #104719;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
`;

const FailedChip = styled(Box)`
  background-color: #FFF0F0;
  color: #8D0404;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
`;

const StyledFlexContainer = styled(FlexContainer)`
  height: 100vh;
`;

const Container = styled(Box)`
  min-height: 100vh;
  max-height: 100vh;
  overflow-y: auto;
`;

export const Runs: React.FC = () => {
  const { data, isLoading, error } = useRuns();
  const [searchQuery, setSearchQuery] = useState('');
  const navigate = useNavigate();

  const filteredRuns = useMemo(() => {
    if (!searchQuery) return data?.runs || [];
    return data?.runs?.filter((run: TRun) => 
      run[RUN_KEYS.RUN_NAME]?.toLowerCase()?.includes(searchQuery.toLowerCase()) ||
      run[RUN_KEYS.TEST_NAME]?.toLowerCase()?.includes(searchQuery.toLowerCase())
    ) || [];
  }, [data?.runs, searchQuery]);

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

  const columns: any[] = [
    {
      id: RUN_KEYS.RUN_NAME,
      header: 'Run name',
      accessorKey: RUN_KEYS.RUN_NAME,
      sortingFn: 'text',
      cell: (cell: any) => (
        <Link
          as="button"
          intent="primary"
          label={cell.row.original[RUN_KEYS.RUN_NAME]}
          onClick={() => {
            navigate(`${ROUTES.RUNS}/${cell.row.original[RUN_KEYS.RUN_NAME]}`);
          }}
        />
      ),
    },
    {
      id: RUN_KEYS.TEST_NAME,
      header: 'Test name',
      accessorKey: RUN_KEYS.TEST_NAME,
      sortingFn: 'text',
    },
    {
      id: RUN_KEYS.TEST_TYPE,
      header: 'Test type',
      accessorKey: RUN_KEYS.TEST_TYPE,
      sortingFn: 'text',
      cell: (cell: any) => TEST_OPTIONS_LABEL_MAP[cell.row.original[RUN_KEYS.TEST_TYPE] as TEST_OPTIONS],
    },
    {
      id: RUN_KEYS.STATUS,
      header: 'Status',
      accessorKey: RUN_KEYS.STATUS,
      sortingFn: 'text',
      cell: (cell: any) => {
        if (cell.row.original[RUN_KEYS.STATUS] === RUN_STATUS.COMPLETED) {
          return (
            <FlexContainer alignItems="center" gap={1}>
              <Icon icon="check-circle" color="#2AA764" size={14} />
              <XSmall color="#2AA764" weight="semibold">{cell.row.original[RUN_KEYS.STATUS]}</XSmall>
            </FlexContainer>
          );
        }
        if (cell.row.original[RUN_KEYS.STATUS] === RUN_STATUS.FAILED) {
          return (
            <FlexContainer alignItems="center" gap={1}>
              <Icon icon="x-circle" color="#D3123F" size={14} />
              <XSmall color="#D3123F" weight="semibold">{cell.row.original[RUN_KEYS.STATUS]}</XSmall>
            </FlexContainer>
          );
        }
        if (cell.row.original[RUN_KEYS.STATUS] === RUN_STATUS.IN_PROGRESS) {
          return (
            <FlexContainer alignItems="center" gap={1}>
              <Icon icon="in-progress" color="#5A52FA" size={14} />
              <XSmall color="#5A52FA" weight="semibold">{cell.row.original[RUN_KEYS.STATUS]}</XSmall>
            </FlexContainer>
          );
        }
        return null;
      },
    },
    {
      id: RUN_KEYS.SUCCESS_RATE,
      header: 'Break down',
      accessorKey: RUN_KEYS.SUCCESS_RATE,
      cell: (cell: any) => {
        if (cell.row.original[RUN_KEYS.STATUS] === RUN_STATUS.COMPLETED) {
          if (cell.row.original[RUN_KEYS.SUCCESS_COUNT] === cell.row.original[RUN_KEYS.TOTAL_COUNT]) {
            return (
              <FlexContainer alignItems="center" gap={1}>
                <SuccessChip>
                  {`ALL ${cell.row.original[RUN_KEYS.SUCCESS_COUNT]} PASS`}
                </SuccessChip>
                <XSmall>/ out of <XSmall weight="semibold">{cell.row.original[RUN_KEYS.TOTAL_COUNT]}</XSmall></XSmall>
              </FlexContainer>
            );
          }
          if (cell.row.original[RUN_KEYS.SUCCESS_COUNT] === cell.row.original[RUN_KEYS.TOTAL_COUNT]) {
            return (
              <FlexContainer alignItems="center" gap={1}>
                <FailedChip>
                  {`ALL ${cell.row.original[RUN_KEYS.FAILED_COUNT]} FAILED`}
                </FailedChip>
                <XSmall>/ out of <XSmall weight="semibold">{cell.row.original[RUN_KEYS.TOTAL_COUNT]}</XSmall></XSmall>
              </FlexContainer>
            );
          }
          return (
            <FlexContainer alignItems="center" gap={1}>
              <SuccessChip>
                {`${cell.row.original[RUN_KEYS.SUCCESS_COUNT]} PASS`}
              </SuccessChip>
              <FailedChip>
                {`${cell.row.original[RUN_KEYS.FAILED_COUNT]} FAILED`}
              </FailedChip>
              <XSmall>/ out of <XSmall weight="semibold">{cell.row.original[RUN_KEYS.TOTAL_COUNT]}</XSmall></XSmall>
            </FlexContainer>
          );
        }
        return "-";
      },
    },
  ];

  return (
    <Container width="100%" p={6}>
      <H5>Run history</H5>
      <FlexContainer mt={4} mb={4} justify="space-between" alignItems="center">
        <Box width={350}>
          <Input
            label=""
            placeholder="Search"
            leftIcon="search"
            size="small"
            value={searchQuery}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSearchQuery(e.target.value)}
            fullWidth
          />
        </Box>
        <Small color="#666974">{`${filteredRuns.length} item${filteredRuns.length > 1 ? 's' : ''}`}</Small>
      </FlexContainer>
      <TableGrid
        rows={filteredRuns}
        columns={columns}
        emptyState={
          <EmptyState
            icon="search"
            title="No runs found"
            description="Try adjusting your search criteria"
            py={6}
          />
        }
        borderlessColumns={true}
      />
    </Container>
  );
};
