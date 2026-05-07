"""
routes/files.py
---------------
Serves PDFs stored in MongoDB GridFS.
- GET /files/{file_id} -> stream PDF bytes
"""

from bson import ObjectId
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from fastapi.responses import StreamingResponse

from database.local_store import UPLOAD_DIR
from database.mongo import get_fs

router = APIRouter(prefix="/files", tags=["Files"])


@router.get("/{file_id}")
async def get_file(file_id: str):
    if file_id.startswith("local-"):
        path = UPLOAD_DIR / file_id.removeprefix("local-")
        if not path.exists() or not path.is_file():
            raise HTTPException(status_code=404, detail="File not found.")
        return FileResponse(path, media_type="application/pdf", filename=path.name)

    fs = get_fs()
    try:
        oid = ObjectId(file_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid file id.")

    try:
        grid_out = await fs.open_download_stream(oid)
    except Exception:
        raise HTTPException(status_code=404, detail="File not found.")

    async def _iterfile():
        # Motor's read_chunk() can return an empty stream on some deployments.
        # read() is reliable here and PDFs are already bounded by upload size.
        data = await grid_out.read()
        if data:
            yield data

    filename = getattr(grid_out, "filename", "document.pdf") or "document.pdf"
    return StreamingResponse(
        _iterfile(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )
