from typing import Dict, Any, List
from .instagram_publisher import InstagramPublisher
from .tiktok_publisher import TikTokPublisher
from .youtube_publisher import YouTubePublisher
from .facebook_publisher import FacebookPublisher

class PublisherFactory:
    """Factory para criar publicadores baseado na plataforma"""
    
    PUBLISHERS = {
        'instagram': InstagramPublisher,
        'tiktok': TikTokPublisher,
        'youtube': YouTubePublisher,
        'facebook': FacebookPublisher
    }
    
    @classmethod
    def create_publisher(cls, platform: str, config: Dict[str, Any]):
        """Criar publicador para plataforma específica"""
        
        publisher_class = cls.PUBLISHERS.get(platform.lower())
        if not publisher_class:
            raise ValueError(f"Plataforma não suportada: {platform}")
        
        return publisher_class(config)
    
    @classmethod
    def create_all_publishers(cls, config: Dict[str, Any]) -> Dict[str, Any]:
        """Criar todos os publicadores configurados"""
        
        publishers = {}
        
        for platform, publisher_class in cls.PUBLISHERS.items():
            try:
                # Verificar se a plataforma está configurada
                platform_config = config.get(platform, {})
                if platform_config.get('enabled', False):
                    publishers[platform] = publisher_class(platform_config)
            except Exception as e:
                print(f"Erro ao criar publicador {platform}: {str(e)}")
        
        return publishers
    
    @classmethod
    def get_supported_platforms(cls) -> List[str]:
        """Listar plataformas suportadas"""
        return list(cls.PUBLISHERS.keys())