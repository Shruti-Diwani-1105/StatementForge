import os
import csv
import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QTextBrowser, QFileDialog, QMessageBox, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor, QTextDocument, QColor, QPageLayout, QPageSize
from PyQt6.QtCore import QMarginsF
from PyQt6.QtPrintSupport import QPrinter

from services.gst_service import GSTService
from widgets.custom_button import PrimaryButton, SecondaryButton
from settings.toast import Toast

class GSTReportWidget(QWidget):
    """
    Renders an interactive, Big-4 style AI-Generated GST Reconciliation Report.
    Provides options to view dynamic charts and tables, and export to Excel, PDF, and CSV.
    """
    closed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_theme = "light"
        
        # State Data
        self.parsed_payload = None
        self.gst_ledger = []
        self.excel_path = None
        
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        # ==========================================
        # TOP BAR: TITLE & DESCRIPTION
        # ==========================================
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)
        self.title_lbl = QLabel("GST Tax Ledger Reconciliation")
        self.title_lbl.setStyleSheet("font-size: 24px; font-weight: 700; color: #0F172A;")
        self.subtitle_lbl = QLabel("Review automatically extracted GST taxes, ITC claims, and audit warnings.")
        self.subtitle_lbl.setStyleSheet("font-size: 13px; color: #64748B;")
        
        text_layout.addWidget(self.title_lbl)
        text_layout.addWidget(self.subtitle_lbl)
        header_layout.addLayout(text_layout)
        header_layout.addStretch()
        
        # Close / Return button
        self.close_btn = SecondaryButton("Back to Dashboard")
        self.close_btn.setFixedWidth(150)
        self.close_btn.clicked.connect(self.close_report)
        header_layout.addWidget(self.close_btn)
        
        main_layout.addWidget(header_widget)

        # ==========================================
        # CONTROL BAR: EXPORT BUTTONS
        # ==========================================
        control_card = QFrame()
        control_card.setObjectName("ControlCard")
        control_card.setStyleSheet("""
            QFrame#ControlCard {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 12px;
            }
        """)
        # Drop shadow for clean floating effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(12)
        shadow.setColor(QColor(0, 0, 0, 15))
        shadow.setOffset(0, 2)
        control_card.setGraphicsEffect(shadow)

        control_layout = QHBoxLayout(control_card)
        control_layout.setContentsMargins(16, 12, 16, 12)
        control_layout.setSpacing(12)

        ctrl_lbl = QLabel("Export Options:")
        ctrl_lbl.setStyleSheet("font-weight: 700; color: #475569; font-size: 12px; text-transform: uppercase;")
        control_layout.addWidget(ctrl_lbl)

        # Export Excel Button (Green accent)
        self.export_excel_btn = QPushButton("Export to Excel (.xlsx)")
        self.export_excel_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.export_excel_btn.setFixedWidth(180)
        self.export_excel_btn.setStyleSheet("""
            QPushButton {
                background-color: #F0FDF4;
                color: #16A34A;
                border: 1px solid #BBF7D0;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #DCFCE7;
            }
        """)
        self.export_excel_btn.clicked.connect(self.export_excel)
        control_layout.addWidget(self.export_excel_btn)

        # Export PDF Button (Blue accent)
        self.export_pdf_btn = QPushButton("Export to PDF (A4 Landscape)")
        self.export_pdf_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.export_pdf_btn.setFixedWidth(200)
        self.export_pdf_btn.setStyleSheet("""
            QPushButton {
                background-color: #EFF6FF;
                color: #2563EB;
                border: 1px solid #BFDBFE;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #DBEAFE;
            }
        """)
        self.export_pdf_btn.clicked.connect(self.export_pdf)
        control_layout.addWidget(self.export_pdf_btn)

        # Export CSV Button (Gray accent)
        self.export_csv_btn = QPushButton("Export to CSV (.csv)")
        self.export_csv_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.export_csv_btn.setFixedWidth(160)
        self.export_csv_btn.setStyleSheet("""
            QPushButton {
                background-color: #F1F5F9;
                color: #475569;
                border: 1px solid #E2E8F0;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #E2E8F0;
            }
        """)
        self.export_csv_btn.clicked.connect(self.export_csv)
        control_layout.addWidget(self.export_csv_btn)
        
        control_layout.addStretch()
        main_layout.addWidget(control_card)

        # ==========================================
        # REPORT VIEW (SCROLLABLE TEXTBROWSER)
        # ==========================================
        viewer_card = QFrame()
        viewer_card.setObjectName("ViewerCard")
        viewer_card.setStyleSheet("""
            QFrame#ViewerCard {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 12px;
            }
        """)
        viewer_layout = QVBoxLayout(viewer_card)
        viewer_layout.setContentsMargins(12, 12, 12, 12)

        self.report_viewer = QTextBrowser()
        self.report_viewer.setOpenExternalLinks(True)
        self.report_viewer.setStyleSheet("border: none; background-color: transparent;")
        viewer_layout.addWidget(self.report_viewer)

        main_layout.addWidget(viewer_card, stretch=1)

    def set_active_report(self, payload, excel_path):
        """Loads and processes the payload to render the GST HTML report."""
        self.parsed_payload = payload
        self.excel_path = excel_path
        
        # Extract/generate GST ledger
        transactions = payload.get("transactions", [])
        self.gst_ledger = GSTService.generate_gst_ledger(transactions)
        
        # Generate and show HTML
        html_content = GSTService.generate_gst_report_html(payload, self.gst_ledger)
        self.report_viewer.setHtml(html_content)
        Toast.success(self, "✓ GST Reconciliation Report rendered successfully!")

    def export_excel(self):
        """Prompts user to save the generated Excel report to a custom directory."""
        if not self.excel_path or not os.path.exists(self.excel_path):
            QMessageBox.warning(self, "File Not Found", "No Excel report was found for this statement.")
            return

        filename = os.path.basename(self.excel_path)
        doc_dir = os.path.expanduser("~/Documents")
        dest_path, _ = QFileDialog.getSaveFileName(
            self, "Save Excel Report", os.path.join(doc_dir, filename), "Excel Files (*.xlsx)"
        )
        
        if not dest_path:
            return

        try:
            import shutil
            shutil.copy(self.excel_path, dest_path)
            Toast.success(self, "✓ Excel Ledger exported successfully!")
            
            # Open file
            if os.name == 'nt':
                os.startfile(dest_path)
            else:
                import subprocess
                subprocess.run(["open", dest_path] if os.name == 'posix' else ["xdg-open", dest_path])
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Could not copy Excel file to destination:\n{e}")

    def export_pdf(self):
        """Prints the report HTML to a high-quality A4 Landscape PDF."""
        html_content = self.report_viewer.toHtml()
        if not html_content or "Disclaimer Footer" not in html_content:
            return

        # Prepare default filename
        bank = self.parsed_payload.get("bank_name", "Bank") if self.parsed_payload else "Statement"
        filename = f"GST_Reconciliation_Report_{bank}_{datetime.datetime.now().strftime('%Y%m%d')}.pdf"
        doc_dir = os.path.expanduser("~/Documents")
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Save GST PDF Report", os.path.join(doc_dir, filename), "PDF Files (*.pdf)"
        )
        
        if not filepath:
            return

        try:
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(filepath)
            
            # Set to A4 Landscape layout
            printer.setPageLayout(
                QPageLayout(
                    QPageSize(QPageSize.PageSizeId.A4),
                    QPageLayout.Orientation.Landscape,
                    QMarginsF(10, 10, 10, 10),
                    QPageLayout.Unit.Millimeter
                )
            )
            
            doc = QTextDocument()
            doc.setHtml(html_content)
            doc.print_(printer)
            
            Toast.success(self, "✓ PDF Report printed successfully in Landscape!")
            
            # Open file
            if os.path.exists(filepath):
                if os.name == 'nt':
                    os.startfile(filepath)
                else:
                    import subprocess
                    subprocess.run(["open", filepath] if os.name == 'posix' else ["xdg-open", filepath])
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Could not print A4 PDF:\n{e}")

    def export_csv(self):
        """Generates and saves the GST transactions ledger to a CSV file."""
        if not self.gst_ledger:
            QMessageBox.warning(self, "No Data", "No transaction ledger data is loaded to export.")
            return

        # Prompt location
        bank = self.parsed_payload.get("bank_name", "Bank") if self.parsed_payload else "Statement"
        filename = f"GST_Ledger_{bank}_{datetime.datetime.now().strftime('%Y%m%d')}.csv"
        doc_dir = os.path.expanduser("~/Documents")
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Save GST CSV Ledger", os.path.join(doc_dir, filename), "CSV Files (*.csv)"
        )
        
        if not filepath:
            return

        try:
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "Date", "Narration", "Category", "Vendor Name", "Total Amount", 
                    "Taxable Value", "GST Rate", "CGST", "SGST", "IGST", 
                    "Total GST", "ITC Eligible", "AI Confidence", "Status"
                ])
                
                for tx in self.gst_ledger:
                    writer.writerow([
                        tx.get("date", ""),
                        tx.get("narration", ""),
                        tx.get("category", ""),
                        tx.get("vendor", ""),
                        tx.get("total_amount", 0.0),
                        tx.get("base_value", 0.0),
                        f"{tx.get('gst_rate', 0.18)*100:.0f}%",
                        tx.get("cgst", 0.0),
                        tx.get("sgst", 0.0),
                        tx.get("igst", 0.0),
                        tx.get("total_gst", 0.0),
                        tx.get("itc_eligible", "No"),
                        f"{tx.get('confidence', 80):.0f}%",
                        tx.get("status", "Estimated")
                    ])
            
            Toast.success(self, "✓ GST CSV Ledger exported successfully!")
            
            # Open file
            if os.name == 'nt':
                os.startfile(filepath)
            else:
                import subprocess
                subprocess.run(["open", filepath] if os.name == 'posix' else ["xdg-open", filepath])
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Could not save CSV ledger:\n{e}")

    def close_report(self):
        """Clears states and returns to the dashboard screen."""
        self.parsed_payload = None
        self.gst_ledger = []
        self.excel_path = None
        self.report_viewer.clear()
        
        self.closed.emit()
        
        # Navigate back to dashboard
        p = self.parent()
        while p:
            if hasattr(p, "switch_dashboard_page"):
                p.switch_dashboard_page("dashboard")
                break
            p = p.parent()

    def update_theme_style(self, theme):
        """Updates colors and themes dynamically to match app settings."""
        self.current_theme = theme
        if theme == "dark":
            self.title_lbl.setStyleSheet("font-size: 24px; font-weight: 700; color: #F8FAFC;")
            self.subtitle_lbl.setStyleSheet("font-size: 13px; color: #94A3B8;")
            self.findChild(QFrame, "ControlCard").setStyleSheet("""
                QFrame#ControlCard {
                    background-color: #1E293B;
                    border: 1px solid #334155;
                    border-radius: 12px;
                }
            """)
            self.findChild(QFrame, "ViewerCard").setStyleSheet("""
                QFrame#ViewerCard {
                    background-color: #1E293B;
                    border: 1px solid #334155;
                    border-radius: 12px;
                }
            """)
        else:
            self.title_lbl.setStyleSheet("font-size: 24px; font-weight: 700; color: #0F172A;")
            self.subtitle_lbl.setStyleSheet("font-size: 13px; color: #64748B;")
            self.findChild(QFrame, "ControlCard").setStyleSheet("""
                QFrame#ControlCard {
                    background-color: #FFFFFF;
                    border: 1px solid #E2E8F0;
                    border-radius: 12px;
                }
            """)
            self.findChild(QFrame, "ViewerCard").setStyleSheet("""
                QFrame#ViewerCard {
                    background-color: #FFFFFF;
                    border: 1px solid #E2E8F0;
                    border-radius: 12px;
                }
            """)
