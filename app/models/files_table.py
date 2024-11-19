from sqlalchemy import Column, Integer, String, TIMESTAMP, LargeBinary, func

from app.database import Base


class UploadedFile(Base):
    __tablename__ = "files"

    id = Column(Integer, primary_key=True, index=True)  # Уникальный идентификатор
    filename = Column(String(255), nullable=False)      # Имя файла
    content = Column(LargeBinary, nullable=False)       # Содержимое файла
    content_type = Column(String(255))                  # MIME-тип файла
    uploaded_at = Column(TIMESTAMP, default=func.now()) # Время загрузки
