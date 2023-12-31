import time
from fastapi import FastAPI, HTTPException, Response
from prometheus_client import make_asgi_app, Counter, Gauge, Histogram
import threading
import random
import os


version = os.getenv("VERSION", "v3.0.0")
HEALTH = 200

app = FastAPI()

# ***** Prometheus metrics *****
EIGEN_FEES_EARNED_TOTAL = Counter(
    'eigen_fees_earned_total',
    'The amount of fees earned in <token>',
    labelnames=["avs_name", "token"]
)
EIGEN_SLASHING_INCURRED_TOTAL = Counter(
    'eigen_slashing_incurred_total',
    'The amount of slashing incurred in <token>',
    labelnames=["avs_name", "token"]
)
EIGEN_BALANCE_TOTAL = Gauge(
    'eigen_balance_total',
    'Node total balance in <token>',
    labelnames=["avs_name", "token"]
)
EIGEN_PERFORMANCE_SCORE = Gauge(
    'eigen_performance_score',
    'The performance metric is a score between 0 and 100 and each developer can define their own way of calculating the score. The score is calculated based on the performance of the Node and the performance of the backing services.',
    labelnames=["avs_name"]
)
EIGEN_RPC_REQUEST_DURATION_SECONDS = Histogram(
    'eigen_rpc_request_duration_seconds',
    'Duration of json-rpc <method> in seconds',
    labelnames=["avs_name", "method", "client", "version"]
)
EIGEN_RPC_REQUEST_TOTAL = Counter(
    'eigen_rpc_request_total',
    'Total of json-rpc <method> requests',
    labelnames=["avs_name", "method", "client", "version"]
)
EIGEN_VERSION = Gauge(
    'eigen_version',
    'Version metadata',
    labelnames=["avs_name", "commit", "runtime", "version", "spec_version"]
).labels(avs_name="mock-avs", commit="84391eb8d93bd3aa0d94c530f3b9bba15ae72cdc", runtime="python", version=version, spec_version="v0.1.0")

app.mount("/metrics", make_asgi_app())
# ***** Prometheus metrics *****


@app.get("/option/{option_target}")
def get_option(option_target: str):
    # Get option from env
    option = os.getenv(option_target)
    if not option:
        raise HTTPException(status_code=404, detail="Option target not found")
    return {"option_value": option}


@app.post("/health/{status_code}")
def update_health(status_code: int):
    global HEALTH
    if status_code not in [200, 206, 503]:
        raise HTTPException(status_code=400, detail="Invalid status code")
    HEALTH = status_code


@app.get("/eigen/node/spec-version")
def get_spec_version():
    return {"api_version": "v1.0.0"}


@app.get("/eigen/node/version")
def get_version():
    return {"version": version}


@app.get("/eigen/node/health", status_code=200)
def get_health(response: Response):
    response.status_code = HEALTH


@app.get("/eigen/node/services")
def get_services():
    return {"services": [
        {
            "id": "db-1",
            "name": "Database",
            "description": "Database description",
            "status": "Up",
        },
        {
            "id": "idx-2",
            "name": "Indexer",
            "description": "Indexer description",
            "status": "Down",
        }
    ]}


@app.get("/eigen/node/services/{service_id}/health")
def get_service_health(service_id: str, response: Response):
    if service_id == "db-1":
        response.status_code = 200
    elif service_id == "idx-2":
        response.status_code = 503
    else:
        raise HTTPException(status_code=404, detail="Service not found")


class BackgroundTasks(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        self.eth_balance = 32
        self.egn_balance = 50

    def run(self) -> None:
        while True:
            earned_eth = random.random()
            slashing_eth = random.random()*0.1
            self.eth_balance += earned_eth - slashing_eth
            earned_egn = random.random()
            slashing_egn = random.random()*0.1
            self.egn_balance += earned_egn - slashing_egn

            EIGEN_FEES_EARNED_TOTAL.labels(
                avs_name="mock-avs",
                token="ETH"
            ).inc(earned_eth)
            EIGEN_FEES_EARNED_TOTAL.labels(
                avs_name="mock-avs",
                token="EGN"
            ).inc(earned_egn)
            EIGEN_SLASHING_INCURRED_TOTAL.labels(
                avs_name="mock-avs",
                token="ETH"
            ).inc(slashing_eth)
            EIGEN_SLASHING_INCURRED_TOTAL.labels(
                avs_name="mock-avs",
                token="EGN"
            ).inc(slashing_egn)
            EIGEN_BALANCE_TOTAL.labels(
                avs_name="mock-avs",
                token="ETH"
            ).set(self.eth_balance)
            EIGEN_BALANCE_TOTAL.labels(
                avs_name="mock-avs",
                token="EGN"
            ).set(self.egn_balance)
            EIGEN_PERFORMANCE_SCORE.labels(
                avs_name="mock-avs"
            ).set(random.randint(80, 100))
            EIGEN_RPC_REQUEST_DURATION_SECONDS.labels(
                avs_name="mock-avs",
                method="eth_getBlockByNumber",
                client="nethermind",
                version="1.19.0"
            ).observe(random.random()*0.3)
            EIGEN_RPC_REQUEST_TOTAL.labels(
                avs_name="mock-avs",
                method="eth_getBlockByNumber",
                client="nethermind",
                version="1.19.0"
            ).inc(1)
            EIGEN_RPC_REQUEST_DURATION_SECONDS.labels(
                avs_name="mock-avs",
                method="eth_call",
                client="nethermind",
                version="1.19.0"
            ).observe(random.random()*0.5)
            EIGEN_RPC_REQUEST_TOTAL.labels(
                avs_name="mock-avs",
                method="eth_call",
                client="nethermind",
                version="1.19.0"
            ).inc(1)
            time.sleep(5)


@app.on_event("startup")
async def startup_event():
    t = BackgroundTasks()
    t.start()
