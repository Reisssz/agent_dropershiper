import asyncio
from typing import List, Dict, Any
from googleapiclient.discovery import build
import yt_dlp
from .base_collector import BaseCollector, VideoData

class YouTubeCollector(BaseCollector):
    """Coletor de vídeos do YouTube Shorts"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.platform = "youtube"
        self.api_key = config.get('api_key')
        if self.api_key:
            self.youtube = build('youtube', 'v3', developerKey=self.api_key)
    
    async def search_videos(self, hashtags: List[str], limit: int = 20) -> List[VideoData]:
        """Buscar YouTube Shorts por hashtags"""
        if not self.api_key:
            print("API Key do YouTube não configurada")
            return []
        
        videos = []
        
        for hashtag in hashtags:
            try:
                # Buscar vídeos curtos (Shorts)
                search_query = f"{hashtag} shorts pets"
                
                request = self.youtube.search().list(
                    part='snippet',
                    q=search_query,
                    type='video',
                    videoDuration='short',  # Vídeos até 4 minutos
                    maxResults=min(10, limit),
                    order='relevance',
                    publishedAfter=(datetime.now() - timedelta(days=30)).isoformat() + 'Z'
                )
                
                response = request.execute()
                
                for item in response.get('items', []):
                    if len(videos) >= limit:
                        break
                    
                    video_id = item['id']['videoId']
                    
                    # Obter estatísticas do vídeo
                    stats_request = self.youtube.videos().list(
                        part='statistics,contentDetails',
                        id=video_id
                    )
                    stats_response = stats_request.execute()
                    
                    if stats_response['items']:
                        stats = stats_response['items'][0]['statistics']
                        content_details = stats_response['items'][0]['contentDetails']
                        
                        # Verificar se é realmente um Short (< 60 segundos)
                        duration = self._parse_duration(content_details.get('duration', 'PT0S'))
                        if duration <= 60:  # Shorts são até 60 segundos
                            video_data = VideoData(
                                source_platform=self.platform,
                                source_id=video_id,
                                source_url=f"https://www.youtube.com/watch?v={video_id}",
                                title=item['snippet']['title'],
                                author=item['snippet']['channelTitle'],
                                hashtags=self._extract_hashtags(item['snippet'].get('description', '')),
                                views=int(stats.get('viewCount', 0)),
                                likes=int(stats.get('likeCount', 0)),
                                duration=duration
                            )
                            videos.append(video_data)
                
            except Exception as e:
                print(f"Erro ao buscar hashtag {hashtag} no YouTube: {str(e)}")
                continue
        
        return videos[:limit]
    
    def _parse_duration(self, duration_str: str) -> int:
        """Converter duração ISO 8601 para segundos"""
        import re
        match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration_str)
        if match:
            hours = int(match.group(1) or 0)
            minutes = int(match.group(2) or 0)
            seconds = int(match.group(3) or 0)
            return hours * 3600 + minutes * 60 + seconds
        return 0
    
    def _extract_hashtags(self, description: str) -> List[str]:
        """Extrair hashtags da descrição"""
        import re
        hashtags = re.findall(r'#\w+', description)
        return [tag.lower() for tag in hashtags[:10]]  # Limitar a 10 hashtags
    
    async def download_video(self, video_data: VideoData, output_path: str) -> str:
        """Baixar vídeo do YouTube usando yt-dlp"""
        try:
            ydl_opts = {
                'outtmpl': f'{output_path}.%(ext)s',
                'format': 'best[height<=720]',
                'writeinfojson': False,
                'writesubtitles': False,
                'ignoreerrors': True,
                'no_warnings': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_data.source_url, download=True)
                if info:
                    filename = ydl.prepare_filename(info)
                    return filename
            
            return None
            
        except Exception as e:
            print(f"Erro ao baixar vídeo do YouTube {video_data.source_id}: {str(e)}")
            return None