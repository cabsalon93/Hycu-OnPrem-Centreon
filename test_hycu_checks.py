#!/usr/bin/env python3
"""
HYCU Monitoring Plugin - Comprehensive Test Suite
Tests all 16 check types with customizable configuration
"""

import subprocess
import sys
import os
from datetime import datetime

# ANSI color codes
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    """Print formatted header"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text.center(70)}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.RESET}\n")

def print_test(number, total, name):
    """Print test information"""
    print(f"{Colors.BOLD}[{number}/{total}] {name}{Colors.RESET}")

def run_check(cmd, description):
    """Run a check command and return result"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        exit_code = result.returncode
        output = result.stdout.strip()
        
        # Determine status color
        if exit_code == 0:
            status_color = Colors.GREEN
            status = "OK"
        elif exit_code == 1:
            status_color = Colors.YELLOW
            status = "WARNING"
        elif exit_code == 2:
            status_color = Colors.RED
            status = "CRITICAL"
        else:
            status_color = Colors.RED
            status = "UNKNOWN"
        
        print(f"  {status_color}[{status}]{Colors.RESET} {output}")
        return exit_code == 0
        
    except subprocess.TimeoutExpired:
        print(f"  {Colors.RED}[TIMEOUT]{Colors.RESET} Check took too long")
        return False
    except Exception as e:
        print(f"  {Colors.RED}[ERROR]{Colors.RESET} {str(e)}")
        return False

