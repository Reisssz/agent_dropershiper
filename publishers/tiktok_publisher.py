import requests
import json
import os
from typing import Dict, Any, Optional
from .base_publisher import BasePublisher

class TikTokPublisher(BasePublisher):
    """Publicador para TikTok usando TikTok Business API"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.platform = "tiktok"
        self.base_url = "https://business-api.tiktok.com/open_api/v1.3"
        self.advertiser_id = config.get('advertiser_id')
        
    async def publish_video(
        self, 
        video_path: str, 
        caption: str, 
        title: Optional[str] = None,
        hashtags: Optional[list] = None
    ) -> Dict[str, Any]:
        """Publicar vídeo no TikTok"""
        
        if not self.access_token:
            return {"success": False, "error": "Token de acesso não configurado"}
        
        if not self.validate_video(video_path):
            return {"success": False, "error": "Vídeo inválido"}
        
        try:
            # TikTok Business API é principalmente para anúncios
            # Para publicação orgânica, usar método alternativo com Playwright
            return await self._publish_with_playwright(video_path, caption, title)
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _publish_with_playwright(
        self, 
        video_path: str, 
        caption: str, 
        title: Optional[str] = None
    ) -> Dict[str, Any]:
        """Publicar usando Playwright (simulação de browser)"""
        
        try:
            from playwright.async_api import async_playwright
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=False)  # Visível para debug
                context = await browser.new_context()
                
                # Carregar cookies de sessão se disponível
                cookies_file = "tiktok_session.json"
                if os.path.exists(cookies_file):
                    with open(cookies_file, 'r') as f:
                        cookies = json.load(f)
                        await context.add_cookies(cookies)
                
                page = await context.new_page()
                
                # Navegar para página de upload
                await page.goto("https://www.tiktok.com/creator-center/upload")
                
                # Aguardar página carregar
                await page.wait_for_selector('[data-e2e="upload-btn"]', timeout=30000)
                
                # Upload do arquivo
                file_input = page.locator('input[type="file"]')
                await file_input.set_input_files(video_path)
                
                # Aguardar processamento do upload
                await page.wait_for_selector('[data-e2e="video-upload-done"]', timeout=120000)
                
                # Adicionar caption
                caption_input = page.locator('[data-e2e="video-caption"]')
                await caption_input.fill(caption)
                
                # Configurar privacidade (público)
                privacy_public = page.locator('[data-e2e="privacy-public"]')
                await privacy_public.click()
                
                # Publicar
                publish_btn = page.locator('[data-e2e="publish-btn"]')
                await publish_btn.click()
                
                # Aguardar confirmação
                await page.wait_for_selector('[data-e2e="upload-success"]', timeout=60000)
                
                # Extrair ID do post se possível
                current_url = page.url
                
                await browser.close()
                
                return {
                    "success": True,
                    "post_id": "tiktok_uploaded",  # TikTok não fornece ID direto
                    "post_url": current_url,
                    "platform": self.platform
                }
        
        except Exception as e:
            return {"success": False, "error": f"Erro no upload automático: {str(e)}"}
    
    async def get_upload_status(self, upload_id: str) -> Dict[str, Any]:
        """TikTok não fornece API pública para status"""
        return {"status": "UNKNOWN", "message": "Status não disponível para TikTok"}