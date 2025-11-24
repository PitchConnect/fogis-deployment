# Webhook Automation Setup Guide

This guide provides step-by-step instructions to implement automated container image update notifications.

---

## Phase 1: Repository Dispatch Setup (Quick Start)

**Time Required**: 30-60 minutes
**Prerequisites**: GitHub account with admin access to repositories

### Step 1: Create GitHub Personal Access Token (PAT)

1. Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click "Generate new token (classic)"
3. Configure the token:
   - **Name**: `Deployment Repository Dispatch`
   - **Expiration**: 90 days (or as per your security policy)
   - **Scopes**:
     - ✅ `repo` (Full control of private repositories)
4. Click "Generate token"
5. **IMPORTANT**: Copy the token immediately (you won't see it again)

### Step 2: Add PAT to Service Repositories

For each service repository (fogis-api-client-python, match-list-processor, etc.):

1. Go to repository Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Add secret:
   - **Name**: `DEPLOYMENT_REPO_TOKEN`
   - **Value**: Paste the PAT from Step 1
4. Click "Add secret"

**Repositories to update**:
- [ ] fogis-api-client-python
- [ ] match-list-processor
- [ ] team-logo-combiner
- [ ] fogis-calendar-phonebook-sync
- [ ] google-drive-service
- [ ] match-list-change-detector

### Step 3: Verify Auto-Update Workflow

The workflow file `.github/workflows/auto-update-images.yml` has been created in this repository.

**Verify it's present**:
```bash
ls -la .github/workflows/auto-update-images.yml
```

**Test manually**:
1. Go to Actions tab in GitHub
2. Select "Auto Update Container Images" workflow
3. Click "Run workflow"
4. Fill in test values:
   - Service: `fogis-api-client-python`
   - Image: `ghcr.io/pitchconnect/fogis-api-client-python`
   - Tag: `latest`
5. Click "Run workflow"
6. Monitor the workflow run
7. Check if a PR is created

### Step 4: Update Service Repository Workflows

For each service repository, add the dispatch trigger to their Docker build workflow.

**Example for fogis-api-client-python**:

Edit `.github/workflows/docker-build.yml` and add this step at the end:

```yaml
- name: Trigger deployment repository update
  if: github.event_name == 'push' && github.ref == 'refs/heads/main'
  run: |
    curl -X POST \
      -H "Accept: application/vnd.github+json" \
      -H "Authorization: Bearer ${{ secrets.DEPLOYMENT_REPO_TOKEN }}" \
      https://api.github.com/repos/PitchConnect/fogis-deployment/dispatches \
      -d '{
        "event_type": "image_published",
        "client_payload": {
          "service": "fogis-api-client-python",
          "image": "ghcr.io/pitchconnect/fogis-api-client-python",
          "tag": "latest",
          "sha": "${{ github.sha }}",
          "repository": "${{ github.repository }}"
        }
      }'
```

**Customize for each service**:
- Change `service` name
- Change `image` URL
- Adjust the workflow file path if different

### Step 5: Test End-to-End

1. Make a small change in a service repository (e.g., update README)
2. Commit and push to main branch
3. Wait for Docker build workflow to complete
4. Check fogis-deployment repository for new PR
5. Verify PR contains correct image information

**Expected Result**:
- ✅ Service builds and pushes new image
- ✅ Deployment repository receives dispatch event
- ✅ Auto-update workflow runs
- ✅ PR is created with image details

---

## Phase 2: Cloudflare Worker Setup (Optional)

**Time Required**: 1-2 hours
**Prerequisites**: Cloudflare account, domain managed by Cloudflare

### Step 1: Install Wrangler CLI

```bash
npm install -g wrangler

# Or using yarn
yarn global add wrangler

# Verify installation
wrangler --version
```

### Step 2: Login to Cloudflare

```bash
wrangler login
```

This will open a browser window for authentication.

### Step 3: Configure Worker

1. Edit `cloudflare-worker/wrangler.toml`:
   - Replace `YOUR_ACCOUNT_ID` with your Cloudflare account ID
   - Replace `yourdomain.com` with your actual domain
   - Update `DEPLOYMENT_REPO` if needed

2. Find your account ID:
   - Go to https://dash.cloudflare.com/
   - Click on "Workers & Pages"
   - Your account ID is shown in the URL or on the overview page

### Step 4: Set Secrets

```bash
cd cloudflare-worker

# Set webhook secret (generate a random string)
wrangler secret put WEBHOOK_SECRET --env production
# Enter a strong random string (e.g., use: openssl rand -hex 32)

# Set GitHub token (use the PAT from Phase 1 or create a new one)
wrangler secret put GITHUB_TOKEN --env production
# Enter your GitHub PAT
```

### Step 5: Deploy Worker

```bash
# Deploy to production
wrangler deploy --env production

# Test deployment
curl https://fogis-webhook-handler-production.YOUR_SUBDOMAIN.workers.dev
```

### Step 6: Configure GitHub Webhook

**Organization Webhook** (recommended):

1. Go to https://github.com/organizations/PitchConnect/settings/hooks
2. Click "Add webhook"
3. Configure:
   - **Payload URL**: `https://fogis-deploy.yourdomain.com/webhook/image-published`
   - **Content type**: `application/json`
   - **Secret**: Use the same value you set in `WEBHOOK_SECRET`
   - **SSL verification**: Enable SSL verification
   - **Events**: Select "Let me select individual events"
     - ✅ Packages
   - **Active**: ✅ Enabled
4. Click "Add webhook"

**Test Webhook**:
1. Click on the webhook you just created
2. Scroll to "Recent Deliveries"
3. Click "Redeliver" on the ping event
4. Check response status (should be 200)

### Step 7: Verify End-to-End

1. Publish a new container image from a service repository
2. Check webhook deliveries in GitHub
3. Check Cloudflare Worker logs:
   ```bash
   wrangler tail --env production
   ```
4. Verify PR is created in deployment repository

---

## Monitoring & Troubleshooting

### Check Workflow Runs

```bash
# View recent workflow runs
gh run list --workflow=auto-update-images.yml --limit 10

# View specific run details
gh run view <run-id>

# View logs
gh run view <run-id> --log
```

### Check Webhook Deliveries

1. Go to GitHub webhook settings
2. Click on the webhook
3. Scroll to "Recent Deliveries"
4. Click on a delivery to see:
   - Request headers
   - Request payload
   - Response status
   - Response body

### Common Issues

**Issue**: PR not created
- **Check**: Workflow run logs in Actions tab
- **Check**: GitHub token permissions
- **Fix**: Ensure PAT has `repo` scope

**Issue**: Webhook signature verification fails
- **Check**: Webhook secret matches in GitHub and Cloudflare
- **Fix**: Regenerate secret and update both locations

**Issue**: Image pull fails
- **Check**: Image exists in GHCR
- **Check**: GitHub token has `packages:read` permission
- **Fix**: Ensure workflow has correct permissions

**Issue**: Container fails to start in smoke tests
- **Check**: Container logs in workflow output
- **Check**: Required environment variables
- **Fix**: Update smoke test configuration

### View Logs

**GitHub Actions**:
```bash
# Using GitHub CLI
gh run list --workflow=auto-update-images.yml
gh run view <run-id> --log
```

**Cloudflare Worker**:
```bash
# Real-time logs
wrangler tail --env production

# Filter logs
wrangler tail --env production --format pretty
```

**Docker Compose** (on deployment server):
```bash
# View service logs
docker compose logs -f <service-name>

# View recent logs
docker compose logs --tail=100 <service-name>
```

---

## Maintenance

### Rotate Secrets

**GitHub PAT** (every 90 days or as per policy):
1. Generate new PAT
2. Update in all service repositories
3. Update in Cloudflare Worker (if using Phase 2)
4. Test with manual workflow run
5. Delete old PAT

**Webhook Secret** (annually or after security incident):
1. Generate new secret
2. Update in Cloudflare Worker
3. Update in GitHub webhook settings
4. Test webhook delivery

### Monitor Usage

**GitHub Actions**:
- Check Actions usage in repository settings
- Free tier: 2,000 minutes/month for private repos
- Monitor: Settings → Billing → Actions usage

**Cloudflare Workers**:
- Check usage in Cloudflare dashboard
- Free tier: 100,000 requests/day
- Monitor: Workers & Pages → Analytics

---

## Next Steps

After successful setup:

1. **Monitor for 1 week**: Ensure automation works reliably
2. **Add notifications**: Configure Discord/Slack notifications
3. **Enable auto-merge**: For PRs that pass all tests
4. **Add staging deployment**: Test in staging before production
5. **Implement rollback**: Automatic rollback on health check failures

---

## Support

**Questions or Issues?**
- Check workflow logs in Actions tab
- Review webhook deliveries in GitHub settings
- Check Cloudflare Worker logs with `wrangler tail`
- Review this guide's troubleshooting section

**Need Help?**
- Create an issue in the repository
- Check GitHub Actions documentation
- Check Cloudflare Workers documentation
