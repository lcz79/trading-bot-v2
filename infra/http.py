import requests
from requests.adapters import HTTPAdapter, Retry

DEFAULT_TIMEOUT = (5, 20)  # (connect, read) in secondi

def new_session():
    s = requests.Session()

    retries = Retry(
        total=4,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"]
    )

    adapter = HTTPAdapter(max_retries=retries, pool_connections=20, pool_maxsize=20)
    s.mount("https://", adapter)
    s.mount("http://", adapter)

    s.headers.update({"Connection": "keep-alive"})
    return s
