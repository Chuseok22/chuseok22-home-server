from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class ExamRoundItem:
    """크롤러가 반환하는 회차 1건."""
    round_name: str
    registration_start: date
    registration_end: date
    exam_date: date | None
    result_announcement_date: date | None
    source_url: str


class BaseExamCrawler(ABC):
    @abstractmethod
    def crawl(self, source_id: str) -> list[ExamRoundItem]:
        """자격증의 크롤러 소스 식별자(source_id)로 회차별 시험 일정을 조회한다."""
        ...
