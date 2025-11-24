# Container Image Webhook Automation Plan

## Executive Summary

This document provides a comprehensive plan to implement an automated webhook notification system that triggers testing/deployment whenever new container images are published to GitHub Container Registry (GHCR). This will eliminate manual intervention and ensure the deployment repository always uses the latest available images.

---

## 1. Current Container Registry Analysis

### ✅ Container Registry: GitHub Container Registry (GHCR)

**Current Setup:**
- **Registry**: `ghcr.io`
- **Organization**: `pitchconnect`
- **Published Images**:
  - `ghcr.io/pitchconnect/fogis-api-client-python:latest`
  - `ghcr.io/pitchconnect/match-list-processor:latest`
  - `ghcr.io/pitchconnect/team-logo-combiner:latest`
  - `ghcr.io/pitchconnect/fogis-calendar-phonebook-sync:latest`
  - `ghcr.io/pitchconnect/google-drive-service:latest`
  - `ghcr.io/pitchconnect/match-list-change-detector:latest`

**Image Build Workflow:**
- Location: `.github/workflows/docker-build.yml.disabled` (currently disabled)
- Triggers: Release published, push to main/develop, pull requests
- Multi-architecture support: `linux/amd64`, `linux/arm64`

---

## 2. GitHub Webhook Support for Container Registry

### ✅ GitHub Supports `registry_package` Webhook Event

**Key Findings:**

1. **Event Name**: `registry_package`
2. **Action Type**: `published` (triggered when a package is published to a registry)
3. **Availability**:
   - ✅ Repository webhooks
   - ✅ Organization webhooks
   - ✅ GitHub Apps

**Webhook Payload Structure:**
```json
{
  "action": "published",
  "registry_package": {
    "id": 12345,
    "name": "fogis-api-client-python",
    "package_type": "container",
    "package_version": {
      "id": 67890,
      "version": "latest",
      "container_metadata": {
        "tag": {
          "digest": "sha256:abc123...",
          "name": "latest"
        }
      }
    },
    "registry": {
      "url": "https://ghcr.io/pitchconnect/fogis-api-client-python"
    }
  },
  "repository": {
    "full_name": "PitchConnect/fogis-api-client-python"
  },
  "sender": {
    "login": "github-actions[bot]"
  }
}
```

**Important Limitation:**
- ⚠️ **Docker/Container images may have limited support**: According to GitHub community discussions, the `registry_package` event has historically had issues with Docker container images
- ✅ **Alternative**: Use GitHub Actions `workflow_run` event or `repository_dispatch` as a more reliable trigger

---

## 3. Webhook Configuration Options

### Option A: GitHub Organization Webhook (Recommended)

**Advantages:**
- ✅ Single webhook for all service repositories
- ✅ Centralized management
- ✅ Catches all package publications across the organization

**Configuration:**
1. Navigate to: `https://github.com/organizations/PitchConnect/settings/hooks`
2. Click "Add webhook"
3. Configure:
   - **Payload URL**: `https://fogis-deploy.yourdomain.com/webhook/image-published`
   - **Content type**: `application/json`
   - **Secret**: Generate a secure secret token
   - **Events**: Select "Packages" → `registry_package`
   - **Active**: ✅ Enabled

### Option B: Repository Dispatch (More Reliable)

**Advantages:**
- ✅ Works reliably with GitHub Actions
- ✅ No external webhook endpoint needed initially
- ✅ Can be triggered from service repository workflows

**Implementation:**
Add to each service repository's Docker build workflow:

```yaml
# In service repos: .github/workflows/docker-build.yml
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
          "service": "${{ matrix.service.name }}",
          "image": "${{ env.IMAGE_PREFIX }}/${{ matrix.service.image }}",
          "tag": "latest",
          "sha": "${{ github.sha }}",
          "repository": "${{ github.repository }}"
        }
      }'
```

---

## 4. Cloudflare Webhook Endpoint Setup

### Option 1: Cloudflare Workers (Recommended)

**Advantages:**
- ✅ Serverless, no infrastructure to manage
- ✅ Global edge deployment
- ✅ Built-in DDoS protection
- ✅ Free tier: 100,000 requests/day
- ✅ Low latency

