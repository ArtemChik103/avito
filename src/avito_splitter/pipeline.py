from __future__ import annotations

from .category_extractor import CategoryExtractor
from .draft_generator import DraftGenerator
from .independence_analyzer import IndependenceAnalyzer
from .loaders import load_catalog_bundle
from .preprocessing import build_clause_contexts
from .schemas import AdInput, EnrichedMicroCategory, SplitResponse


class ServicesSplitter:
    def __init__(self, catalog: list[EnrichedMicroCategory] | None = None) -> None:
        if catalog is None:
            _, catalog = load_catalog_bundle()
        self._catalog = {entry.mcId: entry for entry in catalog}
        self._extractor = CategoryExtractor(catalog)
        self._analyzer = IndependenceAnalyzer()
        self._draft_generator = DraftGenerator()

    def process(self, item: AdInput) -> SplitResponse:
        validated_item = AdInput.model_validate(item)
        clause_contexts = build_clause_contexts(validated_item.description)
        evidences = self._extractor.extract(validated_item, clause_contexts)
        assessments = self._analyzer.analyze(evidences, clause_contexts)
        drafts = self._draft_generator.generate(self._catalog, assessments)
        return SplitResponse(shouldSplit=bool(drafts), drafts=drafts)
