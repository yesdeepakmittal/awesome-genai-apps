# ADK agent on Cloud Run (Vertex AI)

Deploy the FastAPI + Google ADK agent to Cloud Run and call Gemini through Vertex AI. Use the steps below so you do not have to attach roles in the Google Cloud console.

## What you need first

- [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) (`gcloud`) installed and on your `PATH`.
- A GCP project where you can enable APIs and change IAM.
- Billing enabled on the project if required for Vertex AI and Cloud Run.

Set your project and region once per shell session (replace the values):

```bash
export PROJECT_ID="your-project-id"
export REGION="us-central1"
gcloud config set project "$PROJECT_ID"
```

Resolve the project number (used in default service account emails):

```bash
export PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"
```

## 1. Enable APIs

Cloud Run, Cloud Build, Container Registry (for `gcr.io` images), and Vertex AI must be turned on for the project:

```bash
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  containerregistry.googleapis.com \
  aiplatform.googleapis.com \
  --project="$PROJECT_ID"
```

## 2. Grant IAM to the Cloud Run runtime service account (no console)

Cloud Run uses a **service account** at runtime. If you do not pass `--service-account` on deploy, Google uses the **Compute Engine default service account**:

`{PROJECT_NUMBER}-compute@developer.gserviceaccount.com`

Give that account the roles Vertex needs. You can add more role IDs to the `ROLES` list if your agent uses other products (for example Secret Manager or BigQuery).

```bash
RUNTIME_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

ROLES=(
  "roles/aiplatform.user"   # Vertex AI: models, endpoints, generative requests
)

for ROLE in "${ROLES[@]}"; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${RUNTIME_SA}" \
    --role="$ROLE" \
    --condition=None
done
```

If you deploy with a **custom** service account, replace `RUNTIME_SA` with that email (for example `adk-runner@YOUR_PROJECT_ID.iam.gserviceaccount.com`) and run the same loop.

To confirm bindings:

```bash
gcloud projects get-iam-policy "$PROJECT_ID" \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:${RUNTIME_SA}" \
  --format="table(bindings.role)"
```

## 3. Optional: Cloud Build can push to `gcr.io`

`gcloud builds submit` runs as the **Cloud Build** service account:

`{PROJECT_NUMBER}@cloudbuild.gserviceaccount.com`

If the build fails when pushing the image, grant that account access to the project’s Container Registry storage (typical fix for new projects):

```bash
CLOUD_BUILD_SA="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${CLOUD_BUILD_SA}" \
  --role="roles/storage.admin" \
  --condition=None
```

Use a narrower custom role or bucket-level IAM if your organization restricts project-wide Storage Admin.

## 4. Local development credentials

For local runs (for example `uvicorn` with Vertex), use Application Default Credentials:

```bash
gcloud auth application-default login
```

## 5. Build the container image

```bash
gcloud builds submit --tag "gcr.io/${PROJECT_ID}/adk-agent" --project="$PROJECT_ID"
```

## 6. Deploy to Cloud Run

Point `GOOGLE_CLOUD_PROJECT` and `GOOGLE_CLOUD_LOCATION` at your project and Vertex region. The example allows unauthenticated access to the service; remove `--allow-unauthenticated` if you want IAM-only access.

```bash
gcloud run deploy adk-agent \
  --image "gcr.io/${PROJECT_ID}/adk-agent" \
  --platform managed \
  --region "$REGION" \
  --allow-unauthenticated \
  --set-env-vars "GOOGLE_GENAI_USE_VERTEXAI=TRUE,GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GOOGLE_CLOUD_LOCATION=${REGION}" \
  --project="$PROJECT_ID"
```

## 7. Run the API locally (optional)

```bash
uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

---

### Quick reference: one-off `add-iam-policy-binding` (copy and edit)

Grant a single role to the default Compute service account:

```bash
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/aiplatform.user"
```

Replace `--member` with your custom runtime service account if you use one.
