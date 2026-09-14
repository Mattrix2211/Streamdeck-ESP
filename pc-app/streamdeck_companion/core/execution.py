"""Framework-independent action execution orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from .actions import ActionCommand
from .registry import ActionRegistry


class MissingExecutorError(KeyError):
    """Raised when no runtime adapter can execute an action id."""


ActionExecutor = Callable[[Mapping[str, Any]], Any]


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    """Result envelope returned by the Core after a successful execution."""

    action_id: str
    value: Any = None


class ActionEngine:
    """Validates commands in the Core and delegates effects to adapters.

    Executors are injected by the application/integration layer. Therefore
    the Core never imports Windows, Home Assistant, Flask, ESPHome or device
    specific code.
    """

    def __init__(self, registry: ActionRegistry | None = None) -> None:
        self.registry = registry or ActionRegistry()
        self._executors: dict[str, ActionExecutor] = {}

    def register_executor(self, action_id: str, executor: ActionExecutor) -> None:
        if not callable(executor):
            raise TypeError("executor must be callable")
        self._executors[action_id] = executor

    def unregister_executor(self, action_id: str) -> None:
        self._executors.pop(action_id, None)

    def execute(self, command: ActionCommand) -> ExecutionResult:
        self.registry.validate(command)
        executor = self._executors.get(command.action_id)
        if executor is None:
            raise MissingExecutorError(command.action_id)
        value = executor(command.parameters)
        return ExecutionResult(action_id=command.action_id, value=value)
