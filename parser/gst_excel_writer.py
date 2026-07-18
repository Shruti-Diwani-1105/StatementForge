import os
import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

class GSTExcelWriter:
    """Generates professional dual-sheet GST Ledger reports matching the StatementForge aesthetic."""

    @classmethod
    def write_gst_excel(cls, pdf_path: str, bank_name: str, account_holder: str, period: str, gst_ledger: list) -> str:
        """
        Creates an Excel file beside the PDF containing the GST Summary and the GST transaction ledger.
        Returns the absolute Excel file path.
        """
        base, _ = os.path.splitext(pdf_path)
        excel_path = f"{base}_GST_Report.xlsx"
        
        counter = 1
        while os.path.exists(excel_path):
            excel_path = f"{base}_GST_Report_({counter}).xlsx"
            counter += 1

        wb = Workbook()
        font_name = "Segoe UI"
        
        # Styles
        title_font = Font(name=font_name, size=14, bold=True, color="FFFFFF")
        section_hdr_font = Font(name=font_name, size=11, bold=True, color="B45309") # Warm Amber/Orange for GST Section
        bold_lbl_font = Font(name=font_name, size=11, bold=True, color="334155")
        regular_val_font = Font(name=font_name, size=11, color="0F172A")
        bold_val_font = Font(name=font_name, size=11, bold=True, color="0F172A")
        
        amber_hdr_fill = PatternFill(start_color="D97706", end_color="D97706", fill_type="solid") # Dark Amber
        light_amber_fill = PatternFill(start_color="FFFBEB", end_color="FFFBEB", fill_type="solid") # Amber 50
        zebra_fill = PatternFill(start_color="FDFDFD", end_color="F9FAFB", fill_type="solid") # Subtle slate zebra
        
        thin_border = Border(
            left=Side(style='thin', color='CBD5E1'),
            right=Side(style='thin', color='CBD5E1'),
            top=Side(style='thin', color='CBD5E1'),
            bottom=Side(style='thin', color='CBD5E1')
        )
        
        currency_format = '#,##0.00'

        # ----------------------------------------------------
        # SHEET 1: SUMMARY
        # ----------------------------------------------------
        ws_sum = wb.active
        ws_sum.title = "GST Summary"
        ws_sum.views.sheetView[0].showGridLines = True

        # Title Block
        ws_sum.merge_cells("A1:C1")
        title_cell = ws_sum["A1"]
        title_cell.value = "GST Tax Ledger Summary"
        title_cell.font = title_font
        title_cell.fill = amber_hdr_fill
        title_cell.alignment = Alignment(horizontal="center", vertical="center")
        ws_sum.row_dimensions[1].height = 40

        # Totals computation
        total_itc = sum(tx["total_gst"] for tx in gst_ledger if "ITC" in tx["type"])
        total_output = sum(tx["total_gst"] for tx in gst_ledger if "Output" in tx["type"])
        net_payable = total_output - total_itc

        summary_rows = [
            ("", ""),
            ("General Details", ""),
            ("Bank Name", bank_name),
            ("Account Holder", account_holder),
            ("Statement Period", period),
            ("", ""),
            ("GST Reconciliation Summary", ""),
            ("Total GST Paid (ITC claimable)", total_itc),
            ("Total GST Collected (Output tax)", total_output),
            ("Net GST Payable/Refundable", net_payable),
            ("Total GST-Linked Transactions", len(gst_ledger)),
            ("Report Export Date", datetime.datetime.now().strftime("%Y-%m-%d %I:%M %p")),
        ]

        for idx, (label, val) in enumerate(summary_rows, start=2):
            ws_sum.row_dimensions[idx].height = 22
            if not label:
                continue
            
            if val == "":  # Header Sections
                ws_sum.merge_cells(start_row=idx, start_column=1, end_row=idx, end_column=3)
                cell = ws_sum.cell(row=idx, column=1, value=label)
                cell.font = section_hdr_font
                cell.fill = light_amber_fill
                for col in range(1, 4):
                    ws_sum.cell(row=idx, column=col).border = thin_border
            else:  # Key-Value Data Rows
                c_lbl = ws_sum.cell(row=idx, column=1, value=label)
                c_lbl.font = bold_lbl_font
                c_lbl.alignment = Alignment(vertical="center", indent=1)
                c_lbl.border = thin_border
                
                c_val = ws_sum.cell(row=idx, column=2, value=val)
                c_val.border = thin_border
                c_val.alignment = Alignment(vertical="center", indent=1)
                
                if isinstance(val, (int, float)):
                    c_val.font = bold_val_font
                    if label != "Total GST-Linked Transactions":
                        c_val.number_format = currency_format
                        c_val.alignment = Alignment(horizontal="right", vertical="center")
                else:
                    c_val.font = regular_val_font

        ws_sum.column_dimensions["A"].width = 32
        ws_sum.column_dimensions["B"].width = 38
        ws_sum.column_dimensions["C"].width = 15

        # ----------------------------------------------------
        # SHEET 2: GST TRANSACTIONS LEDGER
        # ----------------------------------------------------
        ws_led = wb.create_sheet(title="GST Transactions")
        ws_led.views.sheetView[0].showGridLines = True
        
        headers = ["Date", "Narration", "Type", "Total Amount", "Base Value", "CGST", "SGST", "IGST", "Total GST"]
        ws_led.row_dimensions[1].height = 28
        for col_idx, header in enumerate(headers, start=1):
            cell = ws_led.cell(row=1, column=col_idx, value=header)
            cell.font = Font(name=font_name, size=11, bold=True, color="FFFFFF")
            cell.fill = amber_hdr_fill
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = thin_border

        for r_idx, tx in enumerate(gst_ledger, start=2):
            ws_led.row_dimensions[r_idx].height = 22
            row_data = [
                tx["date"], tx["narration"], tx["type"],
                tx["total_amount"], tx["base_value"], tx["cgst"], tx["sgst"], tx["igst"], tx["total_gst"]
            ]
            for c_idx, val in enumerate(row_data, start=1):
                cell = ws_led.cell(row=r_idx, column=c_idx, value=val)
                cell.font = regular_val_font
                cell.border = thin_border
                if r_idx % 2 == 0:
                    cell.fill = zebra_fill
                
                # Dynamic alignments and formatting
                if c_idx >= 4:
                    cell.number_format = currency_format
                    cell.alignment = Alignment(horizontal="right", vertical="center")
                elif c_idx in [1, 3]:
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                else:
                    cell.alignment = Alignment(vertical="center")

        # Freeze headers & enable auto-filtering
        ws_led.freeze_panes = "A2"
        ws_led.auto_filter.ref = f"A1:I{len(gst_ledger) + 1}"

        # Adjust columns dynamically
        for col in ws_led.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                val_str = str(cell.value or "")
                if isinstance(cell.value, (int, float)) and c_idx >= 4:
                    val_str = f"₹ {cell.value:,.2f}"
                max_len = max(max_len, len(val_str))
            ws_led.column_dimensions[col_letter].width = max(max_len + 3, 12)

        wb.save(excel_path)
        return excel_path
