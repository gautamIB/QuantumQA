# #!/usr/bin/env python3
# """
# Testmo Test Runner - Run Testmo test cases with QuantumQA

# This script reads a Testmo JSON export file, groups test cases by folder,
# and runs the tests in the specified folder using QuantumQA.
# """

# import asyncio
# import argparse
# import sys
# import os
# from pathlib import Path
# from typing import Optional, List

# # Add project root to path
# sys.path.insert(0, str(Path(__file__).parent.parent))

# from quantumqa.api.testmo_processor import TestmoProcessor


# async def main():
#     """Main entry point."""
#     parser = argparse.ArgumentParser(
#         description="Run Testmo test cases with QuantumQA",
#         formatter_class=argparse.RawDescriptionHelpFormatter,
#         epilog="""
# Examples:
#   # Run all tests in the 'Converse' folder
#   python run_testmo_tests.py testmo-cases.json --folder "Converse"
  
#   # Run tests in visible mode (non-headless)
#   python run_testmo_tests.py testmo-cases.json --folder "Converse" --visible
  
#   # Use a specific OpenAI API key
#   python run_testmo_tests.py testmo-cases.json --folder "Converse" --openai-key "your-api-key"
  
#   # Use a specific credentials file
#   python run_testmo_tests.py testmo-cases.json --folder "Converse" --credentials "/path/to/credentials.yaml"
#         """)

#     parser.add_argument('json_file',
#                         help='Path to the Testmo JSON export file')

#     parser.add_argument('--folder',
#                         required=True,
#                         help='Folder name to run tests from')

#     parser.add_argument(
#         '--visible',
#         action='store_true',
#         help='Run UI tests in visible mode (default: headless)')

#     parser.add_argument('--openai-key',
#                         help='OpenAI API key for instruction formatting')

#     parser.add_argument(
#         '--credentials',
#         '--creds',
#         help=
#         'Path to credentials file (default: quantumqa/config/credentials.yaml)'
#     )

#     parser.add_argument(
#         '--config',
#         help='Path to config directory (default: quantumqa/config/)')

#     parser.add_argument(
#         '--storage-state',
#         help='Path to save/load browser state (cookies, localStorage)')

#     parser.add_argument(
#         '--model',
#         default='gpt-3.5-turbo',
#         help=
#         'OpenAI model to use for instruction formatting (default: gpt-3.5-turbo)'
#     )

#     parser.add_argument('--list-folders',
#                         action='store_true',
#                         help='List available folders and exit')

#     args = parser.parse_args()

#     # Validate JSON file exists
#     if not Path(args.json_file).exists():
#         print(f"❌ Error: JSON file not found: {args.json_file}")
#         sys.exit(1)

#     # Auto-detect credentials file if not specified
#     if not args.credentials:
#         default_creds = Path("quantumqa/config/credentials.yaml")
#         if default_creds.exists():
#             args.credentials = str(default_creds)

#     # Use environment variable for OpenAI API key if not specified
#     openai_api_key = args.openai_key or os.environ.get("OPENAI_API_KEY")

#     # Initialize TestmoProcessor
#     processor = TestmoProcessor(openai_api_key=openai_api_key,
#                                 credentials_file=args.credentials,
#                                 config_dir=args.config,
#                                 storage_state_path=args.storage_state,
#                                 headless=not args.visible,
#                                 model=args.model)

#     # Read and parse Testmo JSON
#     test_cases = processor.read_testmo_json(args.json_file)
#     if not test_cases:
#         print("❌ No test cases found in the JSON file")
#         sys.exit(1)

#     # Group test cases by folder
#     grouped_test_cases = processor.group_by_folder(test_cases)

#     # If --list-folders flag is provided, just list the folders and exit
#     if args.list_folders:
#         print("\n📁 Available Folders:")
#         for folder, cases in grouped_test_cases.items():
#             print(f"  - {folder} ({len(cases)} test cases)")
#         sys.exit(0)

#     # Check if the specified folder exists
#     if args.folder not in grouped_test_cases:
#         print(f"❌ Error: Folder '{args.folder}' not found in the test cases")
#         print("\n📁 Available Folders:")
#         for folder in grouped_test_cases.keys():
#             print(f"  - {folder}")
#         sys.exit(1)

#     # Run tests in the specified folder
#     folder_test_cases = grouped_test_cases[args.folder]
#     results = await processor.run_folder_tests(args.folder, folder_test_cases)

#     # Calculate overall success rate
#     successful_tests = sum(1 for r in results
#                            if r.get('success_rate', 0) >= 80)
#     total_tests = len(results)
#     success_rate = (successful_tests / total_tests *
#                     100) if total_tests > 0 else 0

#     print("\n" + "=" * 50)
#     print(f"📊 Overall Results:")
#     print(
#         f"✅ Success Rate: {success_rate:.1f}% ({successful_tests}/{total_tests})"
#     )
#     print("=" * 50)

#     # Exit with appropriate code
#     sys.exit(0 if success_rate >= 80 else 1)


# def sync_main():
#     """Synchronous wrapper for main."""
#     try:
#         asyncio.run(main())
#     except KeyboardInterrupt:
#         print("\n⚠️ Test execution interrupted by user.")
#         sys.exit(1)
#     except Exception as e:
#         print(f"\n❌ Unexpected error: {e}")
#         import traceback
#         traceback.print_exc()
#         sys.exit(1)


# if __name__ == "__main__":
#     sync_main()
