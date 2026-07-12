from parser.table_extractor import TableExtractor
from parser.transaction_parser import TransactionParser
from parser.utils import ParserUtils

class PageProcessor:
    """Manages parsing operations for a single PDF page."""

    @classmethod
    def process_page(cls, pdf_path: str, page_num: int, column_mapping: dict = None, logger=None) -> tuple:
        """
        Runs table extraction and row parsing for a page.
        Tries digital first (if selectable text exists).
        Falls back to local OCR if digital extraction yields 0 transactions.
        Falls back to AI Vision page parsing if local OCR yields 0 transactions or is unavailable.
        Returns a tuple: (list_of_transactions, column_mapping_used, method_used)
        """
        transactions = []
        used_mapping = column_mapping
        is_digital = TableExtractor.has_selectable_text(pdf_path, page_num)
        method_used = "Digital Parser"

        # 1. Try Digital Parse Waterfall
        if is_digital:
            # Try Strategy A: Default layout (border lines)
            try:
                grid_table = TableExtractor.extract_table_digitally_default(pdf_path, page_num, logger)
                if grid_table and len(grid_table) >= 2:
                    grid_table = ParserUtils.split_merged_columns(grid_table)
                    temp_mapping = used_mapping or TransactionParser.detect_columns(grid_table)
                    transactions = TransactionParser.parse_rows(grid_table, temp_mapping)
                    if transactions:
                        used_mapping = temp_mapping
                        method_used = "Digital Parser (Default)"
            except Exception as e:
                if logger:
                    logger.log(f"Page {page_num + 1} digital default strategy error: {e}")

            # Try Strategy B: Text-alignment fallback layout (if Strategy A yielded 0 transactions)
            if not transactions:
                try:
                    grid_table = TableExtractor.extract_table_digitally_text_fallback(pdf_path, page_num, logger)
                    if grid_table and len(grid_table) >= 2:
                        grid_table = ParserUtils.split_merged_columns(grid_table)
                        temp_mapping = used_mapping or TransactionParser.detect_columns(grid_table)
                        transactions = TransactionParser.parse_rows(grid_table, temp_mapping)
                        if transactions:
                            used_mapping = temp_mapping
                            method_used = "Digital Parser (Text Fallback)"
                except Exception as e:
                    if logger:
                        logger.log(f"Page {page_num + 1} digital text strategy fallback error: {e}")

        # 2. Try OCR Fallback (if scanned and digital failed/yielded 0)
        if not transactions and not is_digital:
            method_used = "OCR Parser"
            try:
                grid_table = TableExtractor.extract_table_via_ocr(pdf_path, page_num, logger)
                if grid_table and len(grid_table) >= 2:
                    if not used_mapping:
                        used_mapping = TransactionParser.detect_columns(grid_table)
                    transactions = TransactionParser.parse_rows(grid_table, used_mapping)
            except Exception as e:
                if logger:
                    logger.log(f"Page {page_num + 1} OCR extraction error: {e}")

        # 3. Try AI Vision Last-resort Fallback (if both digital and local OCR failed/yielded 0)
        if not transactions:
            method_used = "AI Vision Fallback"
            try:
                if logger:
                    logger.log(f"Page {page_num + 1}: Local engines failed. Running AI Vision last-resort fallback...")
                
                # Render page to PIL image
                from parser.ocr_parser import OCRParser
                pil_image = OCRParser.render_pdf_page_to_pil(pdf_path, page_num)
                
                # Call GeminiService
                from services.gemini_service import GeminiService
                ai_data = GeminiService.parse_page_image(pil_image)
                
                if ai_data and "transactions" in ai_data:
                    raw_txs = ai_data["transactions"]
                    for tx in raw_txs:
                        date_val = tx.get("Date") or tx.get("date") or ""
                        narr_val = tx.get("Narration") or tx.get("narration") or tx.get("Description") or tx.get("description") or ""
                        debit_val = tx.get("Debit") or tx.get("debit") or ""
                        credit_val = tx.get("Credit") or tx.get("credit") or ""
                        bal_val = tx.get("Balance") or tx.get("balance") or ""
                        
                        transactions.append({
                            "date": str(date_val),
                            "narration": str(narr_val),
                            "debit": ParserUtils.clean_amount(debit_val),
                            "credit": ParserUtils.clean_amount(credit_val),
                            "balance": ParserUtils.clean_balance(bal_val)
                        })
            except Exception as e:
                if logger:
                    logger.log(f"Page {page_num + 1} AI Vision fallback failed: {e}")

        return transactions, used_mapping, method_used
