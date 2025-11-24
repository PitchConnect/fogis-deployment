# FOGIS Webhook Handler - Cloudflare Worker

## Status

⚠️ **Configured but not yet deployed**

This Cloudflare Worker is production-ready but has not been deployed to Cloudflare's edge network. The configuration files are complete and ready for deployment when needed.

---

## Purpose

This Cloudflare Worker acts as a webhook handler that bridges GitHub Container Registry (GHCR) package events with the deployment repository's automated update workflow.

### Architecture Flow

```
┌─────────────────────┐
│ Service Repository  │
│ (e.g., match-list-  │
│  processor)         │
└──────────┬──────────┘
           │
           │ 1. Publishes new image to GHCR
           ▼
┌─────────────────────┐
│ GitHub Container    │
│ Registry (GHCR)     │
└──────────┬──────────┘
           │
           │ 2. Sends webhook notification
           ▼
┌─────────────────────┐
│ Cloudflare Worker   │ ◄── This component
│ (webhook-handler.js)│
└──────────┬──────────┘
           │
           │ 3. Verifies signature & triggers workflow
           ▼
┌─────────────────────┐
│ Deployment Repo     │
│ auto-update-images  │
│ workflow            │
└──────────┬──────────┘
           │
           │ 4. Creates PR with image update
           ▼
┌─────────────────────┐
│ Pull Request        │
│ (Image Update)      │
└─────────────────────┘
```

---

## Features

### Security
- **Webhook signature verification** using HMAC SHA-256
- **Constant-time signature comparison** to prevent timing attacks
- **User-Agent validation** to ensure requests come from GitHub
- **Secret management** via Cloudflare environment variables

### Event Handling
- **registry_package events** - Handles container image publications
- **ping events** - Responds to webhook configuration tests
- **Event filtering** - Only processes published container packages

### Integration
- **GitHub repository_dispatch** - Triggers deployment workflow
- **Metadata forwarding** - Passes image details (service, tag, digest, source)
- **Error handling** - Comprehensive error logging and responses

---

## Files

### `webhook-handler.js`
Main worker implementation with:
- Webhook signature verification
- Event type handling
- GitHub API integration
- Error handling and logging

### `wrangler.toml`
Cloudflare Worker configuration with:
- Environment separation (production/development)
- Custom domain routing (placeholder)
- Environment variables
- Observability settings

---

## Deployment Instructions

### Prerequisites

1. **Cloudflare Account** with Workers enabled
2. **Wrangler CLI** installed:
   ```bash
   npm install -g wrangler
   ```
3. **GitHub Personal Access Token** with `repo` scope
4. **Webhook Secret** (generate a secure random string)

### Step 1: Configure wrangler.toml

Edit `wrangler.toml` and update:

```toml
# Replace with your Cloudflare account ID
# Find it at: https://dash.cloudflare.com/ -> Workers & Pages -> Overview
account_id = "your-actual-account-id"

# Update custom domain (if using)
[env.production]
routes = [
  { pattern = "fogis-deploy.yourdomain.com/webhook/*", zone_name = "yourdomain.com" }
]
```

### Step 2: Configure Secrets

```bash
# Authenticate with Cloudflare
wrangler login

# Set webhook secret (same as configured in GitHub)
wrangler secret put WEBHOOK_SECRET

# Set GitHub token (with repo scope)
wrangler secret put GITHUB_TOKEN
```

### Step 3: Deploy Worker

```bash
# Deploy to production
wrangler deploy --env production

# Or deploy to development
wrangler deploy --env development
```

### Step 4: Configure GitHub Webhooks

For each service repository (e.g., fogis-match-list-processor):

1. Go to **Settings** → **Webhooks** → **Add webhook**
2. **Payload URL**: `https://your-worker-url.workers.dev/webhook` (or custom domain)
3. **Content type**: `application/json`
4. **Secret**: Same value as `WEBHOOK_SECRET`
5. **Events**: Select "Packages" only
6. **Active**: ✅ Checked

### Step 5: Test the Integration

```bash
# Trigger a test by publishing a new image
# The worker should receive the webhook and trigger the auto-update workflow

# Check worker logs
wrangler tail --env production

# Verify workflow was triggered
# Check: https://github.com/PitchConnect/fogis-deployment/actions
```

---

## Environment Variables

### Required Secrets (set via `wrangler secret put`)

| Secret | Description | Example |
|--------|-------------|---------|
| `WEBHOOK_SECRET` | GitHub webhook secret for signature verification | `your-secure-random-string` |
| `GITHUB_TOKEN` | GitHub PAT with `repo` scope | `ghp_xxxxxxxxxxxx` |

### Configuration Variables (in wrangler.toml)

| Variable | Description | Value |
|----------|-------------|-------|
| `DEPLOYMENT_REPO` | Target deployment repository | `PitchConnect/fogis-deployment` |

---

## Testing

### Local Testing

```bash
# Start local development server
wrangler dev

# Send test webhook (in another terminal)
curl -X POST http://localhost:8787 \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: ping" \
  -H "User-Agent: GitHub-Hookshot/test" \
  -H "X-Hub-Signature-256: sha256=test" \
  -d '{"zen": "test"}'
```

### Production Testing

After deployment, test with GitHub's webhook delivery:
1. Go to repository **Settings** → **Webhooks**
2. Click on your webhook
3. Scroll to **Recent Deliveries**
4. Click **Redeliver** on a recent delivery

---

## Monitoring

### View Logs

```bash
# Tail production logs
wrangler tail --env production

# Tail development logs
wrangler tail --env development
```

### Cloudflare Dashboard

Monitor worker metrics at:
- **Requests**: Total requests processed
- **Errors**: Error rate and details
- **CPU Time**: Execution time
- **Success Rate**: Percentage of successful requests

---

## Troubleshooting

### Common Issues

**Worker not receiving webhooks:**
- Verify webhook URL is correct
- Check webhook secret matches
- Ensure worker is deployed and active

**Signature verification fails:**
- Verify `WEBHOOK_SECRET` matches GitHub webhook secret
- Check webhook payload is not modified in transit

**Workflow not triggered:**
- Verify `GITHUB_TOKEN` has `repo` scope
- Check `DEPLOYMENT_REPO` is correct
- Review worker logs for API errors

---

## Related Documentation

- **Webhook Automation Setup**: `docs/operations/WEBHOOK_AUTOMATION_SETUP_GUIDE.md`
- **Auto-Update Workflow**: `.github/workflows/auto-update-images.yml`
- **Cloudflare Workers Docs**: https://developers.cloudflare.com/workers/

---

## Future Enhancements

- [ ] Add support for multiple deployment repositories
- [ ] Implement rate limiting
- [ ] Add Slack/Discord notifications
- [ ] Store webhook events in Cloudflare KV for audit trail
- [ ] Add support for rollback triggers