def load_env():
    """Load configuration from .env file or environment variables"""
    config = {
        'HYCU_HOST': os.getenv('HYCU_HOST', ''),
        'HYCU_TOKEN': os.getenv('HYCU_TOKEN', ''),
        'SCRIPT_PATH': os.getenv('SCRIPT_PATH', './check_hycu_vm_backup_v2.1.py'),
        'VERBOSE': os.getenv('VERBOSE', 'false').lower() == 'true',
        'TIMEOUT': os.getenv('TIMEOUT', '100'),
        'TEST_VM_NAME': os.getenv('TEST_VM_NAME', ''),
        'TEST_TARGET_NAME': os.getenv('TEST_TARGET_NAME', ''),
        'TEST_POLICY_NAME': os.getenv('TEST_POLICY_NAME', ''),
        'JOBS_WARNING': os.getenv('JOBS_WARNING', '5'),
        'JOBS_CRITICAL': os.getenv('JOBS_CRITICAL', '10'),
        'JOBS_PERIOD': os.getenv('JOBS_PERIOD', '24'),
        'LICENSE_WARNING': os.getenv('LICENSE_WARNING', '30'),
        'LICENSE_CRITICAL': os.getenv('LICENSE_CRITICAL', '7'),
        'UNASSIGNED_WARNING': os.getenv('UNASSIGNED_WARNING', '5'),
        'UNASSIGNED_CRITICAL': os.getenv('UNASSIGNED_CRITICAL', '10'),
        'SHARES_WARNING': os.getenv('SHARES_WARNING', '3'),
        'SHARES_CRITICAL': os.getenv('SHARES_CRITICAL', '5'),
        'BUCKETS_WARNING': os.getenv('BUCKETS_WARNING', '2'),
        'BUCKETS_CRITICAL': os.getenv('BUCKETS_CRITICAL', '5'),
        'VALIDATION_WARNING': os.getenv('VALIDATION_WARNING', '5'),
        'VALIDATION_CRITICAL': os.getenv('VALIDATION_CRITICAL', '10'),
        'VALIDATION_PERIOD': os.getenv('VALIDATION_PERIOD', '24'),
        'POLICY_WARNING': os.getenv('POLICY_WARNING', '5'),
        'POLICY_CRITICAL': os.getenv('POLICY_CRITICAL', '10'),
    }
    
    # Try to load .env file if exists
    if os.path.exists('.env'):
        print(f"{Colors.BLUE}[INFO]{Colors.RESET} Loading configuration from .env file")
        with open('.env', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip()
    
    return config

def validate_config(config):
    """Validate required configuration"""
    errors = []
    
    if not config['HYCU_HOST']:
        errors.append("HYCU_HOST is not set")
    
    if not config['HYCU_TOKEN']:
        errors.append("HYCU_TOKEN is not set")
    
    if not os.path.exists(config['SCRIPT_PATH']):
        errors.append(f"Script not found: {config['SCRIPT_PATH']}")
    
    if errors:
        print(f"\n{Colors.RED}[ERROR] Configuration validation failed:{Colors.RESET}")
        for error in errors:
            print(f"  - {error}")
        print(f"\n{Colors.YELLOW}[TIP]{Colors.RESET} Copy env.template to .env and configure it:")
        print(f"  cp env.template .env")
        print(f"  nano .env")
        print(f"  source .env")
        return False
    
    return True

def main():
    """Main test suite execution"""
    
    print_header("HYCU Monitoring Plugin - Test Suite v2.1")
    print(f"Test started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Load configuration
    config = load_env()
    
    # Validate configuration
    if not validate_config(config):
        sys.exit(1)
    
    # Display configuration
    print(f"{Colors.BLUE}Configuration:{Colors.RESET}")
    print(f"  HYCU Host: {config['HYCU_HOST']}")
    print(f"  Token: {'*' * 20}...{config['HYCU_TOKEN'][-10:]}")
    print(f"  Script: {config['SCRIPT_PATH']}")
    print(f"  Verbose: {config['VERBOSE']}")
    
    # Build base command
    base_cmd = f"python3 {config['SCRIPT_PATH']} -l {config['HYCU_HOST']} -T {config['TIMEOUT']}"
    if config['VERBOSE']:
        base_cmd += " -v"
    
    # Test results tracking
    results = {
        'passed': 0,
        'failed': 0,
        'skipped': 0,
        'total': 0
    }
    
    # Test categories
    tests = {
        'network': [
            {
                'name': 'Port Connectivity (8443)',
                'cmd': f"{base_cmd} -t port -n 8443",
                'required': True
            }
        ],
        'global': [
            {
                'name': 'Version Information',
                'cmd': f"{base_cmd} -a {config['HYCU_TOKEN']} -t version",
                'required': True
            },
            {
                'name': 'License Status',
                'cmd': f"{base_cmd} -a {config['HYCU_TOKEN']} -t license -w {config['LICENSE_WARNING']} -c {config['LICENSE_CRITICAL']}",
                'required': True
            },
            {
                'name': 'Jobs Statistics',
                'cmd': f"{base_cmd} -a {config['HYCU_TOKEN']} -t jobs -w {config['JOBS_WARNING']} -c {config['JOBS_CRITICAL']} -p {config['JOBS_PERIOD']}",
                'required': True
            },
            {
                'name': 'Manager Dashboard (Protected)',
                'cmd': f"{base_cmd} -a {config['HYCU_TOKEN']} -n protected -t manager",
                'required': False
            }
        ],
        'storage': [
            {
                'name': 'Shares Monitoring',
                'cmd': f"{base_cmd} -a {config['HYCU_TOKEN']} -t shares -w {config['SHARES_WARNING']} -c {config['SHARES_CRITICAL']}",
                'required': False
            },
            {
                'name': 'Buckets Monitoring',
                'cmd': f"{base_cmd} -a {config['HYCU_TOKEN']} -t buckets -w {config['BUCKETS_WARNING']} -c {config['BUCKETS_CRITICAL']}",
                'required': False
            }
        ],
        'validation': [
            {
                'name': 'Backup Validation',
                'cmd': f"{base_cmd} -a {config['HYCU_TOKEN']} -t backup-validation -w {config['VALIDATION_WARNING']} -c {config['VALIDATION_CRITICAL']} -p {config['VALIDATION_PERIOD']}",
                'required': False
            },
            {
                'name': 'Unassigned Objects',
                'cmd': f"{base_cmd} -a {config['HYCU_TOKEN']} -t unassigned -w {config['UNASSIGNED_WARNING']} -c {config['UNASSIGNED_CRITICAL']}",
                'required': True
            }
        ],
        'objects': [
            {
                'name': 'VM Backup Status',
                'cmd': f"{base_cmd} -a {config['HYCU_TOKEN']} -n \"{config['TEST_VM_NAME']}\" -t vm",
                'required': False,
                'skip_if': not config['TEST_VM_NAME']
            },
            {
                'name': 'Target Health',
                'cmd': f"{base_cmd} -a {config['HYCU_TOKEN']} -n \"{config['TEST_TARGET_NAME']}\" -t target",
                'required': False,
                'skip_if': not config['TEST_TARGET_NAME']
            }
        ],
        'policies': [
            {
                'name': 'Policy Compliance Advanced',
                'cmd': f"{base_cmd} -a {config['HYCU_TOKEN']} -n \"{config['TEST_POLICY_NAME']}\" -t policy-advanced -w {config['POLICY_WARNING']} -c {config['POLICY_CRITICAL']}",
                'required': False,
                'skip_if': not config['TEST_POLICY_NAME']
            }
        ]
    }
    
    # Run tests by category
    test_number = 1
    total_tests = sum(len(tests_list) for tests_list in tests.values())
    
    for category, category_tests in tests.items():
        print_header(f"Testing {category.upper()} Checks")
        
        for test in category_tests:
            results['total'] += 1
            print_test(test_number, total_tests, test['name'])
            
            # Check if test should be skipped
            if test.get('skip_if', False):
                print(f"  {Colors.YELLOW}[SKIPPED]{Colors.RESET} Required configuration not set")
                results['skipped'] += 1
                test_number += 1
                continue
            
            # Run the test
            if run_check(test['cmd'], test['name']):
                results['passed'] += 1
            else:
                results['failed'] += 1
                if test['required']:
                    print(f"  {Colors.RED}[CRITICAL]{Colors.RESET} This is a required test!")
            
            test_number += 1
            print()  # Blank line between tests
    
    # Print summary
    print_header("Test Summary")
    
    print(f"Total Tests:   {results['total']}")
    print(f"{Colors.GREEN}Passed:        {results['passed']}{Colors.RESET}")
    print(f"{Colors.RED}Failed:        {results['failed']}{Colors.RESET}")
    print(f"{Colors.YELLOW}Skipped:       {results['skipped']}{Colors.RESET}")
    
    # Calculate success rate
    executed = results['passed'] + results['failed']
    if executed > 0:
        success_rate = (results['passed'] / executed) * 100
        print(f"\nSuccess Rate:  {success_rate:.1f}%")
    
    print(f"\nTest completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Exit code
    if results['failed'] > 0:
        print(f"\n{Colors.RED}[FAIL]{Colors.RESET} Some tests failed. Review output above.")
        sys.exit(1)
    else:
        print(f"\n{Colors.GREEN}[SUCCESS]{Colors.RESET} All tests passed!")
        sys.exit(0)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}[INTERRUPTED]{Colors.RESET} Test suite interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n{Colors.RED}[ERROR]{Colors.RESET} Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
