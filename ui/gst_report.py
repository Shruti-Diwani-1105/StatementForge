import os
import csv
import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QTextBrowser, QFileDialog, QMessageBox, QGraphicsDropShadowEffect,
    QTabWidget, QTableWidget, QTableWidgetItem, QComboBox, QHeaderView
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
    Features date range filtering, GSTR-2B 3-way reconciliation, live grid editing, and exports.
    """
    closed = pyqtSignal()

    CATEGORIES_LIST = [
        "Bank Charges", "Processing Fees", "Service Charges", "Courier Charges", 
        "Office Expenses", "Utilities", "Software Subscription", "Vendor Payment", 
        "Fuel", "Travel", "Miscellaneous", "Personal"
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_theme = "light"
        
        # State Data
        self.parsed_payload = None
        self.gst_ledger = []
        self.excel_path = None
        self.gstr2b_summary = None
        self.current_date_filter = "All Dates"
        self._is_updating_table = False
        
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
        self.title_lbl = QLabel("GST Tax Ledger Reconciliation & 3-Way Audit")
        self.title_lbl.setStyleSheet("font-size: 22px; font-weight: 700; color: #0F172A;")
        self.subtitle_lbl = QLabel("Filter date ranges, import GSTR-2B purchase files, edit ledger items, and export reports.")
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
        # CONTROL BAR: FILTERS, RECONCILE & EXPORTS
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
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(12)
        shadow.setColor(QColor(0, 0, 0, 15))
        shadow.setOffset(0, 2)
        control_card.setGraphicsEffect(shadow)

        control_layout = QHBoxLayout(control_card)
        control_layout.setContentsMargins(16, 12, 16, 12)
        control_layout.setSpacing(12)

        # 1. Date Range Filter
        filter_lbl = QLabel("Period Filter:")
        filter_lbl.setStyleSheet("font-weight: 700; color: #475569; font-size: 11px; text-transform: uppercase;")
        control_layout.addWidget(filter_lbl)

        self.date_filter_combo = QComboBox()
        self.date_filter_combo.addItems([
            "All Dates", "Q1 (Apr - Jun)", "Q2 (Jul - Sep)", "Q3 (Oct - Dec)", "Q4 (Jan - Mar)"
        ])
        self.date_filter_combo.setFixedWidth(140)
        self.date_filter_combo.setStyleSheet("""
            QComboBox {
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 5px 10px;
                font-weight: 600;
                color: #1E293B;
                background-color: #F8FAFC;
            }
        """)
        self.date_filter_combo.currentTextChanged.connect(self.on_date_filter_changed)
        control_layout.addWidget(self.date_filter_combo)

        # 2. Reconcile GSTR-2B Button (Purple accent)
        self.gstr2b_btn = QPushButton("Import GSTR-2B / Purchase (.xlsx)")
        self.gstr2b_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.gstr2b_btn.setStyleSheet("""
            QPushButton {
                background-color: #F5F3FF;
                color: #7C3AED;
                border: 1px solid #DDD6FE;
                border-radius: 6px;
                padding: 7px 14px;
                font-weight: 600;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #EDE9FE;
            }
        """)
        self.gstr2b_btn.clicked.connect(self.import_gstr2b_file)
        control_layout.addWidget(self.gstr2b_btn)

        control_layout.addSpacing(16)
        ctrl_lbl = QLabel("Export:")
        ctrl_lbl.setStyleSheet("font-weight: 700; color: #475569; font-size: 11px; text-transform: uppercase;")
        control_layout.addWidget(ctrl_lbl)

        # Export Excel Button (Green accent)
        self.export_excel_btn = QPushButton("Excel (.xlsx)")
        self.export_excel_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.export_excel_btn.setStyleSheet("""
            QPushButton {
                background-color: #F0FDF4;
                color: #16A34A;
                border: 1px solid #BBF7D0;
                border-radius: 6px;
                padding: 7px 14px;
                font-weight: 600;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #DCFCE7; }
        """)
        self.export_excel_btn.clicked.connect(self.export_excel)
        control_layout.addWidget(self.export_excel_btn)

        # Export PDF Button (Blue accent)
        self.export_pdf_btn = QPushButton("PDF (A4 Landscape)")
        self.export_pdf_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.export_pdf_btn.setStyleSheet("""
            QPushButton {
                background-color: #EFF6FF;
                color: #2563EB;
                border: 1px solid #BFDBFE;
                border-radius: 6px;
                padding: 7px 14px;
                font-weight: 600;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #DBEAFE; }
        """)
        self.export_pdf_btn.clicked.connect(self.export_pdf)
        control_layout.addWidget(self.export_pdf_btn)

        # Export CSV Button (Gray accent)
        self.export_csv_btn = QPushButton("CSV (.csv)")
        self.export_csv_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.export_csv_btn.setStyleSheet("""
            QPushButton {
                background-color: #F1F5F9;
                color: #475569;
                border: 1px solid #E2E8F0;
                border-radius: 6px;
                padding: 7px 14px;
                font-weight: 600;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #E2E8F0; }
        """)
        self.export_csv_btn.clicked.connect(self.export_csv)
        control_layout.addWidget(self.export_csv_btn)

        # Send via Email Button (Purple/Blue accent)
        self.send_email_btn = QPushButton("✉ Send via Email")
        self.send_email_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.send_email_btn.setStyleSheet("""
            QPushButton {
                background-color: #F5F3FF;
                color: #7C3AED;
                border: 1px solid #DDD6FE;
                border-radius: 6px;
                padding: 7px 14px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #EDE9FE; }
        """)
        self.send_email_btn.clicked.connect(self.open_email_composer)
        control_layout.addWidget(self.send_email_btn)
        
        control_layout.addStretch()
        main_layout.addWidget(control_card)

        # ==========================================
        # DUAL TAB VIEW: ANALYTICS & INTERACTIVE GRID
        # ==========================================
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #E2E8F0;
                border-radius: 12px;
                background-color: #FFFFFF;
            }
            QTabBar::tab {
                background-color: #F1F5F9;
                color: #64748B;
                padding: 10px 20px;
                font-weight: 600;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 4px;
            }
            QTabBar::tab:selected {
                background-color: #FFFFFF;
                color: #2563EB;
                border-bottom: 2px solid #2563EB;
            }
        """)

        # Tab 1: Visual Report (QTextBrowser)
        self.report_viewer = QTextBrowser()
        self.report_viewer.setOpenExternalLinks(True)
        self.report_viewer.setStyleSheet("border: none; background-color: transparent;")
        self.tab_widget.addTab(self.report_viewer, "📊 Visual Audit & Analytics")

        # Tab 2: Interactive Grid Editor (QTableWidget)
        self.grid_editor = QTableWidget()
        self.grid_editor.setAlternatingRowColors(True)
        self.grid_editor.setStyleSheet("""
            QTableWidget {
                border: none;
                gridline-color: #E2E8F0;
                font-size: 11px;
            }
            QHeaderView::section {
                background-color: #FFFBEB;
                color: #B45309;
                font-weight: bold;
                border: 1px solid #FDE68A;
                padding: 6px;
            }
        """)
        self.grid_editor.cellChanged.connect(self.on_grid_cell_changed)
        self.tab_widget.addTab(self.grid_editor, "✏ Interactive Ledger Editor")

        main_layout.addWidget(self.tab_widget, stretch=1)

    def set_active_report(self, payload, excel_path):
        """Loads and processes the payload to render the GST HTML report and populate the editor."""
        self.parsed_payload = payload
        self.excel_path = excel_path
        self.gstr2b_summary = None
        
        transactions = payload.get("transactions", [])
        self.gst_ledger = GSTService.generate_gst_ledger(transactions)
        
        self.render_all_views()
        Toast.success(self, "✓ GST Reconciliation Report & Editor rendered successfully!")

    def render_all_views(self):
        """Re-renders both the HTML report tab and the interactive QTableWidget grid."""
        if not self.parsed_payload:
            return

        # 1. Render HTML report
        html_content = GSTService.generate_gst_report_html(
            self.parsed_payload, self.gst_ledger, self.current_date_filter, self.gstr2b_summary
        )
        self.report_viewer.setHtml(html_content)

        # 2. Populate Interactive QTableWidget
        active_ledger = GSTService.filter_ledger_by_date(self.gst_ledger, self.current_date_filter)
        self.populate_grid_editor(active_ledger)

    def populate_grid_editor(self, active_ledger):
        """Populates the QTableWidget with editable fields."""
        self._is_updating_table = True
        
        headers = [
            "Date", "Narration", "Category", "Vendor Name", "Vendor GSTIN", 
            "Total Amount", "Taxable Val", "GST Rate", "Total GST", "ITC Eligible", "GSTR-2B Status"
        ]
        
        self.grid_editor.clear()
        self.grid_editor.setRowCount(len(active_ledger))
        self.grid_editor.setColumnCount(len(headers))
        self.grid_editor.setHorizontalHeaderLabels(headers)
        
        for r_idx, tx in enumerate(active_ledger):
            # Read-only items
            item_date = QTableWidgetItem(tx.get("date", ""))
            item_date.setFlags(item_date.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.grid_editor.setItem(r_idx, 0, item_date)

            item_narr = QTableWidgetItem(tx.get("narration", ""))
            item_narr.setFlags(item_narr.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.grid_editor.setItem(r_idx, 1, item_narr)

            # Category Dropdown Editor
            cat_combo = QComboBox()
            cat_combo.addItems(self.CATEGORIES_LIST)
            cat_combo.setCurrentText(tx.get("category", "Miscellaneous"))
            cat_combo.currentTextChanged.connect(lambda text, r=r_idx: self.on_category_edited(r, text))
            self.grid_editor.setCellWidget(r_idx, 2, cat_combo)

            # Editable Vendor Name
            item_vendor = QTableWidgetItem(tx.get("vendor", ""))
            self.grid_editor.setItem(r_idx, 3, item_vendor)

            # Editable Vendor GSTIN
            item_gstin = QTableWidgetItem(tx.get("gstin", "Unassigned"))
            self.grid_editor.setItem(r_idx, 4, item_gstin)

            # Read-only Amounts
            item_amt = QTableWidgetItem(f"₹ {tx.get('total_amount', 0.0):,.2f}")
            item_amt.setFlags(item_amt.flags() & ~Qt.ItemFlag.ItemIsEditable)
            item_amt.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.grid_editor.setItem(r_idx, 5, item_amt)

            item_base = QTableWidgetItem(f"₹ {tx.get('base_value', 0.0):,.2f}")
            item_base.setFlags(item_base.flags() & ~Qt.ItemFlag.ItemIsEditable)
            item_base.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.grid_editor.setItem(r_idx, 6, item_base)

            item_rate = QTableWidgetItem(f"{tx.get('gst_rate', 0.18)*100:.0f}%")
            item_rate.setFlags(item_rate.flags() & ~Qt.ItemFlag.ItemIsEditable)
            item_rate.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.grid_editor.setItem(r_idx, 7, item_rate)

            item_gst = QTableWidgetItem(f"₹ {tx.get('total_gst', 0.0):,.2f}")
            item_gst.setFlags(item_gst.flags() & ~Qt.ItemFlag.ItemIsEditable)
            item_gst.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.grid_editor.setItem(r_idx, 8, item_gst)

            # ITC Eligible Dropdown Editor
            itc_combo = QComboBox()
            itc_combo.addItems(["Yes", "No"])
            itc_combo.setCurrentText(tx.get("itc_eligible", "No"))
            itc_combo.currentTextChanged.connect(lambda text, r=r_idx: self.on_itc_edited(r, text))
            self.grid_editor.setCellWidget(r_idx, 9, itc_combo)

            # GSTR-2B Status item
            item_gstr = QTableWidgetItem(tx.get("gstr2b_status", "Not Reconciled"))
            item_gstr.setFlags(item_gstr.flags() & ~Qt.ItemFlag.ItemIsEditable)
            item_gstr.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.grid_editor.setItem(r_idx, 10, item_gstr)

        self.grid_editor.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.grid_editor.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._is_updating_table = False

    def on_grid_cell_changed(self, row, col):
        """Fires when vendor or gstin text is edited in the grid."""
        if self._is_updating_table or not self.gst_ledger:
            return

        active_ledger = GSTService.filter_ledger_by_date(self.gst_ledger, self.current_date_filter)
        if row < 0 or row >= len(active_ledger):
            return

        tx = active_ledger[row]
        if col == 3: # Vendor Name
            new_val = self.grid_editor.item(row, col).text().strip()
            tx["vendor"] = new_val
        elif col == 4: # Vendor GSTIN
            new_val = self.grid_editor.item(row, col).text().strip()
            tx["gstin"] = new_val

        # Re-render HTML view silently
        html_content = GSTService.generate_gst_report_html(
            self.parsed_payload, self.gst_ledger, self.current_date_filter, self.gstr2b_summary
        )
        self.report_viewer.setHtml(html_content)

    def on_category_edited(self, row, new_category):
        """Fires when the user changes a transaction category dropdown."""
        if self._is_updating_table or not self.gst_ledger:
            return
            
        active_ledger = GSTService.filter_ledger_by_date(self.gst_ledger, self.current_date_filter)
        if row < 0 or row >= len(active_ledger):
            return

        tx = active_ledger[row]
        tx["category"] = new_category
        tx["is_business"] = False if new_category == "Personal" else True
        
        # Recalculate rate and breakdown
        rate = GSTService.detect_gst_rate(new_category, tx["narration"])
        tx["gst_rate"] = rate
        itc_eligible = GSTService.is_itc_eligible(new_category, tx["is_business"])
        
        breakdown = GSTService.calculate_gst_breakdown(tx["total_amount"], rate, tx["narration"])
        tx["base_value"] = breakdown["base_value"]
        tx["cgst"] = breakdown["cgst"]
        tx["sgst"] = breakdown["sgst"]
        tx["igst"] = breakdown["igst"]
        tx["total_gst"] = breakdown["total_gst"]
        tx["itc_eligible"] = "Yes" if (itc_eligible and breakdown["total_gst"] > 0) else "No"
        
        self.render_all_views()
        Toast.success(self, f"Updated row #{row+1} category to '{new_category}'")

    def on_itc_edited(self, row, new_itc):
        """Fires when the user toggles ITC eligibility."""
        if self._is_updating_table or not self.gst_ledger:
            return
            
        active_ledger = GSTService.filter_ledger_by_date(self.gst_ledger, self.current_date_filter)
        if row < 0 or row >= len(active_ledger):
            return

        tx = active_ledger[row]
        tx["itc_eligible"] = new_itc
        
        html_content = GSTService.generate_gst_report_html(
            self.parsed_payload, self.gst_ledger, self.current_date_filter, self.gstr2b_summary
        )
        self.report_viewer.setHtml(html_content)

    def on_date_filter_changed(self, new_filter):
        """Fires when user selects a new period filter dropdown option."""
        self.current_date_filter = new_filter
        self.render_all_views()
        Toast.info(self, f"Filtered view to {new_filter}")

    def import_gstr2b_file(self):
        """Prompts user to select a GSTR-2B or Purchase Register file for 3-way reconciliation."""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Select GSTR-2B or Purchase Register File", "", "Excel / CSV Files (*.xlsx *.csv)"
        )
        if not filepath:
            return

        try:
            summary = GSTService.reconcile_with_gstr2b(self.gst_ledger, filepath)
            self.gstr2b_summary = summary
            self.render_all_views()
            
            QMessageBox.information(
                self, "3-Way Reconciliation Complete",
                f"Successfully matched bank transactions against GSTR-2B file!\n\n"
                f"• Matched Entries: {summary['matched_count']}\n"
                f"• Missing in GSTR-2B: {summary['missing_count']}\n"
                f"• Amount Discrepancies: {summary['discrepancy_count']}\n"
                f"• Reconciled ITC: ₹ {summary['matched_gst']:,.2f}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Reconciliation Error", f"Could not process GSTR-2B file:\n{e}")

    def export_excel(self):
        """Generates and saves the updated GST Excel report."""
        if not self.gst_ledger:
            return
            
        active_ledger = GSTService.filter_ledger_by_date(self.gst_ledger, self.current_date_filter)
        doc_dir = os.path.expanduser("~/Documents")
        bank = self.parsed_payload.get("bank_name", "Bank") if self.parsed_payload else "Statement"
        filename = f"GST_Reconciliation_{bank}_{datetime.datetime.now().strftime('%Y%m%d')}.xlsx"
        
        dest_path, _ = QFileDialog.getSaveFileName(
            self, "Save GST Excel Report", os.path.join(doc_dir, filename), "Excel Files (*.xlsx)"
        )
        if not dest_path:
            return

        try:
            from parser.gst_excel_writer import GSTExcelWriter
            out_path = GSTExcelWriter.write_gst_excel(
                dest_path,
                self.parsed_payload.get("bank_name", "Bank"),
                self.parsed_payload.get("account_holder", "Holder"),
                self.parsed_payload.get("period", "Period"),
                active_ledger
            )
            Toast.success(self, "✓ Excel Ledger exported successfully!")
            
            if os.name == 'nt':
                os.startfile(out_path)
            else:
                import subprocess
                subprocess.run(["open", out_path] if os.name == 'posix' else ["xdg-open", out_path])
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Could not write Excel file:\n{e}")

    def export_pdf(self):
        """Prints the report HTML to a high-quality A4 Landscape PDF."""
        html_content = self.report_viewer.toHtml()
        if not html_content:
            return

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
            return

        active_ledger = GSTService.filter_ledger_by_date(self.gst_ledger, self.current_date_filter)
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
                    "Date", "Narration", "Category", "Vendor Name", "Vendor GSTIN", 
                    "Total Amount", "Taxable Value", "GST Rate", "CGST", "SGST", "IGST", 
                    "Total GST", "ITC Eligible", "GSTR-2B Status", "AI Confidence", "Status"
                ])
                
                for tx in active_ledger:
                    writer.writerow([
                        tx.get("date", ""),
                        tx.get("narration", ""),
                        tx.get("category", ""),
                        tx.get("vendor", ""),
                        tx.get("gstin", "Unassigned"),
                        tx.get("total_amount", 0.0),
                        tx.get("base_value", 0.0),
                        f"{tx.get('gst_rate', 0.18)*100:.0f}%",
                        tx.get("cgst", 0.0),
                        tx.get("sgst", 0.0),
                        tx.get("igst", 0.0),
                        tx.get("total_gst", 0.0),
                        tx.get("itc_eligible", "No"),
                        tx.get("gstr2b_status", "Not Reconciled"),
                        f"{tx.get('confidence', 80):.0f}%",
                        tx.get("status", "Estimated")
                    ])
            
            Toast.success(self, "✓ GST CSV Ledger exported successfully!")
            
            if os.name == 'nt':
                os.startfile(filepath)
            else:
                import subprocess
                subprocess.run(["open", filepath] if os.name == 'posix' else ["xdg-open", filepath])
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Could not save CSV ledger:\n{e}")

    def open_email_composer(self):
        """Opens the Email Composer dialog pre-attaching the GST report."""
        from ui.email_composer_dialog import EmailComposerDialog
        
        attachment = getattr(self, "excel_path", None)
        period = getattr(self, "statement_period", "") or "July 2026"
        bank = getattr(self, "bank_name", "") or ""

        dialog = EmailComposerDialog(
            report_type="GST Reconciliation & Analysis Report",
            default_attachment=attachment,
            period=period,
            bank_name=bank,
            parent=self
        )
        dialog.exec()

    def close_report(self):
        """Clears states and returns to the dashboard screen."""
        self.parsed_payload = None
        self.gst_ledger = []
        self.excel_path = None
        self.gstr2b_summary = None
        self.report_viewer.clear()
        
        self.closed.emit()
        
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
            self.title_lbl.setStyleSheet("font-size: 22px; font-weight: 700; color: #F8FAFC;")
            self.subtitle_lbl.setStyleSheet("font-size: 13px; color: #94A3B8;")
            self.findChild(QFrame, "ControlCard").setStyleSheet("""
                QFrame#ControlCard {
                    background-color: #1E293B;
                    border: 1px solid #334155;
                    border-radius: 12px;
                }
            """)
        else:
            self.title_lbl.setStyleSheet("font-size: 22px; font-weight: 700; color: #0F172A;")
            self.subtitle_lbl.setStyleSheet("font-size: 13px; color: #64748B;")
            self.findChild(QFrame, "ControlCard").setStyleSheet("""
                QFrame#ControlCard {
                    background-color: #FFFFFF;
                    border: 1px solid #E2E8F0;
                    border-radius: 12px;
                }
            """)
