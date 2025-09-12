#!/usr/bin/env python3
"""
Custom Test Runner for QuantumQA
Run your own instruction files with the multi-agent system
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from quantumqa import QuantumQA

async def run_custom_test(instruction_file: str):
    """Run a custom test with instructions from a file."""
    
    print("🤖 QuantumQA Custom Test Runner")
    print("=" * 50)
    
    # Initialize QuantumQA
    qa = QuantumQA()
    
    # Load instructions from file
    instruction_path = Path(instruction_file)
    if not instruction_path.exists():
        print(f"❌ Error: Instruction file not found: {instruction_file}")
        return
    
    with open(instruction_path, 'r') as f:
        instructions = [line.strip() for line in f.readlines() if line.strip()]
    
    print(f"📝 Loaded {len(instructions)} instructions from: {instruction_file}")
    print("\n📋 Instructions Preview:")
    for i, instruction in enumerate(instructions[:5], 1):
        print(f"  {i}. {instruction}")
    if len(instructions) > 5:
        print(f"  ... and {len(instructions) - 5} more steps")
    
    print(f"\n🚀 Starting test execution...")
    print("-" * 50)
    
    try:
        # Run the test
        result = await qa.run_test(instructions)
        
        # Display results
        print("\n" + "=" * 50)
        print("📊 TEST RESULTS")
        print("=" * 50)
        
        print(f"🆔 Test ID: {result.test_id}")
        print(f"📊 Status: {result.status.value.upper()}")
        print(f"⏱️  Duration: {result.execution_time:.2f}s")
        print(f"📋 Total Steps: {len(result.steps)}")
        
        if result.steps:
            success_rate = len([s for s in result.steps if s.status.value == 'completed']) / len(result.steps) * 100
            print(f"✅ Success Rate: {success_rate:.1f}%")
            
            print(f"\n📋 Step Details:")
            for step in result.steps:
                status_emoji = "✅" if step.status.value == "completed" else "❌"
                print(f"  {status_emoji} Step {step.step_number}: {step.instruction}")
                if step.error_message:
                    print(f"    🔍 Error: {step.error_message}")
        else:
            print("⚠️  No steps were executed (workflow in development)")
        
        # Show summary
        print(f"\n{result.summary()}")
        
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python run_custom_test.py <instruction_file>")
        print("\nExamples:")
        print("  python run_custom_test.py examples/my_custom_test.txt")
        print("  python run_custom_test.py examples/simple_test.txt")
        print("  python run_custom_test.py examples/complex_search_workflow.txt")
        sys.exit(1)
    
    instruction_file = sys.argv[1]
    asyncio.run(run_custom_test(instruction_file))
