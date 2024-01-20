import os, json, sys, argparse, warnings
import requests

from google.cloud import aiplatform
from google.cloud.aiplatform import Endpoint, Model
from google.api_core.exceptions import InvalidArgument
from google.oauth2 import service_account
import google.auth.transport.requests

KEY_FILE_PATH = "credentials.json"

MODEL_NAME = "s2dr3"
PROJECT_NAME = "s2dr3-202312"
LOCATION = "us-central1"

IMG_URI = "gcr.io/s2dr3-202312/s2dr3:success-1"

PREDICT_PATH = "/predict"
HEALTH_PATH = "/health"
SERVER_PORT = 8080

ENDPOINT_NAME = "s2dr3-endpoint"

warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--datapath', type=str, default='/content/datapath', help='Input image or folder')
    parser.add_argument('--savepath', type=str, default='/content/savepath', help='Output image or folder')
    parser.add_argument('--logpath', type=str, default='/content/logpath', help='Path for logging')
    parser.add_argument('-f', '--force', action='store_true', help="force reprocessing")
    parser.add_argument('-g', '--coreg', action='store_true', help="georeference fo ESRI basmap")
    parser.add_argument('-d', '--debug', action='store_true', help='print debugging messages')
    parser.add_argument('-q', '--quiet', action='store_true', help='run quiet')
    parser.add_argument('-s', '--simulate', action='store_true', help='process a small simulation patch')
    parser.add_argument('-p', '--make_preview', action='store_true', help='Generate and publish preview')
    parser.add_argument('--date', type=str, default=None, help='Date')
    parser.add_argument('--date_range', nargs='+', default=None, help='Date range')
    parser.add_argument('--b10m10', type=str, default=None, help='Direct path of the input S2L2A 10-band image')
    #parser.add_argument('--S2_bias', action='store_true', help='Indicate if S2L2A +1000 bias has been applied')
    parser.add_argument('--aoi', nargs='+', default=None, help='AOI')
    parser.add_argument('--mgrs', type=str, default=None, help='MGRS tile')
    parser.add_argument('--iso', type=str, default=None, help='Country 2-digit ISO code')
    parser.add_argument('--NM', nargs='+', default=None, help='Indices of MGRS subsubtile [0..9 0..9]')
    parser.add_argument('--UV', nargs='+', default=None, help='Indices of MGRS subtile [0..2 0..2]')
    parser.add_argument('--bands_out', nargs='+', default=None, help='Spectral bands to generate in Sentinel-2 notation')
    parser.add_argument('--tile', type=int, default=480, help='Size of the processing tile')
    parser.add_argument('-b', '--batch', type=int, default=1, help='Batch size (only b=1 is supported)')

    args = parser.parse_args()

    request_data = {}
    if args.datapath != "/content/datapath":
        request_data["datapath"] = args.datapath
    if args.savepath != "/content/savepath":
        request_data["savepath"] = args.savepath
    if args.logpath != "/content/logpath":
        request_data["logpath"] = args.logpath
    if args.force != False:
        request_data["force"] = "True"
    if args.coreg != False:
        request_data["coreg"] = "True"
    if args.debug != False:
        request_data["debug"] = "True"
    if args.quiet != False:
        request_data["quiet"] = "True"
    if args.simulate != False:
        request_data["simulate"] = "True"
    if args.make_preview != False:
        request_data["make_preview"] = "True"
    if args.date != None:
        request_data["date"] = args.date
    if args.date_range !=None:
        request_data["date_range"] = args.date_range[0] + " "+ args.date_range[1]
    if args.b10m10 != None:
        request_data["b10m10"] = args.b10m10
    if args.aoi != None:
        aoi_str = ""
        for item in args.aoi:
            aoi_str = aoi_str + item + " "
        request_data["aoi"] = aoi_str
    if args.mgrs != None:
        request_data["mgrs"] = args.mgrs
    if args.iso != None:
        request_data["iso"] = args.iso
    if args.NM != None:
        NM_str = ""
        for item in args.NM:
            NM_str = NM_str + item + " "
        request_data["NM"] = NM_str
    if args.UV != None:
        UV_str = ""
        for item in args.UV:
            UV_str = UV_str + item + " "
        request_data["UV"] = UV_str
    if args.bands_out != None:
        bands_out_str = ""
        for item in args.bands_out:
            bands_out_str = bands_out_str + item + " "
        request_data["bands_out"] = bands_out_str
    if args.tile != 480:
        request_data["tile"] = str(args.tile)
    if args.batch != 1:
        request_data["batch"] = str(args.batch)

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
            serving_container_ports = [SERVER_PORT],
            sync = True,
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

        print(f"\nDeplyoing model - {MODEL_NAME} to endpoint - {ENDPOINT_NAME}.It will take about 20~30 mins. ...\n")

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

    print("Started to get the result ...")

    SCOPES = ['https://www.googleapis.com/auth/cloud-platform']

    creds = service_account.Credentials.from_service_account_file(KEY_FILE_PATH, scopes=SCOPES)
    request = google.auth.transport.requests.Request()
    creds.refresh(request)
    access_token = creds.token

    endpoint_resource_name = endpoint.resource_name
    arr = endpoint_resource_name.split("/")

    PROJECT_ID = "862134799361"
    ENDPOINT_ID = arr[5]

    url = f"https://us-central1-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/us-central1/endpoints/{ENDPOINT_ID}:predict"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    infer_request = {
        "instances": [
            request_data
        ]
    }

    response = requests.post(url, headers=headers, data=json.dumps(infer_request))

    result = json.loads(response.text)
    msg = result["error"]["message"]

    split_message = msg.split(",")
    print("\n\n")
    print(split_message[2])

    print("\n\n")
    is_continue = input("Do you keep the Vertex AI endpoint alive? Press y(yes) or n(no): ")

    if is_continue == 'n' or is_continue == 'no':
        endpoint.undeploy_all()
        endpoint.delete()
        model.delete()

if __name__ == "__main__":
    main()