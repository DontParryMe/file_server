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

@asynccontextmanager
async def lifespan(app: FastAPI):
    await database.connect()
    await create_tables()
    yield
    await database.disconnect()


app = FastAPI(lifespan=lifespan)

database = Database(os.environ['DATABASE_URL'])

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session

@app.post("/upload/")
async def upload_file(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    file_content = await file.read()

    db_file = UploadedFile(
        filename=file.filename,
        content=file_content,
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

    file_like = BytesIO(db_file.content)
    file_like.seek(0)

    filename = urllib.parse.quote(db_file.filename)

    return StreamingResponse(
        file_like, media_type=db_file.content_type,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"}
    )
