import os
import re
import datetime
from difflib import SequenceMatcher
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter


class DuplicateFinderService:
    """
    Core engine for detecting, clustering, auto-resolving, and exporting
    duplicate bank statement transactions across single or multiple files.
    """

    @staticmethod
    def _clean_str(val):
        if val is None:
            return ""
        return str(val).strip()

    @classmethod
    def _format_dd_mm_yyyy(cls, date_str):
        if not date_str:
            return ""
        s = str(date_str).strip().replace(" 00:00:00", "").replace("T00:00:00", "")
        m = re.match(r"^(\d{4})[-/](\d{1,2})[-/](\d{1,2})$", s)
        if m:
            y, month, d = m.groups()
            return f"{int(d):02d}-{int(month):02d}-{y}"
        m_dd = re.match(r"^(\d{1,2})[-/](\d{1,2})[-/](\d{4})$", s)
        if m_dd:
            d, month, y = m_dd.groups()
            return f"{int(d):02d}-{int(month):02d}-{y}"
        return s

    @staticmethod
    def _normalize_text(text):
        """Normalizes text for fuzzy matching by lowercasing and stripping non-alphanumeric noise."""
        if not text:
            return ""
        text = text.lower()
        # Remove common prefixes/suffixes like Ref No, UPI/, etc.
        text = re.sub(r'[^a-z0-9\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    @staticmethod
    def _parse_amount(val):
        """Helper to parse amount floats safely."""
        if val is None:
            return 0.0
        s = str(val).replace(",", "").strip()
        if not s:
            return 0.0
        try:
            return abs(float(s))
        except ValueError:
            return 0.0

    @staticmethod
    def _parse_date(date_str):
        """Helper to convert string dates to datetime.date objects for comparison."""
        if not date_str:
            return None
        s = str(date_str).strip()
        # Common formats
        formats = [
            "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d %b %Y", "%d %B %Y",
            "%d/%m/%y", "%d-%m-%y", "%m/%d/%Y"
        ]
        for fmt in formats:
            try:
                return datetime.datetime.strptime(s, fmt).date()
            except ValueError:
                continue
        return None

    @classmethod
    def analyze_statement(cls, transactions, options=None):
        """
        Analyzes a list of transaction dictionaries and returns duplicate clusters and statistics.

        :param transactions: List of dicts with keys (date, narration, debit, credit, balance, ref_no, etc.)
        :param options: Dict with detection flags:
            - exact_match (bool): Check 100% exact row duplicates (default True)
            - potential_match (bool): Check fuzzy/narration + amount matches (default True)
            - date_window_days (int): Tolerance for date differences in days (default 2)
            - similarity_threshold (float): Narration similarity (0.0 to 1.0, default 0.75)
        :return: Dict containing 'clusters', 'stats', and 'annotated_transactions'
        """
        if options is None:
            options = {}

        exact_match_opt = options.get("exact_match", True)
        potential_match_opt = options.get("potential_match", True)
        date_window_days = int(options.get("date_window_days", 2))
        similarity_thresh = float(options.get("similarity_threshold", 0.75))

        if not transactions:
            return {
                "clusters": [],
                "stats": {
                    "total_transactions": 0,
                    "duplicate_clusters": 0,
                    "duplicate_entries": 0,
                    "flagged_debit_sum": 0.0,
                    "flagged_credit_sum": 0.0,
                    "cleanliness_score": 100.0
                },
                "annotated_transactions": []
            }

        # Prepare normalized items
        items = []
        for idx, tx in enumerate(transactions):
            date_obj = cls._parse_date(tx.get("date", ""))
            debit_amt = cls._parse_amount(tx.get("debit", ""))
            credit_amt = cls._parse_amount(tx.get("credit", ""))
            net_amt = debit_amt if debit_amt > 0 else credit_amt
            tx_type = "Debit" if debit_amt > 0 else ("Credit" if credit_amt > 0 else "Neutral")
            
            raw_date = cls._clean_str(tx.get("date", ""))
            if date_obj:
                clean_date_str = date_obj.strftime("%d-%m-%Y")
            else:
                clean_date_str = cls._format_dd_mm_yyyy(raw_date)
            
            raw_narr = cls._clean_str(tx.get("narration", ""))
            norm_narr = cls._normalize_text(raw_narr)
            ref_no = cls._clean_str(tx.get("ref_no", ""))
            source_file = cls._clean_str(tx.get("source_file", "Current Statement"))
            
            items.append({
                "id": f"tx_{idx}",
                "original_index": idx,
                "raw": tx,
                "date_str": clean_date_str,
                "date_obj": date_obj,
                "raw_narration": raw_narr,
                "norm_narration": norm_narr,
                "debit": debit_amt,
                "credit": credit_amt,
                "amount": net_amt,
                "type": tx_type,
                "ref_no": ref_no,
                "source_file": source_file,
                "balance": cls._clean_str(tx.get("balance", "")),
                "cluster_id": None,
                "match_type": None
            })

        visited = set()
        clusters = []
        cluster_counter = 1

        # 1. Exact Match Pass
        if exact_match_opt:
            exact_groups = {}
            for item in items:
                # Key for exact match
                key = (
                    item["date_str"],
                    item["raw_narration"].lower(),
                    item["debit"],
                    item["credit"],
                    item["balance"]
                )
                exact_groups.setdefault(key, []).append(item)

            for key, group in exact_groups.items():
                if len(group) > 1:
                    c_id = f"CLUSTER_EXACT_{cluster_counter}"
                    cluster_counter += 1
                    for it in group:
                        visited.add(it["id"])
                        it["cluster_id"] = c_id
                        it["match_type"] = "Exact Duplicate"

                    debit_sum = sum(it["debit"] for it in group[1:]) # Count excess as flagged
                    credit_sum = sum(it["credit"] for it in group[1:])
                    
                    clusters.append({
                        "id": c_id,
                        "title": f"Exact Duplicate Cluster #{cluster_counter-1}",
                        "match_type": "Exact Match",
                        "confidence": 100,
                        "risk_level": "High",
                        "badge_color": "#EF4444",
                        "badge_bg": "#FEF2F2",
                        "reason": f"{len(group)} transactions share identical Date ({group[0]['date_str']}), Narration, and Amount ({group[0]['amount']:,.2f}).",
                        "items": group,
                        "flagged_debit": debit_sum,
                        "flagged_credit": credit_sum
                    })

        # 2. Potential / Fuzzy Match Pass
        if potential_match_opt:
            n_items = len(items)
            for i in range(n_items):
                item_i = items[i]
                if item_i["id"] in visited or item_i["amount"] == 0:
                    continue

                current_cluster = [item_i]
                match_reasons = []

                for j in range(i + 1, n_items):
                    item_j = items[j]
                    if item_j["id"] in visited or item_j["amount"] == 0:
                        continue

                    # Amount must be equal (or within 0.01 tolerance)
                    if abs(item_i["amount"] - item_j["amount"]) > 0.01:
                        continue

                    # Transaction type (debit vs credit) must match
                    if item_i["type"] != item_j["type"]:
                        continue

                    # Check Date Window
                    date_diff = None
                    if item_i["date_obj"] and item_j["date_obj"]:
                        date_diff = abs((item_i["date_obj"] - item_j["date_obj"]).days)

                    date_match = (date_diff is not None and date_diff <= date_window_days) or (item_i["date_str"] == item_j["date_str"])

                    if not date_match:
                        continue

                    # Check Narration Similarity
                    sim = SequenceMatcher(None, item_i["norm_narration"], item_j["norm_narration"]).ratio()
                    
                    # Also check cross-statement flag
                    is_cross_file = (item_i["source_file"] != item_j["source_file"])

                    if sim >= similarity_thresh or is_cross_file:
                        current_cluster.append(item_j)
                        if is_cross_file:
                            match_reasons.append(f"Identical amount found across multiple files ('{item_i['source_file']}' & '{item_j['source_file']}')")
                        elif date_diff and date_diff > 0:
                            match_reasons.append(f"Matching amount ({item_i['amount']:,.2f}) within {date_diff} day(s)")
                        else:
                            match_reasons.append(f"Fuzzy narration match ({int(sim*100)}% similarity)")

                if len(current_cluster) > 1:
                    is_cross = any(it["source_file"] != current_cluster[0]["source_file"] for it in current_cluster)
                    m_type = "Cross-Statement Duplicate" if is_cross else "Potential Duplicate"
                    c_id = f"CLUSTER_POTENTIAL_{cluster_counter}"
                    cluster_counter += 1

                    for it in current_cluster:
                        visited.add(it["id"])
                        it["cluster_id"] = c_id
                        it["match_type"] = m_type

                    debit_sum = sum(it["debit"] for it in current_cluster[1:])
                    credit_sum = sum(it["credit"] for it in current_cluster[1:])

                    confidence = 90 if m_type == "Cross-Statement Duplicate" else 75
                    badge_col = "#2563EB" if is_cross else "#F59E0B"
                    badge_bg = "#EFF6FF" if is_cross else "#FFFBEB"

                    clusters.append({
                        "id": c_id,
                        "title": f"{m_type} Cluster #{cluster_counter-1}",
                        "match_type": m_type,
                        "confidence": confidence,
                        "risk_level": "Medium",
                        "badge_color": badge_col,
                        "badge_bg": badge_bg,
                        "reason": match_reasons[0] if match_reasons else f"Flagged potential double charge of {current_cluster[0]['amount']:,.2f}.",
                        "items": current_cluster,
                        "flagged_debit": debit_sum,
                        "flagged_credit": credit_sum
                    })

        # Calculate Overall Stats
        total_tx = len(transactions)
        total_clusters = len(clusters)
        dup_entries_count = sum(len(c["items"]) for c in clusters)
        excess_entries_count = sum(len(c["items"]) - 1 for c in clusters)
        
        total_flagged_debit = sum(c["flagged_debit"] for c in clusters)
        total_flagged_credit = sum(c["flagged_credit"] for c in clusters)

        cleanliness = 100.0 if total_tx == 0 else max(0.0, round(((total_tx - excess_entries_count) / total_tx) * 100, 1))

        stats = {
            "total_transactions": total_tx,
            "duplicate_clusters": total_clusters,
            "duplicate_entries": dup_entries_count,
            "excess_entries": excess_entries_count,
            "flagged_debit_sum": total_flagged_debit,
            "flagged_credit_sum": total_flagged_credit,
            "cleanliness_score": cleanliness
        }

        return {
            "clusters": clusters,
            "stats": stats,
            "annotated_transactions": items
        }

    @classmethod
    def analyze_multiple_statements(cls, statements_payload_list, options=None):
        """
        Combines transactions from multiple statement payloads and flags cross-statement duplicates.
        """
        combined_txs = []
        for p in statements_payload_list:
            file_name = p.get("file_name", p.get("bank_name", "Statement"))
            txs = p.get("transactions", [])
            for tx in txs:
                tx_copy = dict(tx)
                tx_copy["source_file"] = file_name
                combined_txs.append(tx_copy)

        return cls.analyze_statement(combined_txs, options)

    @classmethod
    def apply_auto_resolution(cls, clusters, strategy="keep_first"):
        """
        Applies an automated resolution rule across all duplicate clusters.

        :param clusters: List of cluster objects returned by analyze_statement
        :param strategy: 'keep_first', 'keep_last', or 'keep_highest_ref'
        :return: Dict mapping item_id -> action ('keep' or 'remove')
        """
        decisions = {}
        for c in clusters:
            items = c["items"]
            if not items:
                continue

            if strategy == "keep_last":
                keep_item = items[-1]
            elif strategy == "keep_highest_ref":
                keep_item = max(items, key=lambda x: len(x.get("ref_no", "")))
            else: # default keep_first
                keep_item = items[0]

            for it in items:
                if it["id"] == keep_item["id"]:
                    decisions[it["id"]] = "keep"
                else:
                    decisions[it["id"]] = "remove"

        return decisions

    @classmethod
    def export_duplicate_report(cls, clusters, stats, output_path, analysis_result=None, user_decisions=None):
        """
        Generates a professional openpyxl Excel audit report with Summary, Duplicate Clusters, and Cleaned Ledger.
        """
        wb = openpyxl.Workbook()

        # Styles
        font_header = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        fill_header = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
        fill_exact = PatternFill(start_color="FEF2F2", end_color="FEF2F2", fill_type="solid")
        fill_potential = PatternFill(start_color="FFFBEB", end_color="FFFBEB", fill_type="solid")
        fill_cross = PatternFill(start_color="EFF6FF", end_color="EFF6FF", fill_type="solid")

        thin_border = Border(
            left=Side(style='thin', color='E2E8F0'),
            right=Side(style='thin', color='E2E8F0'),
            top=Side(style='thin', color='E2E8F0'),
            bottom=Side(style='thin', color='E2E8F0')
        )

        # ----------------------------------------------------
        # SHEET 1: AUDIT SUMMARY
        # ----------------------------------------------------
        ws_sum = wb.active
        ws_sum.title = "Audit Summary"
        ws_sum.views.sheetView[0].showGridLines = True

        ws_sum.merge_cells("A1:E1")
        title_cell = ws_sum["A1"]
        title_cell.value = "StatementForge - Duplicate Transaction Audit Report"
        title_cell.font = Font(name="Calibri", size=16, bold=True, color="0F172A")
        title_cell.alignment = Alignment(horizontal="left", vertical="center")

        ws_sum["A2"] = f"Generated on: {datetime.datetime.now().strftime('%d-%m-%Y %H:%M:%S')}"
        ws_sum["A2"].font = Font(name="Calibri", size=10, italic=True, color="64748B")

        # KPI Metrics Table
        ws_sum["A4"] = "Audit Key Metrics"
        ws_sum["A4"].font = Font(name="Calibri", size=12, bold=True, color="1E293B")

        kpis = [
            ("Total Transactions Scanned", stats.get("total_transactions", 0)),
            ("Duplicate Clusters Identified", stats.get("duplicate_clusters", 0)),
            ("Excess Duplicate Entries", stats.get("excess_entries", 0)),
            ("Flagged Duplicate Debits", f"₹ {stats.get('flagged_debit_sum', 0.0):,.2f}"),
            ("Flagged Duplicate Credits", f"₹ {stats.get('flagged_credit_sum', 0.0):,.2f}"),
            ("Statement Cleanliness Score", f"{stats.get('cleanliness_score', 100.0)}%")
        ]

        row = 5
        for metric, val in kpis:
            ws_sum.cell(row=row, column=1, value=metric).font = Font(bold=True, color="475569")
            c_val = ws_sum.cell(row=row, column=2, value=val)
            c_val.font = Font(bold=True, color="0F172A")
            ws_sum.cell(row=row, column=1).border = thin_border
            c_val.border = thin_border
            row += 1

        # ----------------------------------------------------
        # SHEET 2: DUPLICATE CLUSTERS
        # ----------------------------------------------------
        ws_cls = wb.create_sheet(title="Flagged Duplicate Clusters")
        ws_cls.views.sheetView[0].showGridLines = True

        headers = ["Cluster ID", "Match Type", "Confidence", "Source File", "Date", "Narration", "Debit (₹)", "Credit (₹)", "Balance (₹)", "Ref No", "Audit Reason"]
        for col_idx, h in enumerate(headers, 1):
            cell = ws_cls.cell(row=1, column=col_idx, value=h)
            cell.font = font_header
            cell.fill = fill_header
            cell.alignment = Alignment(horizontal="center", vertical="center")

        r = 2
        for c in clusters:
            m_type = c["match_type"]
            fill_bg = fill_exact if m_type == "Exact Match" else (fill_cross if m_type == "Cross-Statement Duplicate" else fill_potential)
            for item in c["items"]:
                ws_cls.cell(row=r, column=1, value=c["id"]).fill = fill_bg
                ws_cls.cell(row=r, column=2, value=c["match_type"]).fill = fill_bg
                ws_cls.cell(row=r, column=3, value=f"{c['confidence']}%").fill = fill_bg
                ws_cls.cell(row=r, column=4, value=item.get("source_file", "")).fill = fill_bg
                ws_cls.cell(row=r, column=5, value=cls._format_dd_mm_yyyy(item.get("date_str", ""))).fill = fill_bg
                ws_cls.cell(row=r, column=6, value=item.get("raw_narration", "")).fill = fill_bg
                ws_cls.cell(row=r, column=7, value=item.get("debit", 0.0)).fill = fill_bg
                ws_cls.cell(row=r, column=8, value=item.get("credit", 0.0)).fill = fill_bg
                ws_cls.cell(row=r, column=9, value=item.get("balance", "")).fill = fill_bg
                ws_cls.cell(row=r, column=10, value=item.get("ref_no", "")).fill = fill_bg
                ws_cls.cell(row=r, column=11, value=c.get("reason", "")).fill = fill_bg

                for c_i in range(1, 12):
                    ws_cls.cell(row=r, column=c_i).border = thin_border
                r += 1

        # ----------------------------------------------------
        # SHEET 3: FULL STATEMENT WITH HIGHLIGHTED DUPLICATES (IF AVAILABLE)
        # ----------------------------------------------------
        sheets_to_autofit = [(ws_sum, 1), (ws_cls, 1)]
        if analysis_result and analysis_result.get("annotated_transactions"):
            ws_hl = wb.create_sheet(title="Full Statement (Highlighted)")
            ws_hl.views.sheetView[0].showGridLines = True
            cls._populate_highlighted_sheet(ws_hl, analysis_result, user_decisions or {}, bank_name="Audit Report")
            sheets_to_autofit.append((ws_hl, 4))

        # Auto-adjust column widths safely without title merged cell skews
        for sheet, start_row in sheets_to_autofit:
            if sheet.title == "Full Statement (Highlighted)":
                continue  # Uses explicit column width dict
            for col in sheet.columns:
                max_len = 0
                for cell in col:
                    if cell.row < start_row:
                        continue
                    if cell.value is not None:
                        max_len = max(max_len, len(str(cell.value)))
                col_letter = get_column_letter(col[0].column)
                sheet.column_dimensions[col_letter].width = max(max_len + 4, 12)

        wb.save(output_path)
        return output_path

    @classmethod
    def export_highlighted_statement(cls, analysis_result, user_decisions, output_path, bank_name="Bank"):
        """
        Generates an Excel statement where all duplicate entries are visually highlighted
        with color fills (Soft Red for exact duplicates, Soft Amber for potential duplicates, Soft Blue for kept originals)
        and explicit Audit Status columns.
        """
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Highlighted Statement"
        ws.views.sheetView[0].showGridLines = True

        cls._populate_highlighted_sheet(ws, analysis_result, user_decisions, bank_name)

        wb.save(output_path)
        return output_path

    @classmethod
    def _populate_highlighted_sheet(cls, ws, analysis_result, user_decisions, bank_name="Bank"):
        """Fills an openpyxl Worksheet with full statement transactions with duplicates highlighted."""
        font_title = Font(name="Calibri", size=14, bold=True, color="0F172A")
        font_sub = Font(name="Calibri", size=9.5, italic=True, color="475569")
        font_header = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        fill_header = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")

        # Color fills for duplicate states
        fill_exact_remove = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")  # Soft Red
        font_exact_remove = Font(name="Calibri", size=10, bold=True, color="991B1B")

        fill_potential_remove = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")  # Soft Amber
        font_potential_remove = Font(name="Calibri", size=10, bold=True, color="92400E")

        fill_kept_original = PatternFill(start_color="EFF6FF", end_color="EFF6FF", fill_type="solid")  # Soft Blue
        font_kept_original = Font(name="Calibri", size=10, bold=True, color="1E40AF")

        fill_clean = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
        font_clean = Font(name="Calibri", size=10, color="334155")

        thin_border = Border(
            left=Side(style='thin', color='E2E8F0'),
            right=Side(style='thin', color='E2E8F0'),
            top=Side(style='thin', color='E2E8F0'),
            bottom=Side(style='thin', color='E2E8F0')
        )

        # Title Block (Merged A1:J1 and A2:J2)
        ws.merge_cells("A1:J1")
        title_cell = ws["A1"]
        title_cell.value = f"StatementForge - {bank_name} Statement (Duplicates Highlighted)"
        title_cell.font = font_title
        title_cell.alignment = Alignment(horizontal="left", vertical="center")

        ws.merge_cells("A2:J2")
        sub_cell = ws["A2"]
        sub_cell.value = f"Generated on: {datetime.datetime.now().strftime('%d-%m-%Y %H:%M:%S')}  |  🟥 Red = Flagged Duplicate (Remove)  |  🟦 Blue = Kept Original  |  White = Clean Transaction"
        sub_cell.font = font_sub
        sub_cell.alignment = Alignment(horizontal="left", vertical="center")

        # Headers
        headers = ["Row #", "Date", "Narration / Description", "Debit (₹)", "Credit (₹)", "Balance (₹)", "Ref No", "Source File", "Audit Status", "User Action"]
        ws.row_dimensions[4].height = 26
        for col_idx, h in enumerate(headers, 1):
            cell = ws.cell(row=4, column=col_idx, value=h)
            cell.font = font_header
            cell.fill = fill_header
            cell.alignment = Alignment(horizontal="center", vertical="center")

        annotated = analysis_result.get("annotated_transactions", []) if analysis_result else []
        clusters = analysis_result.get("clusters", []) if analysis_result else []

        # Map item_id to cluster info
        item_cluster_map = {}
        for c in clusters:
            for it in c["items"]:
                item_cluster_map[it["id"]] = c

        r = 5
        tot_debit = 0.0
        tot_credit = 0.0
        flagged_count = 0

        for idx, item in enumerate(annotated, 1):
            it_id = item["id"]
            action = user_decisions.get(it_id, "keep")
            c_info = item_cluster_map.get(it_id)

            date_val = cls._format_dd_mm_yyyy(item.get("date_str", ""))
            narr_val = item.get("raw_narration", "")
            try:
                deb_val = float(item.get("debit") or 0.0)
            except Exception:
                deb_val = 0.0
            try:
                cred_val = float(item.get("credit") or 0.0)
            except Exception:
                cred_val = 0.0

            tot_debit += deb_val
            tot_credit += cred_val

            raw_bal = str(item.get("balance", "")).replace("*", "").replace(",", "").strip()
            ref_val = item.get("ref_no", "")
            src_val = item.get("source_file", "")

            # Determine audit status and styling
            if c_info:
                m_type = c_info.get("match_type", "Duplicate")
                if action == "remove":
                    flagged_count += 1
                    status_text = f"DUPLICATE ({m_type.upper()})"
                    action_text = "REMOVE (FLAGGED)"
                    if m_type == "Exact Match":
                        row_fill = fill_exact_remove
                        row_font = font_exact_remove
                    else:
                        row_fill = fill_potential_remove
                        row_font = font_potential_remove
                else:
                    status_text = f"DUPLICATE CLUSTER ({m_type.upper()})"
                    action_text = "KEEP (ORIGINAL)"
                    row_fill = fill_kept_original
                    row_font = font_kept_original
            else:
                status_text = "Clean"
                action_text = "Keep"
                row_fill = fill_clean
                row_font = font_clean

            ws.cell(row=r, column=1, value=idx).alignment = Alignment(horizontal="center", vertical="center")
            ws.cell(row=r, column=2, value=date_val).alignment = Alignment(horizontal="center", vertical="center")
            
            c_narr = ws.cell(row=r, column=3, value=narr_val)
            c_narr.alignment = Alignment(horizontal="left", vertical="center", wrap_text=False)

            c_deb = ws.cell(row=r, column=4, value=deb_val if deb_val > 0 else "")
            if deb_val > 0:
                c_deb.number_format = '#,##0.00'
            c_deb.alignment = Alignment(horizontal="right", vertical="center")

            c_cred = ws.cell(row=r, column=5, value=cred_val if cred_val > 0 else "")
            if cred_val > 0:
                c_cred.number_format = '#,##0.00'
            c_cred.alignment = Alignment(horizontal="right", vertical="center")

            try:
                num_bal = float(raw_bal)
                c_bal = ws.cell(row=r, column=6, value=num_bal)
                c_bal.number_format = '#,##0.00'
            except Exception:
                c_bal = ws.cell(row=r, column=6, value=raw_bal)
            c_bal.alignment = Alignment(horizontal="right", vertical="center")

            ws.cell(row=r, column=7, value=ref_val).alignment = Alignment(horizontal="center", vertical="center")
            ws.cell(row=r, column=8, value=src_val).alignment = Alignment(horizontal="left", vertical="center")

            c_stat = ws.cell(row=r, column=9, value=status_text)
            c_stat.alignment = Alignment(horizontal="center", vertical="center")

            c_act = ws.cell(row=r, column=10, value=action_text)
            c_act.alignment = Alignment(horizontal="center", vertical="center")

            # Apply row styling & borders
            for col_i in range(1, 11):
                cell = ws.cell(row=r, column=col_i)
                cell.fill = row_fill
                cell.font = row_font
                cell.border = thin_border

            r += 1

        # Summary Row at Bottom
        ws.cell(row=r, column=1, value="TOTALS").font = Font(name="Calibri", size=11, bold=True)
        ws.cell(row=r, column=3, value=f"{len(annotated)} Transactions ({flagged_count} Flagged Duplicates)").font = Font(name="Calibri", size=11, bold=True)

        c_tot_deb = ws.cell(row=r, column=4, value=tot_debit)
        c_tot_deb.number_format = '#,##0.00'
        c_tot_deb.font = Font(name="Calibri", size=11, bold=True)

        c_tot_cred = ws.cell(row=r, column=5, value=tot_credit)
        c_tot_cred.number_format = '#,##0.00'
        c_tot_cred.font = Font(name="Calibri", size=11, bold=True)

        for col_i in range(1, 11):
            ws.cell(row=r, column=col_i).border = thin_border

        # Explicit responsive column widths (single-line narration expanded)
        max_narr_len = max([len(str(it.get("raw_narration", "") or "")) for it in annotated] + [25])
        col_widths = {
            1: 8,   # Row #
            2: 13,  # Date
            3: max(max_narr_len + 4, 30),  # Narration / Description (single line auto-fitted width)
            4: 16,  # Debit (₹)
            5: 16,  # Credit (₹)
            6: 16,  # Balance (₹)
            7: 15,  # Ref No
            8: 18,  # Source File
            9: 24,  # Audit Status
            10: 20  # User Action
        }
        for col_idx, width in col_widths.items():
            col_letter = get_column_letter(col_idx)
            ws.column_dimensions[col_letter].width = width
