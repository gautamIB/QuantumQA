"""
Command Line Interface for QuantumQA.
"""
import os
import sys
import asyncio
from pathlib import Path
from typing import List, Optional

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.text import Text

from ..agents.orchestrator import OrchestratorAgent
from ..core.llm import VisionLLMClient
from ..core.browser import BrowserConfig
from ..core.models import TestStatus


console = Console()


def get_api_key() -> Optional[str]:
    """Get OpenAI API key from environment or user input."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        console.print("⚠️  No OpenAI API key found in environment.", style="yellow")
        console.print("Please set OPENAI_API_KEY environment variable or pass it directly.")
        api_key = click.prompt("Enter your OpenAI API key", hide_input=True)
    return api_key


def parse_instructions(instructions: str) -> List[str]:
    """Parse instructions from string or file."""
    # Check if it's a file path
    if os.path.isfile(instructions):
        with open(instructions, 'r') as f:
            content = f.read().strip()
            return [line.strip() for line in content.split('\n') if line.strip()]
    else:
        # Treat as direct instruction
        return [instructions.strip()]


@click.group()
@click.version_option(version="0.1.0", prog_name="QuantumQA")
def cli():
    """🤖 QuantumQA - Lightweight Agentic UI Testing Framework"""
    pass


@cli.command()
@click.argument('instructions', required=True)
@click.option('--browser', default='chromium', help='Browser type (chromium, firefox, webkit)')
@click.option('--headless/--no-headless', default=True, help='Run browser in headless mode')
@click.option('--timeout', default=30000, help='Timeout in milliseconds')
@click.option('--api-key', help='OpenAI API key (overrides environment variable)')
@click.option('--save-artifacts', is_flag=True, help='Save screenshots and logs')
@click.option('--debug', is_flag=True, help='Enable debug output')
def run(instructions: str, browser: str, headless: bool, timeout: int, 
        api_key: Optional[str], save_artifacts: bool, debug: bool):
    """Run a test with natural language instructions.
    
    INSTRUCTIONS can be either:
    - A direct instruction: "Navigate to google.com and search for Python"  
    - A file path: test_instructions.txt
    """
    
    # Get API key
    if not api_key:
        api_key = get_api_key()
        if not api_key:
            console.print("❌ No API key provided. Exiting.", style="red")
            sys.exit(1)
    
    # Parse instructions
    try:
        instruction_list = parse_instructions(instructions)
    except Exception as e:
        console.print(f"❌ Error reading instructions: {e}", style="red")
        sys.exit(1)
    
    if not instruction_list:
        console.print("❌ No instructions found.", style="red")
        sys.exit(1)
    
    # Display test plan
    console.print("\n🤖 QuantumQA Test Execution", style="bold blue")
    console.print(Panel(
        "\n".join([f"{i+1}. {inst}" for i, inst in enumerate(instruction_list)]),
        title="📋 Test Instructions",
        border_style="blue"
    ))
    
    # Configure browser
    browser_config = BrowserConfig(
        browser_type=browser,
        headless=headless,
        timeout=timeout
    )
    
    if debug:
        console.print(f"🔧 Browser: {browser} (headless={headless})")
        console.print(f"🔧 Timeout: {timeout}ms")
    
    # Run the test
    try:
        result = asyncio.run(_run_test_async(instruction_list, api_key, browser_config, debug))
        
        # Display results
        _display_results(result, save_artifacts)
        
        # Exit with appropriate code
        sys.exit(0 if result.status == TestStatus.COMPLETED else 1)
        
    except KeyboardInterrupt:
        console.print("\n⚠️  Test interrupted by user.", style="yellow")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n❌ Unexpected error: {e}", style="red")
        if debug:
            import traceback
            console.print(traceback.format_exc(), style="dim")
        sys.exit(1)


async def _run_test_async(
    instructions: List[str], 
    api_key: str, 
    browser_config: BrowserConfig,
    debug: bool
) -> 'TestResult':
    """Run test asynchronously."""
    
    # Initialize components
    llm_client = VisionLLMClient(api_key=api_key)
    orchestrator = OrchestratorAgent(llm_client, browser_config)
    
    # Run test with progress indicator
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("🚀 Executing test...", total=None)
        
        result = await orchestrator.execute_test(instructions)
        
        progress.update(task, completed=True)
    
    return result


def _display_results(result: 'TestResult', save_artifacts: bool):
    """Display test results in a nice format."""
    
    # Status emoji and color
    if result.status == TestStatus.COMPLETED:
        status_emoji = "✅"
        status_color = "green"
    elif result.status == TestStatus.FAILED:
        status_emoji = "❌"  
        status_color = "red"
    else:
        status_emoji = "❓"
        status_color = "yellow"
    
    # Main result panel
    console.print(f"\n{status_emoji} Test {result.status.value.upper()}", style=f"bold {status_color}")
    
    # Summary stats
    passed_steps = len([s for s in result.steps if s.status.value == "completed"])
    total_steps = len(result.steps)
    
    summary_text = Text()
    summary_text.append(f"Steps: {passed_steps}/{total_steps} passed\n")
    summary_text.append(f"Duration: {result.execution_time:.1f}s\n")
    summary_text.append(f"Estimated Cost: ${result.cost_estimate:.3f}")
    
    console.print(Panel(summary_text, title="📊 Results", border_style="blue"))
    
    # Detailed step results
    if result.steps:
        console.print("\n📝 Step Details:", style="bold")
        for step in result.steps:
            step_emoji = "✅" if step.status.value == "completed" else "❌"
            console.print(f"  {step_emoji} Step {step.step_number}: {step.instruction}")
            
            if step.error_message and step.status.value == "failed":
                console.print(f"     💥 Error: {step.error_message}", style="red dim")
    
    # Artifacts info
    if save_artifacts:
        console.print(f"\n📁 Artifacts would be saved to: ./quantumqa_artifacts/{result.test_id}/")


@cli.command()
@click.argument('instructions')
def validate(instructions: str):
    """Validate test instructions without executing them."""
    try:
        instruction_list = parse_instructions(instructions)
        
        console.print("✅ Instructions are valid!", style="green")
        console.print(Panel(
            "\n".join([f"{i+1}. {inst}" for i, inst in enumerate(instruction_list)]),
            title="📋 Parsed Instructions",
            border_style="green"
        ))
        
        console.print(f"\n📊 Found {len(instruction_list)} instruction(s) to execute.")
        
    except Exception as e:
        console.print(f"❌ Invalid instructions: {e}", style="red")
        sys.exit(1)


@cli.command()
def examples():
    """Show example test instructions."""
    
    examples_text = """
1. Simple Navigation Test:
   Navigate to https://google.com
   Verify Google search page loads

2. Login Flow Test:
   Navigate to https://example.com/login
   Click the email input field
   Enter 'test@example.com' in the email field
   Click the password field
   Enter 'password123' in the password field
   Click the login button
   Verify dashboard page appears

3. Search Test:
   Navigate to https://wikipedia.org
   Click the search box
   Type 'Python programming language'
   Press Enter
   Verify Python article page loads

4. Form Test:
   Navigate to https://httpbin.org/forms/post
   Enter 'John Doe' in the customer name field
   Enter 'john@example.com' in the email field
   Click submit button
   Verify form submission success
"""
    
    console.print(Panel(examples_text, title="🌟 Example Tests", border_style="cyan"))
    
    console.print("\n💡 Tips:", style="bold yellow")
    console.print("• Be specific about elements: 'blue Login button' vs 'Login button'")
    console.print("• Use quotes for text input: Enter 'your text here'")  
    console.print("• Add verification steps to confirm actions worked")
    console.print("• Save instructions in .txt files for reuse")


def main():
    """Entry point for CLI."""
    cli()


if __name__ == "__main__":
    main()
