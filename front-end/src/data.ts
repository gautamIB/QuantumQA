import { TEST_OPTIONS, TTest, TRun, RUN_STATUS } from "./constants";

export const TESTS: TTest[] = [
    { id: '1', name: 'Test name 1', type: TEST_OPTIONS.TEST_MO },
    { id: '2', name: 'Test name 2', type: TEST_OPTIONS.TEST_MO },
    { id: '3', name: 'Test name 3', type: TEST_OPTIONS.TEST_MO },
    { id: '4', name: 'Test name 4', type: TEST_OPTIONS.TEST_MO },
    { id: '5', name: 'Test name 5', type: TEST_OPTIONS.TEST_MO },
    { id: '6', name: 'Test name 6', type: TEST_OPTIONS.TEST_MO },
    { id: '7', name: 'Test name 7', type: TEST_OPTIONS.TEST_MO }
];

export const RUNS: TRun[] = [
    { id: '1', name: 'Run name 1', testName: 'Test name 1', testType: TEST_OPTIONS.TEST_MO, status: RUN_STATUS.COMPLETED, total: 25, success: 23, failed: 2 },
    { id: '2', name: 'Run name 2', testName: 'Test name 2', testType: TEST_OPTIONS.TEST_MO, status: RUN_STATUS.COMPLETED, total: 10, success: 5, failed: 5 },
    { id: '3', name: 'Run name 3', testName: 'Test name 3', testType: TEST_OPTIONS.TEST_MO, status: RUN_STATUS.COMPLETED, total: 12, success: 0, failed: 12 },
    { id: '4', name: 'Run name 4', testName: 'Test name 4', testType: TEST_OPTIONS.TEST_MO, status: RUN_STATUS.FAILED },
    { id: '5', name: 'Run name 5', testName: 'Test name 5', testType: TEST_OPTIONS.TEST_MO, status: RUN_STATUS.COMPLETED, total: 15, success: 15, failed: 0 },
    { id: '6', name: 'Run name 6', testName: 'Test name 6', testType: TEST_OPTIONS.TEST_MO, status: RUN_STATUS.IN_PROGRESS },
    { id: '7', name: 'Run name 7', testName: 'Test name 7', testType: TEST_OPTIONS.TEST_MO, status: RUN_STATUS.IN_PROGRESS }
];