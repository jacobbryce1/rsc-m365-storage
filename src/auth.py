"""
RSC OAuth2 Authentication Module
==================================
Obtains a short-lived Bearer token from the RSC service account endpoint.

Security hardening (v2.1):
- TLS certificate verification always enabled
- Token never written to disk or logged
- Explicit request timeout
- Validates HTTP response before returning token
- Exception messages omit credential values
"""

import logging
import os
import requests

logger = logging.getLogger(__name__)

# CA bundle override (e.g. for corporate proxies with custom CAs)
_CA_BUNDLE = os.getenv("RSC_CA_BUNDLE", True)


def get_access_token(rsc_url: str, client_id: str, client_secret: str) -> str:
    """
    Authenticate against RSC using OAuth2 client-credentials flow.

    Parameters
    ----------
    rsc_url:       Base URL, e.g. 'https://myorg.my.rubrik.com'
    client_id:     Service account client ID (UUID string)
    client_secret: Service account client secret

    Returns
    -------
    Bearer token string (short-lived; do not cache or persist).

    Raises
    ------
    requests.HTTPError   – on 4xx/5xx response
    requests.exceptions.SSLError – if TLS verification fails
    ValueError           – if the response body is missing the access_token field
    """
    token_url = f"{rsc_url}/api/client_token"

    try:
        resp = requests.post(
            token_url,
            json={"client_id": client_id, "client_secret": client_secret},
            headers={"Content-Type": "application/json"},
            timeout=30,
            verify=_CA_BUNDLE,          # TLS verification – never disabled
        )
        resp.raise_for_status()         # raises HTTPError on 4xx/5xx
    except requests.exceptions.SSLError as exc:
        # Do not include URL (might contain creds if mis-configured)
        raise requests.exceptions.SSLError(
            "TLS certificate verification failed connecting to RSC. "
            "If you are behind a corporate proxy, set RSC_CA_BUNDLE to "
            "the path of your CA bundle file."
        ) from exc
    except requests.exceptions.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "?"
        # Never log client_id or client_secret
        raise requests.exceptions.HTTPError(
            f"Authentication failed (HTTP {status}). "
            "Check RSC_CLIENT_ID and RSC_CLIENT_SECRET in your .env file."
        ) from exc

    body = resp.json()
    token = body.get("access_token")
    if not token:
        raise ValueError(
            "RSC returned an unexpected authentication response. "
            f"Fields present: {list(body.keys())}"
        )
    return token