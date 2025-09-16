#!/usr/bin/env python3
"""
Testmo Export Runner

A simplified script that extracts test instructions from Testmo CSV exports,
converts them to JSON, and can run the tests using QuantumQA.
"""

import sys
import os
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the parser function
from scripts.parse_testmo_export import parse_testmo_export_to_json


class TestmoExportRunner:
    """A simplified class for processing Testmo exports and running tests."""

    def __init__(self, csv_file: str, json_file: Optional[str] = None):
        """Initialize the runner with input and output file paths.
        
        Args:
            csv_file: Path to the Testmo CSV export file
            json_file: Path where the JSON output will be saved (optional)
        """
        self.csv_file = csv_file

        # If no JSON file path is provided, create one based on the CSV file path
        if json_file is None:
            csv_path = Path(csv_file)
            self.json_file = str(csv_path.parent / f"{csv_path.stem}.json")
        else:
            self.json_file = json_file

        # Ensure the JSON file directory exists
        Path(self.json_file).parent.mkdir(parents=True, exist_ok=True)

    def process(self) -> Dict[str, Any]:
        """Process the CSV file and return the structured data.
        
        Returns:
            Dict containing the structured data from the CSV file
        """
        print(f"🔄 Processing Testmo export: {self.csv_file}")

        # Parse the CSV file to JSON
        parse_testmo_export_to_json(self.csv_file, self.json_file)

        # Load the generated JSON file
        with open(self.json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        print(f"✅ Processed {len(data.get('cases', []))} test cases")
        return data

    def extract_instructions(self,
                             case_id: Optional[int] = None
                             ) -> List[Dict[str, Any]]:
        """Extract test instructions from the processed data.
        
        Args:
            case_id: Optional case ID to filter for a specific test case
            
        Returns:
            List of test cases with their instructions
        """
        # Process the CSV file if not already done
        data = self.process()

        # Extract test cases with their instructions
        test_cases = []

        for case in data.get('cases', []):
            # Skip if case_id is specified and doesn't match
            if case_id and case.get('Case ID') != str(case_id):
                continue

            # Extract case information
            test_case = {
                'id': case.get('Case ID'),
                'title': case.get('Title'),
                'folder': case.get('Section'),
                'priority': case.get('Priority'),
                'steps': case.get('steps', [])
            }

            test_cases.append(test_case)

        print(f"📋 Extracted instructions for {len(test_cases)} test cases")
        return test_cases

    def run_test(self, case_id: int) -> bool:
        """Run a specific test case.
        
        Args:
            case_id: The ID of the test case to run
            
        Returns:
            True if the test passed, False otherwise
        """
        # Extract instructions for the specified case
        test_cases = self.extract_instructions(case_id)

        if not test_cases:
            print(f"❌ Test case with ID {case_id} not found")
            return False

        test_case = test_cases[0]
        print(f"🧪 Running test: {test_case['title']} (ID: {test_case['id']})")

        # Create a temporary file with the test instructions
        temp_file = Path(f"temp_test_{case_id}.txt")
        with open(temp_file, 'w', encoding='utf-8') as f:
            for step in test_case['steps']:
                f.write(f"{step}\n")

        try:
            # Import the run_ui_test function here to avoid circular imports
            from quantumqa_runner import run_ui_test

            # Run the test
            result = run_ui_test(str(temp_file))

            # Clean up the temporary file
            temp_file.unlink()

            return result.get('success', False)
        except Exception as e:
            print(f"❌ Error running test: {e}")

            # Clean up the temporary file
            if temp_file.exists():
                temp_file.unlink()

            return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Process Testmo CSV exports and run tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process a Testmo CSV export file
  python testmo_export_runner.py /path/to/testmo-export.csv
  
  # Process and save to a specific JSON file
  python testmo_export_runner.py /path/to/testmo-export.csv --json /path/to/output.json
  
  # Run a specific test case
  python testmo_export_runner.py /path/to/testmo-export.csv --run 123
        """)

    parser.add_argument('csv_file', help='Path to the Testmo CSV export file')
    parser.add_argument('--json',
                        help='Path where the JSON output will be saved')
    parser.add_argument('--run',
                        type=int,
                        help='Run a specific test case by ID')

    args = parser.parse_args()

    # Validate input file exists
    if not Path(args.csv_file).exists():
        print(f"❌ Error: Input file not found: {args.csv_file}")
        sys.exit(1)

    # Create the runner
    runner = TestmoExportRunner(args.csv_file, args.json)

    # Run a specific test case if requested
    if args.run:
        success = runner.run_test(args.run)
        sys.exit(0 if success else 1)
    else:
        # Just process the file
        runner.process()
        sys.exit(0)


if __name__ == "__main__":
    main()
