import asyncio
from datetime import datetime, timedelta
import logging

from db.repository import UserRepo, CacheRepo
from scraper_tool.scraper import UniversalScraper, CaptchaServiceError
from bot.config import settings
from bot.normalizer import normalize_for_search

from db.engine import async_session_factory


logger = logging.getLogger(__name__)


class UserService:
    def __init__(self, user_repo: UserRepo):
        self.repo = user_repo

    async def has_active_subscription(self, telegram_id: int) -> bool:
        user = await self.repo.get_or_create_user(telegram_id, None)
        return (
            user.subscription_expires_at
            and user.subscription_expires_at > datetime.now()
        )

    async def can_check_url(self, telegram_id: int) -> bool:
        user = await self.repo.get_or_create_user(telegram_id, None)
        if not user.last_url_check_at:
            return True
        return datetime.now() >= user.last_url_check_at + timedelta(minutes=30)

    async def update_user_url_check_time(self, telegram_id: int):
        user = await self.repo.get_or_create_user(telegram_id, None)
        user.last_url_check_at = datetime.now()
        await self.repo.session.commit()

    async def grant_subscription(self, telegram_id: int):
        user = await self.repo.get_or_create_user(telegram_id, None)
        now = datetime.now()
        start_date = (
            user.subscription_expires_at
            if user.subscription_expires_at and user.subscription_expires_at > now
            else now
        )
        user.subscription_expires_at = start_date + timedelta(days=30)
        await self.repo.session.commit()

    async def get_credits(self, telegram_id: int) -> int:
        user = await self.repo.get_or_create_user(telegram_id, None)
        return user.single_check_credits

    async def add_credit(self, telegram_id: int):
        await self.repo.add_credits(telegram_id, 1)

    async def spend_credit(self, telegram_id: int):
        await self.repo.spend_credit(telegram_id)


class SearchService:
    def __init__(self, cache_repo: CacheRepo):
        self.repo = cache_repo

    async def get_entity_verdict(self, query: str) -> str:
        logger.info(f"Выполняю поиск для вынесения вердикта по запросу: '{query}'")
        match = await self.repo.find_first_match(query)

        if match:
            return "❗️ **Организация признана нежелательной / экстремистской / террористической.**"
        else:
            return "✅ **Организация проверена.**"

    async def check_url(self, url: str) -> str:
        logger.info(f"Запускаю скрапер для проверки URL по blocklist.rkn.gov.ru: {url}")
        try:
            with UniversalScraper(capguru_api_key=settings.CAPGURU_API_KEY) as scraper:
                blocklist_result = await asyncio.to_thread(
                    scraper.check_rkn_blocklist, url
                )

        except CaptchaServiceError as e:
            logger.error(
                f"Проверка URL '{url}' не удалась из-за сбоя сервиса капчи: {e}"
            )
            return "CAPTCHA_SERVICE_FAILED"

        blocklist_found = (
            "не найден" not in blocklist_result.get("статус", "не найден").lower()
        )

        if blocklist_found:
            logger.info(f"Вердикт по URL '{url}': ОГРАНИЧЕН (найден в blocklist).")
            return "❗️ **Доступ к сайту ограничен по решению суда.**"
        else:
            logger.info(f"Вердикт по URL '{url}': РАЗРЕШЕН (не найден в blocklist).")
            return "✅ **Ресурс разрешен.**"


async def run_scrapers_and_update_cache():
    logger.info(f"[{datetime.now()}] ЗАПУСК: Плановое обновление кэша реестров.")

    all_data = {}
    try:
        with UniversalScraper(capguru_api_key=settings.CAPGURU_API_KEY) as scraper:
            all_data = await asyncio.to_thread(scraper.run_registry_scrapers)
        logger.info("Скрапинг завершен, получены данные по всем реестрам.")
    except Exception as e:
        logger.error(
            f"Произошла КРИТИЧЕСКАЯ ошибка на этапе скрапинга, обновление прервано: {e}",
            exc_info=True,
        )
        return

    async with async_session_factory() as session:
        cache_repo = CacheRepo(session)

        try:
            minjust_data = all_data.get("minjust", [])
            if minjust_data:
                minjust_to_save = [
                    {
                        "source_type": "minjust",
                        "name": item["name"],
                        "details": item["details"],
                        "search_vector": normalize_for_search(
                            item["name"], item["details"]
                        ),
                    }
                    for item in minjust_data
                ]
                await cache_repo.update_cache("minjust", minjust_to_save)
                logger.info(
                    f"Источник 'minjust' успешно обновлен ({len(minjust_to_save)} записей)."
                )
        except Exception as e:
            logger.error(
                f"Ошибка при обновлении источника 'minjust': {e}", exc_info=True
            )

        try:
            fedsfm_data = all_data.get("fedfsm", [])
            if fedsfm_data:
                fedsfm_to_save = [
                    {
                        "source_type": "fedsfm",
                        "name": item["name"],
                        "details": item["details"],
                        "search_vector": normalize_for_search(
                            item["name"], item["details"]
                        ),
                    }
                    for item in fedsfm_data
                ]
                await cache_repo.update_cache("fedsfm", fedsfm_to_save)
                logger.info(
                    f"Источник 'fedsfm' успешно обновлен ({len(fedsfm_to_save)} записей)."
                )
        except Exception as e:
            logger.error(
                f"Ошибка при обновлении источника 'fedsfm': {e}", exc_info=True
            )

        try:
            fsb_data = all_data.get("fsb", [])
            if fsb_data:
                fsb_to_save = [
                    {
                        "source_type": "fsb",
                        "name": item["name"],
                        "details": item["details"],
                        "search_vector": normalize_for_search(
                            item["name"], item["details"]
                        ),
                    }
                    for item in fsb_data
                ]
                await cache_repo.update_cache("fsb", fsb_to_save)
                logger.info(
                    f"Источник 'fsb' успешно обновлен ({len(fsb_to_save)} записей)."
                )
        except Exception as e:
            logger.error(f"Ошибка при обновлении источника 'fsb': {e}", exc_info=True)

    logger.info(
        f"[{datetime.now()}] ЗАВЕРШЕНИЕ: Плановое обновление кэша реестров завершено."
    )
