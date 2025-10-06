from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

from astroengine.exporters.reports.base import FigureBundle, MarginSpec, ReportMeta


class RelationshipReportBaseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    markdown: str | None = Field(default=None, description="Pre-rendered Markdown body")
    findings: list[dict[str, Any]] | None = Field(
        default=None, description="Interpretation findings used to generate Markdown"
    )
    theme: Literal["default", "dark", "print"] = Field(default="default")
    custom_theme_url: HttpUrl | None = Field(default=None)
    figures: FigureBundle = Field(default_factory=FigureBundle)
    meta: ReportMeta
    include_toc: bool = Field(default=True)
    include_appendix: bool = Field(default=True)
    paper: Literal["A4", "Letter"] = Field(default="A4")
    margins: MarginSpec = Field(default_factory=MarginSpec)
    show_header: bool = Field(default=True)
    show_footer: bool = Field(default=True)
    watermark_text: str | None = Field(default=None)
    header_label: str | None = Field(default=None)
    scores: dict[str, Any] | None = Field(default=None)
    locale: str = Field(default="en")

    @model_validator(mode="after")
    def _validate_payload(self) -> RelationshipReportBaseRequest:
        if not self.markdown and not self.findings:
            raise ValueError("report export requires either markdown or findings")
        return self


class RelationshipReportPdfRequest(RelationshipReportBaseRequest):
    pass


class RelationshipReportDocxRequest(RelationshipReportBaseRequest):
    pass


__all__ = [
    "RelationshipReportPdfRequest",
    "RelationshipReportDocxRequest",
]
