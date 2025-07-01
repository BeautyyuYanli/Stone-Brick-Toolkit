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


# TaskEventDeps: TypeAlias = EventDeps[TaskEvent[T]]

# @dataclass
# class TaskEventDeps(EventDeps[TaskEvent]):
#     _event_being_consuming: bool = False

#     async def consume(
#         self,
#         target: Callable[[], Awaitable[T]],
#     ) -> AsyncGenerator[tuple[TaskEvent, bool] | EndResult[T], Any]:
#         """
#         Run the task which produces `TaskEvent` stream,
#         and consume the stream to yield events.
#         The events are yielded in the following format:
#         - `(event, True)` if the event is a part of the final result
#         - `(event, False)` if the event is not part of the finalresult
#         - `EndResult[T]` if the task is finished
#         """
#         if self._event_being_consuming:
#             raise RuntimeError(
#                 "TaskEvent stream being consuming. Use agent_run instead."
#             )
#         self._event_being_consuming = True

#         stream_span: None | Context = None
#         result: T = None  # type: ignore

#         async def run_task():
#             nonlocal result
#             result = await target()

#         try:
#             async with anyio.create_task_group() as tg:
#                 tg.start_soon(run_task)
#                 async for event in self._event_stream[1]:
#                     if (
#                         stream_span is not None
#                         and isinstance(event, TaskOutputStreamDelta)
#                         and event.ctx.parent_id == stream_span.span_id  # type: ignore
#                     ):
#                         yield event, True
#                         if event.stopped:
#                             break
#                         continue

#                     if event.ctx.parent_id != self.span.span_id:  # type: ignore
#                         yield event, False
#                         continue

#                     if stream_span is None:
#                         if isinstance(event, TaskOutputStream) and event.is_result:
#                             stream_span = event.ctx
#                             yield event, True
#                             continue
#                         elif isinstance(event, TaskOutput) and event.is_result:
#                             yield event, True
#                             break
#                     yield event, False

#             yield EndResult[T](res=result)

#         except BaseExceptionGroup as exc_group:
#             # Re-raise the first exception from the group
#             if exc_group.exceptions:
#                 raise exc_group.exceptions[0] from None
#             raise


# Generic TaskStatus type alias that supports union types
# Usage: TaskStatus[Union[int, str]] or TaskStatus[int]
# Expands to: TaskStart | TaskOutputStream | TaskOutputStreamDelta | TaskOutput[T]
# where T can be a union of types
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
