export const ROUTES = {
    TESTS: '/tests',
    RUNS: '/runs',
    CREATE: '/create',
};

export enum TEST_OPTIONS {
    TEST_MO = 'Test mo',
    END_TO_END_TEST = 'End to end test',
    API_TEST = 'API Test',
};

export enum RUN_STATUS {
    IN_PROGRESS = 'In progress',
    COMPLETED = 'Completed',
    FAILED = 'Failed',
};

export interface TTest {
    id: string;
    name: string;
    type: string;
    folderUrl?: string;
    detailedSteps?: string;
}

export interface TRun {
    id: string;
    name: string;
    testName: string;
    testType: string;
    status: string;
    total?: number;
    success?: number;
    failed?: number;
}

export enum FORM_LABELS {
    TEST_NAME = 'testName',
    TEST_TYPE = 'testType',
    FOLDER_URL = 'folderUrl',
    DETAILED_STEPS = 'detailedSteps',
};