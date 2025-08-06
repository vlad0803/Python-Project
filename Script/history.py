import os
import json
from datetime import datetime
from typing import List
from pydantic import BaseModel


class CommandHistoryRecord(BaseModel):
    timestamp: datetime
    command: str
    devices: List[str]

    @classmethod
    def new(cls, command: str, devices: List[str]) -> "CommandHistoryRecord":
        return cls(
            timestamp=datetime.now(),
            command=command,
            devices=devices
        )


class CommandHistoryManager:
    def __init__(self, path: str = None):
        # Set path to ../data/command_history.jsonl relative to Script folder
        script_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.normpath(os.path.join(script_dir, '..', 'data'))
        default_path = os.path.join(data_dir, 'command_history.jsonl')
        self.path = path or default_path
        os.makedirs(os.path.dirname(self.path), exist_ok=True)

    def save(self, command: str, devices: List[str]) -> None:
        """Save a new command record to the JSONL file."""
        try:
            record = CommandHistoryRecord.new(command, devices)
            with open(self.path, 'a', encoding='utf-8') as f:
                # use Pydantic v2 model_dump() instead of deprecated dict()
                json.dump(record.model_dump(), f, default=str)
                f.write("\n")
        except Exception as e:
            print(f"⚠️ Error saving command: {e}")

    def load_commands(self) -> List[CommandHistoryRecord]:
        """Load all command records from the JSONL file."""
        records = []
        try:
            with open(self.path, 'r', encoding='utf-8') as f:
                for line in f:
                    data = json.loads(line)
                    records.append(CommandHistoryRecord(**data))
        except FileNotFoundError:
            pass
        return records
