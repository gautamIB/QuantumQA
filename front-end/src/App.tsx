import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Sidebar from './components/side-bar/Sidebar';
import {
  FlexContainer,
  FlexItem,
  Box,
  GlobalInheritableThemeStyles,
  InstabaseBetaTheme,
  TInstabaseThemeIcons,
  Theme,
} from '@instabase.com/pollen';
import { Tests } from './pages/Tests';
import { Runs } from './pages/Runs';
import { CreateTest } from './pages/CreateTest';
import { ROUTES } from './constants';
import { Test } from './pages/Test';
import { Run } from './pages/Run';

// Declaration can be either at the root or in a separate .d.ts file
declare module '@instabase.com/pollen' {
  // eslint-disable-next-line @typescript-eslint/no-empty-interface
  export interface IIconTypes extends Record<TInstabaseThemeIcons, never> {}
}

const queryClient = new QueryClient()

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Theme theme={InstabaseBetaTheme}>
        <GlobalInheritableThemeStyles />
        <Router basename="/ui">
          <Box height="100vh" width="100vw" m={0} p={0}>
            <FlexContainer>
              <Sidebar />
              <FlexItem grow={1} shrink={1}>
                <Routes>
                  <Route path="/" element={<Navigate to={ROUTES.TESTS} replace />} />
                  <Route path={ROUTES.TESTS} element={<Tests />}>
                    <Route path=":name" element={<Test />} />
                  </Route>
                  <Route path={ROUTES.CREATE} element={<CreateTest />} />
                  <Route path={ROUTES.RUNS} element={<Runs />} />
                  <Route path={`${ROUTES.RUNS}/:name`} element={<Run />} />
                </Routes>
              </FlexItem>
            </FlexContainer>
          </Box>
        </Router>
      </Theme>
    </QueryClientProvider>
  );
}

export default App;
