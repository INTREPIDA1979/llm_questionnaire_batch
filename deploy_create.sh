#/bin/sh
# set environment valiables
PROJECT_ID=uragasumi25-llm-app-pj
REGION=asia-northeast1
AR_REPO=llm-questionnaire-batch
SERVICE_NAME=llm-questionnaire-batch
SA_NAME=sa-llm-app
DB_USER=root
DB_PASS=1234abcd!
DB_NAME=llm-app-db
INSTANCE_NAME=llm-app-db
INSTANCE_CONNECTION_NAME='uragasumi25-llm-app-pj:asia-northeast1:llm-app-db'
GOOGLE_AI='GEMINI'
#GOOGLE_AI='VERTEX_AI'
GOOGLE_API_KEY='AIzaSyAl57m8ECZw-JfuWzec_EI8ft1IszppBPs'

# Artifacts repositories 作成 #最初の1回だけ…
# gcloud artifacts repositories create $AR_REPO \
#   --location=$REGION \
#   --repository-format=Docker \
#   --project=$PROJECT_ID

# PUSH to Artifact Registry
gcloud builds submit --tag $REGION-docker.pkg.dev/$PROJECT_ID/$AR_REPO/$SERVICE_NAME \
  --project=$PROJECT_ID

# create to Cloud Run
gcloud run jobs create llm-questionnaire-batch \
 --image $REGION-docker.pkg.dev/$PROJECT_ID/$AR_REPO/$SERVICE_NAME \
 --service-account=$SA_NAME@$PROJECT_ID.iam.gserviceaccount.com \
 --region=$REGION \
 --set-env-vars=PROJECT_ID=$PROJECT_ID,LOCATION=$REGION \
 --project=$PROJECT_ID \
 --tasks=1 \
 --cpu=1 \
 --max-retries=0 \
 --memory=512Mi \
 --parallelism=1 \
 --task-timeout=100 \
 --set-env-vars INSTANCE_CONNECTION_NAME=$INSTANCE_CONNECTION_NAME \
 --set-env-vars DB_USER=$DB_USER \
 --set-env-vars DB_PASS=$DB_PASS \
 --set-env-vars DB_NAME=$DB_NAME \
 --set-env-vars GOOGLE_AI=$GOOGLE_AI \
  --set-env-vars GOOGLE_API_KEY=$GOOGLE_API_KEY

gcloud run jobs execute llm-questionnaire-batch --region=asia-northeast1