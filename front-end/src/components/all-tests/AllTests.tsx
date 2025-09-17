import React, { useState, useMemo } from 'react';
import { TableGrid, Input, IconButton, XSmall, TTableGridRowAction, Box, H3, FlexContainer, Small } from '@instabase.com/pollen';
import styled from 'styled-components';
import { ROUTES, TEST_KEYS, TTest } from '../../constants';
import { useMatch, useNavigate } from 'react-router-dom';

const Container = styled(Box)`
  padding: 12px;
  background: white;
  min-height: 100vh;
  max-height: 100vh;
  overflow-y: auto;
  width: 350px;
  min-width: 350px;
  border-right: 1px solid #DEDEE2;
`;

export const AllTests: React.FC<{ tests: TTest[] }> = ({ tests }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const match = useMatch('/tests/:name');
  const testName = decodeURI(match?.params.name || tests[0][TEST_KEYS.TEST_NAME]);

  const [selectedTestName, setSelectedTestName] = useState<string>(testName);
  const navigate = useNavigate();

  const filteredTests = useMemo(() => {
    if (!searchQuery) return tests;
    return tests.filter(test => 
      test[TEST_KEYS.TEST_NAME].toLowerCase().includes(searchQuery.toLowerCase())
    );
  }, [tests, searchQuery]);

  const columns: any[] = [
    {
      id: TEST_KEYS.TEST_NAME,
      header: 'Test name',
      accessorKey: TEST_KEYS.TEST_NAME,
      size: 200,
      grow: 1,
      align: 'start',
      cell: (cell: any) => (
        <Small color="#1C1D20">
          {cell.row.original[TEST_KEYS.TEST_NAME]}
        </Small>
      ),
    },
    {
      id: TEST_KEYS.TEST_TYPE,
      header: 'Type',
      accessorKey: TEST_KEYS.TEST_TYPE,
      size: 100,
      grow: 0,
      align: 'end',
      cell: (cell: any) => (
            <XSmall color="#666974">
            {cell.row.original[TEST_KEYS.TEST_TYPE]}
            </XSmall>
      ),
    }
  ];

  const rowButtonAction: TTableGridRowAction<TTest, 'button'> = (r) => ({
    as: 'button',
    label: `Action for ${r.original[TEST_KEYS.TEST_NAME]}`,
    onClick: () => {
        setSelectedTestName(r.original[TEST_KEYS.TEST_NAME]);
        navigate(`${ROUTES.TESTS}/${encodeURIComponent(r.original[TEST_KEYS.TEST_NAME])}`);
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
        <Small color="#666974">{`${filteredTests.length} test${filteredTests.length > 1 ? 's' : ''}`}</Small>
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
        getRowHighlighted={(row: any) => selectedTestName === row.original[TEST_KEYS.TEST_NAME]}
        emptyState="No tests found. Try adjusting your search criteria."
        borderlessColumns={true}
        style={{
          border: 'none',
        }}
      />
    </Container>
  );
};
