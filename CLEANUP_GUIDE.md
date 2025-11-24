# Repository Cleanup Guide

This guide provides step-by-step instructions for cleaning up the fogis-deployment repository.

## Overview

The repository has accumulated temporary files from debugging and development:
- **58 files** to be deleted (debug scripts, investigation reports, config variants)
- **9 files** to be moved to proper locations (permanent documentation, diagnostic tools)
- **7 files** requiring manual review before deletion
- **Hundreds of Loki monitoring files** to be migrated to Docker volumes

---

## Step 1: Automated Cleanup Script

### What the Script Does

The `cleanup-repository.sh` script automates the removal and organization of files:

1. **Creates directories:**
   - `scripts/diagnostics/` - For diagnostic tools
   - `docs/` - For permanent documentation

2. **Relocates files:**
   - `fix_calendar_sync.sh` → `scripts/diagnostics/calendar-sync-diagnostic.sh`

3. **Moves permanent documentation to `docs/`:**
   - ARM64_IMPLEMENTATION_SUMMARY.md
   - CALENDAR_SERVICE_AUTHENTICATION.md
   - CALENDAR_SYNC_REFEREE_HASH_FIX.md
   - CALENDAR_SYNC_ROOT_CAUSE_ANALYSIS.md
   - CONFIGURATION_IMPROVEMENTS.md
   - DEPENDABOT_TESTING_STRATEGY.md
   - DEPLOYMENT_PREREQUISITES.md
   - CONTAINER_IMAGE_WEBHOOK_AUTOMATION_PLAN.md

4. **Deletes temporary files:**
   - 13 Python debug/test scripts (force_sync_match_*.py, subscriber_fix_*.py, etc.)
   - 2 shell scripts (apply_subscriber_fix.sh, direct_force_sync.sh)
   - 6 configuration variants (ci_updated.yml, pyproject_*.toml, etc.)
   - 2 test images (enhanced_schema_logo_test.png, team_db_id_logo_test.png)
   - 35 investigation reports (temporary AI-generated debugging documents)

5. **Stages deleted Loki files for commit:**
   - 5 deleted Loki database files

### Usage

#### Preview Changes (Safe - Recommended First Step)

```bash
./cleanup-repository.sh --dry-run
```

This shows what would be done without making any changes.

#### Execute Cleanup (With Confirmation)

```bash
./cleanup-repository.sh --execute
```

This will:
1. Show a summary of all changes
2. Ask for confirmation before proceeding
3. Execute the cleanup operations
4. Display a summary of completed actions

#### Execute Without Prompts (Use with Caution)

```bash
./cleanup-repository.sh --execute --yes
```

⚠️ **Warning:** This skips all confirmation prompts. Only use if you're certain.

### Script Options

- `--dry-run` - Preview changes without executing (default)
- `--execute` - Actually perform the cleanup
- `--yes` - Skip confirmation prompts
- `--help` - Show usage information

---

## Step 2: Manual Review of Remaining Files

After running the cleanup script, review these 7 files to determine if they should be kept or deleted:

### Files to Review

1. **QUICK_REFERENCE_REDIS_INTEGRATION.md**
   - Quick reference for Redis integration
   - **Recommendation:** Review content; if useful, move to `docs/`; otherwise delete

2. **REDIS_INTEGRATION_IMPLEMENTATION_GUIDE.md**
   - Implementation guide for Redis integration
   - **Recommendation:** Review content; if useful, move to `docs/`; otherwise delete

3. **REDIS_PUBSUB_VS_STREAMS_ANALYSIS.md**
   - Analysis of Redis Pub/Sub vs Streams
   - **Recommendation:** Architectural decision document; likely worth keeping in `docs/`

4. **WEBHOOK_AUTOMATION_SETUP_GUIDE.md**
   - Setup guide for webhook automation
   - **Recommendation:** Review content; if active feature, move to `docs/`; otherwise delete

5. **redis_message_schema_analysis.md**
   - Schema analysis documentation
   - **Recommendation:** Review content; if useful reference, move to `docs/`; otherwise delete

6. **redis_schema_evolution_strategy.md**
   - Strategy document for schema evolution
   - **Recommendation:** Architectural decision document; likely worth keeping in `docs/`

7. **team-logo-worker-README.md**
   - README for team logo worker
   - **Recommendation:** If service is active, move to `docs/`; otherwise delete

### Review Process

```bash
# View each file
cat QUICK_REFERENCE_REDIS_INTEGRATION.md
cat REDIS_INTEGRATION_IMPLEMENTATION_GUIDE.md
# ... etc

# If keeping, move to docs/
mv REDIS_PUBSUB_VS_STREAMS_ANALYSIS.md docs/

# If deleting
rm QUICK_REFERENCE_REDIS_INTEGRATION.md
```

---

## Step 3: Verify Changes

After running the cleanup script:

```bash
# Check git status
git status

# Review what was deleted
git diff --cached

# Review new directory structure
tree -L 2 scripts/
tree -L 1 docs/
```

---

## Next Steps

After completing the cleanup:

1. **Proceed to Step 2:** Loki Docker Volume Migration (see LOKI_MIGRATION_GUIDE.md)
2. **Review infrastructure files:** GitHub workflows, cloudflare-worker, tests/
3. **Commit changes:**
   ```bash
   git add .
   git commit -m "Clean up temporary debug scripts and organize documentation"
   ```

---

## Rollback

If you need to undo the cleanup (only works if you haven't committed yet):

```bash
# Restore all deleted files
git restore .

# Remove created directories
rm -rf scripts/diagnostics
rm -rf docs/
```

---

## Summary

**Total Impact:**
- 58 files deleted
- 9 files moved to proper locations
- 2 directories created
- 7 files flagged for manual review
- Repository size significantly reduced
- Better organization of documentation and scripts
