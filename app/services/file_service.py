# app/services/file_service.py

import io
from minio import Minio
from minio.error import S3Error
from werkzeug.datastructures import FileStorage

MINIO_ENDPOINT = "host.docker.internal:9000"
MINIO_ACCESS_KEY = "root"
MINIO_SECRET_KEY = "xiao1234"
MINIO_BUCKET = "doc-llm-bucket"
MINIO_SECURE = False

_minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=MINIO_SECURE,
)


def _ensure_bucket():
    """确保 bucket 存在"""
    if not _minio_client.bucket_exists(MINIO_BUCKET):
        _minio_client.make_bucket(MINIO_BUCKET)


def save_task_file(task_id: int, file_obj: FileStorage) -> str:
    """
    把用户上传的文件存到 MinIO，文件名格式：{task_id}_{orig_filename}
    返回存入数据库的 doc 字段值，例如：minio://doc-llm-bucket/123_xxx.docx
    """
    _ensure_bucket()

    orig_filename = file_obj.filename or "unknown"
    object_name = f"{task_id}_{orig_filename}"

    # 处理文件流和大小
    data_bytes = file_obj.read()
    size = len(data_bytes)
    data = io.BytesIO(data_bytes)

    if size is None:
        data_bytes = file_obj.read()
        size = len(data_bytes)
        data = io.BytesIO(data_bytes)

    try:
        _minio_client.put_object(
            MINIO_BUCKET,
            object_name,
            data,
            size,
            content_type=file_obj.mimetype,
        )
    except S3Error as e:
        raise RuntimeError(f"upload file to minio failed: {e}") from e

    # 存到数据库里的 doc 字段，用这个固定格式
    doc_path = f"minio://{MINIO_BUCKET}/{object_name}"
    return doc_path


def download_file(bucket: str, object_name: str) -> bytes:
    """
    从 MinIO 下载文件并返回 bytes 内容。

    调用方式：
        content = download_file("doc-llm-bucket", "15_readme.txt")
        text = content.decode("utf-8")
    """
    try:
        response = _minio_client.get_object(bucket, object_name)
        data = response.read()
        return data
    except S3Error as e:
        raise RuntimeError(f"Download from minio failed: {e}") from e