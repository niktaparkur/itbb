import re
from transliterate import translit
from typing import Optional


def normalize_for_search(name: str, details: Optional[str] = None) -> str:
    aliases = re.findall(r"\((.*?)\)", name)

    if details:
        detail_aliases = re.findall(r"ОГРН: «(.*?)»", details)
        aliases.extend(detail_aliases)

    base_name = re.sub(r"\(.*?\)", "", name).strip()

    all_variants = [base_name] + aliases

    processed_variants = set()
    for variant in all_variants:
        cleaned = re.sub(r'[,;*"\n«»]', " ", variant)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        if not cleaned:
            continue

        cyrillic_variant = cleaned.lower().replace("ё", "е")

        latin_variant = translit(cyrillic_variant, "ru", reversed=True)

        processed_variants.add(cyrillic_variant)
        if latin_variant != cyrillic_variant:
            processed_variants.add(latin_variant)

    return " ".join(list(processed_variants))
