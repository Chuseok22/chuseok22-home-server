from .base import BaseExamCrawler, ExamRoundItem


class ManualCrawler(BaseExamCrawler):
    """Admin에서 수동으로 회차 일정을 입력하는 자격증을 위한 폴백 — 항상 빈 리스트를 반환한다."""

    def crawl(self, source_id: str) -> list[ExamRoundItem]:
        return []
