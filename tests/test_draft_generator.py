from src.avito_splitter.draft_generator import DraftGenerator
from src.avito_splitter.schemas import EnrichedMicroCategory, Evidence, EvidenceAssessment


def make_assessment(
    mc_id: int,
    mc_title: str,
    clause_text: str,
    first_char_index: int = 0,
) -> EvidenceAssessment:
    return EvidenceAssessment(
        evidence=Evidence(
            mcId=mc_id,
            mcTitle=mc_title,
            matchedPhrase=mc_title.lower(),
            sentenceIndex=0,
            clauseIndex=0,
            clauseText=clause_text,
            clauseTextNormalized=clause_text.lower(),
            clauseTextLemmatized=clause_text.lower(),
            firstCharIndex=first_char_index,
        ),
        status="confirmed",
        reason="test",
    )


def test_generates_fallback_template_and_preserves_identity() -> None:
    category = EnrichedMicroCategory(
        mcId=101,
        mcTitle="Сантехника",
        keyPhrases=["разводка труб", "установка сантехники"],
        matchPhrases=["сантехника"],
        draftLead="Отдельно выполняем сантехнические работы.",
    )
    drafts = DraftGenerator().generate({101: category}, [make_assessment(101, "Сантехника", "сантехника")])

    assert len(drafts) == 1
    assert drafts[0].mcId == 101
    assert drafts[0].mcTitle == "Сантехника"
    assert drafts[0].text.startswith("Отдельно выполняем сантехнические работы.")
    assert "разводка труб" in drafts[0].text


def test_limits_draft_length() -> None:
    category = EnrichedMicroCategory(
        mcId=102,
        mcTitle="Электрика",
        keyPhrases=["очень длинная ключевая фраза " * 8, "вторая очень длинная фраза " * 8],
        matchPhrases=["электрика"],
        draftLead="Очень длинное вводное предложение " * 12,
    )
    drafts = DraftGenerator().generate({102: category}, [make_assessment(102, "Электрика", "электрика")])

    assert len(drafts[0].text) <= 320


def test_uses_context_snippet_when_clause_is_specific() -> None:
    category = EnrichedMicroCategory(
        mcId=103,
        mcTitle="Натяжные потолки",
        keyPhrases=["натяжные потолки"],
        matchPhrases=["натяжные потолки"],
        draftLead="Выполняем монтаж натяжных потолков как отдельную услугу.",
    )
    drafts = DraftGenerator().generate(
        {103: category},
        [make_assessment(103, "Натяжные потолки", "отдельно выполняем монтаж натяжных потолков под ключ")],
    )

    assert drafts[0].text
    assert "Отдельно выполняем монтаж натяжных потолков под ключ." in drafts[0].text