**Implementation Steps:**

#### Step 1: Create Cloudflare Worker

```javascript
// webhook-handler.js
export default {
  async fetch(request, env) {
    // Verify webhook signature
    const signature = request.headers.get('X-Hub-Signature-256');
    if (!await verifySignature(request, signature, env.WEBHOOK_SECRET)) {
      return new Response('Unauthorized', { status: 401 });
    }

    const payload = await request.json();

    // Extract image information
    const { action, registry_package, repository } = payload;

    if (action !== 'published') {
      return new Response('OK - Not a publish event', { status: 200 });
    }

    // Trigger deployment workflow
    const deploymentResponse = await fetch(
      'https://api.github.com/repos/PitchConnect/fogis-deployment/dispatches',
      {
        method: 'POST',
        headers: {
          'Accept': 'application/vnd.github+json',
          'Authorization': `Bearer ${env.GITHUB_TOKEN}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          event_type: 'image_published',
          client_payload: {
            service: registry_package.name,
            image: registry_package.registry.url,
            tag: registry_package.package_version.container_metadata.tag.name,
            digest: registry_package.package_version.container_metadata.tag.digest,
            repository: repository.full_name
          }
        })
      }
    );

    if (!deploymentResponse.ok) {
      return new Response('Failed to trigger deployment', { status: 500 });
    }

    return new Response('Deployment triggered', { status: 200 });
  }
};

async function verifySignature(request, signature, secret) {
  const body = await request.clone().text();
  const encoder = new TextEncoder();
  const key = await crypto.subtle.importKey(
    'raw',
    encoder.encode(secret),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign']
  );
  const signed = await crypto.subtle.sign('HMAC', key, encoder.encode(body));
  const expectedSignature = 'sha256=' + Array.from(new Uint8Array(signed))
    .map(b => b.toString(16).padStart(2, '0'))
    .join('');
  return signature === expectedSignature;
}
```

#### Step 2: Deploy Worker

```bash
# Install Wrangler CLI
npm install -g wrangler

# Login to Cloudflare
wrangler login

# Create worker
wrangler init fogis-webhook-handler

# Add secrets
wrangler secret put WEBHOOK_SECRET
wrangler secret put GITHUB_TOKEN

# Deploy
wrangler deploy
```

#### Step 3: Configure Custom Domain

```toml
# wrangler.toml
name = "fogis-webhook-handler"
main = "webhook-handler.js"
compatibility_date = "2025-01-01"

[env.production]
routes = [
  { pattern = "fogis-deploy.yourdomain.com/webhook/*", zone_name = "yourdomain.com" }
]
```

### Option 2: Cloudflare Pages Functions

**Advantages:**
- ✅ Integrated with Pages deployment
- ✅ File-based routing
- ✅ Easy to version control

**Implementation:**

```javascript
// functions/webhook/image-published.js
export async function onRequestPost(context) {
  const { request, env } = context;

  // Verify signature
  const signature = request.headers.get('X-Hub-Signature-256');
  if (!await verifySignature(request, signature, env.WEBHOOK_SECRET)) {
    return new Response('Unauthorized', { status: 401 });
  }

  const payload = await request.json();

  // Trigger deployment
  // ... (same logic as Worker)

  return new Response('OK', { status: 200 });
}
```

---

## 5. Deployment Automation Workflow

### Recommended Approach: GitHub Actions `repository_dispatch`

Create a new workflow in `fogis-deployment` repository:

```yaml
# .github/workflows/auto-update-images.yml
name: Auto Update Container Images

on:
  repository_dispatch:
    types: [image_published]
  workflow_dispatch:
    inputs:
      service:
        description: 'Service name'
        required: true
      image:
        description: 'Image URL'
        required: true

