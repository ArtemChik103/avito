from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class MicroCategory(BaseModel):
    mcId: int
    mcTitle: str
    keyPhrases: list[str] = Field(default_factory=list)

    @field_validator("mcTitle")
    @classmethod
    def validate_title(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("mcTitle must not be empty")
        return normalized

    @field_validator("keyPhrases")
    @classmethod
    def validate_key_phrases(cls, value: list[str]) -> list[str]:
        cleaned = [phrase.strip() for phrase in value if phrase.strip()]
        if not cleaned:
            raise ValueError("keyPhrases must contain at least one non-empty phrase")
        return cleaned


class EnrichedMicroCategory(MicroCategory):
    matchPhrases: list[str] = Field(default_factory=list)
    draftLead: str

    @field_validator("matchPhrases")
    @classmethod
    def validate_match_phrases(cls, value: list[str]) -> list[str]:
        cleaned = [phrase.strip() for phrase in value if phrase.strip()]
        if not cleaned:
            raise ValueError("matchPhrases must contain at least one non-empty phrase")
        return cleaned

    @field_validator("draftLead")
    @classmethod
    def validate_draft_lead(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("draftLead must not be empty")
        return normalized


class AdInput(BaseModel):
    itemId: int
    mcId: int
    mcTitle: str
    description: str

    @field_validator("mcTitle", "description")
    @classmethod
    def validate_non_empty_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("text fields must not be empty")
        return normalized


class Draft(BaseModel):
    mcId: int
    mcTitle: str
    text: str

    @field_validator("mcTitle", "text")
    @classmethod
    def validate_draft_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("draft fields must not be empty")
        return normalized


class SplitResponse(BaseModel):
    shouldSplit: bool
    drafts: list[Draft] = Field(default_factory=list)

    @model_validator(mode="after")
    def ensure_consistency(self) -> "SplitResponse":
        if self.shouldSplit != bool(self.drafts):
            raise ValueError("shouldSplit must reflect whether drafts are present")
        return self


class GoldExpectation(BaseModel):
    shouldSplit: bool
    draftMcIds: list[int] = Field(default_factory=list)

    @model_validator(mode="after")
    def ensure_consistency(self) -> "GoldExpectation":
        if self.shouldSplit != bool(self.draftMcIds):
            raise ValueError("gold expectation shouldSplit must reflect draftMcIds")
        return self


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
