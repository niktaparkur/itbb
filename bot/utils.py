from urllib.parse import urlparse


def normalize_url_for_search(url: str) -> str:
    if "://" not in url:
        url = "http://" + url

    parsed_uri = urlparse(url)
    domain = parsed_uri.netloc

    if domain.startswith("www."):
        domain = domain[4:]

    return domain
