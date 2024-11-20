import os
import urllib
from contextlib import asynccontextmanager
from io import BytesIO

from databases import Database
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import StreamingResponse

from app.database import create_tables, AsyncSessionLocal
from app.models.files_table import UploadedFile
import urllib.parse

from app.utils import get_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await database.connect()
    await create_tables()
    yield
    await database.disconnect()


app = FastAPI(lifespan=lifespan)

database = Database(os.environ['DATABASE_URL'])

@app.post("/upload/")
async def upload_file(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    chunk_size = 1024 * 1024
    content = bytearray()

    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        content.extend(chunk)

    db_file = UploadedFile(
        filename=file.filename,
        content=bytes(content),
        content_type=file.content_type
    )

    db.add(db_file)
    await db.commit()
    await db.refresh(db_file)

    return {
        "id": db_file.id,
        "filename": db_file.filename,
        "content_type": db_file.content_type,
        "uploaded_at": db_file.uploaded_at
    }


@app.get("/download/{file_id}")
async def download_file(file_id: int, db: AsyncSession = Depends(get_db)):
    query = select(UploadedFile).filter(UploadedFile.id == file_id)
    result = await db.execute(query)
    db_file = result.scalar_one_or_none()

    if db_file is None:
        raise HTTPException(status_code=404, detail="File not found")

    filename = urllib.parse.quote(db_file.filename)

    async def file_iterator(content: bytes, chunk_size: int = 1024 * 1024):
        start = 0
        while start < len(content):
            end = min(start + chunk_size, len(content))
            yield content[start:end]
            start = end

    return StreamingResponse(
        file_iterator(db_file.content),
        media_type=db_file.content_type,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"}
    )
