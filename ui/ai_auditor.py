"""
Backward compatibility module for AI Auditor.
Redirects to AIReportWidget in ui/ai_report.py.
"""
from ui.ai_report import AIReportWidget as AIAuditorWidget, AIWorker, DBQueryWorker, format_indian_currency

__all__ = ["AIAuditorWidget", "AIWorker", "DBQueryWorker", "format_indian_currency"]
