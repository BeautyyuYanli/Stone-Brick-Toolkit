from dataclasses import dataclass
from typing import Generic, Literal, TypeVar

from typing_extensions import TypeAlias

from stone_brick.asynclib import StreamRunner
from stone_brick.llm.events.events import Event, EventDeps

T = TypeVar("T")

# Task events should be like:
# |
# |-- EventTaskStart
# |        |-- EventTaskOutput
# |        |-- EventTaskOutput
# |       ...
# |
# |-- EventTaskStart
#          |-- EventTaskOutput
#          |-- EventTaskOutputStream (optional)
#          |            |
#          |            |-- EventTaskOutputStreamDelta
#          |            |
#          |            |-- EventTaskOutputStreamDelta
#          |            |
#          |           ...
#         ...


@dataclass(kw_only=True)
class TaskStart:
    """Represents a task start event"""

    event_type: Literal["task_start"] = "task_start"
    task_desc: str


@dataclass(kw_only=True)
class TaskOutput(Generic[T]):
    """Represents a task output event"""

    event_type: Literal["task_output"] = "task_output"
    data: T


@dataclass(kw_only=True)
class TaskOutputStream:
    """Represents a task output stream event"""

    event_type: Literal["task_output_stream"] = "task_output_stream"
    is_result: bool = False


@dataclass(kw_only=True)
class TaskOutputStreamDelta:
    """Represents a task output delta event"""

    event_type: Literal["task_output_delta"] = "task_output_delta"
    delta: str
    stopped: bool = False



TaskStatus: TypeAlias = (
    TaskStart | TaskOutputStream | TaskOutputStreamDelta | TaskOutput[T]
)
TaskEvent: TypeAlias = Event[TaskStatus[T]]
TaskEventDeps: TypeAlias = EventDeps[TaskStatus[T]]
T1 = TypeVar("T1")
TaskStreamRunner: TypeAlias = StreamRunner[TaskEvent[T], T1]


def print_task_event(e: TaskEvent[T]):
    event = e.content
    if isinstance(event, TaskStart):
        print(f"Task start: {event.task_desc}")
    elif isinstance(event, TaskOutput):
        print(f"Task output: {event.data}")
    elif isinstance(event, TaskOutputStream):
        print("Task output stream:\n" + "=" * 60)
    elif isinstance(event, TaskOutputStreamDelta):
        if event.stopped:
            print("\n" + "=" * 60)
        else:
            print(event.delta, end="", flush=True)
