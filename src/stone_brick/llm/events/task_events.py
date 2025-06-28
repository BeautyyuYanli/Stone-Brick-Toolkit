from copy import copy
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Awaitable, Callable, Generic, Literal, TypeVar

import anyio
from exceptiongroup import BaseExceptionGroup
from typing_extensions import Self, TypeAlias

from stone_brick.llm.events.events import Context, Event, EventDeps

T = TypeVar("T")

# Task events should be like:
# |
# |-- EventTaskRoot
# |        |
# |        |-- EventTaskOutput
# |        |-- EventTaskOutput
# |       ...
# |
# |-- EventTaskRoot
#          |-- EventTaskOutputStream (optional)
#          |            |
#          |            |-- EventTaskOutputStreamDelta
#          |            |
#          |            |-- EventTaskOutputStreamDelta
#          |            |
#          |           ...
#         ...


TaskEventTypes = Literal[
    "task_start", "task_output", "task_output_stream", "task_output_delta"
]


class EventTaskStart(Event[TaskEventTypes], Generic[T]):
    """Represents a task root event"""

    event_type: Literal["task_start"] = "task_start"
    task_desc: str
    task_args: T | Any


class EventTaskOutput(Event[TaskEventTypes], Generic[T]):
    """Represents a task output event"""

    event_type: Literal["task_output"] = "task_output"
    is_result: bool = False
    task_output: T | Any


class EventTaskOutputStream(Event[TaskEventTypes], Generic[T]):
    """Represents a task output stream event"""

    event_type: Literal["task_output_stream"] = "task_output_stream"
    is_result: bool = False


class EventTaskOutputStreamDelta(Event[TaskEventTypes], Generic[T]):
    """Represents a task output delta event"""

    event_type: Literal["task_output_delta"] = "task_output_delta"
    task_output_delta: T | Any
    stopped: bool = False

    def get_text(self) -> str | None:
        return str(self.task_output_delta)


TaskEvent: TypeAlias = (
    EventTaskStart
    | EventTaskOutput
    | EventTaskOutputStream
    | EventTaskOutputStreamDelta
)


@dataclass
class EndResult(Generic[T]):
    res: T


@dataclass
class TaskEventDeps(EventDeps[TaskEvent]):
    _event_being_consuming: bool = False

    async def consume(
        self,
        target: Callable[[], Awaitable[T]],
    ) -> AsyncGenerator[tuple[TaskEvent, bool] | EndResult[T], Any]:
        """
        Run the task which produces `TaskEvent` stream,
        and consume the stream to yield events.
        The events are yielded in the following format:
        - `(event, True)` if the event is a part of the final result
        - `(event, False)` if the event is not part of the finalresult
        - `EndResult[T]` if the task is finished
        """
        if self._event_being_consuming:
            raise RuntimeError(
                "TaskEvent stream being consuming. Use agent_run instead."
            )
        self._event_being_consuming = True

        stream_span: None | Context = None
        result: T = None  # type: ignore

        async def run_task():
            nonlocal result
            result = await target()

        try:
            async with anyio.create_task_group() as tg:
                tg.start_soon(run_task)
                async for event in self._event_stream[1]:
                    if (
                        stream_span is not None
                        and isinstance(event, EventTaskOutputStreamDelta)
                        and event.ctx.parent_id == stream_span.span_id  # type: ignore
                    ):
                        yield event, True
                        if event.stopped:
                            break
                        continue

                    if event.ctx.parent_id != self._event_span.span_id:  # type: ignore
                        yield event, False
                        continue

                    if stream_span is None:
                        if isinstance(event, EventTaskOutputStream) and event.is_result:
                            stream_span = event.ctx
                            yield event, True
                            continue
                        elif isinstance(event, EventTaskOutput) and event.is_result:
                            yield event, True
                            break
                    yield event, False

            yield EndResult[T](res=result)

        except BaseExceptionGroup as exc_group:
            # Re-raise the first exception from the group
            if exc_group.exceptions:
                raise exc_group.exceptions[0] from None
            raise


def print_task_event(event: TaskEvent):
    if isinstance(event, EventTaskStart):
        print(f"Task call: {event.task_desc} with args: \n{event.task_args}")
    elif isinstance(event, EventTaskOutput):
        print(f"Task output: {event.task_output}")
    elif isinstance(event, EventTaskOutputStream):
        print("Task output stream:")
    elif isinstance(event, EventTaskOutputStreamDelta):
        if event.stopped:
            print()
        else:
            print(event.task_output_delta, end="", flush=True)
