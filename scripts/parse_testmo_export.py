#!/usr/bin/env python3
"""
Testmo CSV Export Parser

This script parses a Testmo CSV export file and converts it to a JSON file
with all the runs and cases information.
"""

import csv
import json
import sys
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
import argparse


class TestmoExportParser:
    """Parser for Testmo CSV exports to convert them to structured JSON."""

    def __init__(self, input_file: str, output_file: str):
        """Initialize the parser with input and output file paths.
        
        Args:
            input_file: Path to the Testmo CSV export file
            output_file: Path where the JSON output will be saved
        """
        self.input_file = input_file
        self.output_file = output_file

    def parse(self) -> Dict[str, Any]:
        """Parse the CSV file and return structured data.
        
        Returns:
            Dict containing the structured data from the CSV file
        """
        print(f"📄 Parsing CSV file: {self.input_file}")

        # Initialize the data structure
        data = {"run": {}, "cases": []}

        # Read the CSV file
        with open(self.input_file, 'r', encoding='utf-8') as f:
            # Use csv.reader with semicolon delimiter and quote character
            reader = csv.reader(f, delimiter=';', quotechar='"')

            # Process header information (run metadata)
            for _ in range(20):  # Read first 20 rows to capture metadata
                try:
                    row = next(reader)
                    if len(row) >= 2:
                        key = row[0].strip('"')
                        value = row[1].strip('"')
                        if key == "Project ID":
                            data["run"]["project_id"] = int(value)
                        elif key == "Project":
                            data["run"]["project_name"] = value
                        elif key == "Run ID":
                            data["run"]["run_id"] = int(value)
                        elif key == "Run":
                            data["run"]["run_name"] = value
                        elif key == "Created at":
                            data["run"]["created_at"] = value
                        elif key == "Created by":
                            data["run"]["created_by"] = value
                        elif key == "Closed":
                            data["run"]["closed"] = (value.lower() == "yes")
                except StopIteration:
                    break

            # Skip until we find the test cases header row
            found_header = False
            header_row = None

            for row in reader:
                # Look for a row that contains "Case ID" to identify the header
                if any("Case ID" in cell for cell in row):
                    found_header = True
                    header_row = [cell.strip('"') for cell in row]
                    break

            if not found_header:
                print("❌ Could not find test cases header in CSV file")
                return data

            # Process test cases
            for row in reader:
                if not row or len(row) < len(header_row):
                    continue

                case = {}
                for i, header in enumerate(header_row):
                    if i < len(row):
                        case[header] = row[i].strip('"')

                # Extract steps from the custom steps field
                if "Custom Steps" in case:
                    steps_text = case.get("Custom Steps", "")
                    steps = self._extract_steps(steps_text)
                    case["steps"] = steps

                data["cases"].append(case)

        print(f"✅ Successfully parsed {len(data['cases'])} test cases")
        return data

    def _extract_steps(self, steps_text: str) -> List[str]:
        """Extract individual steps from the steps text.
        
        Args:
            steps_text: The text containing the test steps
            
        Returns:
            List of individual test steps
        """
        # Split by newlines and filter out empty lines
        steps = [
            step.strip() for step in steps_text.split("\n") if step.strip()
        ]
        return steps

    def save_json(self, data: Dict[str, Any]) -> None:
        """Save the structured data as a JSON file.
        
        Args:
            data: The structured data to save
        """
        print(f"💾 Saving JSON to: {self.output_file}")

        # Create directory if it doesn't exist
        output_path = Path(self.output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Save the JSON file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"✅ JSON file saved successfully")


def parse_testmo_export_to_json(input_file: str, output_file: str) -> None:
    """Parse a Testmo CSV export file and convert it to JSON.
    
    Args:
        input_file: Path to the Testmo CSV export file
        output_file: Path where the JSON output will be saved
    """
    parser = TestmoExportParser(input_file, output_file)
    data = parser.parse()
    parser.save_json(data)
    print(f"✅ Conversion completed: {input_file} → {output_file}")
