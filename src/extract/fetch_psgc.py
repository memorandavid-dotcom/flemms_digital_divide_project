"""Source 2: official region names from the PSGC API (REST, JSON).

The survey only stores numeric region codes. This module downloads the
Philippine Standard Geographic Code (PSGC) region list so the curated layer
can attach official region names instead of a hand-typed mapping.

The response is saved unchanged in data/raw/psgc/ (raw layer), together with
a small metadata file recording when and where it was retrieved.
"""
import time

import requests

from src.config import layer_path, psgc_base_url, settings
from src.utils.io_utils import read_json, utc_now, write_json
from src.utils.logging_utils import get_logger

log = get_logger(__name__)

REQUIRED_KEYS = {"code", "name", "regionName", "psgc10DigitCode"}


def _validate_payload(payload) -> None:
    """Fail fast if the API returns something that is not a region list."""
    if not isinstance(payload, list) or not payload:
        raise ValueError("PSGC API returned an empty or non-list response")
    missing = REQUIRED_KEYS - set(payload[0])
    if missing:
        raise ValueError(f"PSGC API response is missing fields: {sorted(missing)}")
    minimum = settings()["sources"]["psgc_regions"]["min_records"]
    if len(payload) < minimum:
        raise ValueError(f"PSGC API returned {len(payload)} regions, expected at least {minimum}")


def fetch_regions(batch_id: str, attempts: int = 3, timeout: int = 20) -> dict:
    """Download the region list. Returns metadata about the snapshot used."""
    source = settings()["sources"]["psgc_regions"]
    url = psgc_base_url() + source["endpoint"]
    out_dir = layer_path("raw") / source["folder"]
    data_file = out_dir / "regions.json"
    meta_file = out_dir / "regions.meta.json"

    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            log.info("Requesting %s (attempt %d/%d)", url, attempt, attempts)
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            payload = response.json()
            _validate_payload(payload)
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            log.warning("PSGC request failed: %s", exc)
            if attempt < attempts:
                time.sleep(2 ** attempt)
            continue

        write_json(payload, data_file)
        meta = {
            "source": "PSGC API",
            "url": url,
            "retrieved_at": utc_now(),
            "batch_id": batch_id,
            "records": len(payload),
            "status": "fresh",
        }
        write_json(meta, meta_file)
        log.info("Saved %d regions to %s", len(payload), data_file)
        return meta

    # The API is down: reuse the last good snapshot so the pipeline can still run,
    # but say so loudly in the logs and in the metadata.
    if data_file.exists() and meta_file.exists():
        meta = read_json(meta_file)
        meta["status"] = "cached"
        log.warning("PSGC API unavailable (%s). Using cached snapshot from %s",
                    last_error, meta.get("retrieved_at"))
        return meta
    raise RuntimeError(f"PSGC API unavailable and no cached snapshot exists: {last_error}")
