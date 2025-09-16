#!/usr/bin/env python3
"""
Start Chrome with Remote Debugging for QuantumQA

This script starts Chrome with remote debugging enabled, allowing QuantumQA
to connect to an existing browser instance for faster testing and preserved authentication.
"""

import subprocess
import sys
import os
import platform
import argparse
import time


def find_chrome_executable():
    """Find Chrome executable based on platform."""
    
    system = platform.system().lower()
    
    chrome_paths = {
        'darwin': [  # macOS
            '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
            '/Applications/Chrome.app/Contents/MacOS/Google Chrome'
        ],
        'linux': [
            '/usr/bin/google-chrome',
            '/usr/bin/google-chrome-stable',
            '/usr/bin/chromium-browser',
            '/usr/bin/chromium'
        ],
        'windows': [
            r'C:\Program Files\Google\Chrome\Application\chrome.exe',
            r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
            os.path.expanduser(r'~\AppData\Local\Google\Chrome\Application\chrome.exe')
        ]
    }
    
    paths = chrome_paths.get(system, [])
    
    for path in paths:
        if os.path.exists(path):
            return path
    
    # Try to find in PATH
    try:
        result = subprocess.run(['which', 'google-chrome'], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
    except:
        pass
    
    try:
        result = subprocess.run(['which', 'chrome'], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
    except:
        pass
    
    return None


def start_chrome_debug(debug_port=9222, user_data_dir=None, additional_args=None):
    """Start Chrome with remote debugging enabled."""
    
    chrome_path = find_chrome_executable()
    if not chrome_path:
        print("❌ Chrome executable not found!")
        print("Please install Google Chrome or provide the path manually.")
        return False
    
    print(f"🔍 Found Chrome at: {chrome_path}")
    
    # Default user data directory
    if not user_data_dir:
        user_data_dir = os.path.expanduser("~/QuantumQA_ChromeProfile")
    
    # Ensure user data directory exists
    os.makedirs(user_data_dir, exist_ok=True)
    
    # Chrome arguments for debugging
    chrome_args = [
        chrome_path,
        f"--remote-debugging-port={debug_port}",
        f"--user-data-dir={user_data_dir}",
        "--no-first-run",
        "--disable-default-apps",
        "--disable-popup-blocking",
        "--disable-translate",
        "--disable-background-timer-throttling",
        "--disable-renderer-backgrounding",
        "--disable-backgrounding-occluded-windows",
        "--disable-ipc-flooding-protection",
        "--disable-hang-monitor",
        "--disable-prompt-on-repost",
        "--disable-sync",
        "--enable-automation",
        "--password-store=basic",
        "--use-mock-keychain"
    ]
    
    # Add any additional arguments
    if additional_args:
        chrome_args.extend(additional_args)
    
    print(f"🚀 Starting Chrome with remote debugging on port {debug_port}")
    print(f"📁 Using profile directory: {user_data_dir}")
    print(f"🔗 Connect URL: http://localhost:{debug_port}")
    
    try:
        # Start Chrome process
        process = subprocess.Popen(chrome_args, 
                                 stdout=subprocess.DEVNULL, 
                                 stderr=subprocess.DEVNULL)
        
        # Give Chrome time to start
        time.sleep(3)
        
        # Check if process is still running
        if process.poll() is None:
            print("✅ Chrome started successfully!")
            print(f"🆔 Process ID: {process.pid}")
            print("\n📋 How to use:")
            print("  1. Chrome is now running with remote debugging enabled")
            print("  2. You can manually log into websites in this Chrome instance")
            print("  3. Run QuantumQA tests to connect to this browser:")
            print(f"     python run_vision_test.py examples/conversation_with_login.txt --visible")
            print("\n🛑 To stop Chrome, close the browser window or press Ctrl+C")
            
            try:
                # Wait for process to finish
                process.wait()
            except KeyboardInterrupt:
                print("\n🛑 Shutting down Chrome...")
                process.terminate()
                process.wait()
                print("✅ Chrome stopped")
                
            return True
        else:
            print("❌ Chrome failed to start")
            return False
            
    except Exception as e:
        print(f"❌ Error starting Chrome: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Start Chrome with Remote Debugging for QuantumQA",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start Chrome with default settings:
  python start_chrome_debug.py
  
  # Use custom port:
  python start_chrome_debug.py --port 9223
  
  # Use custom profile directory:
  python start_chrome_debug.py --profile ~/MyTestProfile
  
  # Add custom Chrome arguments:
  python start_chrome_debug.py --args "--incognito --start-maximized"
        """
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=9222,
        help="Remote debugging port (default: 9222)"
    )
    
    parser.add_argument(
        "--profile",
        help="Custom Chrome profile directory (default: ~/QuantumQA_ChromeProfile)"
    )
    
    parser.add_argument(
        "--args",
        help="Additional Chrome arguments (space-separated)"
    )
    
    args = parser.parse_args()
    
    additional_args = args.args.split() if args.args else None
    
    success = start_chrome_debug(
        debug_port=args.port,
        user_data_dir=args.profile,
        additional_args=additional_args
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
