# === Standard library ===
import sys
import os
import re
import tempfile
import shutil
from datetime import datetime

# === Third-party ===
import pandas as pd
import requests
import whisper
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from cycle_detection import CycleDetectionApp
from solar_production_simulation import SolarProductionSimulation
from history import CommandHistoryManager
from devices import DeviceDetector
from pattern import PatternAnalyzer
from recommendations import RecommendationCalculator
from recommendation_trainer import RecommendationModelTrainer
from models import CommandRequest, Recommendation

# === Path fix for imports ===
sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
)


# === FastAPI application configuration ===

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)


manager = CommandHistoryManager()
detector = DeviceDetector()
model_whisper = whisper.load_model("base")

BASE_PATH = os.path.normpath(
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        '..',
        'data'
    )
)


def normalize_command(text: str) -> str:
    return re.sub(r"[^\w\s]", "", text.lower()).strip()


def is_orthodox_holiday(date_str: str) -> bool:
    try:
        year, month, day = map(int, date_str.split("-"))
        url = f"https://orthocal.info/api/gregorian/{year}/{month}/{day}"
        r = requests.get(url, timeout=5)
        js = r.json()
        return bool(js.get("feasts"))
    except Exception as e:
        print(f"[Holiday] Error for {date_str}: {e}")
        return False


def detect_and_save_devices(command: str) -> list[str]:
    norm_command = normalize_command(command)
    devices = detector.detect(norm_command)
    if devices:
        manager.save(command, devices)
    return devices


def run_detection(device: str):
    path = os.path.join(BASE_PATH, f"consumption_{device}.csv")
    if os.path.exists(path):
        try:
            app = CycleDetectionApp(path)
            app.run()
        except Exception as e:
            print(f"⚠️ Error detecting cycles for {device}: {e}")


def run_detections_and_trainings(devices: list[str]):
    permanent = ["fridge", "freezer", "boiler"]
    all_devices = devices + permanent
    for d in all_devices:
        run_detection(d)
    for d in devices:
        train_model(d)


def train_model(device: str):
    csv_in = os.path.join(BASE_PATH, f"consumption_{device}_ai_cycles.csv")
    model_out = os.path.join(BASE_PATH, f"recommendation_model_{device}.pkl")
    RecommendationModelTrainer(csv_in, model_out).run()


def analyze_patterns(devices: list[str]):
    analyzer = PatternAnalyzer(devices=devices, base_path=BASE_PATH)
    analyzer.analyze()
    return analyzer


def calculate_recommendations(devices: list[str]):
    rc = RecommendationCalculator(devices)
    return rc.calculate()


def sort_recommendations(recommendations: list[dict]) -> list[dict]:
    return sorted(
        recommendations,
        key=lambda x: datetime.strptime(
            f"{x['date']} {x['time']}",
            "%Y-%m-%d %H:%M"
        )
    )


def mark_holidays(recommendations: list[dict]):
    for r in recommendations:
        r["holiday"] = is_orthodox_holiday(r["date"])


def load_solar_production() -> pd.DataFrame:
    path = os.path.join(BASE_PATH, "solar_production_hourly.csv")
    return pd.read_csv(path, parse_dates=["time"])


# === FastAPI endpoints ===

@app.post("/ai")
def ai_command(request: CommandRequest):
    try:
        devices = detect_and_save_devices(request.command)
        if not devices:
            return {
                "error": (
                    f"Unknown device in command: "
                    f"'{request.command}'"
                )
            }

        all_devices = devices + ["fridge", "freezer", "boiler"]
        run_detections_and_trainings(devices)
        analyzer = analyze_patterns(all_devices)
        summary = analyzer.get_pattern_summary()

        # Use English summary keys
        patterns_per_day = summary.get("patterns_per_day", {})
        statistics = summary.get("statistics", {})
        error_messages = summary.get("error_messages", {})

        results, threshold = calculate_recommendations(devices)
        results = sort_recommendations(results)
        mark_holidays(results)

        filtered_statistics = {
            d: statistics[d]
            for d in patterns_per_day
            if d in statistics
        }

        return {
            "recommendations": [Recommendation(**r).dict() for r in results],
            "devices": devices,
            "patterns_per_day": patterns_per_day,
            "statistics": filtered_statistics,
            "error_messages": error_messages,
            "bonus_threshold": round(threshold, 2)
        }

    except Exception as e:
        print(f"❗ Error processing command: {e}")
        return {"error": f"Internal error: {str(e)}"}


@app.get("/commands")
def get_commands():
    return {"commands": [rec.dict() for rec in manager.load_commands()]}


@app.get("/solar_production")
def solar_production():
    try:
        path = os.path.join(BASE_PATH, "solar_production_hourly.csv")

        if not os.path.exists(path):
            return {"error": "CSV file does not exist."}

        df = pd.read_csv(path, parse_dates=["time"])

        if (
            df.empty or
            "time" not in df.columns or
            "energy_kwh" not in df.columns
        ):
            return {"error": "File does not contain valid data."}

        return JSONResponse({
            "status": "ok",
            "hours": (
                df.sort_values("time")["time"]
                .dt.strftime("%Y-%m-%d %H:%M").tolist()
            ),
            "values": (
                df["energy_kwh"].round(2).tolist()
            )
        })

    except Exception as e:
        return {"error": f"Read error: {e}"}


@app.get("/generate_solar_production")
def generate_solar_production():
    try:
        simulation = SolarProductionSimulation(
            latitude=46.798833,
            longitude=23.744472,
            tilt=45,
            azimuth=-98,
            efficiency=0.225,
            panel_width_mm=1762,
            panel_height_mm=1134,
            num_panels=12,
            output_csv=os.path.join(BASE_PATH, "solar_production_hourly.csv")
        )
        simulation.run()
        return {"status": "ok"}
    except Exception as e:
        return {"error": f"Simulation error: {str(e)}"}


@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...)):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
            shutil.copyfileobj(file.file, tmp)
            path = tmp.name
        result = model_whisper.transcribe(path, language="en")
        os.remove(path)
        return {"text": result["text"]}
    except Exception as e:
        return {"error": f"Transcription error: {e}"}
