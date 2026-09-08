import os
import json
import unittest

class TestDragDropHandler(unittest.TestCase):
    def test_drag_drop_ipc_payload(self):
        sample_path = "/Users/test/Documents/sample_statement.pdf"
        payload = json.dumps({"path": sample_path, "fileName": "sample_statement.pdf"})
        data = json.loads(payload)
        
        self.assertEqual(data.get("path"), sample_path)
        self.assertTrue(sample_path.endswith(".pdf"))

    def test_pdf_extension_check(self):
        pdf_file = "statement_2024.PDF"
        non_pdf = "image.png"
        
        self.assertTrue(pdf_file.lower().endswith(".pdf"))
        self.assertFalse(non_pdf.lower().endswith(".pdf"))

if __name__ == "__main__":
    unittest.main()
