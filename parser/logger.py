class ParserLogger:
    """Handles structured logging output, keeping track of history and output formatting."""

    def __init__(self):
        self.logs = []

    def log(self, message: str):
        """Appends log line and prints to stdout."""
        self.logs.append(message)
        print(f"[Parser] {message}")

    def log_page_success(self, page_num: int, is_digital: bool, count: int, method_used: str, confidence: int = 99):
        """Logs details of a successfully parsed page."""
        self.log(f"Processing Page {page_num}")
        self.log(f"Extraction Method: {method_used}")
        self.log(f"Transactions Found: {count}")
        self.log(f"Confidence: {confidence}%")
        self.log("-" * 32)

    def log_page_failure(self, page_num: int, error_msg: str):
        """Logs details of a failed page extraction."""
        self.log(f"Page {page_num} Failed")
        self.log(f"Reason: {error_msg}")
        self.log("Continuing Remaining Pages...")
        self.log("-" * 32)

    def log_summary(self, total_pages: int, failed_pages: int, initial_count: int, final_count: int):
        """Logs overall parsing execution summaries."""
        self.log("=" * 32)
        self.log(f"Pages Processed: {total_pages - failed_pages}")
        self.log(f"Transactions Extracted: {initial_count}")
        self.log(f"Transactions Written: {final_count}")
        self.log(f"Failed Pages: {failed_pages}")
        if initial_count == final_count:
            self.log("Verification: The number of extracted transactions exactly matches the number of rows written to the Excel file.")
        else:
            self.log(f"Verification Check: Mismatch detected between extracted ({initial_count}) and written ({final_count}) transactions.")
        self.log("Excel Generated Successfully")

    def get_logs(self) -> str:
        """Returns all aggregated log entries as a newline-separated string."""
        return "\n".join(self.logs)
