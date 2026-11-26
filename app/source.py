"""Read exactly two configured Azure Parquet parts; no local ingestion engine."""
import io
import os
import re
from hashlib import sha256
from .domain import FIELDS, MAX_ROWS

MAX_BYTES = 8 * 1024 * 1024

def load_batch():
    mode = os.getenv("CORTEX_MODE", "demo")
    if mode == "demo":
        return demo_batch()
    if mode != "azure":
        raise ValueError("CORTEX_MODE must be demo or azure")
    from azure.core import MatchConditions
    from azure.identity import AzureCliCredential, ManagedIdentityCredential
    from azure.storage.blob import BlobServiceClient
    import pyarrow.parquet as pq

    account = os.environ["CORTEX_STORAGE_ACCOUNT"]
    if not re.fullmatch(r"[a-z0-9]{3,24}", account):
        raise ValueError("Invalid storage account name")
    paths = [os.environ["CORTEX_SILVER_PATH"], os.environ["CORTEX_QUARANTINE_PATH"]]
    if any(not p.startswith("nyc311/") or not p.endswith(".parquet") for p in paths):
        raise ValueError("Configure exact nyc311 Parquet blob paths")
    auth = os.getenv("CORTEX_AUTH", "cli")
    if auth not in {"cli", "managed_identity"}:
        raise ValueError("Unsupported authentication mode")
    credential = AzureCliCredential() if auth == "cli" else ManagedIdentityCredential()
    batches, sources = [], []
    try:
        with BlobServiceClient(f"https://{account}.blob.core.windows.net", credential=credential,
                               connection_timeout=10, read_timeout=20, retry_total=1) as service:
            for container, path in zip(("silver", "quarantine"), paths):
                client = service.get_blob_client(container, path)
                props = client.get_blob_properties()
                if not 0 < props.size <= MAX_BYTES:
                    raise ValueError("Blob exceeds the bounded review size; aggregate in Azure first")
                data = client.download_blob(etag=props.etag,
                    match_condition=MatchConditions.IfNotModified, max_concurrency=1).readall()
                if len(data) != props.size:
                    raise ValueError("Unexpected blob length")
                parquet = pq.ParquetFile(io.BytesIO(data))
                if parquet.metadata.num_rows > MAX_ROWS:
                    raise ValueError("Too many records; prepare a bounded review batch in Azure")
                rows = parquet.read(columns=list(FIELDS)).to_pylist()
                batches.append(rows)
                sources.append({"container": container, "path": path, "etag": props.etag,
                                "sha256": sha256(data).hexdigest(), "records": len(rows)})
    finally:
        credential.close()
    return batches[0], batches[1], {"mode": "azure", "sources": sources,
        "scope": "Two explicitly configured historical Parquet parts; not live citywide data."}

def demo_batch():
    """Clearly labeled synthetic example; contains no copied municipal records."""
    def row(key, agency, reason):
        return dict(unique_key=key, agency=agency, complaint_type="Example service",
                    status="Closed", closed_date="2024-01-02" if reason=="VALID" else "",
                    quality_reason=reason)
    return [row("DEMO-1","Agency A","VALID"), row("DEMO-2","Agency B","VALID")], [
        row("DEMO-3","Agency A","CLOSED_WITHOUT_DATE")], {
        "mode": "demo", "sources": [], "scope": "Synthetic example only; not connected to Azure."}
