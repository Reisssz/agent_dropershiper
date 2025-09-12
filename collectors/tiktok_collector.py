import asyncio
import json
from typing import List, Dict, Any, Optional
from playwright.async_api import async_playwright
import yt_dlp
from .base_collector import BaseCollector, VideoData
import re

class TikTokCollector(BaseCollector):
    """Coletor de vídeos do TikTok usando Playwright + yt-dlp"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.platform = "tiktok"
        self.base_url = "https://www.tiktok.com"
    
    async def search_videos(self, hashtags: List[str], limit: int = 20) -> List[VideoData]:
        """Buscar vídeos no TikTok por hashtags"""
        videos = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            page = await context.new_page()
            
            for hashtag in hashtags:
                try:
                    # Navegar para página da hashtag
                    hashtag_clean = hashtag.replace("#", "")
                    url = f"{self.base_url}/tag/{hashtag_clean}"
                    
                    await page.goto(url, wait_until="networkidle")
                    await asyncio.sleep(3)
                    
                    # Scroll para carregar mais vídeos
                    for _ in range(3):
                        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        await asyncio.sleep(2)
                    
                    # Extrair links dos vídeos
                    video_links = await page.evaluate("""
                        () => {
                            const links = [];
                            const videoElements = document.querySelectorAll('a[href*="/video/"]');
                            videoElements.forEach(el => {
                                if (links.length < 20) {  // Limit per hashtag
                                    links.push(el.href);
                                }
                            });
                            return links;
                        }
                    """)
                    
                    # Processar cada vídeo
                    for video_url in video_links[:limit]:
                        if len(videos) >= limit:
                            break
                            
                        video_data = await self._extract_video_data(page, video_url)
                        if video_data:
                            videos.append(video_data)
                    
                except Exception as e:
                    print(f"Erro ao buscar hashtag {hashtag}: {str(e)}")
                    continue
            
            await browser.close()
        
        return videos[:limit]
    
    async def _extract_video_data(self, page, video_url: str) -> Optional[VideoData]:
        """Extrair metadados de um vídeo específico"""
        try:
            await page.goto(video_url, wait_until="networkidle")
            await asyncio.sleep(2)
            
            # Extrair dados usando JavaScript
            video_info = await page.evaluate("""
                () => {
                    // Tentar extrair dados do objeto __UNIVERSAL_DATA_FOR_REHYDRATION__
                    const scripts = document.querySelectorAll('script');
                    let data = null;
                    
                    for (let script of scripts) {
                        if (script.innerHTML.includes('__UNIVERSAL_DATA_FOR_REHYDRATION__')) {
                            const match = script.innerHTML.match(/__UNIVERSAL_DATA_FOR_REHYDRATION__\s*=\s*({.+?});/);
                            if (match) {
                                try {
                                    data = JSON.parse(match[1]);
                                    break;
                                } catch (e) {
                                    console.log('Erro ao parsear JSON:', e);
                                }
                            }
                        }
                    }
                    
                    if (!data) return null;
                    
                    // Navegar pela estrutura do TikTok para encontrar dados do vídeo
                    const defaultScope = data?.['__DEFAULT_SCOPE__'] || {};
                    const pageProps = defaultScope?.['webapp.video-detail'] || {};
                    const itemInfo = pageProps?.itemInfo?.itemStruct || {};
                    
                    if (!itemInfo.id) return null;
                    
                    return {
                        id: itemInfo.id,
                        title: itemInfo.desc || '',
                        author: itemInfo.author?.nickname || itemInfo.author?.uniqueId || '',
                        views: itemInfo.stats?.playCount || 0,
                        likes: itemInfo.stats?.diggCount || 0,
                        shares: itemInfo.stats?.shareCount || 0,
                        comments: itemInfo.stats?.commentCount || 0,
                        hashtags: (itemInfo.textExtra || []).map(tag => tag.hashtagName).filter(Boolean),
                        duration: itemInfo.video?.duration || 0,
                        downloadUrl: itemInfo.video?.downloadAddr || itemInfo.video?.playAddr
                    };
                }
            """)
            
            if not video_info or not video_info.get('id'):
                return None
            
            # Extrair ID do vídeo da URL como fallback
            video_id = video_info.get('id') or self._extract_video_id(video_url)
            
            return VideoData(
                source_platform=self.platform,
                source_id=video_id,
                source_url=video_url,
                title=video_info.get('title', '')[:500],  # Limitar tamanho
                author=video_info.get('author', '')[:200],
                hashtags=video_info.get('hashtags', []),
                views=video_info.get('views', 0),
                likes=video_info.get('likes', 0),
                duration=video_info.get('duration'),
                download_url=video_info.get('downloadUrl')
            )
            
        except Exception as e:
            print(f"Erro ao extrair dados do vídeo {video_url}: {str(e)}")
            return None
    
    def _extract_video_id(self, url: str) -> str:
        """Extrair ID do vídeo da URL"""
        match = re.search(r'/video/(\d+)', url)
        return match.group(1) if match else url.split('/')[-1]
    
    async def download_video(self, video_data: VideoData, output_path: str) -> str:
        """Baixar vídeo usando yt-dlp"""
        try:
            # Configuração do yt-dlp
            ydl_opts = {
                'outtmpl': f'{output_path}.%(ext)s',
                'format': 'best[height<=720]',  # Limitar qualidade para economizar espaço
                'writeinfojson': False,
                'writesubtitles': False,
                'ignoreerrors': True,
                'no_warnings': True,
            }
            
            # Baixar vídeo
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_data.source_url, download=True)
                
                # Encontrar arquivo baixado
                if info:
                    filename = ydl.prepare_filename(info)
                    return filename
                
            return None
            
        except Exception as e:
            print(f"Erro ao baixar vídeo {video_data.source_id}: {str(e)}")
            return None