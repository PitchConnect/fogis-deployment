# Pre-commit Hooks Setup Guide

## Overview

This guide documents the setup and usage of pre-commit hooks in the FOGIS deployment repositories to ensure code quality and prevent CI/CD pipeline failures.

## What are Pre-commit Hooks?

Pre-commit hooks are scripts that run automatically before each commit to check code quality, formatting, and other standards. They help catch issues early in the development process, before code reaches the CI/CD pipeline.

## Benefits

- **Prevent CI/CD Failures**: Catch code quality issues before they reach the remote repository
- **Consistent Code Style**: Automatically format code according to project standards
- **Security Scanning**: Detect potential security vulnerabilities with bandit
- **Type Checking**: Catch type-related errors with mypy
- **Import Organization**: Automatically sort and organize imports with isort

## Repository Status

### ✅ Match List Processor (`match-list-processor/`)
- **Pre-commit Configuration**: `.pre-commit-config.yaml` ✓
- **Hooks Installed**: ✓ (as of 2025-09-23)
- **Status**: All hooks passing

### ✅ Calendar Service (`fogis-calendar-phonebook-sync/`)
- **Pre-commit Configuration**: `.pre-commit-config.yaml` ✓
- **Hooks Installed**: ✓ (as of 2025-09-23)
- **Status**: All hooks passing

## Installation Instructions

### Prerequisites
- Python 3.7+ installed
- Git repository initialized
- `pre-commit` package installed

### Step 1: Install pre-commit (if not already installed)
```bash
pip install pre-commit
```

### Step 2: Install hooks in each repository

#### For Match List Processor:
```bash
cd match-list-processor
pre-commit install
```

#### For Calendar Service:
```bash
cd fogis-calendar-phonebook-sync
pre-commit install
```

### Step 3: Verify installation
```bash
# Check that hooks are installed
ls -la .git/hooks/pre-commit

# Run hooks on all files to test
pre-commit run --all-files
```

## Configured Hooks

### Match List Processor Hooks
1. **trailing-whitespace**: Removes trailing whitespace
2. **end-of-file-fixer**: Ensures files end with a newline
3. **check-yaml**: Validates YAML syntax
4. **check-added-large-files**: Prevents committing large files
5. **check-merge-conflict**: Detects merge conflict markers
6. **debug-statements**: Detects debug statements (pdb, etc.)
7. **black**: Python code formatter
8. **isort**: Import sorter and organizer
9. **flake8**: Python linter (style and error checking)
10. **mypy**: Static type checker
11. **bandit**: Security vulnerability scanner

### Calendar Service Hooks
1. **trailing-whitespace**: Removes trailing whitespace
2. **end-of-file-fixer**: Ensures files end with a newline
3. **check-yaml**: Validates YAML syntax
4. **check-json**: Validates JSON syntax
5. **check-added-large-files**: Prevents committing large files
6. **isort**: Import sorter and organizer
7. **black**: Python code formatter
8. **flake8**: Python linter (style and error checking)
9. **bandit**: Security vulnerability scanner
10. **pytest**: Runs tests to ensure functionality

## Usage

### Automatic Execution
Pre-commit hooks run automatically when you commit:
```bash
git add .
git commit -m "Your commit message"
# Hooks will run automatically before the commit
```

### Manual Execution
You can run hooks manually:
```bash
# Run all hooks on all files
pre-commit run --all-files

# Run all hooks on staged files only
pre-commit run

# Run a specific hook
pre-commit run black
pre-commit run flake8
```

### Bypassing Hooks (Not Recommended)
In emergency situations, you can bypass hooks:
```bash
git commit --no-verify -m "Emergency commit"
```
**⚠️ Warning**: Only use this in genuine emergencies as it defeats the purpose of quality checks.

## Common Issues and Solutions

### Issue 1: Flake8 E402 - Module level import not at top of file
**Problem**: Import statements after `sys.path.insert()` calls
**Solution**: Add `# noqa: E402` comment to the import line
```python
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))
from redis_integration.config import RedisConfig  # noqa: E402
```

### Issue 2: Black formatting conflicts
**Problem**: Black reformats code differently than expected
**Solution**: Let black handle formatting automatically, or configure black settings in `pyproject.toml`

### Issue 3: Test failures in pre-commit
**Problem**: Tests fail due to environment issues or missing dependencies
**Solution**: 
- Ensure all dependencies are installed
- Check environment variables and configuration
- Fix failing tests before committing

### Issue 4: Import sorting conflicts
**Problem**: isort and other tools disagree on import order
**Solution**: Configure isort settings in `pyproject.toml` or `.isort.cfg`

## Configuration Files

### Match List Processor Configuration
- **Pre-commit**: `.pre-commit-config.yaml`
- **Python Project**: `pyproject.toml`
- **Flake8**: Configuration in `pyproject.toml`

### Calendar Service Configuration
- **Pre-commit**: `.pre-commit-config.yaml`
- **Pytest**: `pytest.ini`
- **Python Project**: `pyproject.toml` (if exists)

## Team Workflow

### For New Team Members
1. Clone the repository
2. Install pre-commit: `pip install pre-commit`
3. Install hooks: `pre-commit install`
4. Test installation: `pre-commit run --all-files`

### For Existing Team Members
If you haven't installed hooks yet:
1. Navigate to repository root
2. Run: `pre-commit install`
3. Test: `pre-commit run --all-files`

### Best Practices
1. **Always install hooks** when working on a new repository
2. **Run hooks manually** before committing large changes
3. **Fix issues immediately** rather than bypassing hooks
4. **Keep hooks updated** by running `pre-commit autoupdate` periodically
5. **Communicate changes** to hook configuration with the team

## Troubleshooting

### Hooks not running
```bash
# Check if hooks are installed
ls -la .git/hooks/pre-commit

# Reinstall if missing
pre-commit install
```

### Hooks failing unexpectedly
```bash
# Update hooks to latest versions
pre-commit autoupdate

# Clear cache and retry
pre-commit clean
pre-commit run --all-files
```

### Performance issues
```bash
# Run hooks in parallel (if supported)
pre-commit run --all-files --parallel

# Skip slow hooks for quick commits (not recommended for final commits)
SKIP=mypy,bandit git commit -m "Quick fix"
```

## Maintenance

### Updating Hooks
```bash
# Update all hooks to latest versions
pre-commit autoupdate

# Commit the updated configuration
git add .pre-commit-config.yaml
git commit -m "Update pre-commit hooks"
```

### Adding New Hooks
1. Edit `.pre-commit-config.yaml`
2. Add new hook configuration
3. Test: `pre-commit run --all-files`
4. Commit changes

### Removing Hooks
1. Remove hook from `.pre-commit-config.yaml`
2. Test: `pre-commit run --all-files`
3. Commit changes

## Integration with CI/CD

The pre-commit hooks are designed to match the CI/CD pipeline requirements:
- **Code formatting** matches CI expectations
- **Linting rules** align with CI checks
- **Security scanning** prevents vulnerabilities from reaching CI
- **Test execution** ensures functionality before CI

## Support

For issues with pre-commit hooks:
1. Check this documentation
2. Review hook configuration in `.pre-commit-config.yaml`
3. Check pre-commit documentation: https://pre-commit.com/
4. Contact the development team

---

**Last Updated**: 2025-09-23  
**Maintained By**: FOGIS Development Team
