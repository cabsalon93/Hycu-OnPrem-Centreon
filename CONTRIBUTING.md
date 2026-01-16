# Contributing to HYCU Monitoring Plugin

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to the project.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Coding Guidelines](#coding-guidelines)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)

## Code of Conduct

Be respectful, inclusive, and professional. We're all here to improve HYCU monitoring together.

## Getting Started

### Prerequisites

- Python 3.7+
- Git
- Access to a HYCU test environment
- HYCU API token for testing

### Fork and Clone

```bash
# Fork the repository on GitHub, then:
git clone https://github.com/YOUR_USERNAME/hycu-monitoring-plugin.git
cd hycu-monitoring-plugin

# Add upstream remote
git remote add upstream https://github.com/ORIGINAL_OWNER/hycu-monitoring-plugin.git
```

## Development Setup

### 1. Create Test Environment

```bash
# Copy environment template
cp env.template .env

# Edit with your test HYCU credentials
nano .env

# Load environment
source .env
```

### 2. Install Development Tools (Optional)

```bash
# For linting and formatting
pip3 install pylint black

# For testing
pip3 install pytest
```

### 3. Test Current Version

```bash
# Run test suite
python3 test_hycu_checks.py

# Test manually
python3 check_hycu_vm_backup_v2.1.py -l $HYCU_HOST -a $HYCU_TOKEN -t version -v
```

## How to Contribute

### Types of Contributions

1. **Bug Fixes** - Fix issues in existing check types
2. **New Features** - Add new check types or capabilities
3. **Documentation** - Improve README, HOWTO, or code comments
4. **Testing** - Add test cases or improve test coverage
5. **Performance** - Optimize API calls or processing

### Reporting Bugs

**Before submitting:**
- Check if the issue already exists in GitHub Issues
- Test with verbose mode (`-v`) to gather debug info
- Verify it's not a configuration issue

**Bug Report Template:**
```markdown
**Describe the bug**
Clear description of what's wrong

**To Reproduce**
Steps to reproduce:
1. Run command: `python3 check_hycu_vm_backup_v2.1.py ...`
2. See error: ...

**Expected behavior**
What should happen

**Environment:**
- HYCU Version: 5.2.0
- Python Version: 3.9.7
- OS: CentOS 8

**Verbose Output:**
```
[paste verbose output here]
```

**Additional context**
Any other relevant information
```

### Suggesting Features

**Feature Request Template:**
```markdown
**Feature Description**
What new check type or feature you want

**Use Case**
Why this would be useful

**Proposed Implementation**
How it could work (API endpoints, parameters, output)

**Example Usage**
```bash
python3 check_hycu_vm_backup_v2.1.py -l HOST -a TOKEN -t new-type -n NAME
```

**Expected Output**
What the check should return
```

## Coding Guidelines

### Python Style

Follow PEP 8 with these specifics:

```python
# Use type hints
def check_something(host: str, token: str, timeout: int) -> Tuple[int, str]:
    """
    Clear docstring explaining function
    
    Args:
        host: HYCU host
        token: API token
        timeout: Request timeout
        
    Returns:
        Tuple of (exit_code, output_message)
    """
    pass

# Constants in UPPERCASE
EXIT_OK = 0
FIELD_NAME = 'vmName'

# Functions in snake_case
def check_vm_backup():
    pass

# Classes in PascalCase
class HycuAPIError(Exception):
    pass
```

### Code Structure for New Check Types

When adding a new check type, follow this template:

```python
def check_new_type(host: str, headers: dict, timeout: int,
                   warning_threshold: int = 5, 
                   critical_threshold: int = 10,
                   verbose: bool = False) -> Tuple[int, str]:
    """
    Check [description of what this monitors]
    
    Args:
        host: HYCU host
        headers: Request headers
        timeout: Request timeout
        warning_threshold: Warning threshold
        critical_threshold: Critical threshold
        verbose: Enable verbose output
        
    Returns:
        Tuple of (exit_code, output_message)
    """
    # 1. Build API URL
    url = f'https://{host}:8443/rest/v1.0/endpoint'
    
    # 2. Make API request
    try:
        data = api_request(url, headers, timeout, verbose)
    except Exception as e:
        return EXIT_CRITICAL, f"CRITICAL: API Error - {str(e)}"
    
    # 3. Process data
    stats = {
        'total': 0,
        'failed': 0
    }
    
    if 'entities' in data:
        for item in data['entities']:
            stats['total'] += 1
            if item.get('status') == 'FAILED':
                stats['failed'] += 1
    
    if verbose:
        print(f"DEBUG: Stats: {stats}")
    
    # 4. Determine exit code
    if stats['failed'] >= critical_threshold:
        exit_code = EXIT_CRITICAL
        status_label = "CRITICAL"
    elif stats['failed'] >= warning_threshold:
        exit_code = EXIT_WARNING
        status_label = "WARNING"
    else:
        exit_code = EXIT_OK
        status_label = "OK"
    
    # 5. Format output message
    message = f"{status_label}: {stats['failed']}/{stats['total']} failed"
    
    # 6. Add performance data
    perfdata = f"|failed={stats['failed']};{warning_threshold};{critical_threshold};0;{stats['total']} total={stats['total']};;;0;"
    
    return exit_code, message + " " + perfdata
```

### Adding to Main Routing

```python
# In parse_arguments(), add to valid types
valid_types = [..., 'new-type']

# In main(), add routing
elif options.scantype == 'new-type':
    exit_code, output = check_new_type(
        options.host, headers, options.timeout,
        options.warning_threshold,
        options.critical_threshold,
        options.verbose
    )
```

### Documentation Requirements

Every new check type needs:

1. **Docstring** in the function
2. **README.md** section with usage example
3. **HOWTO.md** integration guide
4. **CHANGELOG.md** entry
5. **Test case** in test_hycu_checks.py

## Testing

### Manual Testing

```bash
# Test new check type
python3 check_hycu_vm_backup_v2.1.py -l $HYCU_HOST -a $HYCU_TOKEN -t new-type -v

# Test with thresholds
python3 check_hycu_vm_backup_v2.1.py -l $HYCU_HOST -a $HYCU_TOKEN -t new-type -w 5 -c 10

# Test error handling (wrong host)
python3 check_hycu_vm_backup_v2.1.py -l invalid-host -a $HYCU_TOKEN -t new-type
```

### Automated Testing

Add test case to `test_hycu_checks.py`:

```python
{
    'name': 'New Type Check',
    'cmd': f"{base_cmd} -a {config['HYCU_TOKEN']} -t new-type -w 5 -c 10",
    'required': False
}
```

### Test Checklist

Before submitting PR:

- [ ] Runs without errors
- [ ] Returns proper exit codes (0/1/2/3)
- [ ] Performance data format is correct
- [ ] Verbose mode works
- [ ] Error handling tested
- [ ] Works with invalid inputs
- [ ] Documentation updated
- [ ] CHANGELOG.md updated

## Pull Request Process

### 1. Create Feature Branch

```bash
# Update your fork
git checkout main
git pull upstream main

# Create feature branch
git checkout -b feature/new-check-type
```

### 2. Make Changes

```bash
# Make your changes
nano check_hycu_vm_backup_v2.1.py

# Test thoroughly
python3 test_hycu_checks.py

# Commit with clear message
git add check_hycu_vm_backup_v2.1.py
git commit -m "Add new-type check for monitoring XYZ

- Implements new-type check using /rest/v1.0/endpoint
- Adds configurable thresholds
- Includes performance metrics
- Updates documentation"
```

### 3. Update Documentation

```bash
# Update README.md with usage example
# Update HOWTO.md with integration guide
# Update CHANGELOG.md with entry
# Update test suite

git add README.md HOWTO.md CHANGELOG.md test_hycu_checks.py
git commit -m "docs: Update documentation for new-type check"
```

### 4. Push and Create PR

```bash
# Push to your fork
git push origin feature/new-check-type

# Create Pull Request on GitHub
# Fill in the PR template with details
```

### PR Template

```markdown
## Description
Brief description of what this PR does

## Type of Change
- [ ] Bug fix
- [ ] New feature (new check type)
- [ ] Documentation update
- [ ] Performance improvement

## Testing Done
- Tested on HYCU version: 5.2.0
- Test commands run:
  ```bash
  python3 check_hycu_vm_backup_v2.1.py ...
  ```
- Test results: All passed

## Checklist
- [ ] Code follows project style
- [ ] Self-review done
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] Tests added/updated
- [ ] All tests pass

## Screenshots (if applicable)
```

### 5. Code Review

- Address reviewer feedback promptly
- Update PR based on comments
- Keep PR focused (one feature per PR)

### 6. Merge

Once approved, maintainers will merge your PR.

## Questions?

- Open a [GitHub Discussion](https://github.com/YOUR_USERNAME/hycu-monitoring-plugin/discussions)
- Check existing [Issues](https://github.com/YOUR_USERNAME/hycu-monitoring-plugin/issues)

---

**Thank you for contributing! 🎉**
