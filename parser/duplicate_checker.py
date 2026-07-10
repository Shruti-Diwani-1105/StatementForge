class DuplicateChecker:
    """Filters duplicate parsed records while preserving genuine repeated transactions (varying balances)."""

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

            tx_key = (date, narration, debit, credit, balance, ref_no)

            narr_lower = narration.lower()
            if any(term in narr_lower for term in ["brought forward", "carried forward", "b/f", "c/f", "opening balance", "closing balance"]):
                continue

            if tx_key in seen_keys:
                continue

            seen_keys.add(tx_key)
            deduplicated.append(tx)

        return deduplicated
