import re
import time
import logging
import requests
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class CaptchaServiceError(Exception):
    pass


class UniversalScraper:
    _CAPGURU_IN_URL = "https://api.cap.guru/in.php"
    _CAPGURU_RES_URL = "https://api.cap.guru/res.php"

    _REGISTRY_TARGETS = {
        "minjust": {
            "url": "https://minjust.gov.ru/ru/documents/7756/",
            "wait_for": (By.ID, "documentcontent"),
            "parser_method": "_parse_minjust",
        },
        "fedfsm": {
            "url": "https://fedsfm.ru/documents/terrorists-catalog-portal-act",
            "wait_for": (By.ID, "russianFL"),
            "parser_method": "_parse_fedfsm",
        },
        "fsb": {
            "url": "http://www.fsb.ru/fsb/npd/terror.htm",
            "wait_for": (By.CLASS_NAME, "table"),
            "parser_method": "_parse_fsb",
        },
    }

    def __init__(self, capguru_api_key: str, headless: bool = True):
        self.capguru_api_key = capguru_api_key
        self.logger = logging.getLogger(self.__class__.__name__)
        self.driver = self._initialize_driver(headless)

    def _initialize_driver(self, headless: bool):
        self.logger.info("Инициализация драйвера WebDriver (Chrome)...")
        options = Options()
        if headless:
            options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-extensions")
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        )
        try:
            service = ChromeService()
            driver = webdriver.Chrome(service=service, options=options)
            driver.set_page_load_timeout(40)
            driver.implicitly_wait(10)
            self.logger.info("Драйвер Chrome успешно инициализирован.")
            return driver
        except Exception as e:
            self.logger.error(
                "Ошибка при инициализации драйвера Chrome: %s", e, exc_info=True
            )
            raise

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    @staticmethod
    def _parse_minjust(html_content: str) -> list[dict]:
        soup = BeautifulSoup(html_content, "html.parser")
        table = soup.find("table")
        if not table:
            return []

        data = []
        for row in table.find_all("tr"):
            cells = row.find_all("td")

            if len(cells) < 4:
                continue

            header_cells = row.find_all("th")
            if (
                len(header_cells) > 3
                and "Полное и сокращенное" in header_cells[3].get_text()
            ):
                continue

            name = cells[3].get_text(strip=True)

            if not name:
                continue

            details_parts = []
            if cells[0].get_text(strip=True):
                details_parts.append(
                    f"Номер в перечне: {cells[0].get_text(strip=True)}"
                )
            if cells[1].get_text(strip=True):
                details_parts.append(
                    f"Распоряжение Минюста: {cells[1].get_text(strip=True)}"
                )
            if cells[2].get_text(strip=True):
                details_parts.append(
                    f"Решение Генпрокуратуры: {cells[2].get_text(strip=True)}"
                )

            details_str = " | ".join(details_parts)
            data.append({"name": name, "details": details_str})

        return data

    @staticmethod
    def _parse_fedfsm(html_content: str) -> list[dict]:
        all_entries = []
        soup = BeautifulSoup(html_content, "html.parser")
        org_container = soup.find("div", id="russianUL")
        if org_container:
            for item in org_container.find_all("li"):
                all_entries.append(
                    {
                        "name": re.sub(r"^\d+\.\s*", "", item.get_text(strip=True)),
                        "details": "Тип: Организация",
                    }
                )
        ind_container = soup.find("div", id="russianFL")
        if ind_container:
            pattern = re.compile(r"^\d+\.\s*(.*?),\s*([\d\.]+\s*г\.р\.)\s*(.*);?$")
            for item in ind_container.find_all("li"):
                text = item.get_text(strip=True).replace("\n", " ")
                match = pattern.search(text)
                if match:
                    all_entries.append(
                        {
                            "name": match.group(1).strip(),
                            "details": f"Тип: Физ. лицо | ДР: {match.group(2).strip()} | Место рождения: {match.group(3).strip(';')}",
                        }
                    )
        return all_entries

    @staticmethod
    def _parse_fsb(html_content: str) -> list[dict]:
        soup = BeautifulSoup(html_content, "html.parser")
        table = soup.find("table", class_="table")
        if not table:
            return []
        organizations_list = []
        for row in table.find("tbody").find_all("tr")[1:]:
            cells = row.find_all("td")
            if len(cells) == 3:
                name = cells[1].get_text(separator=" ", strip=True)
                court_info = " ".join(
                    div.get_text(strip=True) for div in cells[2].find_all("div")
                )
                organizations_list.append(
                    {"name": name, "details": re.sub(r"\s+", " ", court_info).strip()}
                )
        return organizations_list

    @staticmethod
    def _parse_rkn_blocklist_result(soup: BeautifulSoup) -> dict:
        search_res = soup.find("p", id="searchresurs")
        if not search_res:
            return {
                "статус": "Ресурс не найден в реестре (отсутствует 'searchresurs')."
            }
        summary = search_res.get_text(strip=True)
        restrictions = []
        table = soup.find("table", id="tbl_search")
        if table:
            for row in table.find("tbody").find_all("tr"):
                cells = [
                    td.get_text(separator="\n", strip=True) for td in row.find_all("td")
                ]
                if len(cells) == 3:
                    restrictions.append(
                        {
                            "Тип ограничения": cells[0],
                            "Статья": cells[1],
                            "Основание": cells[2],
                        }
                    )
        if not restrictions:
            return {"статус": f"{summary}. Ограничений не найдено."}
        return {"статус": summary, "ограничения": restrictions}

    def _solve_captcha(self, vernet_param: int):
        try:
            wait = WebDriverWait(self.driver, 20)
            try:
                captcha_image_element = wait.until(
                    EC.visibility_of_element_located((By.ID, "captcha_image"))
                )
            except Exception:
                self.logger.warning(
                    "Не удалось найти элемент 'captcha_image' на странице."
                )
                return None
            image_base64 = captcha_image_element.screenshot_as_base64
            self.logger.info("Изображение капчи получено. Отправка в сервис решения...")
            try:
                payload = {
                    "key": self.capguru_api_key,
                    "method": "base64",
                    "body": image_base64,
                    "json": 1,
                }
                response = requests.post(self._CAPGURU_IN_URL, data=payload, timeout=30)
                response.raise_for_status()
                response_data = response.json()
            except requests.exceptions.RequestException as e:
                self.logger.error(
                    "Сервис решения капчи недоступен (ошибка сети): %s", e
                )
                raise CaptchaServiceError(
                    "Сервис решения капчи временно недоступен (ошибка сети)."
                )
            if response_data.get("status") != 1:
                error_text = response_data.get("request", "Неизвестная ошибка API")
                self.logger.error("API сервиса капчи вернуло ошибку: %s", error_text)
                if "ERROR_ZERO_BALANCE" in error_text:
                    raise CaptchaServiceError(
                        "Закончились средства на балансе сервиса решения капчи."
                    )
                raise CaptchaServiceError(f"Ошибка сервиса капчи: {error_text}")
            captcha_id = response_data.get("request")
            self.logger.info("Капча успешно отправлена. ID задачи: %s", captcha_id)
            time.sleep(10)
            for _ in range(20):
                params = {
                    "key": self.capguru_api_key,
                    "action": "get",
                    "id": captcha_id,
                    "json": 1,
                    "vernet": vernet_param,
                }
                result_response = requests.get(
                    self._CAPGURU_RES_URL, params=params, timeout=30
                )
                result_data = result_response.json()
                if result_data.get("status") == 1:
                    solution = result_data.get("request")
                    self.logger.info("Капча решена. Ответ: %s", solution)
                    return solution
                elif result_data.get("request") == "CAPCHA_NOT_READY":
                    self.logger.info("Капча еще не готова, ждем 5 секунд...")
                    time.sleep(5)
                else:
                    error_text = result_data.get(
                        "request", "Неизвестная ошибка получения результата"
                    )
                    self.logger.error(
                        "Ошибка при получении решения капчи: %s", error_text
                    )
                    if "ERROR_CAPTCHA_UNSOLVABLE" in error_text:
                        raise CaptchaServiceError(
                            "Капча не может быть решена. Возможно, она слишком сложная."
                        )
                    raise CaptchaServiceError(f"Ошибка сервиса капчи: {error_text}")
            self.logger.warning(
                "Не удалось получить решение капчи за отведенное время."
            )
            return None
        except CaptchaServiceError:
            raise
        except Exception as e:
            self.logger.error(
                "Произошла непредвиденная ошибка при работе с капчей: %s",
                e,
                exc_info=True,
            )
            return None

    def _click_element_robustly(self, wait, actions, selector_type, selector_value):
        element = wait.until(
            EC.element_to_be_clickable((selector_type, selector_value))
        )
        self.driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center'});", element
        )
        time.sleep(0.5)
        actions.move_to_element(element).click().perform()
        self.logger.info("Успешный клик по элементу: %s", selector_value)
        time.sleep(2)

    def _get_page_content(self, target_name: str, url: str, wait_for: tuple):
        try:
            self.driver.get(url)
            wait = WebDriverWait(self.driver, 60)
            actions = ActionChains(self.driver)
            if target_name == "fedfsm":
                self.logger.info("Выполняю последовательность кликов для fedsfm.ru...")
                try:
                    self._click_element_robustly(
                        wait,
                        actions,
                        By.CSS_SELECTOR,
                        'a[data-toggle="collapse"][href="#NationalPart"]',
                    )
                    self._click_element_robustly(
                        wait,
                        actions,
                        By.CSS_SELECTOR,
                        'a[data-toggle="collapse"][href="#russianUL"]',
                    )
                    self._click_element_robustly(
                        wait,
                        actions,
                        By.CSS_SELECTOR,
                        'a[data-toggle="collapse"][href="#russianFL"]',
                    )
                    wait.until(EC.visibility_of_element_located((By.ID, "russianUL")))
                    wait.until(EC.visibility_of_element_located(wait_for))
                    self.logger.info("Все секции fedsfm.ru успешно раскрыты.")
                except Exception as click_error:
                    self.logger.error(
                        "Ошибка во время кликов на fedsfm.ru: %s",
                        click_error,
                        exc_info=True,
                    )
                    self.driver.save_screenshot(f"fedsfm_error_{int(time.time())}.png")
                    return None
            else:
                wait.until(EC.visibility_of_element_located(wait_for))
            return self.driver.page_source
        except Exception as e:
            self.logger.error(
                "Ошибка при получении страницы %s: %s", url, e, exc_info=True
            )
            return None

    def run_registry_scrapers(self) -> dict[str, list]:
        self.logger.info("=== ЗАПУСК СКРАПИНГА РЕЕСТРОВ ===")
        all_data = {}
        for i, (name, config) in enumerate(list(self._REGISTRY_TARGETS.items())):
            self.logger.info("--- Начинаю обработку: %s (%s) ---", name, config["url"])
            html_content = self._get_page_content(
                name, config["url"], config["wait_for"]
            )
            if not html_content:
                self.logger.warning("Не удалось получить контент для %s.", name)
                all_data[name] = []
                continue
            parsed_data = getattr(self, config["parser_method"])(html_content)
            all_data[name] = parsed_data
            self.logger.info(
                "Парсинг %s завершен. Найдено записей: %d", name, len(parsed_data)
            )
            if i < len(self._REGISTRY_TARGETS) - 1:
                time.sleep(2)
        self.logger.info("=== СКРАПИНГ РЕЕСТРОВ ЗАВЕРШЕН ===")
        return all_data

    def check_rkn_blocklist(self, domain_to_check: str) -> dict:
        site_url = "https://blocklist.rkn.gov.ru/"
        self.logger.info(
            "--- Начинаю проверку '%s' на сайте %s ---", domain_to_check, site_url
        )
        max_retries = 15
        for attempt in range(max_retries):
            try:
                self.driver.get(site_url)
                time.sleep(1)
                captcha_solution = self._solve_captcha(vernet_param=2)
                if not captcha_solution:
                    self.logger.warning(
                        "Не удалось решить капчу (попытка %d/%d).",
                        attempt + 1,
                        max_retries,
                    )
                    continue
                self.driver.find_element(By.ID, "captcha").send_keys(captcha_solution)
                self.driver.find_element(By.ID, "inputMsg").send_keys(domain_to_check)
                self.driver.find_element(By.ID, "send_but2").click()
                self.logger.info(
                    "Данные для проверки '%s' отправлены.", domain_to_check
                )
                time.sleep(5)
                soup = BeautifulSoup(self.driver.page_source, "html.parser")
                error_div = soup.find("div", id="error")
                if (
                    error_div
                    and "неверно указан защитный код"
                    in error_div.get_text(strip=True).lower()
                ):
                    self.logger.warning(
                        "Ошибка: неверно указан защитный код (попытка %d/%d).",
                        attempt + 1,
                        max_retries,
                    )
                    continue
                return self._parse_rkn_blocklist_result(soup)
            except Exception as e:
                self.logger.error(
                    "Критическая ошибка при проверке blocklist (попытка %d/%d): %s",
                    attempt + 1,
                    max_retries,
                    e,
                    exc_info=True,
                )
                time.sleep(5)
        return {
            "статус": f"Критическая ошибка: не удалось выполнить проверку для '{domain_to_check}' после {max_retries} попыток."
        }

    def close(self):
        if self.driver:
            self.logger.info("Закрытие драйвера WebDriver...")
            self.driver.quit()
            self.driver = None
            self.logger.info("Драйвер закрыт.")
