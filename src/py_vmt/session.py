from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class Session:
    start_time: datetime
    project_name: str
    end_time: datetime | None = None

    # def __init__(
    #     self, start_time: datetime | None, project_name: str, end_time: datetime | None = None
    # ) -> None:
    #     self.start_time = start_time or datetime.now(timezone.utc)
    #     self.project_name = project_name

    # TODO: Add a static `start` method
    @staticmethod
    def start(project_name: str) -> "Session":
        return Session(datetime.now(timezone.utc), project_name)

    def stop(self):
        self.end_time = datetime.now(timezone.utc)

    @staticmethod
    def hydrate(data: dict) -> "Session":
        start_time = datetime.fromisoformat(data["start_time"])
        end_time = None
        if "end_time" in data:
            end_time = datetime.fromisoformat(data["end_time"])

        return Session(start_time, data["project_name"], end_time)

    def marshal(self) -> dict:
        marshalled_data = {
            'project_name': self.project_name,
        }

        if self.start_time:
            marshalled_data['start_time'] = datetime.isoformat(self.start_time)

        if self.end_time:
            marshalled_data['end_time'] = datetime.isoformat(self.end_time)

        return marshalled_data
