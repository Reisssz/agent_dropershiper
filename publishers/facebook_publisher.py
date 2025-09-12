import requests
from typing import Dict, Any, Optional
from .base_publisher import BasePublisher

class FacebookPublisher(BasePublisher):
    """Publicador para Facebook Reels"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.platform = "facebook"
        self.base_url = "https://graph.facebook.com/v18.0"
        self.page_id = config.get('page_id')
    
    async def publish_video(
        self, 
        video_path: str, 
        caption: str, 
        title: Optional[str] = None,
        hashtags: Optional[list] = None
    ) -> Dict[str, Any]:
        """Publicar vídeo como Reel no Facebook"""
        
        if not self.access_token or not self.page_id:
            return {"success": False, "error": "Token ou Page ID não configurado"}
        
        if not self.validate_video(video_path):
            return {"success": False, "error": "Vídeo inválido"}
        
        try:
            # Upload do vídeo
            upload_url = f"{self.base_url}/{self.page_id}/videos"
            
            with open(video_path, 'rb') as video_file:
                files = {'source': video_file}
                data = {
                    'description': caption,
                    'published': 'true',
                    'access_token': self.access_token
                }
                
                response = requests.post(upload_url, data=data, files=files, timeout=300)
                result = response.json()
                
                if 'id' in result:
                    video_id = result['id']
                    video_url = f"https://www.facebook.com/{self.page_id}/videos/{video_id}"
                    
                    return {
                        "success": True,
                        "post_id": video_id,
                        "post_url": video_url,
                        "platform": self.platform
                    }
                else:
                    return {
                        "success": False,
                        "error": result.get('error', {}).get('message', 'Erro no upload')
                    }
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_upload_status(self, video_id: str) -> Dict[str, Any]:
        """Verificar status do vídeo no Facebook"""
        
        try:
            status_url = f"{self.base_url}/{video_id}"
            params = {
                'fields': 'status',
                'access_token': self.access_token
            }
            
            response = requests.get(status_url, params=params)
            result = response.json()
            
            return {
                "status": result.get('status', {}).get('video_status', 'UNKNOWN')
            }
        
        except Exception as e:
            return {"status": "ERROR", "error": str(e)}