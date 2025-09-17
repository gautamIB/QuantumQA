import { TEST_OPTIONS, TTest, TRun, RUN_STATUS, TStep } from "./constants";

export const TESTS: TTest[] =
[
    {
        "test_name": "Test 7",
        "test_type": "UI",
        "file_path": "Test/UI/Test 7.txt",
        "created_at": "2025-09-17T14:32:10.499890",
        "modified_at": "2025-09-17T14:32:10.499890",
        "size_bytes": 6,
        "status": "warning"
    },
    {
        "test_name": "Test case 6",
        "test_type": "UI",
        "file_path": "Test/UI/Test case 6.txt",
        "created_at": "2025-09-17T14:30:15.125920",
        "modified_at": "2025-09-17T14:30:15.125920",
        "size_bytes": 13,
        "status": "warning"
    },
    {
        "test_name": "UI Test 5",
        "test_type": "UI",
        "file_path": "Test/UI/UI Test 5.txt",
        "created_at": "2025-09-17T14:28:47.796576",
        "modified_at": "2025-09-17T14:28:47.796576",
        "size_bytes": 6,
        "status": "warning"
    },
    {
        "test_name": "UI Test 4",
        "test_type": "UI",
        "file_path": "Test/UI/UI Test 4.txt",
        "created_at": "2025-09-17T14:26:34.042804",
        "modified_at": "2025-09-17T14:26:34.042804",
        "size_bytes": 6,
        "status": "warning"
    },
    {
        "test_name": "UI Test 3",
        "test_type": "UI",
        "file_path": "Test/UI/UI Test 3.txt",
        "created_at": "2025-09-17T14:23:54.448166",
        "modified_at": "2025-09-17T14:23:54.448166",
        "size_bytes": 11,
        "status": "warning"
    },
    {
        "test_name": "UI Test 2",
        "test_type": "UI",
        "file_path": "Test/UI/UI Test 2.txt",
        "created_at": "2025-09-17T14:18:28.611329",
        "modified_at": "2025-09-17T14:18:28.611329",
        "size_bytes": 17,
        "status": "warning"
    },
    {
        "test_name": "UI Test",
        "test_type": "UI",
        "file_path": "Test/UI/UI Test.txt",
        "created_at": "2025-09-17T14:17:04.623640",
        "modified_at": "2025-09-17T14:17:04.623640",
        "size_bytes": 9,
        "status": "warning"
    },
    {
        "test_name": "New Test",
        "test_type": "UI",
        "file_path": "Test/UI/New Test.txt",
        "created_at": "2025-09-17T13:18:08.360292",
        "modified_at": "2025-09-17T13:18:08.360292",
        "size_bytes": 12,
        "status": "warning"
    },
    {
        "test_name": "sample_ui_test",
        "test_type": "UI",
        "file_path": "Test/UI/sample_ui_test.txt",
        "created_at": "2025-09-17T10:24:40.041620",
        "modified_at": "2025-09-17T10:24:40.041620",
        "size_bytes": 98,
        "status": "valid"
    },
    {
        "test_name": "sample_api_test",
        "test_type": "API",
        "file_path": "Test/API/sample_api_test.yml",
        "created_at": "2025-09-17T10:24:40.041424",
        "modified_at": "2025-09-17T10:24:40.041424",
        "size_bytes": 350,
        "status": "valid"
    }
];

export const RUNS: TRun[] = [
    {
        "run_name": "login_test_run_1",
        "test_file": "Test/UI/sample_ui_test.txt",
        "test_type": "UI",
        "status": "FAILED",
        "started_at": "2025-09-17T10:18:31.497585",
        "completed_at": "2025-09-17T10:19:16.146288",
        "duration_seconds": 44.648703,
        "success_rate": 75.0,
        "log_file_url": "/runs/login_test_run_1/logs",
        "report_file_url": "/runs/login_test_run_1/report"
    },
    {
        "run_name": "test_with_stored_creds",
        "test_file": "Test/UI/sample_ui_test.txt",
        "test_type": "UI",
        "status": "FAILED",
        "started_at": "2025-09-17T10:02:46.857744",
        "completed_at": "2025-09-17T10:03:38.288011",
        "duration_seconds": 51.430267,
        "success_rate": 75.0,
        "log_file_url": "/runs/test_with_stored_creds/logs",
        "report_file_url": "/runs/test_with_stored_creds/report"
    }
];

export const RUN: TRun = {
    "run_name": "test_with_stored_creds",
    "test_file": "Test/UI/sample_ui_test.txt",
    "test_type": "UI",
    "status": "FAILED",
    "started_at": "2025-09-17T10:02:46.857744",
    "completed_at": "2025-09-17T10:03:38.288011",
    "duration_seconds": 51.430267,
    "success_rate": 75.0,
    "log_file_url": "/runs/test_with_stored_creds/logs",
    "report_file_url": "/runs/test_with_stored_creds/report"
}

export const STEPS: TStep[] = [{
    name: "Clicked on the create button",
    status: "COMPLETED",
  }, {
    name: "Clicked on something",
    status: "COMPLETED",
  }, {
    name: "Clicked on save",
    status: "PROCESSING",
  }, {
    name: "Some process which is described by the user which is long and time consuming",
    status: "FAILED",
    error_message: "Some thing happens, while clicking on the button it, kept loading for long time.",
}, {
    name: "Clicked on save",
    status: "PROCESSING",
  }];

// export const RUNS: TRun[] = [
//     { id: '1', name: 'Run name 1', testName: 'Test name 1', testType: TEST_OPTIONS.TEST_MO, status: RUN_STATUS.COMPLETED, total: 25, success: 23, failed: 2 },
//     { id: '2', name: 'Run name 2', testName: 'Test name 2', testType: TEST_OPTIONS.TEST_MO, status: RUN_STATUS.COMPLETED, total: 10, success: 5, failed: 5 },
//     { id: '3', name: 'Run name 3', testName: 'Test name 3', testType: TEST_OPTIONS.TEST_MO, status: RUN_STATUS.COMPLETED, total: 12, success: 0, failed: 12 },
//     { id: '4', name: 'Run name 4', testName: 'Test name 4', testType: TEST_OPTIONS.TEST_MO, status: RUN_STATUS.FAILED },
//     { id: '5', name: 'Run name 5', testName: 'Test name 5', testType: TEST_OPTIONS.TEST_MO, status: RUN_STATUS.COMPLETED, total: 15, success: 15, failed: 0 },
//     { id: '6', name: 'Run name 6', testName: 'Test name 6', testType: TEST_OPTIONS.TEST_MO, status: RUN_STATUS.IN_PROGRESS },
//     { id: '7', name: 'Run name 7', testName: 'Test name 7', testType: TEST_OPTIONS.TEST_MO, status: RUN_STATUS.IN_PROGRESS }
// ];