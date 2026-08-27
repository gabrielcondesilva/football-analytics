"""Shared PDF assembly, reused by every Report in this package.

No test coverage here by design (see the spec's Testing Decisions): this is
the I/O layer (PDF generation), verified manually.
"""

from __future__ import annotations

import io

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import StyleSheet1, getSampleStyleSheet
from reportlab.platypus import Flowable, SimpleDocTemplate


def get_styles() -> StyleSheet1:
    return getSampleStyleSheet()


def render_pdf(story: list[Flowable]) -> bytes:
    buffer = io.BytesIO()
    SimpleDocTemplate(buffer, pagesize=A4).build(story)
    return buffer.getvalue()
