from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()

class Video(Base):
    __tablename__ = "videos"
    
    id = Column(Integer, primary_key=True, index=True)
    source_platform = Column(String(50), nullable=False)  # tiktok, youtube
    source_id = Column(String(100), unique=True, nullable=False)
    source_url = Column(String(500), nullable=False)
    
    # Metadados originais
    title = Column(String(500))
    author = Column(String(200))
    hashtags = Column(Text)  # JSON string
    views = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    
    # Processamento
    status = Column(String(50), default="collected")  # collected, processed, published
    local_path = Column(String(500))  # Caminho do arquivo original
    processed_path = Column(String(500))  # Caminho do arquivo processado
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)

class Publication(Base):
    __tablename__ = "publications"
    
    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, nullable=False)  # FK para Video
    platform = Column(String(50), nullable=False)  # instagram, tiktok, youtube
    
    # Dados da publicação
    platform_post_id = Column(String(100))
    post_url = Column(String(500))
    caption = Column(Text)
    
    # Métricas
    views = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    engagement_rate = Column(Float, default=0.0)
    
    # Status
    status = Column(String(50), default="pending")  # pending, published, failed
    published_at = Column(DateTime(timezone=True), nullable=True)
    last_metrics_update = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Campaign(Base):
    __tablename__ = "campaigns"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    
    # Configurações da campanha
    target_hashtags = Column(Text)  # JSON string
    cta_text = Column(String(200))  # Call to Action
    watermark_enabled = Column(Boolean, default=True)
    
    # Agendamento
    active = Column(Boolean, default=True)
    posts_per_day = Column(Integer, default=3)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())