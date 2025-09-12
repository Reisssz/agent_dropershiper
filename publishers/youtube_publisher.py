import os
import httplib2
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import argparser, run_flow
from typing import Dict, Any, Optional
from .base_publisher import BasePublisher

class YouTubePublisher(BasePublisher):
    """Publicador para YouTube Shorts"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.platform = "youtube"
        self.client_secrets_file = config.get('client_secrets_file', 'youtube_secrets.json')
        self.credentials_file = config.get('credentials_file', 'youtube_credentials.json')
        self.scope = "https://www.googleapis.com/auth/youtube.upload"
        
        # Configurar autenticação
        self.youtube = self._authenticate()
    
    def _authenticate(self):
        """Autenticar com YouTube API"""
        try:
            # Fluxo de autenticação OAuth2
            flow = flow_from_clientsecrets(
                self.client_secrets_file,
                scope=self.scope,
                message="Arquivo de secrets não encontrado"
            )
            
            storage = Storage(self.credentials_file)
            credentials = storage.get()
            
            if credentials is None or credentials.invalid:
                flags = argparser.parse_args(args=[])
                credentials = run_flow(flow, storage, flags)
            
            # Construir serviço
            youtube = build("youtube", "v3", http=credentials.authorize(httplib2.Http()))
            return youtube
            
        except Exception as e:
            print(f"Erro na autenticação do YouTube: {str(e)}")
            return None
    
    async def publish_video(
        self, 
        video_path: str, 
        caption: str, 
        title: Optional[str] = None,
        hashtags: Optional[list] = None
    ) -> Dict[str, Any]:
        """Publicar vídeo como YouTube Short"""
        
        if not self.youtube:
            return {"success": False, "error": "YouTube não autenticado"}
        
        if not self.validate_video(video_path):
            return {"success": False, "error": "Vídeo inválido"}
        
        try:
            # Preparar metadados
            title = title or "Pet Short Video"
            if len(title) > 100:
                title = title[:97] + "..."
            
            # Adicionar #Shorts para YouTube reconhecer como Short
            if hashtags:
                tags = hashtags + ["Shorts", "pets", "animals"]
            else:
                tags = ["Shorts", "pets", "animals", "petshop"]
            
            description = caption + "\n\n#Shorts"
            
            # Configurar upload
            body = {
                'snippet': {
                    'title': title,
                    'description': description,
                    'tags': tags,
                    'categoryId': '15',  # Pets & Animals
                    'defaultLanguage': 'pt',
                    'defaultAudioLanguage': 'pt'
                },
                'status': {
                    'privacyStatus': 'public',
                    'selfDeclaredMadeForKids': False
                }
            }
            
            # Criar media upload
            media = MediaFileUpload(
                video_path,
                chunksize=-1,
                resumable=True,
                mimetype='video/*'
            )
            
            # Executar upload
            insert_request = self.youtube.videos().insert(
                part=','.join(body.keys()),
                body=body,
                media_body=media
            )
            
            # Upload com retry
            response = None
            error = None
            retry = 0
            
            while response is None:
                try:
                    status, response = insert_request.next_chunk()
                    if status:
                        print(f"Upload {int(status.progress() * 100)}% completo")
                except HttpError as e:
                    if e.resp.status in [500, 502, 503, 504]:
                        # Erro recuperável
                        error = f"Erro recuperável: {e}"
                        retry += 1
                        if retry > 5:
                            break
                        time.sleep(2 ** retry)
                    else:
                        raise
            
            if response is not None:
                video_id = response.get('id')
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                
                return {
                    "success": True,
                    "post_id": video_id,
                    "post_url": video_url,
                    "platform": self.platform
                }
            else:
                return {"success": False, "error": error or "Upload falhou"}
            
        except HttpError as e:
            return {"success": False, "error": f"HTTP Error: {e}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_upload_status(self, video_id: str) -> Dict[str, Any]:
        """Verificar status de processamento do vídeo"""
        
        if not self.youtube:
            return {"status": "ERROR", "error": "YouTube não autenticado"}
        
        try:
            response = self.youtube.videos().list(
                part="status,processingDetails",
                id=video_id
            ).execute()
            
            if response['items']:
                item = response['items'][0]
                status = item['status']
                processing = item.get('processingDetails', {})
                
                return {
                    "status": status.get('uploadStatus', 'unknown'),
                    "privacy": status.get('privacyStatus'),
                    "processing_status": processing.get('processingStatus'),
                    "processing_progress": processing.get('processingProgress')
                }
            
            return {"status": "NOT_FOUND"}
            
        except Exception as e:
            return {"status": "ERROR", "error": str(e)}