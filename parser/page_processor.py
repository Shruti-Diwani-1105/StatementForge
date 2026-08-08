from parser.table_extractor import TableExtractor
from parser.transaction_parser import TransactionParser
from parser.utils import ParserUtils, PDF_LOCK

class PageProcessor:
    """Manages parsing operations for a single PDF page."""

    @classmethod
    def process_page(cls, pdf_path: str, page_num: int, column_mapping: dict = None, logger=None) -> tuple:
        """
        Runs table extraction and row parsing for a page.
        Tries digital first, falls back to OCR, and then AI Vision.
        Returns a tuple: (transactions, page_headers, page_mapping, method_used, grid_table, confidence)
        """
        from parser.table_extractor import TableExtractor
        from parser.transaction_parser import TransactionParser
        from parser.utils import ParserUtils, PDF_LOCK

        # 1. Run TableExtractor to get grid and headers
        struct = TableExtractor.extract_structured_table(pdf_path, page_num, logger)
        grid_table = struct["raw_grid"]
        method_used = struct["method"]
        confidence = struct["confidence"]
        page_headers = struct["headers"]

        transactions = []
        used_mapping = column_mapping

        # 2. Parse rows if grid table exists
        if grid_table and len(grid_table) >= 2:
            grid_table = ParserUtils.split_merged_columns(grid_table)
            
            # Detect page-specific mapping dynamically
            temp_mapping = TransactionParser.detect_columns(grid_table)
            if not temp_mapping and used_mapping:
                temp_mapping = used_mapping
            
            if temp_mapping:
                used_mapping = temp_mapping
                transactions = TransactionParser.parse_rows(grid_table, used_mapping)

        # 3. Fallback to AI Vision last resort if no transactions found
        if not transactions:
            method_used = "AI Vision Fallback"
            confidence = 0.80
            try:
                if logger:
                    logger.log(f"Page {page_num + 1}: Local engines failed. Running AI Vision last-resort fallback...")
                
                from parser.ocr_parser import OCRParser
                from services.gemini_service import GeminiService
                
                pil_image = OCRParser.render_pdf_page_to_pil(pdf_path, page_num)
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

        return transactions, page_headers, used_mapping, method_used, grid_table, confidence
