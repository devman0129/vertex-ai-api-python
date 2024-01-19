from google.cloud import aiplatform
from google.cloud.aiplatform import Endpoint, Model
from google.api_core.exceptions import InvalidArgument
from google.oauth2 import service_account

MODEL_NAME = "s2dr3"
PROJECT_NAME = "s2dr3-202312"

LOCATION = "us-central1"
ENDPOINT_NAME = "endpoint_detector"

credentials = service_account.Credentials.from_service_account_file('credentials.json')

aiplatform.init(
    project = PROJECT_NAME,
    location = LOCATION,
    credentials = credentials
)

print("Checking imported model ...")

models = Model.list(filter=f'displayName="{MODEL_NAME}"')

if models:
    model = models[0]
    print(f"Model - {MODEL_NAME} was already imported successfully!")

else:
    print(f"Model - {MODEL_NAME} was not detected. Started importing from container registry ...")
    model = aiplatform.Model.upload(
        display_name=MODEL_NAME,
        serving_container_image_uri="gcr.io/s2dr3-202312/s2dr3:success-1",
        serving_container_predict_route="/predict",
        serving_container_health_route="/health",
        serving_container_ports=[8080],
        sync=True,
    )
    model.wait()
