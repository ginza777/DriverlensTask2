# main.py
from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import asyncio
from pathlib import Path
import os
import sys

# infer_and_track_violations.py faylidagi funksiyani import qilish
# 'app' katalogini sys.path ga qo'shish (kerakli bo'lsa)
sys.path.append(str(Path(
    __file__).resolve().parent))  # Bu o'zgarish main.py va infer_and_track_violations.py bir xil katalogda bo'lsa ishlaydi

from infer_and_track_violations import analyze_video_for_violations

app = FastAPI()

# Frontend (HTML, CSS, JS) fayllarini joylashuvi
# Docker konteynerida /app/static bo'ladi
# Directory 'static' o'rniga to'liq yo'lni beramiz, agar main.py va static bir xil darajada bo'lsa
app.mount("/static", StaticFiles(directory="/app/static"), name="static")

# Natija fayllari uchun katalog
app.mount("/results", StaticFiles(directory="/app/results"), name="results") # Bu ham mutlaq yo'l bo'lishi yaxshi

templates = Jinja2Templates(directory="templates")

# Video tahlili holatini saqlash uchun global o'zgaruvchi
analysis_progress = {"current_frame": 0, "total_frames": 1}
analysis_result = None


class VideoAnalysisRequest(BaseModel):
    video_path: str  # Videoning Docker konteyneri ichidagi yo'li


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("landing.html", {"request": request})


@app.post("/analyze_video")
async def analyze_video(request: VideoAnalysisRequest, background_tasks: BackgroundTasks):
    global analysis_progress, analysis_result

    # Progressni boshlang'ich holatiga qaytarish
    analysis_progress = {"current_frame": 0, "total_frames": 1}
    analysis_result = None

    video_to_process = request.video_path
    # Model yo'lini Docker konteyneri ichidagi joylashuvga moslab belgilash
    model_to_use = "/app/runs/train/exp_fast_train3/weights/best.pt"

    if not Path(video_to_process).exists():
        raise HTTPException(status_code=404, detail=f"Video not found at {video_to_process}")

    if not Path(model_to_use).exists():
        print(f"Warning: Model not found at {model_to_use}. Using default YOLOv8n.")

    def video_analysis_task(video_path, model_path):
        global analysis_progress, analysis_result

        def update_progress_callback(current_frame, total_frames):
            analysis_progress["current_frame"] = current_frame
            analysis_progress["total_frames"] = total_frames

        try:
            result = analyze_video_for_violations(video_path, model_path, update_progress_callback)
            analysis_result = result
            print("Analysis completed in background task.")
        except Exception as e:
            print(f"Error during video analysis: {e}")
            analysis_result = {"error": str(e)}
        finally:
            analysis_progress["current_frame"] = analysis_progress["total_frames"]

    background_tasks.add_task(video_analysis_task, video_to_process, model_to_use)

    return {"message": "Video tahlili boshlandi", "status": "processing"}


@app.get("/progress")
async def get_progress():
    global analysis_progress
    return analysis_progress


@app.get("/results_data")
async def get_results_data():
    global analysis_result
    if analysis_result is None:
        raise HTTPException(status_code=404, detail="Analysis results not yet available or no analysis started.")
    return analysis_result