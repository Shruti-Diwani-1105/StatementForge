import re

class DuplicateChecker:
    """Filters duplicate parsed records while preserving genuine repeated transactions (varying balances)."""

    META_REGEX = re.compile(
        r"\b(brought\s+forward|carried\s+forward|b/f|c/f|opening\s+balance|closing\s+balance)\b",
        re.IGNORECASE
    )

    @classmethod
    def remove_duplicates(cls, transactions: list) -> list:
        """
        Deduplicates transaction lists.
        Two transactions are considered duplicates only if:
        1. All fields (date, narration, debit, credit, balance) are completely identical.
        2. If balance is present and non-empty, and it matches, it is highly likely a double-read.
        """
        if not transactions:
            return []

        deduplicated = []
        seen_keys = set()

        for tx in transactions:
            date = tx.get("date", "").strip()
            narration = tx.get("narration", "").strip()
            debit = tx.get("debit", "").strip()
            credit = tx.get("credit", "").strip()
            balance = tx.get("balance", "")
            balance = str(balance).strip() if balance is not None else ""
            ref_no = tx.get("ref_no", "").strip()

            row_idx = tx.get("_grid_row_idx", "")
            tx_key = (date, narration, debit, credit, balance, ref_no, row_idx)

            if cls.META_REGEX.search(narration):
                if not debit and not credit:
                    continue

            if tx_key in seen_keys:
                continue

            seen_keys.add(tx_key)
            if "_grid_row_idx" in tx:
                del tx["_grid_row_idx"]
            deduplicated.append(tx)

        return deduplicated

