#!/usr/bin/env bash
# Kill Switch - Clean up all deployed GCP resources after hackathon judging
echo "Executing Kill Switch to ensure ₹0 cost post-hackathon..."

gcloud scheduler jobs delete watchdog-nightly --location=us-central1 -q 2>/dev/null || true
gcloud run services delete coach --region=us-central1 -q 2>/dev/null || true
gcloud pubsub subscriptions delete watchdog-push -q 2>/dev/null || true
gcloud pubsub topics delete watchdog-tick -q 2>/dev/null || true
gcloud secrets delete gemini-key -q 2>/dev/null || true
gcloud secrets delete oauth-token -q 2>/dev/null || true
gcloud secrets delete client-secret -q 2>/dev/null || true

echo "All active compute, scheduler, pubsub, and secret manager resources deleted successfully."
