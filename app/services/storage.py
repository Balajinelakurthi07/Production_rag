import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from typing import BinaryIO, Tuple
import uuid

from app.config import settings


class StorageService:
    """Handles object storage interactions (S3 / Scality / MinIO)."""

    def __init__(self):
        self.s3_client = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )
        self.bucket_name = settings.S3_BUCKET_NAME
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self) -> None:
        """Creates the bucket if it doesn't already exist."""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
        except ClientError:
            try:
                self.s3_client.create_bucket(Bucket=self.bucket_name)
            except Exception as e:
                print(f"Warning: Could not create S3 bucket '{self.bucket_name}': {e}")

    def upload_file(
        self,
        file_obj: BinaryIO,
        filename: str,
        department_id: uuid.UUID,
        content_type: str = "application/octet-stream",
    ) -> Tuple[str, str]:
        """
        Uploads a raw document to S3 with a structured key:
        `departments/{dept_id}/{uuid}_{filename}`
        Returns: (s3_key, s3_uri)
        """
        unique_id = uuid.uuid4().hex[:8]
        s3_key = f"departments/{department_id}/{unique_id}_{filename}"

        self.s3_client.upload_fileobj(
            file_obj,
            self.bucket_name,
            s3_key,
            ExtraArgs={"ContentType": content_type},
        )

        s3_uri = f"s3://{self.bucket_name}/{s3_key}"
        return s3_key, s3_uri


storage_service = StorageService()

