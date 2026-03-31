BLOCKING_PATTERNS = (
    "включая",
    "в составе",
    "в рамках",
    "как часть",
    "входит в стоимость",
    "при заказе",
    "вместе с",
    "в комплекте",
)

CONFIRMING_PATTERNS = (
    "отдельно",
    "также выполняем",
    "а также",
    "можно заказать",
    "как отдельная услуга",
    "выполняем отдельно",
)

LIST_SEPARATORS = (",", ";", ":", " - ", " — ")
SENTENCE_SPLIT_PATTERN = r"(?<=[.!?])\s+"
CLAUSE_SPLIT_PATTERN = r"\s*(?:,|;|:| - | — )\s*"

MAX_EVIDENCE_SENTENCES = 2
MAX_DRAFT_LENGTH = 320
