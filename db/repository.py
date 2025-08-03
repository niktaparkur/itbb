import re

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from db.models import Base, User, SearchableItem


class BaseRepo:

    def __init__(self, session: AsyncSession, model: Base):
        self.session = session
        self.model = model

    async def get_by_id(self, obj_id: int):
        return await self.session.get(self.model, obj_id)


class UserRepo(BaseRepo):
    def __init__(self, session: AsyncSession):
        super().__init__(session, User)

    async def get_or_create_user(self, telegram_id: int, username: str | None) -> User:
        query = select(User).where(User.telegram_id == telegram_id)
        result = await self.session.execute(query)
        user = result.scalar_one_or_none()

        if user is None:
            user = User(telegram_id=telegram_id, username=username)
            self.session.add(user)
            await self.session.commit()
            await self.session.refresh(user)
        return user


class CacheRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def update_cache(self, source_type: str, data: list[dict]):
        await self.session.execute(
            delete(SearchableItem).where(SearchableItem.source_type == source_type)
        )

        if data:
            await self.session.run_sync(
                lambda session: session.bulk_insert_mappings(SearchableItem, data)
            )
        await self.session.commit()

    async def find_first_match(self, query: str) -> SearchableItem | None:
        clean_query = (
            re.sub(r'[\s,;*"\n«»]+', " ", query).strip().lower().replace("ё", "е")
        )
        if not clean_query:
            return None

        stmt = (
            select(SearchableItem)
            .where(SearchableItem.search_vector.like(f"%{clean_query}%"))
            .limit(1)
        )

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
