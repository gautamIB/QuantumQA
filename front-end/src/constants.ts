export enum ROUTES {
    TESTS = '/tests',
    RUNS = '/runs',
    CREATE = '/create',
};

export enum API_KEYS {
    TEST_CONFIGURATIONS = 'test-configurations',
    RUNS = 'test-runs',
    RUN = 'test-run',
    REPORT = 'report',
    LOGS = 'logs',
};

export enum API_ENDPOINTS {
    GET_TEST_CONFIGURATIONS = '/test-configurations',
    CREATE_TEST_CONFIGURATION = '/test-configurations',
    GET_RUNS = '/runs',
    GET_RUN_REPORT = '/report',
    GET_RUN_LOGS = '/logs',
    CREATE_RUN = '/runs',
};

export enum TEST_OPTIONS {
    TEST_MO = 'TESTMO',
    END_TO_END_TEST = 'UI',
    API_TEST = 'API',
};

export enum RUN_STATUS {
    IN_PROGRESS = 'PROCESSING',
    COMPLETED = 'COMPLETED',
    FAILED = 'FAILED',
};

export enum STEP_STATUS {
    SUCCESS = 'COMPLETED',
    FAILED = 'FAILED',
    IN_PROGRESS = 'PROCESSING',
};

export enum FORM_LABELS {
    TEST_NAME = 'testName',
    TEST_TYPE = 'testType',
    TEST_MO_URL = 'testMoUrl',
    STEPS = 'steps',
};

export enum TEST_KEYS {
    TEST_NAME = 'test_name',
    TEST_TYPE = 'test_type',
    FILE_PATH = 'file_path',
    CREATED_AT = 'created_at',
    MODIFIED_AT = 'modified_at',
    SIZE_BYTES = 'size_bytes',
    STATUS = 'status',
    TEST_MO_URL = 'test_mo_url',
    STEPS = 'instruction',
}

export enum RUN_KEYS {
    RUN_NAME = 'run_name',
    TEST_FILE = 'test_file',
    TEST_NAME = 'test_name',
    TEST_TYPE = 'test_type',
    STATUS = 'status',
    STARTED_AT = 'started_at',
    COMPLETED_AT = 'completed_at',
    DURATION_SECONDS = 'duration_seconds',
    SUCCESS_RATE = 'success_rate',
    LOG_FILE_URL = 'log_file_url',
    REPORT_FILE_URL = 'report_file_url',
    TOTAL_COUNT = 'steps_total',
    SUCCESS_COUNT = 'steps_passed',
    FAILED_COUNT = 'steps_failed',
}

export enum REPORT_KEYS {
    TOTAL_COUNT = 'steps_total',
    SUCCESS_COUNT = 'steps_passed',
    FAILED_COUNT = 'steps_failed',
    ERROR_SUMMARY = 'error_summary',
    STEPS = 'steps',
}

export enum STEP_KEYS {
    NAME = 'name',
    STATUS = 'status',
    ERROR_MESSAGE = 'error_message',
}

export interface TTest {
    [TEST_KEYS.TEST_NAME]: string;
    [TEST_KEYS.TEST_TYPE]: string;
    [TEST_KEYS.FILE_PATH]: string;
    [TEST_KEYS.CREATED_AT]: string;
    [TEST_KEYS.MODIFIED_AT]: string;
    [TEST_KEYS.SIZE_BYTES]: number;
    [TEST_KEYS.STATUS]: string;
    [TEST_KEYS.TEST_MO_URL]?: string;
    [TEST_KEYS.STEPS]?: string;
}

export interface TRun {
    [RUN_KEYS.RUN_NAME]: string;
    [RUN_KEYS.TEST_FILE]: string;
    [RUN_KEYS.TEST_NAME]?: string;
    [RUN_KEYS.TEST_TYPE]: string;
    [RUN_KEYS.STATUS]: string;
    [RUN_KEYS.STARTED_AT]: string;
    [RUN_KEYS.COMPLETED_AT]: string;
    [RUN_KEYS.DURATION_SECONDS]?: number;
    [RUN_KEYS.SUCCESS_RATE]?: number;
    [RUN_KEYS.LOG_FILE_URL]?: string;
    [RUN_KEYS.REPORT_FILE_URL]?: string;
};

export interface TReport {
    [REPORT_KEYS.TOTAL_COUNT]: number;
    [REPORT_KEYS.SUCCESS_COUNT]: number;
    [REPORT_KEYS.FAILED_COUNT]: number;
    [REPORT_KEYS.ERROR_SUMMARY]: string;
    [REPORT_KEYS.STEPS]: TStep[];
}

export interface TStep {
    [STEP_KEYS.NAME]: string;
    [STEP_KEYS.STATUS]: string;
    [STEP_KEYS.ERROR_MESSAGE]?: string;
}