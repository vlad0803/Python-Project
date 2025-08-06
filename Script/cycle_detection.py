import os
import sys
import json
import pandas as pd

# Thresholds for each device
DEVICE_THRESHOLDS = {
    "washing_machine": {"min_duration": 1.0, "min_energy": 0.1},
    "dishwasher": {"min_duration": 1.0, "min_energy": 0.1},
    "fridge": {"min_duration": 0.5, "min_energy": 0.01},
    "freezer": {"min_duration": 0.5, "min_energy": 0.01},
    "boiler": {"min_duration": 0.5, "min_energy": 0.01},
}


class FilePathHelper:
    def __init__(self, filepath: str):
        self.basepath = os.path.splitext(filepath)[0]
        self.filename = os.path.basename(filepath)

    def get_device_name(self) -> str:
        return self.filename.replace("consumption_", "").replace(".csv", "")

    def get_output_csv_path(self) -> str:
        return self.basepath + "_ai_cycles.csv"

    def get_output_json_path(self) -> str:
        return self.basepath + "_ai_stats.json"


class ThresholdProvider:
    def __init__(self, device: str):
        self.device = device

    def get_thresholds(self) -> dict:
        return DEVICE_THRESHOLDS.get(
            self.device,
            {"min_duration": 0.5, "min_energy": 0.01}
        )


class DataFrameLoader:
    def __init__(self, filepath: str):
        self.filepath = filepath

    def load(self) -> pd.DataFrame:
        df = pd.read_csv(self.filepath, parse_dates=["timestamp"])
        if "in_cycle" not in df.columns:
            raise ValueError("Column 'in_cycle' does not exist in file!")
        df["in_cycle"] = df["in_cycle"].astype(int)
        return df


class CycleProcessor:
    def __init__(self, thresholds: dict):
        self.thresholds = thresholds
        self.in_cycle = False
        self.start_time = None
        self.total_energy = 0.0
        self.results = []

    def process_row(self, row: pd.Series):
        pred = row["in_cycle"]
        energy = row.get("energy_consumed_kwh", 0.0) or 0.0

        if not self.in_cycle and pred == 1:
            self._start_cycle(row["timestamp"], energy)
        elif self.in_cycle and pred == 1:
            self._continue_cycle(energy)
        elif self.in_cycle and pred == 0:
            self._end_cycle(row["timestamp"])

    def _start_cycle(self, timestamp, energy):
        self.in_cycle = True
        self.start_time = timestamp
        self.total_energy = energy

    def _continue_cycle(self, energy):
        self.total_energy += energy

    def _end_cycle(self, timestamp):
        duration = (timestamp - self.start_time).total_seconds() / 60
        if (
            duration >= self.thresholds["min_duration"]
            and self.total_energy >= self.thresholds["min_energy"]
        ):
            self.results.append({
                "start": self.start_time,
                "stop": timestamp,
                "duration_min": round(duration, 1),
                "energy_kwh": round(self.total_energy, 3)
            })
        self._reset_cycle()

    def _reset_cycle(self):
        self.in_cycle = False
        self.start_time = None
        self.total_energy = 0.0

    def get_results(self) -> pd.DataFrame:
        return pd.DataFrame(self.results)


class StatisticsCalculator:
    def __init__(self, device: str):
        self.device = device

    def calculate(self, df: pd.DataFrame) -> dict:
        return {
            self.device: {
                "avg_duration_min": round(df["duration_min"].mean(), 1),
                "avg_energy_kwh": round(df["energy_kwh"].mean(), 3),
                "cycle_count": len(df)
            }
        }


class ResultsWriter:
    def __init__(self, csv_path: str, json_path: str):
        self.csv_path = csv_path
        self.json_path = json_path

    def write_csv(self, df: pd.DataFrame):
        df.to_csv(self.csv_path, index=False)

    def write_json(self, statistics: dict):
        with open(self.json_path, "w") as f:
            json.dump(statistics, f, indent=2)


class CycleDetectionApp:
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.paths = FilePathHelper(filepath)

    def run(self):
        print(f"🔍 Starting cycle processing for {self.filepath}", flush=True)

        device = self.paths.get_device_name()
        thresholds = ThresholdProvider(device).get_thresholds()
        df = DataFrameLoader(self.filepath).load()

        processor = CycleProcessor(thresholds)
        for _, row in df.iterrows():
            processor.process_row(row)

        results_df = processor.get_results()
        ResultsWriter(
            self.paths.get_output_csv_path(),
            self.paths.get_output_json_path()
        ).write_csv(results_df)

        if not results_df.empty:
            statistics = StatisticsCalculator(device).calculate(results_df)
            ResultsWriter(
                self.paths.get_output_csv_path(),
                self.paths.get_output_json_path()
            ).write_json(statistics)
            self._print_success()
        else:
            self._print_no_cycles()

    def _print_success(self):
        print("Files with cycles and statistics:")
        print(f"✅ CSV: {self.paths.get_output_csv_path()}")
        print(f"✅ JSON: {self.paths.get_output_json_path()}")

    def _print_no_cycles(self):
        print("⚠️ No valid cycles detected.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python cycle_detection.py <file.csv>")
        sys.exit(1)

    app = CycleDetectionApp(sys.argv[1])
    app.run()