jobs:
  update-and-test:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: write

    steps:
      - name: Checkout repository
        uses: actions/checkout@v5

      - name: Extract service information
        id: service-info
        run: |
          SERVICE="${{ github.event.client_payload.service || github.event.inputs.service }}"
          IMAGE="${{ github.event.client_payload.image || github.event.inputs.image }}"
          TAG="${{ github.event.client_payload.tag || 'latest' }}"
          DIGEST="${{ github.event.client_payload.digest || '' }}"

          echo "service=$SERVICE" >> $GITHUB_OUTPUT
          echo "image=$IMAGE" >> $GITHUB_OUTPUT
          echo "tag=$TAG" >> $GITHUB_OUTPUT
          echo "digest=$DIGEST" >> $GITHUB_OUTPUT

      - name: Pull and verify new image
        run: |
          echo "🔍 Pulling new image: ${{ steps.service-info.outputs.image }}:${{ steps.service-info.outputs.tag }}"
          docker pull ${{ steps.service-info.outputs.image }}:${{ steps.service-info.outputs.tag }}

          # Verify image
          docker inspect ${{ steps.service-info.outputs.image }}:${{ steps.service-info.outputs.tag }}

      - name: Run smoke tests
        run: |
          echo "🧪 Running smoke tests for ${{ steps.service-info.outputs.service }}"

          # Create minimal test environment
          cat > .env.test << 'EOF'
          FOGIS_USERNAME=test_user
          FOGIS_PASSWORD=test_password
          DEBUG_MODE=1
          LOG_LEVEL=INFO
          EOF

          # Start service
          docker run -d \
            --name test-${{ steps.service-info.outputs.service }} \
            --env-file .env.test \
            ${{ steps.service-info.outputs.image }}:${{ steps.service-info.outputs.tag }}

          # Wait for health check
          sleep 10

          # Verify service is running
          docker ps | grep test-${{ steps.service-info.outputs.service }}

          # Cleanup
          docker stop test-${{ steps.service-info.outputs.service }}
          docker rm test-${{ steps.service-info.outputs.service }}

      - name: Create deployment PR
        uses: peter-evans/create-pull-request@v7
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
          commit-message: |
            chore: update ${{ steps.service-info.outputs.service }} image

            - Service: ${{ steps.service-info.outputs.service }}
            - Image: ${{ steps.service-info.outputs.image }}:${{ steps.service-info.outputs.tag }}
            - Digest: ${{ steps.service-info.outputs.digest }}
          title: '🚀 Auto-update: ${{ steps.service-info.outputs.service }} image'
          body: |
            ## 🚀 Automated Image Update

            A new container image has been published and is ready for deployment.

            ### 📦 Image Details
            - **Service**: `${{ steps.service-info.outputs.service }}`
            - **Image**: `${{ steps.service-info.outputs.image }}:${{ steps.service-info.outputs.tag }}`
            - **Digest**: `${{ steps.service-info.outputs.digest }}`
            - **Source Repository**: `${{ github.event.client_payload.repository }}`

            ### ✅ Automated Checks
            - [x] Image pulled successfully
            - [x] Image verified
            - [x] Smoke tests passed

            ### 🔄 Next Steps
            1. Review changes
            2. Merge this PR to deploy to production
            3. Monitor deployment health

            ---
            *This PR was automatically created by the image update automation system.*
          branch: auto-update-${{ steps.service-info.outputs.service }}-${{ github.run_number }}
          delete-branch: true
```

---

## 6. Implementation Roadmap

### Phase 1: Quick Win - Repository Dispatch (Week 1)

**Goal**: Get basic automation working without external infrastructure

**Tasks**:
1. ✅ Create `auto-update-images.yml` workflow in `fogis-deployment` repository
2. ✅ Generate GitHub Personal Access Token (PAT) with `repo` scope
3. ✅ Add PAT as secret `DEPLOYMENT_REPO_TOKEN` to each service repository
4. ✅ Update service repository workflows to trigger `repository_dispatch`
5. ✅ Test with manual workflow dispatch
6. ✅ Monitor first automated update

**Deliverables**:
- Automated PR creation when images are published
- Smoke tests run before PR creation
- Manual merge required for deployment

### Phase 2: Cloudflare Webhook Endpoint (Week 2-3)

**Goal**: Add external webhook endpoint for more flexibility

**Tasks**:
1. ✅ Set up Cloudflare Worker
2. ✅ Configure custom domain routing
3. ✅ Add webhook secrets management
4. ✅ Configure GitHub organization webhook
5. ✅ Test webhook delivery
6. ✅ Add monitoring and logging

**Deliverables**:
- Public webhook endpoint: `https://fogis-deploy.yourdomain.com/webhook/image-published`
- Signature verification
- Webhook delivery logs

