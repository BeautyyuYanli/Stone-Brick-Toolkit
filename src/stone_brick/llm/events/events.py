import math
from dataclasses import dataclass, field
from typing import (
    Generic,
    Optional,
    TypeVar,
)
from typing_extensions import Self
from uuid import uuid4

from anyio import create_memory_object_stream
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
from pydantic import BaseModel, Field
from copy import copy

T = TypeVar("T")


class Context(BaseModel):
    trace_id: int = Field(default_factory=lambda: uuid4().int)
    span_id: int = Field(default_factory=lambda: uuid4().int)
    parent_id: Optional[int] = None

    def spawn(self) -> "Context":
        return Context(
            trace_id=self.trace_id,
            span_id=uuid4().int,
            parent_id=self.span_id,
        )


class Event(BaseModel, Generic[T]):
    ctx: Context | None = None
    event_type: T


TE = TypeVar("TE", bound=Event)

@dataclass(kw_only=True)
class EventDeps(Generic[TE]):
    _event_span: Context = field(default_factory=lambda: Context())
    _event_stream: tuple[MemoryObjectSendStream[TE], MemoryObjectReceiveStream[TE]] = field(
        default_factory=lambda: create_memory_object_stream(max_buffer_size=math.inf)
    )

    async def event_send(self, event: TE):
        event.ctx = event.ctx or self._event_span.spawn()
        await self._event_stream[0].send(event)


    def spawn(self) -> Self:
        another_deps = copy(self)
        another_deps._event_span = self._event_span.spawn()
        return another_deps
