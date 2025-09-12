import asyncio
from typing import Dict, Any, List, Optional
from .publisher_factory import PublisherFactory

class MultiPublisher:
    """Publicador que pode postar em múltiplas plataformas simultaneamente"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.publishers = PublisherFactory.create_all_publishers(config)
    
    async def publish_to_all(
        self, 
        video_path: str, 
        caption: str, 
        title: Optional[str] = None,
        hashtags: Optional[list] = None,
        platforms: Optional[List[str]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """Publicar vídeo em múltiplas plataformas"""
        
        # Usar todas as plataformas disponíveis se não especificado
        if platforms is None:
            platforms = list(self.publishers.keys())
        
        # Filtrar apenas plataformas disponíveis
        available_platforms = [p for p in platforms if p in self.publishers]
        
        if not available_platforms:
            return {"error": "Nenhuma plataforma disponível"}
        
        # Executar publicações em paralelo
        tasks = []
        for platform in available_platforms:
            publisher = self.publishers[platform]
            task = publisher.publish_video(video_path, caption, title, hashtags)
            tasks.append((platform, task))
        
        # Aguardar todos os resultados
        results = {}
        for platform, task in tasks:
            try:
                result = await task
                results[platform] = result
            except Exception as e:
                results[platform] = {"success": False, "error": str(e)}
        
        return results
    
    async def get_platform_stats(self) -> Dict[str, Any]:
        """Obter estatísticas das plataformas"""
        
        stats = {
            "total_platforms": len(self.publishers),
            "available_platforms": list(self.publishers.keys()),
            "platform_status": {}
        }
        
        for platform, publisher in self.publishers.items():
            try:
                # Testar conectividade básica
                test_result = await publisher.get_upload_status("test")
                stats["platform_status"][platform] = {
                    "status": "active",
                    "last_check": "ok"
                }
            except Exception as e:
                stats["platform_status"][platform] = {
                    "status": "error",
                    "error": str(e)
                }
        
        return stats
    
    def add_platform(self, platform: str, config: Dict[str, Any]):
        """Adicionar nova plataforma dinamicamente"""
        try:
            publisher = PublisherFactory.create_publisher(platform, config)
            self.publishers[platform] = publisher
            return True
        except Exception as e:
            print(f"Erro ao adicionar plataforma {platform}: {str(e)}")
            return False
    
    def remove_platform(self, platform: str):
        """Remover plataforma"""
        if platform in self.publishers:
            del self.publishers[platform]
            return True
        return False