### Phase 3: Enhanced Testing & Auto-Merge (Week 4)

**Goal**: Fully automated deployment with comprehensive testing

**Tasks**:
1. ✅ Add integration tests to auto-update workflow
2. ✅ Implement auto-merge for passing tests
3. ✅ Add rollback mechanism
4. ✅ Configure notifications (Discord/Slack)
5. ✅ Add deployment health monitoring

**Deliverables**:
- Fully automated deployment pipeline
- Automatic rollback on failures
- Real-time notifications

---

## 7. Security Considerations

### Webhook Security

1. **Signature Verification**
   - ✅ Always verify `X-Hub-Signature-256` header
   - ✅ Use constant-time comparison to prevent timing attacks
   - ✅ Rotate webhook secrets regularly

2. **Access Control**
   - ✅ Use GitHub PAT with minimal required scopes
   - ✅ Store secrets in GitHub Secrets or Cloudflare environment variables
   - ✅ Implement rate limiting on webhook endpoint

3. **Network Security**
   - ✅ Use HTTPS only
   - ✅ Cloudflare provides DDoS protection
   - ✅ Log all webhook deliveries for audit

### Deployment Security

1. **Image Verification**
   - ✅ Verify image digest before deployment
   - ✅ Run security scans (Trivy) on new images
   - ✅ Check for critical vulnerabilities

2. **Automated Testing**
   - ✅ Run smoke tests before creating PR
   - ✅ Require status checks to pass before merge
   - ✅ Test in staging environment first

---

## 8. Monitoring & Observability

### Webhook Monitoring

```javascript
// Add to Cloudflare Worker
async function logWebhookEvent(payload, status) {
  await fetch(env.LOGGING_ENDPOINT, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      timestamp: new Date().toISOString(),
      event_type: 'webhook_received',
      service: payload.registry_package?.name,
      action: payload.action,
      status: status,
      repository: payload.repository?.full_name
    })
  });
}
```

### Deployment Monitoring

Add to `auto-update-images.yml`:

```yaml
- name: Send notification
  if: always()
  run: |
    STATUS="${{ job.status }}"
    SERVICE="${{ steps.service-info.outputs.service }}"

    curl -X POST ${{ secrets.DISCORD_WEBHOOK_URL }} \
      -H "Content-Type: application/json" \
      -d "{
        \"content\": \"🚀 Image Update: **$SERVICE**\",
        \"embeds\": [{
          \"title\": \"Deployment Status: $STATUS\",
          \"color\": $([ \"$STATUS\" = \"success\" ] && echo \"3066993\" || echo \"15158332\"),
          \"fields\": [
            {\"name\": \"Service\", \"value\": \"$SERVICE\", \"inline\": true},
            {\"name\": \"Status\", \"value\": \"$STATUS\", \"inline\": true},
            {\"name\": \"Image\", \"value\": \"${{ steps.service-info.outputs.image }}\"}
          ]
        }]
      }"
```

---

## 9. Cost Analysis

### Cloudflare Workers

- **Free Tier**: 100,000 requests/day
- **Paid Plan**: $5/month for 10M requests
- **Expected Usage**: ~50-100 requests/day (well within free tier)
- **Cost**: **$0/month**

### GitHub Actions

- **Free Tier**: 2,000 minutes/month for private repos
- **Expected Usage**: ~10 minutes per image update × 6 services × 4 updates/month = 240 minutes/month
- **Cost**: **$0/month** (within free tier)

### Total Monthly Cost: **$0**

---

## 10. Alternative Approaches

### Alternative 1: GitHub Actions Only (No External Webhook)

**Pros**:
- ✅ No external infrastructure
- ✅ Simpler setup
- ✅ All within GitHub ecosystem

**Cons**:
- ❌ Requires PAT in each service repository
- ❌ Less flexible for future integrations
- ❌ Harder to add custom logic

