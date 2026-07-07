import os
import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

class ExcelGenerator:
    """Generates a professional two-sheet Excel file matching StatementForge styling guidelines."""

    @classmethod
    def generate_excel(cls, pdf_path, bank_name, account_holder, period, transactions):
        """
        Generates and saves the formatted Excel spreadsheet beside the original PDF.
        Handles filename collisions by adding (1), (2), etc.
        Returns the absolute path to the generated Excel file.
        """
        # 1. Resolve filename collision beside the PDF
        base, _ = os.path.splitext(pdf_path)
        excel_path = base + ".xlsx"
        counter = 1
        while os.path.exists(excel_path):
            excel_path = f"{base}_({counter}).xlsx"
            counter += 1

        wb = Workbook()

        # Fonts & Styles
        font_name = "Segoe UI"
        title_font = Font(name=font_name, size=14, bold=True, color="FFFFFF")
        section_hdr_font = Font(name=font_name, size=11, bold=True, color="1E3A8A")
        bold_label_font = Font(name=font_name, size=11, bold=True, color="334155")
        regular_val_font = Font(name=font_name, size=11, color="0F172A")
        bold_val_font = Font(name=font_name, size=11, bold=True, color="0F172A")

        # Color Fills
        blue_hdr_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid") # Dark Blue #1E3A8A
        light_blue_fill = PatternFill(start_color="EFF6FF", end_color="EFF6FF", fill_type="solid") # Blue 50 #EFF6FF
        zebra_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid") # Slate 50 #F8FAFC

        # Borders
        thin_border = Border(
            left=Side(style='thin', color='CBD5E1'),
            right=Side(style='thin', color='CBD5E1'),
            top=Side(style='thin', color='CBD5E1'),
            bottom=Side(style='thin', color='CBD5E1')
        )

        currency_format = '₹ #,##0.00'

        # ----------------------------------------------------
        # SHEET 1: TRANSACTIONS
        # ----------------------------------------------------
        ws_tx = wb.active
        ws_tx.title = "Transactions"
        ws_tx.views.sheetView[0].showGridLines = True

        # Columns: Date, Narration, Debit, Credit, Balance
        headers = ["Date", "Narration", "Debit", "Credit", "Balance"]

        # Write Headers
        ws_tx.row_dimensions[1].height = 28
        for col_idx, header in enumerate(headers, start=1):
            cell = ws_tx.cell(row=1, column=col_idx)
            cell.value = header
            cell.font = Font(name=font_name, size=11, bold=True, color="FFFFFF")
            cell.fill = blue_hdr_fill
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = thin_border

        # Write Data
        num_transactions = len(transactions)
        total_debit = 0.0
        total_credit = 0.0
        
        for row_idx, tx in enumerate(transactions, start=2):
            ws_tx.row_dimensions[row_idx].height = 20
            
            c_date = ws_tx.cell(row=row_idx, column=1, value=tx["date"])
            c_date.alignment = Alignment(horizontal="center", vertical="center")
            
            c_narr = ws_tx.cell(row=row_idx, column=2, value=tx["narration"])
            c_narr.alignment = Alignment(vertical="center")
            
            # Debit (default to 0.0)
            deb = float(tx.get("debit", 0.0) or 0.0)
            total_debit += deb
            c_deb = ws_tx.cell(row=row_idx, column=3, value=deb)
            c_deb.number_format = currency_format
            c_deb.alignment = Alignment(horizontal="right", vertical="center")
            
            # Credit (default to 0.0)
            cred = float(tx.get("credit", 0.0) or 0.0)
            total_credit += cred
            c_cred = ws_tx.cell(row=row_idx, column=4, value=cred)
            c_cred.number_format = currency_format
            c_cred.alignment = Alignment(horizontal="right", vertical="center")
            
            # Balance (can be float or None)
            bal_val = tx.get("balance")
            if bal_val is not None:
                bal = float(bal_val)
                c_bal = ws_tx.cell(row=row_idx, column=5, value=bal)
                c_bal.number_format = currency_format
                c_bal.alignment = Alignment(horizontal="right", vertical="center")
            else:
                c_bal = ws_tx.cell(row=row_idx, column=5, value="-")
                c_bal.alignment = Alignment(horizontal="center", vertical="center")
            
            # Style each cell
            for col_idx in range(1, 6):
                cell = ws_tx.cell(row=row_idx, column=col_idx)
                cell.font = regular_val_font
                cell.border = thin_border
                if row_idx % 2 == 0:
                    cell.fill = zebra_fill

        # Freeze Header Row
        ws_tx.freeze_panes = "A2"

        # Apply Auto Filter
        if num_transactions > 0:
            ws_tx.auto_filter.ref = f"A1:E{num_transactions + 1}"

        # Adjust Columns automatically
        for col in ws_tx.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                val = cell.value
                if val is not None:
                    if cell.number_format == currency_format and isinstance(val, (int, float)):
                        val_str = f"₹ {val:,.2f}"
                    else:
                        val_str = str(val)
                    max_len = max(max_len, len(val_str))
            ws_tx.column_dimensions[col_letter].width = max(max_len + 3, 12)

        # ----------------------------------------------------
        # SHEET 2: SUMMARY
        # ----------------------------------------------------
        ws_sum = wb.create_sheet(title="Summary")
        ws_sum.views.sheetView[0].showGridLines = True

        # Header Title block
        ws_sum.merge_cells("A1:C1")
        title_cell = ws_sum["A1"]
        title_cell.value = "StatementForge Summary Report"
        title_cell.font = title_font
        title_cell.fill = blue_hdr_fill
        title_cell.alignment = Alignment(horizontal="center", vertical="center")
        ws_sum.row_dimensions[1].height = 40

        # Calculate opening & closing balances
        opening_balance = 0.0
        closing_balance = 0.0
        if num_transactions > 0:
            first_tx = transactions[0]
            last_tx = transactions[-1]
            first_bal = first_tx.get("balance")
            last_bal = last_tx.get("balance")
            
            if first_bal is not None:
                opening_balance = first_bal + first_tx.get("debit", 0.0) - first_tx.get("credit", 0.0)
            if last_bal is not None:
                closing_balance = last_bal

        # Build Summary Rows
        summary_rows = [
            ("", ""), # spacer
            ("Account Details", ""),
            ("Bank Name", bank_name or "Unknown Bank"),
            ("Account Holder", account_holder or "Unknown"),
            ("Statement Period", period or "Unknown Period"),
            ("", ""), # spacer
            ("Financial Details", ""),
            ("Opening Balance", opening_balance),
            ("Closing Balance", closing_balance),
            ("Total Debit", total_debit),
            ("Total Credit", total_credit),
            ("Transaction Count", num_transactions),
            ("", ""), # spacer
            ("Metadata", ""),
            ("Generated Date", datetime.datetime.now().strftime("%Y-%m-%d %I:%M %p")),
            ("Generated By", "StatementForge")
        ]

        for idx, (label, val) in enumerate(summary_rows, start=2):
            ws_sum.row_dimensions[idx].height = 22
            
            if not label:
                continue
                
            if val == "": # Header section label
                ws_sum.merge_cells(start_row=idx, start_column=1, end_row=idx, end_column=3)
                cell = ws_sum.cell(row=idx, column=1)
                cell.value = label
                cell.font = section_hdr_font
                cell.fill = light_blue_fill
                cell.alignment = Alignment(vertical="center", indent=1)
                for col in range(1, 4):
                    ws_sum.cell(row=idx, column=col).border = thin_border
            else: # Row with content
                c_lbl = ws_sum.cell(row=idx, column=1)
                c_lbl.value = label
                c_lbl.font = bold_label_font
                c_lbl.alignment = Alignment(vertical="center", indent=1)
                c_lbl.border = thin_border
                
                c_val = ws_sum.cell(row=idx, column=2)
                c_val.value = val
                c_val.border = thin_border
                c_val.alignment = Alignment(vertical="center", indent=1)
                
                if isinstance(val, (int, float)):
                    c_val.font = bold_val_font
                    if label != "Transaction Count":
                        c_val.number_format = currency_format
                        c_val.alignment = Alignment(horizontal="right", vertical="center")
                    else:
                        c_val.alignment = Alignment(horizontal="left", vertical="center")
                else:
                    c_val.font = regular_val_font

        ws_sum.column_dimensions["A"].width = 28
        ws_sum.column_dimensions["B"].width = 38
        ws_sum.column_dimensions["C"].width = 15

        # Save workbook to final path
        wb.save(excel_path)
        return excel_path
