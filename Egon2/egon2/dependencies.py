"""FastAPI-Depends-Provider für Egon2."""

from __future__ import annotations

from fastapi import Depends, Request

from egon2.agents.registry import AgentRegistry
from egon2.core.agent_dispatcher import AgentDispatcher
from egon2.core.task_manager import TaskManager
from egon2.database import Database
from egon2.llm_client import LLMClient
from egon2.state import AppState


def get_state(request: Request) -> AppState:
    return request.app.state.egon


def get_db(state: AppState = Depends(get_state)) -> Database:
    assert state.db is not None
    return state.db


def get_llm(state: AppState = Depends(get_state)) -> LLMClient:
    assert state.llm is not None
    return state.llm


def get_tasks(state: AppState = Depends(get_state)) -> TaskManager:
    assert state.tasks is not None
    return state.tasks


def get_registry(state: AppState = Depends(get_state)) -> AgentRegistry:
    assert state.registry is not None
    return state.registry


def get_dispatcher(state: AppState = Depends(get_state)) -> AgentDispatcher:
    assert state.dispatcher is not None
    return state.dispatcher


__all__ = [
    "get_state",
    "get_db",
    "get_llm",
    "get_tasks",
    "get_registry",
    "get_dispatcher",
]
