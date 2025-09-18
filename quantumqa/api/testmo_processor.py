#!/usr/bin/env python3
"""
Testmo Processor - Utility for processing Testmo test cases and running them with QuantumQA
"""

import json
import asyncio
import sys
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union
import openai
from dataclasses import dataclass, asdict
from collections import defaultdict
import tempfile

# Add project root to path to ensure imports work correctly
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from quantumqa_runner import run_ui_test


@dataclass
class TestmoTestCase:
    """Structured representation of a Testmo test case."""
    case_id: str
    test_id: str
    test_name: str
    folder: str
    status: str
    description: str = ""
    priority: str = "Normal"
    state: str = "Active"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TestmoTestCase':
        """Create a TestmoTestCase from a dictionary."""
        return cls(case_id=data.get("Case ID", ""),
                   test_id=data.get("Test ID", ""),
                   test_name=data.get("Test", ""),
                   folder=data.get("Folder", ""),
                   status=data.get("Status", ""),
                   description=data.get("Description", ""),
                   priority=data.get("Priority", "Normal"),
                   state=data.get("State", "Active"))

    def to_dict(self) -> Dict[str, Any]:
        """Convert TestmoTestCase to a dictionary for JSON serialization."""
        return {
            "Case ID": self.case_id,
            "Test ID": self.test_id,
            "Test": self.test_name,
            "Folder": self.folder,
            "Status": self.status,
            "Description": self.description,
            "Priority": self.priority,
            "State": self.state
        }


