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
from database.mongo import get_db

router = APIRouter(prefix="/files", tags=["Files"])


@router.get("/{file_id}")
async def get_file(file_id: str):
    if file_id.startswith("local-"):
        path = UPLOAD_DIR / file_id.removeprefix("local-")
        if not path.exists() or not path.is_file():
            raise HTTPException(status_code=404, detail="File not found.")
        return FileResponse(path, media_type="application/pdf", filename=path.name)

    try:
        oid = ObjectId(file_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid file id.")

    db = get_db()
    file_doc = await db.fs.files.find_one({"_id": oid})
    if not file_doc:
        raise HTTPException(status_code=404, detail="File not found.")

    filename = file_doc.get("filename", "document.pdf") or "document.pdf"

    async def _iter_gridfs_chunks():
        async for chunk in db.fs.chunks.find({"files_id": oid}).sort("n", 1):
            data = chunk.get("data")
            if data:
                yield bytes(data)

    headers = {
        "Content-Disposition": f'inline; filename="{filename}"',
        "Accept-Ranges": "none",
    }
    if file_doc.get("length") is not None:
        headers["Content-Length"] = str(file_doc["length"])

    return StreamingResponse(
        _iter_gridfs_chunks(),
        media_type=file_doc.get("metadata", {}).get("contentType", "application/pdf"),
        headers=headers,
    )
