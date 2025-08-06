import os
import numpy as np
import pandas as pd
import joblib
from itertools import product
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, confusion_matrix


class DataLoader:
    def __init__(self, csv_path: str):
        self.csv_path = csv_path

    def load_dataframe(self) -> pd.DataFrame:
        return pd.read_csv(self.csv_path, parse_dates=["start"])

    def extract_device_name(self) -> str:
        filename = os.path.basename(self.csv_path)
        return (
            filename.replace("consumption_", "")
            .replace("_ai_cycles.csv", "")
        )


class LabelGenerator:
    @staticmethod
    def generate_labels(df: pd.DataFrame) -> pd.DataFrame:
        df["hour"] = df["start"].dt.hour
        df["weekday"] = df["start"].dt.weekday
        df["label"] = 1
        return df[["hour", "weekday", "label"]]


class Combinator:
    @staticmethod
    def all_combinations() -> pd.DataFrame:
        return pd.DataFrame(
            list(product(range(24), range(7))),
            columns=["hour", "weekday"]
        )


class LabelMerger:
    @staticmethod
    def merge_labels(
        all_df: pd.DataFrame,
        positive_df: pd.DataFrame
    ) -> pd.DataFrame:
        all_df["label"] = all_df.apply(
            lambda row: 1 if (
                (positive_df["hour"] == row["hour"]) &
                (positive_df["weekday"] == row["weekday"])
            ).any() else 0,
            axis=1
        )
        return all_df


class FeatureEngineer:
    @staticmethod
    def add_circular_features(df: pd.DataFrame) -> pd.DataFrame:
        df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
        df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)
        df["weekday_sin"] = np.sin(2 * np.pi * df["weekday"] / 7)
        df["weekday_cos"] = np.cos(2 * np.pi * df["weekday"] / 7)
        return df


class DataSplitter:
    @staticmethod
    def split(df: pd.DataFrame):
        features = ["hour_sin", "hour_cos", "weekday_sin", "weekday_cos"]
        X = df[features]
        y = df["label"]
        return train_test_split(X, y, test_size=0.2, random_state=42)


class ModelBuilder:
    def __init__(self):
        self.model = GradientBoostingClassifier(
            n_estimators=100,
            learning_rate=0.1,
            random_state=42
        )

    def train(self, X_train, y_train):
        self.model.fit(X_train, y_train)

    def predict(self, X_test):
        return self.model.predict(X_test)

    def get_model(self):
        return self.model


class Evaluator:
    @staticmethod
    def report_accuracy(y_test, y_pred, device):
        acc = accuracy_score(y_test, y_pred)
        print(f"📊 Test accuracy for {device}: {acc:.2%}")

    @staticmethod
    def report_confusion_matrix(y_test, y_pred):
        print("📊 Confusion matrix:")
        print(confusion_matrix(y_test, y_pred))

    @staticmethod
    def report_label_distribution(y_all):
        print("📊 Label distribution:")
        print(y_all.value_counts())

    @staticmethod
    def report_prediction_distribution(y_pred):
        print("📊 Prediction distribution:")
        print(pd.Series(y_pred).value_counts())


class ModelSaver:
    @staticmethod
    def save(model, path: str):
        joblib.dump(model, path)
        print(f"💾 Model saved: {path}")


class RecommendationModelTrainer:
    def __init__(self, csv_path: str, model_output: str):
        self.csv_path = csv_path
        self.model_output = model_output

    def run(self):
        # 1. Load and prepare data
        loader = DataLoader(self.csv_path)
        df_raw = loader.load_dataframe()
        device = loader.extract_device_name()
        print(f"🔧 Processing device: {device}")

        # 2. Generate labels and combinations
        positive = LabelGenerator.generate_labels(df_raw)
        all_df = Combinator.all_combinations()
        labeled = LabelMerger.merge_labels(all_df, positive)

        # 3. Feature engineering
        features = FeatureEngineer.add_circular_features(labeled)

        # 4. Split data
        X_train, X_test, y_train, y_test = DataSplitter.split(features)

        # 5. Train model
        builder = ModelBuilder()
        builder.train(X_train, y_train)
        y_pred = builder.predict(X_test)

        # 6. Evaluate
        Evaluator.report_accuracy(y_test, y_pred, device)
        Evaluator.report_confusion_matrix(y_test, y_pred)
        Evaluator.report_label_distribution(features["label"])
        Evaluator.report_prediction_distribution(y_pred)

        # 7. Save model
        ModelSaver.save(builder.get_model(), self.model_output)


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print(
            "Usage: python recommendation_trainer.py "
            "<input_csv> <output_model.pkl>"
        )
        sys.exit(1)
    trainer = RecommendationModelTrainer(sys.argv[1], sys.argv[2])
    trainer.run()
