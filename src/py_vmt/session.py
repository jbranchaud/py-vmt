from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from py_vmt.time_helpers import find_nearest_timestamp_interval


@dataclass
class Session:
    start_time: datetime
    project_name: str
    end_time: datetime | None = None

    def __lt__(self, other):
        if not isinstance(other, Session):
            return NotImplemented
        return self.start_time < other.start_time

    @staticmethod
    def start(project_name: str) -> "Session":
        return Session(datetime.now(timezone.utc), project_name)

    def round_end_time(
        self, exact_end_time: datetime, interval: timedelta = timedelta(minutes=15)
    ) -> datetime:
        return find_nearest_timestamp_interval(
            self.start_time, exact_end_time, interval
        )

    def stop(self, at: datetime | None = None, round: bool = False):
        exact_end_time = at or datetime.now(timezone.utc)
        if round:
            # difference between `self.start_time` and
            rounded_end_time = self.round_end_time(exact_end_time)
            self.end_time = rounded_end_time
        else:
            self.end_time = exact_end_time

    def duration(self) -> timedelta:
        lhs_time = self.end_time or datetime.now(timezone.utc)

        return lhs_time - self.start_time

    @staticmethod
    def hydrate(data: dict) -> "Session":
        start_time = datetime.fromisoformat(data["start_time"])
        end_time = None
        if "end_time" in data:
            end_time = datetime.fromisoformat(data["end_time"])

        return Session(start_time, data["project_name"], end_time)

    def marshal(self) -> dict:
        marshalled_data = {
            "project_name": self.project_name,
        }

        if self.start_time:
            marshalled_data["start_time"] = datetime.isoformat(self.start_time)

        if self.end_time:
            marshalled_data["end_time"] = datetime.isoformat(self.end_time)

        return marshalled_data
