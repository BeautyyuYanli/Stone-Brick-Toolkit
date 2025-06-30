from copy import copy
from dataclasses import dataclass, field
from typing import (
    Generic,
    Optional,
    TypeVar,
)
from uuid import uuid4

from anyio.streams.memory import MemoryObjectSendStream
from pydantic import BaseModel, Field
from typing_extensions import Self

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
    content: T


TE = TypeVar("TE", bound=Event)


@dataclass()
class EventDeps(Generic[T]):
    producer: MemoryObjectSendStream[Event[T]]
    span: Context = field(default_factory=lambda: Context())

    async def send(self, content: T, as_root: bool = False):
        if as_root:
            await self.producer.send(Event(ctx=self.span, content=content))
        else:
            await self.producer.send(Event(ctx=self.span.spawn(), content=content))

    def spawn(self) -> Self:
        another_deps = copy(self)
        another_deps.span = self.span.spawn()
        return another_deps
