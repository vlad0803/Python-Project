# pattern analysis module
import os
import json
import pandas as pd
from typing import Optional, List, Dict
from pydantic import BaseModel, Field
from models import PatternDay


BASE_PATH = os.path.normpath(
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        '..',
        'data'
    )
)


class PatternFileManager:
    def __init__(self, base_path: str = BASE_PATH):
        self.base_path = base_path

    def get_csv_path(self, device: str) -> str:
        filename = f"consumption_{device}_ai_cycles.csv"
        return os.path.join(self.base_path, filename)

    def get_json_path(self, device: str) -> str:
        filename = f"consumption_{device}_ai_stats.json"
        return os.path.join(self.base_path, filename)

    def load_cycles(self, device: str) -> Optional[pd.DataFrame]:
        path = self.get_csv_path(device)
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            return None
        return pd.read_csv(path, parse_dates=["start"])

    def load_stats(self, device: str) -> Optional[dict]:
        path = self.get_json_path(device)
        if not os.path.exists(path):
            return None
        with open(path, encoding="utf-8") as f:
            js = json.load(f)
            # Stats key may be device or prefixed
            return js.get(device) or js.get(f"consumption_{device}")


class AnalyzedDevice(BaseModel):
    device: str
    patterns_per_day: Optional[Dict] = None
    statistics: Optional[Dict] = None
    error_messages: List[str] = Field(default_factory=list)

    def is_valid(self) -> bool:
        return self.patterns_per_day is not None or self.statistics is not None


class PatternPerDay:
    @staticmethod
    def from_counts(day: str, cnt, total: int) -> PatternDay:
        maxc = cnt.max()
        hours = [
            {"hour": int(o), "cycle_count": int(n)}
            for o, n in cnt[cnt == maxc].items()
        ]
        return PatternDay(day=day, hours=hours, total=total)


class PatternExtractor:
    ZILE_ORDINE = [
        "monday", "tuesday", "wednesday", "thursday",
        "friday", "saturday", "sunday"
    ]

    def extract(self, df: pd.DataFrame) -> Dict:
        if df.empty:
            return {}

        df = self._add_day_hour_columns(df)
        total_pe_zi = self._calculate_totals(df)
        if not total_pe_zi:
            return {}

        pattern = self._build_patterns(df, total_pe_zi)
        return self._sort_by_day(pattern)

    def _add_day_hour_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        df["day"] = df["start"].dt.day_name().str.lower()
        df["hour"] = df["start"].dt.hour
        return df

    def _calculate_totals(self, df: pd.DataFrame) -> Dict:
        return {
            day: len(df[df["day"] == day])
            for day in df["day"].unique()
            if not df[df["day"] == day].empty
        }

    def _build_patterns(
        self,
        df: pd.DataFrame,
        total_pe_zi: dict
    ) -> dict:
        pattern = {}
        for day in total_pe_zi:
            subset = df[df["day"] == day]
            cnt = subset["hour"].value_counts()
            if cnt.empty:
                continue
            pattern_day = PatternPerDay.from_counts(day, cnt, total_pe_zi[day])
            pattern[day] = pattern_day.dict()
        return pattern

    def _sort_by_day(self, pattern: dict) -> dict:
        return dict(
            sorted(
                pattern.items(),
                key=lambda x: self.ZILE_ORDINE.index(x[0])
            )
        )


class PatternAnalyzer:
    def __init__(self, devices: List[str], base_path: str = BASE_PATH):
        self.devices = devices
        self.file_manager = PatternFileManager(base_path)
        self.extractor = PatternExtractor()
        self._results: Dict[str, AnalyzedDevice] = {}

    def analyze(self):
        self._results.clear()
        for device in self.devices:
            result = self._process(device)
            self._results[device] = result

    def _process(self, device: str) -> AnalyzedDevice:
        analyzed = AnalyzedDevice(device=device)

        try:
            df = self.file_manager.load_cycles(device)
            if df is not None:
                analyzed.patterns_per_day = self.extractor.extract(df)
            else:
                analyzed.error_messages.append("CSV file missing or empty")
        except Exception as e:
            analyzed.error_messages.append(f"Error reading cycles: {e}")

        try:
            stats = self.file_manager.load_stats(device)
            if stats:
                analyzed.statistics = stats
        except Exception as e:
            analyzed.error_messages.append(f"Error reading statistics: {e}")

        return analyzed

    def get(self, name: str) -> Optional[AnalyzedDevice]:
        return self._results.get(name)

    def get_valid_devices(self) -> List[AnalyzedDevice]:
        return [d for d in self._results.values() if d.is_valid()]

    def get_devices_with_errors(self) -> List[AnalyzedDevice]:
        return [d for d in self._results.values() if d.error_messages]

    def get_pattern_summary(self) -> dict:
        patterns = {
            d.device: d.patterns_per_day
            for d in self.get_valid_devices()
        }
        stats = {
            d.device: d.statistics
            for d in self.get_valid_devices()
        }
        errors = {
            d.device: d.error_messages
            for d in self.get_devices_with_errors()
        }
        return {
            "patterns_per_day": patterns,
            "statistics": stats,
            "error_messages": errors
        }
