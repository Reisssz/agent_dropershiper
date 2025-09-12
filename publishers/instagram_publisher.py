import requests
import time
import os
from typing import Dict, Any, Optional
from .base_publisher import BasePublisher

class InstagramPublisher(BasePublisher):
    """Publicador para Instagram Reels"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.platform = "instagram"
        self.base_url = "https://graph.facebook.com/v18.0"
        self.page_id = config.get('page_id')
        
    async def publish_video(
        self, 
        video_path: str, 
        caption: str, 
        title: Optional[str] = None,
        hashtags: Optional[list] = None
    ) -> Dict[str, Any]:
        """Publicar vídeo como Reel no Instagram"""
        
        if not self.access_token or not self.page_id:
            return {"success": False, "error": "Token ou Page ID não configurado"}
        
        if not self.validate_video(video_path):
            return {"success": False, "error": "Vídeo inválido"}
        
        try:
            # Passo 1: Criar container de mídia
            container_result = await self._create_media_container(video_path, caption)
            if not container_result.get('success'):
                return container_result
            
            creation_id = container_result['creation_id']
            
            # Passo 2: Aguardar processamento
            await self._wait_for_processing(creation_id)
            
            # Passo 3: Publicar
            publish_result = await self._publish_media(creation_id)
            
            return publish_result
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _create_media_container(self, video_path: str, caption: str) -> Dict[str, Any]:
        """Criar container de mídia para Reel"""
        
        try:
            # Upload do vídeo para Facebook/Instagram
            upload_url = f"{self.base_url}/{self.page_id}/media"
            
            with open(video_path, 'rb') as video_file:
                files = {'source': video_file}
                data = {
                    'caption': caption,
                    'media_type': 'REELS',
                    'access_token': self.access_token
                }
                
                response = requests.post(upload_url, data=data, files=files, timeout=300)
                result = response.json()
                
                if 'id' in result:
                    return {
                        "success": True,
                        "creation_id": result['id']
                    }
                else:
                    return {
                        "success": False,
                        "error": result.get('error', {}).get('message', 'Erro no upload')
                    }
        
        except Exception as e:
            return {"success": False, "error": f"Erro no upload: {str(e)}"}
    
    async def _wait_for_processing(self, creation_id: str, max_attempts: int = 30):
        """Aguardar processamento do vídeo"""
        
        for attempt in range(max_attempts):
            status = await self.get_upload_status(creation_id)
            
            if status.get('status') == 'FINISHED':
                return True
            elif status.get('status') == 'ERROR':
                raise Exception(f"Erro no processamento: {status.get('error_message')}")
            
            # Aguardar 10 segundos entre tentativas
            time.sleep(10)
        
        raise Exception("Timeout no processamento do vídeo")
    
    async def _publish_media(self, creation_id: str) -> Dict[str, Any]:
        """Publicar mídia processada"""
        
        try:
            publish_url = f"{self.base_url}/{self.page_id}/media_publish"
            
            data = {
                'creation_id': creation_id,
                'access_token': self.access_token
            }
            
            response = requests.post(publish_url, data=data)
            result = response.json()
            
            if 'id' in result:
                post_id = result['id']
                post_url = f"https://www.instagram.com/reel/{post_id}"
                
                return {
                    "success": True,
                    "post_id": post_id,
                    "post_url": post_url,
                    "platform": self.platform
                }
            else:
                return {
                    "success": False,
                    "error": result.get('error', {}).get('message', 'Erro na publicação')
                }
        
        except Exception as e:
            return {"success": False, "error": f"Erro na publicação: {str(e)}"}
    
    async def get_upload_status(self, creation_id: str) -> Dict[str, Any]:
        """Verificar status do upload"""
        
        try:
            status_url = f"{self.base_url}/{creation_id}"
            params = {
                'fields': 'status_code,status',
                'access_token': self.access_token
            }
            
            response = requests.get(status_url, params=params)
            result = response.json()
            
            return {
                "status": result.get('status', 'UNKNOWN'),
                "status_code": result.get('status_code', 'UNKNOWN')
            }
        
        except Exception as e:
            return {"status": "ERROR", "error_message": str(e)}