"""nLDT data lake client: filesystem or S3/MinIO backend + DuckDB analytics."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import Any, BinaryIO
from urllib.parse import urlparse

NLDT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FS_ROOT = NLDT_ROOT / "data" / "lake"
DEFAULT_BUCKET = os.environ.get("NLDT_LAKE_BUCKET", "nldt-poc-lake")
DENY_PATH = NLDT_ROOT / "data" / "lake-deny.json"


def lake_backend() -> str:
    return (os.environ.get("NLDT_LAKE_BACKEND") or "fs").lower()


def fs_root() -> Path:
    root = Path(os.environ.get("NLDT_LAKE_FS_ROOT") or DEFAULT_FS_ROOT)
    root.mkdir(parents=True, exist_ok=True)
    return root


def load_deny() -> dict[str, Any]:
    if DENY_PATH.is_file():
        return json.loads(DENY_PATH.read_text(encoding="utf-8"))
    return {}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_lake_uri(uri: str) -> tuple[str, str]:
    """Return (scheme, key) for lake://bucket/key or s3://bucket/key or lake://key."""
    raw = uri.strip()
    if raw.startswith("lake://"):
        rest = raw[len("lake://") :]
        if rest.startswith(DEFAULT_BUCKET + "/"):
            return "lake", rest[len(DEFAULT_BUCKET) + 1 :]
        return "lake", rest
    if raw.startswith("s3://"):
        parsed = urlparse(raw)
        key = parsed.path.lstrip("/")
        return "s3", key
    raise ValueError(f"unsupported lake URI: {uri}")


class LakeClient:
    """Thin object-store facade."""

    def put_file(self, key: str, src: Path, *, metadata: dict[str, str] | None = None) -> str:
        raise NotImplementedError

    def put_bytes(self, key: str, data: bytes, *, content_type: str = "application/octet-stream") -> str:
        raise NotImplementedError

    def get_file(self, key: str, dest: Path) -> Path:
        raise NotImplementedError

    def get_bytes(self, key: str) -> bytes:
        raise NotImplementedError

    def exists(self, key: str) -> bool:
        raise NotImplementedError

    def list_keys(self, prefix: str = "") -> list[str]:
        raise NotImplementedError

    def uri_for(self, key: str) -> str:
        return f"lake://{DEFAULT_BUCKET}/{key.lstrip('/')}"


