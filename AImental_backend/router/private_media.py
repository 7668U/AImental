from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field

from model.private_media import private_media_table
from security.data_encryption import DataEncryptionError
from .auth import get_current_user_id


router = APIRouter(
    prefix="/private-media",
    tags=["Private media"],
)


class DirectUploadRequest(BaseModel):
    media_type: str = Field(pattern="^(avatar|checkin)$")
    content_type: str
    size: int = Field(gt=0)


@router.post("/uploads", summary="Prepare a private COS direct upload")
def prepare_direct_upload(
    payload: DirectUploadRequest,
    current_user_id: str = Depends(get_current_user_id),
):
    try:
        return private_media_table.prepare_direct_upload(
            owner_user_id=current_user_id,
            media_type=payload.media_type,
            content_type=payload.content_type,
            size=payload.size,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/{media_id}", summary="Read a signed private media object")
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
