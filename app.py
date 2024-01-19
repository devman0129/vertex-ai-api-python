from google.cloud import aiplatform
from google.cloud.aiplatform import Endpoint, Model
from google.api_core.exceptions import InvalidArgument
from google.oauth2 import service_account

KEY_FILE_PATH = "credentials.json"

MODEL_NAME = "s2dr3"
PROJECT_NAME = "s2dr3-202312"
LOCATION = "us-central1"

IMG_URI = "gcr.io/s2dr3-202312/s2dr3:success-1"

PREDICT_PATH = "/predict"
HEALTH_PATH = "/health"
SERVER_PORT = 8080

ENDPOINT_NAME = "s2dr3-endpoint"

credentials = service_account.Credentials.from_service_account_file(KEY_FILE_PATH)

aiplatform.init(
    project = PROJECT_NAME,
    location = LOCATION,
    credentials = credentials
)

print("\nChecking models ...\n")

models = Model.list(filter=f'displayName="{MODEL_NAME}"')

if models:
    model = models[0]
    print(f"\nModel - {MODEL_NAME} was already imported successfully!\n")

else:
    print(f"\nModel - {MODEL_NAME} was not detected. Started importing from container registry ...\n")
    model = aiplatform.Model.upload(
        display_name = MODEL_NAME,
        serving_container_image_uri = IMG_URI,
        serving_container_predict_route = PREDICT_PATH,
        serving_container_health_route = HEALTH_PATH,
        serving_container_ports=[SERVER_PORT],
        sync=True,
    )
    model.wait()
    print(f"\nModel - {MODEL_NAME} was imported successfully!\n")

print("\nChecking endpoints ...\n")

endpoints = Endpoint.list(filter=f'displayName="{ENDPOINT_NAME}"')

if endpoints:
    endpoint = endpoints[0]
    print(f"\nEndpoint - {ENDPOINT_NAME} was already created successfully!\n")
else:
    print(f"\nEndpoint {ENDPOINT_NAME} doesn't exist, creating ...\n")
    endpoint = aiplatform.Endpoint.create(display_name=ENDPOINT_NAME)
    print(f"\nEndpoint - {ENDPOINT_NAME} was created successfully!\n")

    print(f"\nDeplyoing model - {MODEL_NAME} to endpoint - {ENDPOINT_NAME} ...\n")

    model.deploy(
        endpoint = endpoint,
        deployed_model_display_name = MODEL_NAME,
        traffic_percentage = 100,
        machine_type = "n1-standard-2",
        min_replica_count = 1,
        max_replica_count = 1,
        accelerator_type = "NVIDIA_TESLA_T4",
        accelerator_count = 1,
        sync = True,
    )

    print("\nModel deployed - complete!\n")

endpoint.undeploy_all()
endpoint.delete()
model.delete()