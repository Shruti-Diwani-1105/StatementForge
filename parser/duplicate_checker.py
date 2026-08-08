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
        seen_contents = {}

        for tx in transactions:
            date = tx.get("date", "").strip()
            narration = tx.get("narration", "").strip()
            debit = tx.get("debit", "").strip()
            credit = tx.get("credit", "").strip()
            balance = tx.get("balance", "")
            balance = str(balance).strip() if balance is not None else ""
            ref_no = tx.get("ref_no", "").strip()

            page = tx.get("_source_page", "")
            row_idx = tx.get("_source_row", tx.get("_grid_row_idx", ""))

            # Uniqueness based on location and content
            tx_key = (date, narration, debit, credit, balance, ref_no, page, row_idx)
            content_key = (date, narration, debit, credit, balance, ref_no)

            if cls.META_REGEX.search(narration):
                if not debit and not credit:
                    continue

            if tx_key in seen_keys:
                continue

            seen_keys.add(tx_key)
            
            if content_key in seen_contents:
                # Legit identical transactions from different positions - mark as possible duplicate
                tx["_possible_duplicate"] = True
                for prev_tx in seen_contents[content_key]:
                    prev_tx["_possible_duplicate"] = True
                seen_contents[content_key].append(tx)
            else:
                seen_contents[content_key] = [tx]

            deduplicated.append(tx)

        return deduplicated

