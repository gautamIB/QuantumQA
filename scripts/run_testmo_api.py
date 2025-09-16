# #!/usr/bin/env python3
# """
# Testmo API Client Example

# Demonstrates how to use the Testmo API client to fetch projects, test runs, and test cases.
# """

# import sys
# import asyncio
# import argparse
# from pathlib import Path
# from typing import Optional, List
# import json

# # Add project root to path
# sys.path.insert(0, str(Path(__file__).parent.parent))

# from quantumqa.api.testmo_client import TestmoClient, TestmoClientOptions
# from quantumqa.api.testmo_client import TestmoProject, TestmoRun, TestmoCase, TestmoCaseDetail, TestmoStatus


# async def fetch_projects(client: TestmoClient) -> List[TestmoProject]:
#     """Fetch all projects from Testmo."""
#     print("📋 Fetching projects...")
#     projects = await client.get_projects()
#     print(f"✅ Found {len(projects)} projects")
#     return projects


# async def fetch_runs(client: TestmoClient, project_id: int) -> List[TestmoRun]:
#     """Fetch all test runs for a project."""
#     print(f"📋 Fetching runs for project {project_id}...")
#     runs = await client.get_runs(project_id)
#     print(f"✅ Found {len(runs)} runs")

#     # Sort runs by ID (oldest first)
#     if runs:
#         runs.sort(key=lambda run: run.id if run.id else 999999, reverse=True)
#         print(f"📅 Sorted runs by ID (oldest first)")

#     return runs


# async def fetch_cases(client: TestmoClient,
#                       project_id: int) -> List[TestmoCase]:
#     """Fetch all test cases for a project."""
#     print(f"📋 Fetching test cases for project {project_id}...")
#     cases = await client.get_cases(project_id)
#     print(f"✅ Found {len(cases)} test cases")
#     return cases


# async def fetch_case_details(client: TestmoClient,
#                              case_id: int) -> TestmoCaseDetail:
#     """Fetch detailed information for a test case."""
#     print(f"📋 Fetching details for test case {case_id}...")
#     case_details = await client.get_case(case_id)
#     print(f"✅ Retrieved test case details: {case_details.title}")
#     return case_details


# async def fetch_results(client: TestmoClient, run_id: int) -> List[dict]:
#     """Fetch all test results for a run."""
#     print(f"📋 Fetching results for run {run_id}...")
#     results = await client.get_results(run_id)
#     print(f"✅ Found {len(results)} test results")
#     return results


# async def fetch_run_details(client: TestmoClient, run_id: int) -> TestmoRun:
#     """Fetch detailed information for a specific run."""
#     print(f"📋 Fetching details for run {run_id}...")
#     run_details = await client.get_run(run_id)
#     print(f"✅ Retrieved run details: {run_details.name}")
#     return run_details


# async def main(args):
#     """Main entry point."""
#     # Create client options
#     options = TestmoClientOptions(base_url=args.base_url,
#                                   auth_credential=args.auth_credential,
#                                   timeout=args.timeout,
#                                   page_size=args.page_size)

#     # Create client
#     client = TestmoClient(options, args.credentials_file)

#     # Fetch projects
#     projects = await fetch_projects(client)

#     if not projects:
#         print("❌ No projects found")
#         return

#     # Select first project if not specified
#     project_id = args.project_id
#     for project in projects:
#         print(f"Projects: {project.name}")
#         if project.name and project.name.lower() == "ai hub":
#             project_id = project.id
#             print(f"ℹ️ Using AIHub project: {project}")
#             break
#         else:
#             print(f"❌ Skipping project: {project.name}")

#     # sys.exit(0)
#     # Fetch runs for project

#     if project_id is None:
#         print("❌ No project found")
#         return

#     runs = await fetch_runs(client, project_id)

#     if not runs:
#         print("❌ No runs found for this project")
#         return

#     # Get the latest run (first one after sorting)
#     latest_run = runs[0]
#     print(
#         f"\n🔍 Latest run: {latest_run.name} (ID: {latest_run.id}, Created: {latest_run.created_on})"
#     )

#     print(f"Latest run: {latest_run}")

#     # Fetch results for the latest run
#     results = await fetch_results(client, latest_run.id)
#     print(f"Results: {results}")
#     # Print summary of results
#     print(f"\n📊 Latest Run Results Summary:")
#     status_counts = {}
#     for result in results:
#         status_id = result.status_id
#         status_counts[status_id] = status_counts.get(status_id, 0) + 1

#     for status_id, count in status_counts.items():
#         print(
#             f"Status {status_id}: Status {TestmoStatus(status_id).name} {count} test(s)"
#         )

#     # sys.exit(0)

#     print("\n✅ Testmo API client example completed successfully")
#     # return

#     # Fetch test cases for project (skipped)
#     # cases = await fetch_cases(client, project_id)

#     # # Fetch details for first test case if available
#     # if cases:
#     #     case_id = cases[0].id
#     #     case_details = await fetch_case_details(client, case_id)

#     #     # Print detailed case information
#     #     print("\n📝 Test Case Details:")
#     #     print(f"Title: {case_details.title}")
#     #     print(f"ID: {case_details.id}")
#     #     if case_details.custom_steps:
#     #         print(f"Steps: {len(case_details.custom_steps)}")
#     #         for i, step in enumerate(case_details.custom_steps, 1):
#     #             print(f"  Step {i}: {step.get('content', 'No content')}")
#     #     if case_details.custom_expected:
#     #         print(f"Expected Result: {case_details.custom_expected}")

#     # Fetch results for first run if available
#     if runs:
#         run_id = runs[0].id
#         results = await fetch_results(client, run_id)

#         # Print summary of results
#         print(f"\n📊 Run Results Summary for {runs[0].name}:")
#         status_counts = {}
#         for result in results:
#             status_id = result.status_id
#             status_counts[status_id] = status_counts.get(status_id, 0) + 1

#         for status_id, count in status_counts.items():
#             print(f"Status {status_id}: {count} test(s)")

#     print("\n✅ Testmo API client example completed successfully")


# def create_parser() -> argparse.ArgumentParser:
#     """Create command line argument parser."""
#     parser = argparse.ArgumentParser(
#         description="Testmo API Client Example",
#         formatter_class=argparse.ArgumentDefaultsHelpFormatter)

#     parser.add_argument("--base-url",
#                         default="https://instabase.testmo.net",
#                         help="Testmo instance base URL")

#     parser.add_argument("--auth-credential",
#                         default="testmo-api.key",
#                         help="Credential reference in credentials.yaml")

#     parser.add_argument("--credentials-file",
#                         default=str(
#                             Path(__file__).parent.parent / "quantumqa" /
#                             "config" / "credentials.yaml"),
#                         help="Path to credentials.yaml file")

#     parser.add_argument("--project-id",
#                         type=int,
#                         help="Specific project ID to use")

#     parser.add_argument("--timeout",
#                         type=int,
#                         default=60,
#                         help="API request timeout in seconds")

#     parser.add_argument("--page-size",
#                         type=int,
#                         default=250,
#                         help="Number of items per page for paginated requests")

#     return parser


# if __name__ == "__main__":
#     parser = create_parser()
#     args = parser.parse_args()

#     try:
#         asyncio.run(main(args))
#     except KeyboardInterrupt:
#         print("\n❌ Operation cancelled by user")
#     except Exception as e:
#         print(f"\n❌ Error: {e}")
#         sys.exit(1)
