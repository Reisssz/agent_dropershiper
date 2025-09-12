from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from .database import get_db, create_tables
from .models import Video, Publication, Campaign
from .config import settings

app = FastAPI(title="Pet Agent API", version="1.0.0")

@app.on_event("startup")
async def startup_event():
    create_tables()
    print("🚀 Pet Agent iniciado!")

@app.get("/")
async def root():
    return {"message": "Pet Agent API - Sistema de Marketing Automatizado para Pet Shop"}

@app.get("/videos/")
async def list_videos(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    videos = db.query(Video).offset(skip).limit(limit).all()
    return videos

@app.get("/videos/{video_id}")
async def get_video(video_id: int, db: Session = Depends(get_db)):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Vídeo não encontrado")
    return video

@app.get("/publications/")
async def list_publications(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    publications = db.query(Publication).offset(skip).limit(limit).all()
    return publications

@app.get("/campaigns/")
async def list_campaigns(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    campaigns = db.query(Campaign).offset(skip).limit(limit).all()
    return campaigns

@app.post("/campaigns/")
async def create_campaign(name: str, description: str = "", db: Session = Depends(get_db)):
    campaign = Campaign(name=name, description=description)
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return campaign

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)