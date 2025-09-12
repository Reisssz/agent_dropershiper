from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import json

@dataclass
class VideoData:
    """Estrutura padrão para dados de vídeo coletados"""
    source_platform: str
    source_id: str
    source_url: str
    title: str
    author: str
    hashtags: List[str]
    views: int
    likes: int
    duration: Optional[int] = None
    description: Optional[str] = None
    download_url: Optional[str] = None

class BaseCollector(ABC):
    """Interface base para todos os coletores"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.platform = ""
    
    @abstractmethod
    async def search_videos(self, hashtags: List[str], limit: int = 20) -> List[VideoData]:
        """Buscar vídeos por hashtags"""
        pass
    
    @abstractmethod
    async def download_video(self, video_data: VideoData, output_path: str) -> str:
        """Baixar vídeo e retornar caminho local"""
        pass
    
    async def collect_videos(self, hashtags: List[str], limit: int = 20) -> List[Dict[str, Any]]:
        """Método principal para coleta completa"""
        videos = await self.search_videos(hashtags, limit)
        results = []
        
        for video in videos:
            try:
                # Baixar vídeo
                local_path = await self.download_video(video, f"videos/raw/{video.source_id}")
                
                # Preparar dados para salvar no banco
                video_dict = {
                    "source_platform": video.source_platform,
                    "source_id": video.source_id,
                    "source_url": video.source_url,
                    "title": video.title,
                    "author": video.author,
                    "hashtags": json.dumps(video.hashtags),
                    "views": video.views,
                    "likes": video.likes,
                    "local_path": local_path,
                    "status": "collected"
                }
                
                results.append(video_dict)
                
            except Exception as e:
                print(f"Erro ao processar vídeo {video.source_id}: {str(e)}")
                continue
        
        return results