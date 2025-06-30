from contextlib import AbstractAsyncContextManager
from copy import copy
from dataclasses import dataclass
from functools import wraps
from inspect import isawaitable
from typing import (
    Awaitable,
    Callable,
    Generic,
    TypeVar,
)

from pydantic_ai import RunContext
from pydantic_ai.agent import AgentRunResult
from pydantic_ai.result import StreamedRunResult
from typing_extensions import Concatenate, ParamSpec, Self

from stone_brick.llm import (
    EventDeps,
    TaskEventDeps,
    TaskOutput,
    TaskOutputStream,
    TaskOutputStreamDelta,
    TaskStart,
    TaskStatus,
    TaskStreamRunner,
)

T = TypeVar("T")
TOutput = TypeVar("TOutput")


@dataclass(kw_only=True)
class PydanticAIDeps(Generic[TOutput]):
    event_deps: TaskEventDeps[TOutput]

    def spawn(self) -> Self:
        new_deps = copy(self)
        new_deps.event_deps = self.event_deps.spawn()
        return new_deps


TDeps = TypeVar("TDeps", bound=PydanticAIDeps)
TEventDeps = TypeVar("TEventDeps", bound=EventDeps)


def fork_pydantic_ai_ctx(ctx: RunContext[TDeps]) -> RunContext[TDeps]:
    new_ctx = copy(ctx)
    new_ctx.deps = ctx.deps.spawn()
    return new_ctx


async def prod_run_stream(
    deps: EventDeps[TaskStatus],
    stream: AbstractAsyncContextManager[StreamedRunResult[TDeps, T]],
    is_result: bool = False,
) -> StreamedRunResult[TDeps, T]:
    """Run the agent and produce `TaskEvent` stream into a channel inside the `deps`. Finally return a `StreamedRunResult`."""
    stream_deps = deps.spawn()
    await stream_deps.send(TaskOutputStream(is_result=is_result), as_root=True)

    async with stream as response:
        # Do streaming
        async for result in response.stream_text(delta=True):
            await stream_deps.send(TaskOutputStreamDelta(delta=result))
        await stream_deps.send(TaskOutputStreamDelta(delta="", stopped=True))
        return response


async def prod_run(
    deps: EventDeps[TaskStatus], run: Awaitable[AgentRunResult[T]]
) -> AgentRunResult[T]:
    """Run the agent and produce `TaskEvent` stream into a channel inside the `deps`. Finally return a `AgentRunResult`."""
    result = await run
    await deps.send(TaskOutput(data=result.output))
    return result


P = ParamSpec("P")


def flow_with_span(
    func: Callable[Concatenate[TEventDeps, P], Awaitable[T] | T],
) -> Callable[Concatenate[TEventDeps, P], Awaitable[T] | T]:
    """This decorator is used to wrap a workflow with EventDeps, which will spawn a span for function call and send a `TaskStart`."""

    @wraps(func)
    async def wrapper(ctx: TEventDeps, *args: P.args, **kwargs: P.kwargs):
        # Spawn root span
        new_ctx = ctx.spawn()
        await new_ctx.send(
            TaskStart(task_desc=func.__name__),
            as_root=True,
        )
        # Execute the actual function
        func_call = func(new_ctx, *args, **kwargs)
        if isawaitable(func_call):
            result = await func_call
        else:
            result = func_call
        return result

    return wrapper


def tool_with_span(
    func: Callable[Concatenate[RunContext[TDeps], P], Awaitable[T] | T],
) -> Callable[Concatenate[RunContext[TDeps], P], Awaitable[T] | T]:
    """This decorator is used to wrap a Pydantic AI tool, which will spawn a span for the tool call and send a `TaskStart`."""

    @wraps(func)
    async def wrapper(ctx: RunContext[TDeps], *args: P.args, **kwargs: P.kwargs):
        # Spawn root span
        new_ctx = fork_pydantic_ai_ctx(ctx)
        await new_ctx.deps.event_deps.send(
            TaskStart(task_desc=func.__name__),
            as_root=True,
        )
        # Execute the actual function
        func_call = func(new_ctx, *args, **kwargs)
        if isawaitable(func_call):
            result = await func_call
        else:
            result = func_call
        return result

    return wrapper


@dataclass()
class EndResult(Generic[T]):
    data: T


NoneType = type(None)


async def agent_run(
    run: Awaitable[AgentRunResult[T]],
    t: type[TOutput] = NoneType,
):
    """Start running the agent and yield events.
    It internally uses `prod_run` to run the agent which produces `TaskEvent` stream,
    and consuming the stream to yield events.
    """
    async with (
        TaskStreamRunner[TOutput, AgentRunResult[T]]() as runner,
        runner.run(
            prod_run(TaskEventDeps[TOutput](runner.producer), run),
        ) as loop,
    ):
        async for event in loop:
            yield event
    yield EndResult(data=runner.result)


async def agent_run_stream(
    stream: AbstractAsyncContextManager[StreamedRunResult[TDeps, T]],
    t: type[TOutput] = NoneType,
    is_result: bool = False,
):
    """Start running the agent and yield events.
    It internally uses `prod_run_stream` to run the agent which produces `TaskEvent` stream,
    and consuming the stream to yield events.
    """
    async with (
        TaskStreamRunner[TOutput, StreamedRunResult[TDeps, T]]() as runner,
        runner.run(
            prod_run_stream(TaskEventDeps[TOutput](runner.producer), stream, is_result),
        ) as loop,
    ):
        async for event in loop:
            yield event
    yield EndResult(data=runner.result)
