from fastapi import APIRouter, HTTPException, Query, Response

from model.private_media import private_media_table
from security.data_encryption import DataEncryptionError


router = APIRouter(
    prefix="/private-media",
    tags=["Private media"],
)


@router.get("/{media_id}", summary="读取短时签名保护的用户图片")
def read_private_media(
    media_id: str,
    expires: int = Query(...),
    signature: str = Query(..., min_length=20),
):
    if not private_media_table.verify_signed_request(media_id, expires, signature):
        raise HTTPException(status_code=403, detail="Private media URL is invalid or expired.")

    try:
        content, content_type = private_media_table.read(media_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Private media not found.")
    except DataEncryptionError:
        raise HTTPException(status_code=500, detail="Private media could not be decrypted.")

    return Response(
        content=content,
        media_type=content_type,
        headers={
            "Cache-Control": "private, max-age=300",
            "X-Content-Type-Options": "nosniff",
        },
    )
