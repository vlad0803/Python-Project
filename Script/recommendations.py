import os
import json
import joblib
import pandas as pd
import numpy as np
import calendar
from typing import List, Tuple
from models import Recommendation


class SolarProductionReader:
    def __init__(self, path: str):
        self.path = path

    def read(self) -> pd.DataFrame:
        try:
            df = pd.read_csv(self.path, parse_dates=["time"])
            return df.dropna()
        except Exception as e:
            print(f"⚠️ Error reading CSV: {e}")
            return pd.DataFrame()


class FilteredProduction:
    def __init__(self, dataframe: pd.DataFrame):
        self.df = dataframe

    def keep_7_day_interval(self) -> pd.DataFrame:
        today = pd.Timestamp.now().normalize()
        return self.df[
            (self.df["time"] >= today) &
            (self.df["time"] < today + pd.Timedelta(days=7))
        ]


BASE_PATH = os.path.normpath(
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        '..', 'data'
    )
)


class DeviceHabitModel:
    def __init__(self, device: str):
        self.device = device
        self.path = os.path.join(
            BASE_PATH,
            f"recommendation_model_{device}.pkl"
        )

    def _hour_and_day_to_features(
        self,
        hour: int,
        weekday: int
    ) -> pd.DataFrame:
        df = pd.DataFrame([[hour, weekday]], columns=["hour", "weekday"])
        df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
        df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)
        df["weekday_sin"] = np.sin(2 * np.pi * df["weekday"] / 7)
        df["weekday_cos"] = np.cos(2 * np.pi * df["weekday"] / 7)
        return df[["hour_sin", "hour_cos", "weekday_sin", "weekday_cos"]]

    def is_habit(self, hour_str: str, day_str: str) -> bool:
        try:
            hour_int = int(hour_str.split(":")[0])
            weekday_map = {
                d.lower(): i
                for i, d in enumerate(calendar.day_name)
            }
            weekday_int = weekday_map.get(day_str.lower(), -1)
            if weekday_int == -1:
                return False
            model = joblib.load(self.path)
            X = self._hour_and_day_to_features(hour_int, weekday_int)
            return model.predict(X)[0] == 1
        except Exception:
            return False


class HistoricConsumption:
    def __init__(self, devices: List[str]):
        self.devices = devices
        self.permanent_devices = ["fridge", "freezer", "boiler"]

    def calculate_total(self) -> float:
        total = 0.0
        all_devices = self.permanent_devices + self.devices
        for d in all_devices:
            stats_path = os.path.join(
                BASE_PATH,
                f"consumption_{d}_ai_stats.json"
            )
            try:
                if os.path.exists(stats_path):
                    with open(stats_path, encoding="utf-8") as f:
                        stats = json.load(f)
                        entry = (
                            stats.get(d)
                            or stats.get(f"consumption_{d}")
                            or {}
                        )
                        total += entry.get("avg_energy_kwh", 0.5)
                else:
                    total += 0.5
            except Exception:
                total += 0.5
        return total


class RecommendationScoreCalculator:
    def __init__(self, devices: List[str]):
        self.models = [DeviceHabitModel(d) for d in devices]

    def weekday_name(self, dt) -> str:
        return calendar.day_name[dt.weekday()].lower()

    def score(self, row, bonus_threshold: float) -> float:
        hour_str = f"{int(row['hour']):02d}:00"
        day_str = self.weekday_name(row["time"])
        is_habit = all(
            model.is_habit(hour_str, day_str) for model in self.models
        )
        if is_habit and row["energy_kwh"] >= bonus_threshold:
            return float(row["energy_kwh"] + bonus_threshold)
        return float(row["energy_kwh"])


class RecommendationCreator:
    def __init__(self, devices: List[str]):
        self.devices = devices
        self.scorer = RecommendationScoreCalculator(devices)

    def create(self, row) -> Recommendation:
        hour_str = f"{row['time'].hour:02d}:00"
        day_str = self.scorer.weekday_name(row["time"])
        is_habit = all(
            model.is_habit(hour_str, day_str) for model in self.scorer.models
        )
        rec = Recommendation(
            date=str(row["time"].date()),
            time=hour_str,
            day=day_str,
            energy=round(row["energy_kwh"], 2),
            habit=is_habit,
            controllable_devices=self.devices,
            score=round(row.get("scor", row.get("energy_kwh")), 2)
        )
        return rec


class RecommendationCalculator:
    def __init__(self, devices: List[str], bonus_reserve: float = 1.0):
        self.devices = devices
        self.bonus_reserve = bonus_reserve

    def calculate(self) -> Tuple[List[dict], float]:
        reader = SolarProductionReader(
            os.path.join(
                BASE_PATH,
                "solar_production_hourly.csv"
            )
        )
        df = reader.read()
        if df.empty:
            return [], 0.0
        df = FilteredProduction(df).keep_7_day_interval()
        total_consumption = HistoricConsumption(self.devices).calculate_total()
        threshold = total_consumption + self.bonus_reserve
        creator = RecommendationCreator(self.devices)
        results = []
        for _, group in df.groupby(df["time"].dt.date):
            sub = group[group["energy_kwh"] >= threshold].copy()
            if sub.empty:
                continue
            sub["scor"] = sub.apply(
                lambda r: creator.scorer.score(r, threshold), axis=1
            )
            top = sub.nlargest(3, "scor")
            for _, row in top.iterrows():
                rec = creator.create(row)
                results.append(rec.dict())
        return results, threshold
