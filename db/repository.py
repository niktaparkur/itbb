import re

from sqlalchemy import select, delete, func, text, case
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

    async def add_credits(self, telegram_id: int, amount: int = 1):
        user = await self.get_or_create_user(telegram_id, None)
        user.single_check_credits += amount
        await self.session.commit()

    async def spend_credit(self, telegram_id: int):
        user = await self.get_or_create_user(telegram_id, None)
        if user.single_check_credits > 0:
            user.single_check_credits -= 1
            await self.session.commit()
            return True
        return False


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

    async def find_first_match(self, query: str) -> bool:
        clean_query = (
            re.sub(r'[\s,;*"\n«»]+', " ", query).strip().lower().replace("ё", "е")
        )
        if not clean_query:
            return False

        query_words = clean_query.split()

        strict_query = " ".join([f"+{word}*" for word in query_words])

        stmt = (
            select(func.count())
            .select_from(SearchableItem)
            .where(
                SearchableItem.search_vector.match(
                    strict_query, mysql_mode="IN BOOLEAN MODE"
                )
            )
        )

        result = await self.session.execute(stmt)
        count = result.scalar_one()

        return count > 0