class TestmoProcessor:
    """Process Testmo test cases and run them with QuantumQA."""

    def __init__(self,
                 openai_api_key: Optional[str] = None,
                 credentials_file: Optional[str] = None,
                 config_dir: Optional[str] = None,
                 storage_state_path: Optional[str] = None,
                 headless: bool = False,
                 model: str = "gpt-3.5-turbo"):
        """
        Initialize the TestmoProcessor.
        
        Args:
            openai_api_key: OpenAI API key for instruction formatting
            credentials_file: Path to credentials file for QuantumQA
            config_dir: Path to config directory for QuantumQA
            storage_state_path: Path to storage state file for browser state
            headless: Whether to run tests in headless mode
            model: OpenAI model to use for instruction formatting
        """
        self.openai_api_key = openai_api_key or os.environ.get(
            "OPENAI_API_KEY")
        self.credentials_file = credentials_file
        self.config_dir = config_dir
        self.storage_state_path = storage_state_path
        self.headless = headless
        self.model = model

        # Initialize OpenAI client if API key is provided
        if self.openai_api_key:
            openai.api_key = self.openai_api_key
            self.client = openai.OpenAI(api_key=self.openai_api_key)
        else:
            self.client = None
            print(
                "⚠️ No OpenAI API key provided. LLM-based instruction formatting will not be available."
            )
            print(
                "   Set the OPENAI_API_KEY environment variable or provide it as a parameter."
            )

    def read_testmo_json(self, json_file_path: str) -> List[TestmoTestCase]:
        """
        Read and parse Testmo JSON export file.
        
        Args:
            json_file_path: Path to the JSON file
            
        Returns:
            List of TestmoTestCase objects
        """
        try:
            # Read JSON file
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            #Check if the json is an array
            # Extract test cases
            if isinstance(data, list):
                test_cases_data = data
            else:
                test_cases_data = data.get('cases', [])
            # Convert to TestmoTestCase objects
            test_cases = [
                TestmoTestCase.from_dict(tc) for tc in test_cases_data
            ]

            print(
                f"✅ Successfully read {len(test_cases)} test cases from {json_file_path}"
            )
            return test_cases

        except Exception as e:
            print(f"❌ Error reading Testmo JSON: {e}")
            return []

    def group_by_folder(
            self, test_cases: List[TestmoTestCase]
    ) -> Dict[str, List[TestmoTestCase]]:
        """
        Group test cases by folder.
        
        Args:
            test_cases: List of TestmoTestCase objects
            
        Returns:
            Dictionary mapping folder names to lists of test cases
        """
        grouped = defaultdict(list)

        for test_case in test_cases:
            grouped[test_case.folder].append(test_case)

        # Print summary
        print(f"\n📊 Test Cases by Folder:")
        for folder, cases in grouped.items():
            print(
                f"  📁 {folder}: {len(cases)} test cases, Active cases: {len([c for c in cases if c.state == 'Active'])}"
            )

        return dict(grouped)

    async def format_instructions_with_llm(
            self, test_case: Union[TestmoTestCase,
                                   List[TestmoTestCase]]) -> str:
        """
        Format test case into QuantumQA instructions using LLM.
        
        Args:
            test_case: TestmoTestCase object
            
        Returns:
            Formatted instructions as string
        """
        if not self.client:
            print("⚠️ Cannot format instructions: No OpenAI client available")
            # Return a basic instruction format as fallback
            return Exception("No OpenAI client available")

        try:
            # Prepare prompt for the LLM
            system_prompt = """
            You are an expert test automation engineer. Convert the given test case into step-by-step instructions 
            for the QuantumQA framework. Use the following action patterns in your instructions:
                        
            Action Patterns:
            1. Navigate: "Navigate to [URL]" or "Go to [URL]"
            2. Click: "Click on [element]" or "Click [element]"
            3. Type: "Type [text] in [field]"
            4. Verify: "Verify [condition]" or "Check [condition]"
            5. Wait: "Wait for [condition]" or "Wait [seconds] seconds"
            6. Run Function: "Run function [function_name] [arguments]"
            7. Upload: "Upload file from path: [path]" or "Upload file by path: [path]"
            8. Send: "Send message" or "Send button click"
            9. Select: "Select [option] from dropdown"
            10. Explore: "Explore [element]"
            11. Test: "Test [condition]"
            12. Confirm: "Confirm [condition]"
            13. Close: "Close [element]"
            14. Scroll: "Scroll to [position]"

            Prerequisites:
            1. Navigate to https://aihub.instabase.com/
            2. Verify that the AIHub homepage loads successfully.
            3. Login to AIHub homepage with {cred:aihub-prod.prod_username} and {cred:aihub-prod.prod_password} if not already logged in.
            4. Verify that the user is logged in successfully.
            4. After logging in, Click on Workspaces on the top menu bar.
            
            Prefix # in the txt before any comment or non-action or not an instruction item
            Each instruction should be clear, concise, and on its own line.
            Focus on creating executable steps that the automation framework can understand.
            Do not include any explanations or comments beyond the actual instructions.
            Convert the provided test cases by user into step-by-step instructions for the QuantumQA framework that can be chronologically executed in one flow.
            Break down each test case into smaller steps specifically defined pre and post steps to achieve the test case.
            """

            user_prompt = ""
            if isinstance(test_case, List):
                # print(f"List of Testcases: {test_case}")
                for tc in test_case:
                    user_prompt += f"""
                    Test Name: {tc.test_name}
                    Test ID: {tc.test_id}
                    Description: {tc.description if tc.description else ""}
                    """
            else:
                print(f"Testcase: {test_case}")
                user_prompt += f"""
                Test Name: {test_case.test_name}
                Test ID: {test_case.test_id}
                Description: {test_case.description if test_case.description else ""}
                """

            # print(f"🧠 Generating instructions for test cases: {test_case}")

            # Call the OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{
                    "role": "system",
                    "content": system_prompt
                }, {
                    "role": "user",
                    "content": user_prompt
                }],
                temperature=0.3,  # Lower temperature for more consistent outputs
                max_tokens=1000)

            # Extract and return the generated instructions
            instructions = response.choices[0].message.content.strip()

            # Add a header with test case information
            if isinstance(test_case, List):
                header = "#Merged Test Cases:\n"
                for tc in test_case:
                    # header += f"# Test: {tc.test_name}\n# ID: {tc.test_id}\n# Folder: {tc.folder}\n\n"
                    pass
            else:
                # header = f"# Test: {test_case.test_name}\n# ID: {test_case.test_id}\n# Folder: {test_case.folder}\n\n"
                pass
            formatted_instructions = header + instructions
            num_steps = len(instructions.split('\n'))
            print(f"✅ Generated instructions {num_steps} steps)")
            return formatted_instructions

        except Exception as e:
            print(f"❌ Error formatting instructions with LLM: {e}")
            # Return a basic instruction format as fallback
            # return f"# Test: {test_case.test_name}\n\n# Description: {test_case.description}\n"
            import traceback
            traceback.print_exc()
            # print(f"Testcases: {test_case}")
            return Exception("Error formatting instructions with LLM")

    async def run_test_case(
        self, test_case: Union[TestmoTestCase,
                               List[TestmoTestCase]]) -> Dict[str, Any]:
        """
        Run a single test case using QuantumQA.
        
        Args:
            test_case: TestmoTestCase object
            
        Returns:
            Dictionary with test results
        """
        try:
            # Format instructions using LLM
            instructions = await self.format_instructions_with_llm(test_case)

            # Create a temporary file with the instructions
            with tempfile.NamedTemporaryFile(mode='w',
                                             suffix='.txt',
                                             delete=False) as temp_file:
                temp_file_path = temp_file.name
                temp_file.write(instructions)

            local_instructions_path = f"/Users/jeminjain/ProjectsOnGit/QuantumQA/generated_instructions/Converse_combined_cases.txt"
            # save instructions to a file
            with open(local_instructions_path, "w") as f:
                f.write(instructions)

            print(f"\n🚀 Running test: {test_case}")
            print(
                f"📝 Instruction file: {temp_file_path}, Local instructions path: {local_instructions_path}"
            )
            print("=" * 50)

            # Run the test using QuantumQA
            report = await run_ui_test(
                instruction_file=local_instructions_path,
                headless=self.headless,
                credentials_file=self.credentials_file,
                config_dir=self.config_dir)
            # storage_state_path=self.storage_state_path)

            # report = await run_vision_test(
            #     instruction_file=temp_file_path,
            #     headless=self.headless,
            #     credentials_file=self.credentials_file,
            #     config_dir=self.config_dir,
            #     storage_state_path=self.storage_state_path)

            # Clean up the temporary file
            try:
                os.unlink(temp_file_path)
            except Exception:
                pass

            if report:
                # Add test case information to the report
                if not isinstance(test_case, List):
                    report["test_case"] = {
                        "id": test_case.test_id,
                        "name": test_case.test_name,
                        "folder": test_case.folder
                    }
                else:
                    report["test_case"] = {
                        "id": "Combined Cases",
                        "name": "Combined Cases",
                        "folder": "Combined Cases"
                    }
                    print(f"\n✅ Test completed: {test_case[0].test_name}")
                    print(
                        f"📊 Success Rate: {report['success_rate']:.1f}% ({report['successful_steps']}/{report['total_steps']})"
                    )
                    return report

            else:
                print(f"\n❌ Test failed: {test_case}")
                return {
                    "success_rate": 0,
                    "successful_steps": 0,
                    "total_steps": 0,
                    "test_case": {
                        "id": "Combined Cases",
                        "name": "Combined Cases",
                        "folder": "Combined Cases"
                    },
                    "error": "Test execution failed"
                }

        except Exception as e:
            print(f"\n❌ Error running test case: {e}")
            import traceback
            traceback.print_exc()

            return {
                "success_rate": 0,
                "successful_steps": 0,
                "total_steps": 0,
                "test_case": {
                    "id": "Combined Cases",
                    "name": "Combined Cases",
                    "folder": "Combined Cases"
                },
                "error": str(e)
            }

    async def run_folder_tests(
            self, folder_name: str,
            test_cases: List[TestmoTestCase]) -> List[Dict[str, Any]]:
        """
        Run all test cases in a folder one at a time.
        
        Args:
            folder_name: Name of the folder
            test_cases: List of TestmoTestCase objects in the folder
            
        Returns:
            List of test results
        """
        print(f"\n📁 Running tests in folder: {folder_name}")
        print(f"🧪 Total tests: {len(test_cases)}")
        print("=" * 50)

        results = []

        for i, test_case in enumerate(test_cases):
            print(f"\n📌 Test {i+1}/{len(test_cases)}: {test_case}")
            result = await self.run_test_case(test_case)
            results.append(result)

        # Print summary
        successful_tests = sum(1 for r in results
                               if r.get('success_rate', 0) >= 80)
        success_rate = (successful_tests / len(results) *
                        100) if results else 0

        print("\n" + "=" * 50)
        print(f"📊 Folder Results: {folder_name}")
        print(
            f"✅ Success Rate: {success_rate:.1f}% ({successful_tests}/{len(results)})"
        )
        print("=" * 50)

        return results

    async def process_json_file_for_folder(
            self, json_file_path: str,
            folder_name: str) -> List[Dict[str, Any]]:
        """
        Process a Testmo JSON file and run tests for a specific folder.
        
        Args:
            json_file_path: Path to the Testmo JSON file
            folder_name: Name of the folder to run tests for
            
        Returns:
            List of test results
        """
        # Read and parse Testmo JSON
        test_cases = self.read_testmo_json(json_file_path)
        if not test_cases:
            print("❌ No test cases found in the JSON file")
            return []

        # Group test cases by folder
        grouped_test_cases = self.group_by_folder(test_cases)

        # Check if the specified folder exists
        if folder_name not in grouped_test_cases:
            print(
                f"❌ Error: Folder '{folder_name}' not found in the test cases")
            print("\n📁 Available Folders:")
            for folder in grouped_test_cases.keys():
                print(f"  - {folder}")
            return []

        # Run tests in the specified folder
        folder_test_cases = grouped_test_cases[folder_name]

        # Save folder_test_cases to a file (convert to dict first for JSON serialization)
        # if folder_name == "Converse":
        #     test_cases_dict = [tc.to_dict() for tc in folder_test_cases]
        #     with open(
        #             f"/Users/jeminjain/ProjectsOnGit/QuantumQA/downloads/{folder_name.lower()}_test_cases.json",
        #             "w") as f:
        #         json.dump(test_cases_dict, f, indent=2)

        # remove all test cases with state not Active
        folder_test_cases = [
            tc for tc in folder_test_cases if tc.state == "Active"
        ]
        print(
            f"Running {len(folder_test_cases)} test cases in folder: {folder_name}"
        )
        # results = await self.run_folder_tests(folder_name, folder_test_cases)

        results = await self.combine_and_run_test_cases(folder_test_cases)

        return results

    async def combine_and_run_test_cases(
            self, test_cases: List[TestmoTestCase]) -> List[Dict[str, Any]]:
        """
        Combine test cases into a single test case and run it.
        """

        return await self.run_test_case(test_cases)


async def main():
    """Main entry point."""
    processor = TestmoProcessor()
    await processor.process_json_file_for_folder(
        # "/Users/jeminjain/ProjectsOnGit/QuantumQA/downloads/testmo-cases.json",
        "/Users/jeminjain/ProjectsOnGit/QuantumQA/downloads/converse_test_cases_subset.json",
        "Converse")


if __name__ == "__main__":
    asyncio.run(main())
