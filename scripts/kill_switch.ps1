# PowerShell Kill Switch
Write-Host "Executing Kill Switch to ensure ₹0 cost post-hackathon..."
gcloud scheduler jobs delete watchdog-nightly --location=us-central1 -q
gcloud run services delete coach --region=us-central1 -q
gcloud pubsub subscriptions delete watchdog-push -q
gcloud pubsub topics delete watchdog-tick -q
gcloud secrets delete gemini-key -q
gcloud secrets delete oauth-token -q
gcloud secrets delete client-secret -q
Write-Host "All active compute, scheduler, pubsub, and secret manager resources deleted successfully."
