import React, { useState, useMemo } from 'react';
import { TableGrid, Input, IconButton, XSmall, TTableGridRowAction, Box, H3, FlexContainer, Small } from '@instabase.com/pollen';
import styled from 'styled-components';
import { ROUTES, TTest } from '../../constants';
import { useMatch, useNavigate } from 'react-router-dom';

const Container = styled(Box)`
  padding: 12px;
  background: white;
  min-height: 100vh;
  width: 350px;
  border-right: 1px solid #DEDEE2;
`;

export const AllTests: React.FC<{ tests: TTest[] }> = ({ tests }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const match = useMatch('/tests/:id');
  const testId = match?.params.id || tests[0].id;

  const [selectedRowId, setSelectedRowId] = useState<string>(testId);
  const navigate = useNavigate();

  const filteredTests = useMemo(() => {
    if (!searchQuery) return tests;
    return tests.filter(test => 
      test.name.toLowerCase().includes(searchQuery.toLowerCase())
    );
  }, [tests, searchQuery]);

  const columns: any[] = [
    {
      id: 'name',
      header: 'Test name',
      accessorKey: 'name',
      size: 200,
      grow: 1,
      align: 'start',
      cell: (cell: any) => (
        <Small color="#1C1D20">
          {cell.row.original.name}
        </Small>
      ),
    },
    {
      id: 'type',
      header: 'Type',
      accessorKey: 'type',
      size: 100,
      grow: 0,
      align: 'end',
      cell: (cell: any) => (
            <XSmall color="#666974">
            {cell.row.original.type}
            </XSmall>
      ),
    }
  ];

  const rowButtonAction: TTableGridRowAction<TTest, 'button'> = (r) => ({
    as: 'button',
    label: `Action for ${r.original.name}`,
    onClick: () => {
        setSelectedRowId(r.original.id);
        navigate(`${ROUTES.TESTS}/${r.original.id}`);
    },
  });

  const handleCreateTest = () => {
    navigate(ROUTES.CREATE);
  };

  return (
    <Container>
        <H3>Tests</H3>
        <FlexContainer alignItems="center" justify="space-between" mt={4} mb={4}>
        <IconButton icon="plus-circle" iconSize="medium" label="Create test" onClick={handleCreateTest}/>
        <Small color="#666974">{filteredTests.length} tests</Small>
        </FlexContainer>
          <Input
            label=""
            leftIcon="search"
            placeholder="Search"
            value={searchQuery}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSearchQuery(e.target.value)}
            fullWidth
            size="small"
            mb={4}
          />
      <TableGrid
        rows={filteredTests}
        columns={columns}
        hideHeaders={true}
        rowAction={rowButtonAction}
        getRowHighlighted={(row: any) => selectedRowId === row.original.id}
        emptyState="No tests found. Try adjusting your search criteria."
        borderlessColumns={true}
        style={{
          border: 'none',
        }}
      />
    </Container>
  );
};
