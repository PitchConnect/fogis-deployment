# Pre-commit Hooks Quick Reference

## 🚀 Quick Setup (New Developer)
```bash
# 1. Install pre-commit
pip install pre-commit

# 2. Install hooks in match-list-processor
cd match-list-processor
pre-commit install

# 3. Install hooks in calendar service
cd ../fogis-calendar-phonebook-sync
pre-commit install

# 4. Test installation
pre-commit run --all-files
```

## 📋 Daily Commands

### Run hooks manually
```bash
# All hooks on all files
pre-commit run --all-files

# All hooks on staged files only
pre-commit run

# Specific hook only
pre-commit run black
pre-commit run flake8
```

### Normal commit workflow
```bash
git add .
git commit -m "Your message"
# Hooks run automatically ✨
```

## 🔧 Common Fixes

### Fix formatting issues
```bash
# Let black fix formatting automatically
pre-commit run black --all-files

# Let isort fix imports automatically  
pre-commit run isort --all-files
```

### Fix flake8 E402 (imports after sys.path)
```python
# Add this comment to the import line:
from redis_integration.config import RedisConfig  # noqa: E402
```

### Emergency bypass (use sparingly!)
```bash
git commit --no-verify -m "Emergency fix"
```

## 🛠️ Troubleshooting

### Hooks not running?
```bash
# Check installation
ls -la .git/hooks/pre-commit

# Reinstall if missing
pre-commit install
```

### Hooks failing?
```bash
# Update to latest versions
pre-commit autoupdate

# Clear cache and retry
pre-commit clean
pre-commit run --all-files
```

## 📊 Hook Status

### ✅ Match List Processor
- trailing-whitespace ✓
- end-of-file-fixer ✓
- check-yaml ✓
- check-added-large-files ✓
- check-merge-conflict ✓
- debug-statements ✓
- black ✓
- isort ✓
- flake8 ✓
- mypy ✓
- bandit ✓

### ✅ Calendar Service
- trailing-whitespace ✓
- end-of-file-fixer ✓
- check-yaml ✓
- check-json ✓
- check-added-large-files ✓
- isort ✓
- black ✓
- flake8 ✓
- bandit ✓
- pytest ✓

## 🎯 What Each Hook Does

| Hook | Purpose |
|------|---------|
| **black** | Formats Python code |
| **isort** | Sorts and organizes imports |
| **flake8** | Checks code style and errors |
| **mypy** | Static type checking |
| **bandit** | Security vulnerability scanning |
| **pytest** | Runs tests |
| **trailing-whitespace** | Removes trailing spaces |
| **end-of-file-fixer** | Ensures files end with newline |

## 🚨 Emergency Contacts

- **Documentation**: See `PRE_COMMIT_SETUP_GUIDE.md`
- **Issues**: Contact development team
- **Pre-commit Docs**: https://pre-commit.com/

---
*Keep this reference handy! 📌*
