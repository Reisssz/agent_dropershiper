from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import os

class BasePublisher(ABC):
    """Interface base para todos os publicadores"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.platform = ""
        self.access_token = config.get('access_token')
    
    @abstractmethod
    async def publish_video(
        self, 
        video_path: str, 
        caption: str, 
        title: Optional[str] = None,
        hashtags: Optional[list] = None
    ) -> Dict[str, Any]:
        """Publicar vídeo na plataforma"""
        pass
    
    @abstractmethod
    async def get_upload_status(self, upload_id: str) -> Dict[str, Any]:
        """Verificar status de upload"""
        pass
    
    def validate_video(self, video_path: str) -> bool:
        """Validar se o vídeo atende aos requisitos da plataforma"""
        if not os.path.exists(video_path):
            return False
        
        # Verificar tamanho do arquivo (max 100MB por padrão)
        max_size = self.config.get('max_file_size', 100 * 1024 * 1024)
        if os.path.getsize(video_path) > max_size:
            return False
        
        return True