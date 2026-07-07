import os
import datetime
import re
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

class ExcelGenerator:
    """Generates a professional two-sheet Excel file matching StatementForge styling guidelines."""

    @classmethod
    def _parse_numeric(cls, val):
        """Attempts to parse a value to int or float. Returns parsed number, or original string if not numeric, or None if empty."""
        if val is None:
            return None
        val_str = str(val).strip()
        if val_str == "" or val_str.lower() in ["none", "null", "-", "cr", "dr"]:
            return None
        # Remove commas and currency symbols
        clean_str = re.sub(r"[^\d\.\-]", "", val_str)
        if not clean_str:
            return val_str
        try:
            if "." in clean_str:
                return float(clean_str)
            return int(clean_str)
        except ValueError:
            return val_str

    @classmethod
    def _parse_date(cls, val):
        """Attempts to parse standard date strings. Returns datetime.date, or original string."""
        if val is None:
            return None
        val_str = str(val).strip()
        date_formats = [
            "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d",
            "%d/%m/%y", "%d-%m-%y",
            "%d %b %Y", "%d-%b-%Y", "%d-%b-%y"
        ]
        for fmt in date_formats:
            try:
                dt = datetime.datetime.strptime(val_str, fmt)
                return dt.date()
            except ValueError:
                pass
        return val_str

    @classmethod
    def generate_excel(cls, pdf_path, bank_name, account_holder, period, transactions):
        """
        Generates and saves the formatted Excel spreadsheet beside the original PDF.
        Handles filename collisions by adding (1), (2), etc.
        Returns the absolute path to the generated Excel file.
        """
        # Resolve filename collision beside the PDF
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

        # 1. Determine all unique keys present in the transactions list
        all_keys = set()
        for tx in transactions:
            all_keys.update(tx.keys())

        # Preferred ordering patterns and their mapped header display names
        preferred_order = [
            ("date", "Date"),
            ("value_date", "Value Date"),
            ("value date", "Value Date"),
            ("valuedate", "Value Date"),
            ("narration", "Transaction Description / Narration"),
            ("description", "Transaction Description / Narration"),
            ("transaction description", "Transaction Description / Narration"),
            ("cheque_number", "Cheque Number / Reference Number"),
            ("cheque no", "Cheque Number / Reference Number"),
            ("cheque_no", "Cheque Number / Reference Number"),
            ("chequeno", "Cheque Number / Reference Number"),
            ("ref_no", "Cheque Number / Reference Number"),
            ("ref no", "Cheque Number / Reference Number"),
            ("reference number", "Cheque Number / Reference Number"),
            ("reference_number", "Cheque Number / Reference Number"),
            ("debit", "Debit"),
            ("credit", "Credit"),
            ("balance", "Balance"),
            ("transaction_type", "Transaction Type"),
            ("transaction type", "Transaction Type"),
            ("type", "Transaction Type"),
            ("branch", "Branch")
        ]

        headers = []
        key_order = []
        seen_keys = set()

        # Step 1: Add preferred keys in order
        for key_pat, header_name in preferred_order:
            for actual_key in all_keys:
                if actual_key.lower() == key_pat and actual_key not in seen_keys:
                    headers.append(header_name)
                    key_order.append(actual_key)
                    seen_keys.add(actual_key)
                    break

        # Step 2: Add any extra / bank-specific keys
        for actual_key in all_keys:
            if actual_key not in seen_keys:
                header_name = actual_key.replace("_", " ").title()
                headers.append(header_name)
                key_order.append(actual_key)
                seen_keys.add(actual_key)

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
        exported_rows_count = 0

        for row_idx, tx in enumerate(transactions, start=2):
            try:
                ws_tx.row_dimensions[row_idx].height = 20
                for col_idx, key in enumerate(key_order, start=1):
                    cell = ws_tx.cell(row=row_idx, column=col_idx)
                    val = tx.get(key)

                    header_lower = headers[col_idx - 1].lower()
                    is_currency = any(term in header_lower for term in ["debit", "credit", "balance", "amount"])

                    if is_currency:
                        parsed_val = cls._parse_numeric(val)
                        if parsed_val is not None and isinstance(parsed_val, (int, float)):
                            cell.value = parsed_val
                            cell.number_format = currency_format
                            cell.alignment = Alignment(horizontal="right", vertical="center")
                        else:
                            cell.value = None # Empty cell
                            cell.alignment = Alignment(horizontal="center", vertical="center")
                    elif "date" in header_lower:
                        parsed_date = cls._parse_date(val)
                        cell.value = parsed_date
                        if isinstance(parsed_date, datetime.date):
                            cell.number_format = 'yyyy-mm-dd'
                        cell.alignment = Alignment(horizontal="center", vertical="center")
                    else:
                        parsed_val = cls._parse_numeric(val)
                        cell.value = parsed_val
                        if isinstance(parsed_val, (int, float)):
                            cell.alignment = Alignment(horizontal="right", vertical="center")
                        else:
                            cell.alignment = Alignment(horizontal="left", vertical="center")

                    cell.font = regular_val_font
                    cell.border = thin_border
                    if row_idx % 2 == 0:
                        cell.fill = zebra_fill
                
                exported_rows_count += 1
            except Exception as e:
                print(f"ExcelGenerator: Error exporting transaction at index {row_idx - 2}: {e}. Row data: {tx}")
                try:
                    # Staging partial data so the row is not dropped
                    ws_tx.cell(row=row_idx, column=1, value="ERROR")
                    ws_tx.cell(row=row_idx, column=2, value=f"Failed to export row: {e}")
                    exported_rows_count += 1
                except Exception:
                    pass

        # Verify Row Count
        if exported_rows_count != num_transactions:
            print(f"ExcelGenerator Warning: Expected to export {num_transactions} rows, but wrote {exported_rows_count}.")
        else:
            print(f"ExcelGenerator Success: Verified {exported_rows_count} transactions written to Excel.")

        # Freeze Header Row
        ws_tx.freeze_panes = "A2"

        # Apply Auto Filter
        if num_transactions > 0:
            last_col_letter = get_column_letter(len(headers))
            ws_tx.auto_filter.ref = f"A1:{last_col_letter}{num_transactions + 1}"

        # Adjust Columns automatically
        for col in ws_tx.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                val = cell.value
                if val is not None:
                    if isinstance(val, datetime.date):
                        val_str = val.strftime('%Y-%m-%d')
                    elif isinstance(val, (int, float)) and any(term in ws_tx.cell(row=1, column=cell.column).value.lower() for term in ["debit", "credit", "balance", "amount"]):
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

        # Calculate opening & closing balances and totals
        opening_balance = 0.0
        closing_balance = 0.0
        total_debit = 0.0
        total_credit = 0.0

        for tx in transactions:
            deb_val = cls._parse_numeric(tx.get("debit"))
            if isinstance(deb_val, (int, float)):
                total_debit += deb_val
            cred_val = cls._parse_numeric(tx.get("credit"))
            if isinstance(cred_val, (int, float)):
                total_credit += cred_val

        if num_transactions > 0:
            first_tx = transactions[0]
            last_tx = transactions[-1]
            first_bal = cls._parse_numeric(first_tx.get("balance"))
            last_bal = cls._parse_numeric(last_tx.get("balance"))
            first_deb = cls._parse_numeric(first_tx.get("debit")) or 0.0
            first_cred = cls._parse_numeric(first_tx.get("credit")) or 0.0

            if first_bal is not None:
                opening_balance = first_bal + first_deb - first_cred
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
