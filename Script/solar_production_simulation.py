import requests
import pandas as pd
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone, tzinfo


@dataclass
class SolarProductionSimulation:
    latitude: float
    longitude: float
    tilt: int
    azimuth: int
    efficiency: float
    panel_width_mm: int
    panel_height_mm: int
    num_panels: int
    output_csv: str
    tz: tzinfo = field(default_factory=lambda: timezone(timedelta(hours=3)))

    def _calc_total_area(self) -> float:
        panel_area_m2 = (
            self.panel_width_mm * self.panel_height_mm
        ) / 1_000_000
        return panel_area_m2 * self.num_panels

    def _build_url(self) -> str:
        start_date = datetime.now().date()
        end_date = start_date + timedelta(days=6)
        return (
            "https://api.open-meteo.com/v1/forecast?"
            f"latitude={self.latitude}&longitude={self.longitude}"
            f"&hourly=global_tilted_irradiance"
            f"&timezone=Europe%2FBucharest"
            f"&start_date={start_date}&end_date={end_date}"
            f"&tilt={self.tilt}&azimuth={self.azimuth}"
        )

    def _filter_past_hours(self, df: pd.DataFrame) -> pd.DataFrame:
        now = datetime.now(self.tz)
        return df[
            (df["time"].dt.date > now.date()) |
            (
                (df["time"].dt.date == now.date())
                & (df["time"].dt.hour > now.hour)
            )
        ]

    def run(self):
        print("🔄 Generating solar production simulation...")

        url = self._build_url()
        response = requests.get(url)
        data = response.json()

        if (
            "hourly" not in data
            or "global_tilted_irradiance" not in data["hourly"]
        ):
            print("❌ API did not return valid hourly data.")
            return

        df = pd.DataFrame(data["hourly"])
        df["time"] = pd.to_datetime(df["time"])
        df["hour"] = df["time"].dt.hour

        total_area = self._calc_total_area()
        df["energy_kwh"] = (
            df["global_tilted_irradiance"] * total_area * self.efficiency
        ) / 1000

        df = self._filter_past_hours(df)
        df.to_csv(self.output_csv, index=False)

        print(f"✅ CSV generated: {self.output_csv}")
