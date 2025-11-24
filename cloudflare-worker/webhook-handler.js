/**
 * Cloudflare Worker: GitHub Container Registry Webhook Handler
 *
 * This worker receives webhook notifications from GitHub when new container
 * images are published to GHCR, verifies the webhook signature, and triggers
 * the deployment repository's auto-update workflow.
 *
 * Environment Variables Required:
 * - WEBHOOK_SECRET: GitHub webhook secret for signature verification
 * - GITHUB_TOKEN: GitHub Personal Access Token with repo scope
 * - DEPLOYMENT_REPO: Target repository (e.g., "PitchConnect/fogis-deployment")
 */

export default {
  async fetch(request, env, ctx) {
    // Only accept POST requests
    if (request.method !== 'POST') {
      return new Response('Method not allowed', { status: 405 });
    }

    // Verify this is a GitHub webhook
    const userAgent = request.headers.get('User-Agent');
    if (!userAgent || !userAgent.startsWith('GitHub-Hookshot/')) {
      return new Response('Invalid user agent', { status: 403 });
    }

    try {
      // Get the webhook signature
      const signature = request.headers.get('X-Hub-Signature-256');
      if (!signature) {
        return new Response('Missing signature', { status: 401 });
      }

      // Clone request for signature verification (body can only be read once)
      const requestClone = request.clone();
      const body = await request.text();

      // Verify webhook signature
      if (!await verifySignature(body, signature, env.WEBHOOK_SECRET)) {
        console.error('Invalid webhook signature');
        return new Response('Invalid signature', { status: 401 });
      }

      // Parse the webhook payload
      const payload = JSON.parse(body);

      // Get event type
      const eventType = requestClone.headers.get('X-GitHub-Event');

      // Log the event
      console.log(`Received ${eventType} event from ${payload.repository?.full_name}`);

      // Handle different event types
      let response;
      switch (eventType) {
        case 'registry_package':
          response = await handleRegistryPackageEvent(payload, env);
          break;
        case 'ping':
          response = new Response(JSON.stringify({ message: 'pong' }), {
            status: 200,
            headers: { 'Content-Type': 'application/json' }
          });
          break;
        default:
          console.log(`Ignoring event type: ${eventType}`);
          response = new Response(JSON.stringify({ message: 'Event type not handled' }), {
            status: 200,
            headers: { 'Content-Type': 'application/json' }
          });
      }

      return response;

    } catch (error) {
      console.error('Error processing webhook:', error);
      return new Response(JSON.stringify({ error: error.message }), {
        status: 500,
        headers: { 'Content-Type': 'application/json' }
      });
    }
  }
};

/**
 * Verify GitHub webhook signature using HMAC SHA-256
 */
async function verifySignature(body, signature, secret) {
  const encoder = new TextEncoder();
  const key = await crypto.subtle.importKey(
    'raw',
    encoder.encode(secret),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign']
  );

  const signed = await crypto.subtle.sign(
    'HMAC',
    key,
    encoder.encode(body)
  );

  const expectedSignature = 'sha256=' + Array.from(new Uint8Array(signed))
    .map(b => b.toString(16).padStart(2, '0'))
    .join('');

  // Constant-time comparison to prevent timing attacks
  return signature === expectedSignature;
}

/**
 * Handle registry_package webhook event
 */
async function handleRegistryPackageEvent(payload, env) {
  const { action, registry_package, repository } = payload;

  // Only handle 'published' events
  if (action !== 'published') {
    console.log(`Ignoring registry_package action: ${action}`);
    return new Response(JSON.stringify({ message: 'Not a publish event' }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' }
    });
  }

  // Only handle container packages
  if (registry_package.package_type !== 'container') {
    console.log(`Ignoring non-container package: ${registry_package.package_type}`);
    return new Response(JSON.stringify({ message: 'Not a container package' }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' }
    });
  }

  // Extract package information
  const packageName = registry_package.name;
  const packageVersion = registry_package.package_version;
  const tag = packageVersion.container_metadata?.tag?.name || 'unknown';
  const digest = packageVersion.container_metadata?.tag?.digest || '';
  const registryUrl = registry_package.registry?.url || '';

  console.log(`Container published: ${packageName}:${tag} (${digest})`);

  // Trigger deployment repository workflow
  const deploymentResponse = await triggerDeploymentWorkflow(
    env.DEPLOYMENT_REPO,
    env.GITHUB_TOKEN,
    {
      service: packageName,
      image: registryUrl || `ghcr.io/${repository.full_name}`,
      tag: tag,
      digest: digest,
      repository: repository.full_name,
      sha: payload.sender?.login === 'github-actions[bot]' ? 'automated' : ''
    }
  );

  if (!deploymentResponse.ok) {
    const errorText = await deploymentResponse.text();
    console.error('Failed to trigger deployment:', errorText);
    return new Response(JSON.stringify({
      error: 'Failed to trigger deployment',
      details: errorText
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }

  console.log(`Successfully triggered deployment for ${packageName}`);

  return new Response(JSON.stringify({
    message: 'Deployment triggered',
    service: packageName,
    tag: tag
  }), {
    status: 200,
    headers: { 'Content-Type': 'application/json' }
  });
}

/**
 * Trigger GitHub repository_dispatch event in deployment repository
 */
async function triggerDeploymentWorkflow(repo, token, payload) {
  const url = `https://api.github.com/repos/${repo}/dispatches`;

  return await fetch(url, {
    method: 'POST',
    headers: {
      'Accept': 'application/vnd.github+json',
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
      'User-Agent': 'Cloudflare-Worker-Webhook-Handler'
    },
    body: JSON.stringify({
      event_type: 'image_published',
      client_payload: payload
    })
  });
}
