from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from typing import List, Optional
from datetime import datetime
from pathlib import Path
from .models import AgentInteraction, DataCollectionRequest
from .storage import StorageManager


app = FastAPI(title="Agent History Collector API", version="1.0.0")
storage = StorageManager()


@app.get("/")
async def root():
    return {"message": "Agent History Collector API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.post("/api/v1/interactions", response_model=dict)
async def upload_interactions(request: DataCollectionRequest):
    try:
        filename = None
        if request.source:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{request.source}_{timestamp}.jsonl"
        
        saved_path = storage.save(request.interactions, filename)
        
        return {
            "success": True,
            "count": len(request.interactions),
            "file_path": str(saved_path),
            "source": request.source,
            "tags": request.tags
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/interaction", response_model=dict)
async def upload_single_interaction(interaction: AgentInteraction):
    try:
        saved_path = storage.save_single(interaction)
        return {
            "success": True,
            "interaction_id": interaction.id,
            "file_path": str(saved_path)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/interactions", response_model=List[AgentInteraction])
async def get_interactions(limit: Optional[int] = None):
    try:
        interactions = storage.load_all()
        if limit is not None:
            interactions = interactions[:limit]
        return interactions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/stats", response_model=dict)
async def get_stats():
    try:
        interactions = storage.load_all()
        files = storage.get_all_files()
        return {
            "total_interactions": len(interactions),
            "total_files": len(files),
            "files": [str(f) for f in files]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/v1/interactions", response_model=dict)
async def clear_interactions():
    try:
        count = len(storage.load_all())
        storage.clear_all()
        return {"success": True, "cleared_count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
