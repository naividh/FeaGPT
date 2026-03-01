#!/bin/bash
# FeaGPT Cloud Run Deployment Script
# Deploys the FeaGPT API server to Google Cloud Run with Firebase integration.
#
# Prerequisites:
#   - gcloud CLI installed and authenticated
#   - Docker installed
#   - Firebase CLI installed (npm install -g firebase-tools)
#   - Environment variables set: GCP_PROJECT_ID, GEMINI_API_KEY
#
# Usage:
#   chmod +x deploy/deploy_cloudrun.sh
#   ./deploy/deploy_cloudrun.sh

set -euo pipefail

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:?Set GCP_PROJECT_ID environment variable}"
REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="feagpt-api"
IMAGE_NAME="${REGION}-docker.pkg.dev/${PROJECT_ID}/feagpt/${SERVICE_NAME}"
GEMINI_KEY="${GEMINI_API_KEY:?Set GEMINI_API_KEY environment variable}"

echo "========================================="
echo "  FeaGPT Cloud Run Deployment"
echo "========================================="
echo "Project:  ${PROJECT_ID}"
echo "Region:   ${REGION}"
echo "Service:  ${SERVICE_NAME}"
echo ""

# Step 1: Enable required APIs
echo "[1/7] Enabling Google Cloud APIs..."
gcloud services enable \
    run.googleapis.com \
        cloudbuild.googleapis.com \
            artifactregistry.googleapis.com \
                firestore.googleapis.com \
                    --project="${PROJECT_ID}" --quiet

                    # Step 2: Create Artifact Registry repository (if not exists)
                    echo "[2/7] Setting up Artifact Registry..."
                    gcloud artifacts repositories describe feagpt \
                        --location="${REGION}" \
                            --project="${PROJECT_ID}" 2>/dev/null || \
                            gcloud artifacts repositories create feagpt \
                                --repository-format=docker \
                                    --location="${REGION}" \
                                        --project="${PROJECT_ID}" \
                                            --description="FeaGPT Docker images"

                                            # Step 3: Configure Docker authentication
                                            echo "[3/7] Configuring Docker authentication..."
                                            gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet

                                            # Step 4: Build Docker image
                                            echo "[4/7] Building Docker image..."
                                            TAG=$(date +%Y%m%d-%H%M%S)
                                            docker build -t "${IMAGE_NAME}:${TAG}" -t "${IMAGE_NAME}:latest" .

                                            # Step 5: Push to Artifact Registry
                                            echo "[5/7] Pushing image to Artifact Registry..."
                                            docker push "${IMAGE_NAME}:${TAG}"
                                            docker push "${IMAGE_NAME}:latest"

                                            # Step 6: Deploy to Cloud Run
                                            echo "[6/7] Deploying to Cloud Run..."
                                            gcloud run deploy "${SERVICE_NAME}" \
                                                --image="${IMAGE_NAME}:${TAG}" \
                                                    --region="${REGION}" \
                                                        --project="${PROJECT_ID}" \
                                                            --platform=managed \
                                                                --memory=4Gi \
                                                                    --cpu=2 \
                                                                        --timeout=600 \
                                                                            --max-instances=10 \
                                                                                --min-instances=0 \
                                                                                    --port=8000 \
                                                                                        --set-env-vars="GEMINI_API_KEY=${GEMINI_KEY}" \
                                                                                            --set-env-vars="FEAGPT_ENV=production" \
                                                                                                --allow-unauthenticated

                                                                                                # Step 7: Get service URL
                                                                                                echo "[7/7] Getting service URL..."
                                                                                                SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" \
                                                                                                    --region="${REGION}" \
                                                                                                        --project="${PROJECT_ID}" \
                                                                                                            --format="value(status.url)")

                                                                                                            echo ""
                                                                                                            echo "========================================="
                                                                                                            echo "  Deployment Complete!"
                                                                                                            echo "========================================="
                                                                                                            echo "Service URL: ${SERVICE_URL}"
                                                                                                            echo "Health:      ${SERVICE_URL}/health"
                                                                                                            echo "API Docs:    ${SERVICE_URL}/docs"
                                                                                                            echo ""
                                                                                                            echo "Test with:"
                                                                                                            echo "  curl ${SERVICE_URL}/health"
                                                                                                            echo "  curl -X POST ${SERVICE_URL}/api/analyze \\"
                                                                                                            echo "    -H 'Content-Type: application/json' \\"
                                                                                                            echo "    -d '{\"description\": \"Analyze a cantilever beam\"}'"
                                                                                                            echo ""

                                                                                                            # Optional: Deploy Firebase hosting
                                                                                                            if command -v firebase &> /dev/null; then
                                                                                                                echo "Deploying Firebase Hosting..."
                                                                                                                    firebase deploy --only hosting --project="${PROJECT_ID}"
                                                                                                                        echo "Firebase Hosting deployed!"
                                                                                                                        fi