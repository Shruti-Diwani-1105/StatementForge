import re

class GSTService:
    """Classifies transactions and calculates GST (CGST/SGST/IGST) amounts."""
    
    DEFAULT_GST_RATE = 0.18  # 18% standard GST for banking & services in India

    # Keywords that suggest a transaction involves GST or tax
    GST_KEYWORDS = [
        "gst", "cgst", "sgst", "igst", "tax", "fee", "chg", "charge",
        "commission", "comm.", "invoice", "bill", "service"
    ]

    @classmethod
    def is_gst_applicable(cls, narration: str) -> bool:
        """Determines if a transaction narration likely includes GST."""
        narration_lower = narration.lower()
        return any(kw in narration_lower for kw in cls.GST_KEYWORDS)

    @classmethod
    def calculate_gst_breakdown(cls, amount: float, is_debit: bool, narration: str) -> dict:
        """
        Calculates Base Value and GST components (CGST, SGST, IGST).
        Assumes the transaction amount is GST inclusive.
        """
        if amount <= 0:
            return {
                "base_value": 0.0, "cgst": 0.0, "sgst": 0.0, "igst": 0.0, "total_gst": 0.0
            }

        # Calculate GST and Base taxable value (amount = base_value * 1.18)
        base_value = amount / (1.0 + cls.DEFAULT_GST_RATE)
        total_gst = amount - base_value

        # Heuristic for IGST vs CGST/SGST:
        # Default to CGST + SGST (Intrastate) unless IGST is explicitly in the narration
        if "igst" in narration.lower():
            cgst = 0.0
            sgst = 0.0
            igst = total_gst
        else:
            cgst = total_gst / 2.0
            sgst = total_gst / 2.0
            igst = 0.0

        return {
            "base_value": round(base_value, 2),
            "cgst": round(cgst, 2),
            "sgst": round(sgst, 2),
            "igst": round(igst, 2),
            "total_gst": round(total_gst, 2)
        }

    @classmethod
    def generate_gst_ledger(cls, transactions: list) -> list:
        """Processes raw bank transactions and builds a GST ledger."""
        gst_ledger = []
        if not transactions:
            return gst_ledger

        for tx in transactions:
            narration = tx.get("narration", "")
            debit = tx.get("debit", 0.0)
            credit = tx.get("credit", 0.0)

            # Safely parse debit and credit to float since they can be string representations
            try:
                debit_val = float(debit) if debit else 0.0
            except (ValueError, TypeError):
                debit_val = 0.0

            try:
                credit_val = float(credit) if credit else 0.0
            except (ValueError, TypeError):
                credit_val = 0.0

            # Determine transaction type and amount
            if debit_val > 0:
                amount = debit_val
                tx_type = "Debit (ITC Claimable)"
                is_debit = True
            elif credit_val > 0:
                amount = credit_val
                tx_type = "Credit (GST Output)"
                is_debit = False
            else:
                continue

            if cls.is_gst_applicable(narration):
                breakdown = cls.calculate_gst_breakdown(amount, is_debit, narration)
                gst_ledger.append({
                    "date": tx.get("date", ""),
                    "narration": narration,
                    "type": tx_type,
                    "total_amount": amount,
                    "base_value": breakdown["base_value"],
                    "cgst": breakdown["cgst"],
                    "sgst": breakdown["sgst"],
                    "igst": breakdown["igst"],
                    "total_gst": breakdown["total_gst"]
                })
        return gst_ledger