class FilesystemLakeClient(LakeClient):
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or fs_root()
        (self.root / DEFAULT_BUCKET).mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        return self.root / DEFAULT_BUCKET / key.lstrip("/")

    def put_file(self, key: str, src: Path, *, metadata: dict[str, str] | None = None) -> str:
        dest = self._path(key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(src, dest)
        else:
            shutil.copy2(src, dest)
            if metadata:
                dest.with_suffix(dest.suffix + ".meta.json").write_text(
                    json.dumps(metadata, indent=2), encoding="utf-8"
                )
        return self.uri_for(key)

    def put_bytes(self, key: str, data: bytes, *, content_type: str = "application/octet-stream") -> str:
        dest = self._path(key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return self.uri_for(key)

    def get_file(self, key: str, dest: Path) -> Path:
        src = self._path(key)
        if not src.exists():
            raise FileNotFoundError(key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(src, dest)
        else:
            shutil.copy2(src, dest)
        return dest

    def get_bytes(self, key: str) -> bytes:
        src = self._path(key)
        if not src.is_file():
            raise FileNotFoundError(key)
        return src.read_bytes()

    def exists(self, key: str) -> bool:
        return self._path(key).exists()

    def list_keys(self, prefix: str = "") -> list[str]:
        base = self.root / DEFAULT_BUCKET
        if not base.is_dir():
            return []
        keys: list[str] = []
        for p in base.rglob("*"):
            if p.is_file() and p.name.endswith(".meta.json"):
                continue
            if p.is_file():
                rel = p.relative_to(base).as_posix()
                if rel.startswith(prefix.lstrip("/")):
                    keys.append(rel)
        return sorted(keys)


class S3LakeClient(LakeClient):
    def __init__(self) -> None:
        try:
            import boto3
        except ImportError as exc:
            raise RuntimeError("boto3 required for NLDT_LAKE_BACKEND=s3 (pip install boto3)") from exc
        endpoint = os.environ.get("NLDT_LAKE_ENDPOINT")
        self.bucket = DEFAULT_BUCKET
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=os.environ.get("NLDT_LAKE_ACCESS_KEY", "minioadmin"),
            aws_secret_access_key=os.environ.get("NLDT_LAKE_SECRET_KEY", "minioadmin"),
            region_name=os.environ.get("NLDT_LAKE_REGION", "us-east-1"),
        )
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except Exception:
            self.client.create_bucket(Bucket=self.bucket)

    def put_file(self, key: str, src: Path, *, metadata: dict[str, str] | None = None) -> str:
        if src.is_dir():
            for f in src.rglob("*"):
                if f.is_file():
                    rel = f.relative_to(src).as_posix()
                    self.client.upload_file(str(f), self.bucket, f"{key.rstrip('/')}/{rel}")
        else:
            extra = {"Metadata": metadata or {}}
            self.client.upload_file(str(src), self.bucket, key.lstrip("/"), ExtraArgs=extra if metadata else None)
        return self.uri_for(key)

    def put_bytes(self, key: str, data: bytes, *, content_type: str = "application/octet-stream") -> str:
        self.client.put_object(Bucket=self.bucket, Key=key.lstrip("/"), Body=data, ContentType=content_type)
        return self.uri_for(key)

    def get_file(self, key: str, dest: Path) -> Path:
        dest.parent.mkdir(parents=True, exist_ok=True)
        self.client.download_file(self.bucket, key.lstrip("/"), str(dest))
        return dest

    def get_bytes(self, key: str) -> bytes:
        obj = self.client.get_object(Bucket=self.bucket, Key=key.lstrip("/"))
        return obj["Body"].read()

    def exists(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=key.lstrip("/"))
            return True
        except Exception:
            return False

    def list_keys(self, prefix: str = "") -> list[str]:
        keys: list[str] = []
        token = None
        while True:
            kwargs: dict[str, Any] = {"Bucket": self.bucket, "Prefix": prefix.lstrip("/")}
            if token:
                kwargs["ContinuationToken"] = token
            resp = self.client.list_objects_v2(**kwargs)
            for item in resp.get("Contents") or []:
                keys.append(item["Key"])
            if not resp.get("IsTruncated"):
                break
            token = resp.get("NextContinuationToken")
        return keys

    def uri_for(self, key: str) -> str:
        return f"s3://{self.bucket}/{key.lstrip('/')}"


def get_lake_client() -> LakeClient:
    if lake_backend() == "s3":
        return S3LakeClient()
    return FilesystemLakeClient()


def resolve_uri_to_local(uri: str, *, cache_dir: Path | None = None) -> Path:
    """Resolve file://, lake://, s3:// or plain path to a local Path."""
    if uri.startswith("file://"):
        return Path(urlparse(uri).path)
    if uri.startswith("lake://") or uri.startswith("s3://"):
        _, key = parse_lake_uri(uri)
        client = get_lake_client()
        cache = cache_dir or (NLDT_ROOT / "data" / "lake-cache")
        dest = cache / key
        if isinstance(client, FilesystemLakeClient):
            src = client._path(key)
            if src.is_dir():
                return src
            if src.is_file():
                return src
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists():
            client.get_file(key, dest)
        return dest
    return Path(uri)


def duckdb_connect(readonly: bool = True):
    """Open DuckDB for lake analytics (Parquet/JSON/Iceberg over local lake or S3)."""
    try:
        import duckdb
    except ImportError as exc:
        raise RuntimeError("duckdb required: pip install duckdb") from exc
    con = duckdb.connect(database=":memory:")
    for ext in ("httpfs", "json", "iceberg", "parquet"):
        try:
            con.execute(f"INSTALL {ext}; LOAD {ext};")
        except Exception:
            try:
                con.execute(f"LOAD {ext};")
            except Exception:
                pass
    if lake_backend() == "s3":
        endpoint = os.environ.get("NLDT_LAKE_ENDPOINT", "").replace("http://", "").replace("https://", "")
        key = os.environ.get("NLDT_LAKE_ACCESS_KEY", "minioadmin")
        secret = os.environ.get("NLDT_LAKE_SECRET_KEY", "minioadmin")
        con.execute(f"SET s3_access_key_id='{key}';")
        con.execute(f"SET s3_secret_access_key='{secret}';")
        if endpoint:
            con.execute(f"SET s3_endpoint='{endpoint}';")
            con.execute("SET s3_url_style='path';")
            con.execute("SET s3_use_ssl=false;")
    return con


def register_inventory_view(con, inventory_path: Path | None = None) -> None:
    path = inventory_path or (NLDT_ROOT / "data" / "lake-inventory.json")
    if not path.is_file():
        raise FileNotFoundError(path)
    con.execute(
        f"""
        CREATE OR REPLACE VIEW lake_datasets AS
        SELECT unnest(datasets) AS d
        FROM read_json_auto('{path.as_posix()}', maximum_object_size=33554432)
        """
    )
    con.execute(
        """
        CREATE OR REPLACE VIEW lake_dataset_rows AS
        SELECT
          d.id AS id,
          d.poc AS poc,
          d.zone AS zone,
          d.kind AS kind,
          d.accessClass AS access_class,
          d.lakeKey AS lake_key,
          d.lakeUri AS lake_uri,
          d.localPath AS local_path,
          d.sha256 AS sha256,
          d.bytes AS bytes,
          d.exists AS exists_flag
        FROM lake_datasets
        """
    )


def write_inventory_parquet(inventory_path: Path | None = None, out_path: Path | None = None) -> Path:
    """Materialize inventory datasets as Parquet for DuckDB/Iceberg/dbt."""
    inv = inventory_path or (NLDT_ROOT / "data" / "lake-inventory.json")
    out = out_path or (fs_root() / DEFAULT_BUCKET / "catalog" / "inventory.parquet")
    out.parent.mkdir(parents=True, exist_ok=True)
    data = json.loads(inv.read_text(encoding="utf-8"))
    rows = data.get("datasets") or []
    jl = out.with_suffix(".jsonl")
    with jl.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    con = duckdb_connect()
    con.execute(
        f"COPY (SELECT * FROM read_json_auto('{jl.as_posix()}')) "
        f"TO '{out.as_posix()}' (FORMAT PARQUET)"
    )
    return out
