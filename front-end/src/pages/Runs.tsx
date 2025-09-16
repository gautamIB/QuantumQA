import React, { useMemo, useState } from 'react';
import { Box, FlexContainer, H5, Input, Small, TableGrid, Icon, XSmall } from '@instabase.com/pollen';
import { RUN_STATUS, TRun } from '../constants';
import { RUNS } from '../data';
import styled from 'styled-components';

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

export const Runs: React.FC = () => {
  const [runs, setRuns] = useState<TRun[]>(RUNS);
  const [searchQuery, setSearchQuery] = useState('');

  const columns: any[] = [
    {
      id: 'name',
      header: 'Run name',
      accessorKey: 'name',
      sortingFn: 'text',
    },
    {
      id: 'testName',
      header: 'Test name',
      accessorKey: 'testName',
      sortingFn: 'text',
    },
    {
      id: 'testType',
      header: 'Test type',
      accessorKey: 'testType',
      sortingFn: 'text',
    },
    {
      id: 'status',
      header: 'Status',
      accessorKey: 'status',
      sortingFn: 'text',
      cell: (cell: any) => {
        if (cell.row.original.status === RUN_STATUS.COMPLETED) {
          return (
            <FlexContainer alignItems="center" gap={1}>
              <Icon icon="check-circle" color="#2AA764" size={14} />
              <XSmall color="#2AA764" weight="semibold">{cell.row.original.status}</XSmall>
            </FlexContainer>
          );
        }
        if (cell.row.original.status === RUN_STATUS.FAILED) {
          return (
            <FlexContainer alignItems="center" gap={1}>
              <Icon icon="x-circle" color="#D3123F" size={14} />
              <XSmall color="#D3123F" weight="semibold">{cell.row.original.status}</XSmall>
            </FlexContainer>
          );
        }
        if (cell.row.original.status === RUN_STATUS.IN_PROGRESS) {
          return (
            <FlexContainer alignItems="center" gap={1}>
              <Icon icon="in-progress" color="#5A52FA" size={14} />
              <XSmall color="#5A52FA" weight="semibold">{cell.row.original.status}</XSmall>
            </FlexContainer>
          );
        }
        return null;
      },
    },
    {
      id: 'breakdown',
      header: 'Break down',
      accessorKey: 'total',
      cell: (cell: any) => {
        if (cell.row.original.status === RUN_STATUS.COMPLETED) {
          if (cell.row.original.total === cell.row.original.success) {
            return (
              <FlexContainer alignItems="center" gap={1}>
                <SuccessChip>
                  {`ALL ${cell.row.original.success} PASS`}
                </SuccessChip>
                <XSmall>/ out of <XSmall weight="semibold">{cell.row.original.total}</XSmall></XSmall>
              </FlexContainer>
            );
          }
          if (cell.row.original.total === cell.row.original.failed) {
            return (
              <FlexContainer alignItems="center" gap={1}>
                <FailedChip>
                  {`ALL ${cell.row.original.failed} FAILED`}
                </FailedChip>
                <XSmall>/ out of <XSmall weight="semibold">{cell.row.original.total}</XSmall></XSmall>
              </FlexContainer>
            );
          }
          return (
            <FlexContainer alignItems="center" gap={1}>
              <SuccessChip>
                {`${cell.row.original.success} PASS`}
              </SuccessChip>
              <FailedChip>
                {`${cell.row.original.failed} FAILED`}
              </FailedChip>
              <XSmall>/ out of <XSmall weight="semibold">{cell.row.original.total}</XSmall></XSmall>
            </FlexContainer>
          );
        }
        return "-";
      },
    },
  ];

  const filteredRuns = useMemo(() => {
    if (!searchQuery) return runs;
    return runs.filter(run => 
      run.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      run.testName.toLowerCase().includes(searchQuery.toLowerCase())
    );
  }, [runs, searchQuery]);

  return (
    <Box width="100%" height="100vh" p={6}>
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
        <Small color="#666974">{runs.length} items</Small>
      </FlexContainer>
      <TableGrid
        rows={filteredRuns}
        columns={columns}
        emptyState="No runs found. Try adjusting your search criteria."
        borderlessColumns={true}
      />
    </Box>
  );
};
