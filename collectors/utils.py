import os
import hashlib
from typing import List
from datetime import datetime, timedelta

def create_directories(paths: List[str]):
    """Criar diretórios se não existirem"""
    for path in paths:
        os.makedirs(path, exist_ok=True)

def generate_filename(video_id: str, platform: str, extension: str = "mp4") -> str:
    """Gerar nome único para arquivo"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{platform}_{video_id}_{timestamp}.{extension}"

def calculate_file_hash(filepath: str) -> str:
    """Calcular hash MD5 do arquivo para detectar duplicatas"""
    if not os.path.exists(filepath):
        return ""
    
    hash_md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def is_recent_video(created_date: str, days: int = 7) -> bool:
    """Verificar se o vídeo é recente"""
    try:
        video_date = datetime.fromisoformat(created_date.replace('Z', '+00:00'))
        cutoff_date = datetime.now() - timedelta(days=days)
        return video_date >= cutoff_date
    except:
        return True  # Se não conseguir parsear, assumir que é recente