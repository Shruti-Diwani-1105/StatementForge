from abc import ABC, abstractmethod

class BaseParser(ABC):
    """Abstract Base Class for all local bank statement parsers."""
    
    @classmethod
    @abstractmethod
    def parse(cls, raw_text: str) -> dict:
        """
        Parses raw text from digital PDF statements.
        Returns a dictionary containing:
        {
            "metadata": {
                "bank_name": str,
                "account_holder": str,
                "account_number": str,
                "period": str,
                "currency": str
            },
            "transactions": list of dicts (each having date, narration, debit, credit, balance)
        }
        """
        pass
