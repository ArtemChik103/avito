from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class MicroCategory(BaseModel):
    mcId: int
    mcTitle: str
    keyPhrases: list[str] = Field(default_factory=list)


class EnrichedMicroCategory(MicroCategory):
    matchPhrases: list[str] = Field(default_factory=list)
    draftLead: str


class AdInput(BaseModel):
    itemId: int
    mcId: int
    mcTitle: str
    description: str


class Draft(BaseModel):
    mcId: int
    mcTitle: str
    text: str


class SplitResponse(BaseModel):
    shouldSplit: bool
    drafts: list[Draft] = Field(default_factory=list)


class GoldExpectation(BaseModel):
    shouldSplit: bool
    draftMcIds: list[int] = Field(default_factory=list)


class GoldExample(BaseModel):
    name: str
    item: AdInput
    expected: GoldExpectation


class ClauseContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    sentenceIndex: int
    clauseIndex: int
    sentenceText: str
    clauseText: str
    clauseTextNormalized: str
    clauseTextLemmatized: str


class Evidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    mcId: int
    mcTitle: str
    matchedPhrase: str
    sentenceIndex: int
    clauseIndex: int
    clauseText: str
    clauseTextNormalized: str
    clauseTextLemmatized: str
    firstCharIndex: int


class EvidenceAssessment(BaseModel):
    model_config = ConfigDict(frozen=True)

    evidence: Evidence
    status: Literal["blocked", "confirmed", "neutral"]
    reason: str


class DraftContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    category: EnrichedMicroCategory
    assessments: list[EvidenceAssessment]
