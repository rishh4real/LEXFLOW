#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

if ! command -v firebase >/dev/null 2>&1; then
  echo "Error: firebase CLI is not installed." >&2
  echo "Install it from https://firebase.google.com/docs/cli" >&2
  exit 1
fi

if ! command -v gcloud >/dev/null 2>&1; then
  echo "Error: gcloud CLI is not installed." >&2
  echo "Install it from https://cloud.google.com/sdk/docs/install" >&2
  exit 1
fi

if [ -z "${FIREBASE_PROJECT_ID:-}" ]; then
  echo "Error: FIREBASE_PROJECT_ID is not set." >&2
  echo "Set it before running: export FIREBASE_PROJECT_ID=your_project_id" >&2
  exit 1
fi

if [ -z "${GROQ_API_KEY:-}" ]; then
  echo "Error: GROQ_API_KEY is not set." >&2
  echo "Set it before running: export GROQ_API_KEY=your_key" >&2
  exit 1
fi

if [ -z "${JWT_SECRET:-}" ]; then
  echo "Error: JWT_SECRET is not set." >&2
  echo "Set it before running: export JWT_SECRET=your_secret" >&2
  exit 1
fi

REGION="${CLOUD_RUN_REGION:-us-central1}"
SERVICE_NAME="lexflow-api"
IMAGE_NAME="gcr.io/$FIREBASE_PROJECT_ID/$SERVICE_NAME"

echo "==> Deploying frontend to Firebase Hosting"
cd "$ROOT_DIR/frontend"
npm install
npm run build

echo "==> Deploying Firebase Hosting"
cd "$ROOT_DIR"
firebase deploy --only hosting --project "$FIREBASE_PROJECT_ID"

echo "==> Building backend container"
cd "$ROOT_DIR/backend"
if [ ! -f Dockerfile ]; then
  echo "Error: backend/Dockerfile missing." >&2
  exit 1
fi

gcloud config set project "$FIREBASE_PROJECT_ID"
gcloud builds submit --tag "$IMAGE_NAME"

echo "==> Deploying backend to Cloud Run"
gcloud run deploy "$SERVICE_NAME" \
  --image "$IMAGE_NAME" \
  --platform managed \
  --region "$REGION" \
  --allow-unauthenticated \
  --set-env-vars "GROQ_API_KEY=$GROQ_API_KEY,JWT_SECRET=$JWT_SECRET"

echo "\nDeployment complete!"
echo "Frontend: https://$(firebase hosting:sites:get | tail -n1)"
echo "Backend service: $SERVICE_NAME"