**Recommendation**: Start with this approach (Phase 1)

### Alternative 2: Self-Hosted Webhook Server

**Pros**:
- ✅ Full control
- ✅ Can integrate with existing infrastructure

**Cons**:
- ❌ Requires server maintenance
- ❌ Need to handle security, scaling, monitoring
- ❌ Higher operational overhead

**Recommendation**: Not recommended given Cloudflare Workers availability

### Alternative 3: Flux CD / ArgoCD

**Pros**:
- ✅ GitOps-native approach
- ✅ Automatic image updates
- ✅ Built-in rollback

**Cons**:
- ❌ Requires Kubernetes (current setup uses Docker Compose)
- ❌ Significant architecture change
- ❌ Steeper learning curve

**Recommendation**: Consider for future if migrating to Kubernetes

---

## 11. Recommended Implementation Plan

### Immediate Action (This Week)

**Implement Phase 1: Repository Dispatch**

1. Create the `auto-update-images.yml` workflow
2. Generate GitHub PAT
3. Add PAT to service repositories
4. Update one service repository workflow as a test
5. Trigger manual test
6. Monitor and iterate

**Why Start Here**:
- ✅ Zero infrastructure setup
- ✅ Can be done in 1-2 hours
- ✅ Immediate value
- ✅ Easy to test and validate
- ✅ Foundation for future enhancements

### Next Steps (Week 2-3)

**Add Cloudflare Webhook Endpoint**

1. Set up Cloudflare Worker
2. Configure custom domain
3. Add GitHub organization webhook
4. Migrate from repository dispatch to webhook trigger

**Why Add This**:
- ✅ More scalable
- ✅ Centralized webhook management
- ✅ Easier to add custom logic
- ✅ Better for multi-repository setups

### Future Enhancements (Month 2+)

1. **Auto-merge**: Automatically merge PRs that pass all tests
2. **Staging deployment**: Deploy to staging environment first
3. **Canary deployments**: Gradual rollout of new images
4. **Rollback automation**: Automatic rollback on health check failures
5. **Image digest pinning**: Pin to specific image digests for reproducibility

---

## 12. Success Metrics

### Key Performance Indicators (KPIs)

1. **Time to Deployment**
   - **Current**: Manual, variable (hours to days)
   - **Target**: < 15 minutes from image publish to PR creation
   - **Measurement**: GitHub Actions workflow duration

2. **Deployment Frequency**
   - **Current**: Ad-hoc, manual
   - **Target**: Automated on every image publish
   - **Measurement**: Number of automated PRs created per week

3. **Deployment Success Rate**
   - **Current**: Unknown (manual process)
   - **Target**: > 95% successful automated deployments
   - **Measurement**: Ratio of successful to failed workflow runs

4. **Manual Intervention Required**
   - **Current**: 100% (all deployments manual)
   - **Target**: < 10% (only for complex changes)
   - **Measurement**: Percentage of PRs requiring manual fixes

---

## 13. Conclusion

### Summary

This plan provides a **phased approach** to implementing automated webhook notifications for container image updates:

1. **Phase 1** (Week 1): Quick win with GitHub Actions `repository_dispatch`
2. **Phase 2** (Week 2-3): Add Cloudflare webhook endpoint for scalability
3. **Phase 3** (Week 4+): Enhanced testing and auto-merge

### Recommended Next Steps

1. ✅ **Review this plan** with the team
2. ✅ **Decide on domain name** for webhook endpoint (e.g., `fogis-deploy.yourdomain.com`)
3. ✅ **Start with Phase 1** implementation (repository dispatch)
4. ✅ **Test with one service** before rolling out to all services
5. ✅ **Monitor and iterate** based on results

### Expected Benefits

- ⚡ **Faster deployments**: From hours/days to minutes
- 🔄 **Automated updates**: No manual intervention needed
- 🛡️ **Safer deployments**: Automated testing before deployment
- 📊 **Better visibility**: Notifications and monitoring
- 🎯 **Consistent process**: Same workflow for all services

---

**Questions or need help with implementation? Let me know!**
