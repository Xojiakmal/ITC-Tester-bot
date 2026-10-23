from typing import Any, Dict, Optional
from aiogram.fsm.storage.base import BaseStorage, StorageKey, StateType
from aiogram.fsm.state import State
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.user import BotFsmState
from app.models.base import utc_now


class DatabaseFsmStorage(BaseStorage):
    """Persistent FSM storage for aiogram backed by the relational database.

    Persists multi-step conversation states across restarts.
    """

    def __init__(self, session_factory=None):
        self._session_factory = session_factory or AsyncSessionLocal

    async def set_state(self, key: StorageKey, state: StateType = None) -> None:
        state_str = state.state if isinstance(state, State) else state
        async with self._session_factory() as session:
            stmt = select(BotFsmState).where(BotFsmState.telegram_id == key.user_id)
            result = await session.execute(stmt)
            record = result.scalars().first()

            if record:
                record.state = state_str
                record.updated_at = utc_now()
            else:
                record = BotFsmState(
                    telegram_id=key.user_id,
                    state=state_str,
                    data={},
                    updated_at=utc_now(),
                )
                session.add(record)
            await session.commit()

    async def get_state(self, key: StorageKey) -> Optional[str]:
        async with self._session_factory() as session:
            stmt = select(BotFsmState.state).where(BotFsmState.telegram_id == key.user_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def set_data(self, key: StorageKey, data: Dict[str, Any]) -> None:
        async with self._session_factory() as session:
            stmt = select(BotFsmState).where(BotFsmState.telegram_id == key.user_id)
            result = await session.execute(stmt)
            record = result.scalars().first()

            if record:
                record.data = dict(data)
                record.updated_at = utc_now()
            else:
                record = BotFsmState(
                    telegram_id=key.user_id,
                    state=None,
                    data=dict(data),
                    updated_at=utc_now(),
                )
                session.add(record)
            await session.commit()

    async def get_data(self, key: StorageKey) -> Dict[str, Any]:
        async with self._session_factory() as session:
            stmt = select(BotFsmState.data).where(BotFsmState.telegram_id == key.user_id)
            result = await session.execute(stmt)
            data = result.scalar_one_or_none()
            return dict(data) if data else {}

    async def close(self) -> None:
        pass
