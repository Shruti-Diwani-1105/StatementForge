import os
import unittest

class TestExportFilename(unittest.TestCase):
    def test_csv_export_filename_resolution(self):
        pdf_path = "/Users/testuser/Documents/Bank_Statement_Jan2024.pdf"
        base_name, _ = os.path.splitext(os.path.basename(pdf_path))
        pdf_dir = os.path.dirname(pdf_path)
        
        csv_filename = f"{base_name}.csv"
        csv_path = os.path.join(pdf_dir, csv_filename)
        
        self.assertEqual(csv_filename, "Bank_Statement_Jan2024.csv")
        self.assertEqual(csv_path, "/Users/testuser/Documents/Bank_Statement_Jan2024.csv")

    def test_json_export_filename_resolution(self):
        pdf_path = "/Users/testuser/Documents/Bank_Statement_Jan2024.pdf"
        base_name, _ = os.path.splitext(os.path.basename(pdf_path))
        pdf_dir = os.path.dirname(pdf_path)
        
        json_filename = f"{base_name}.json"
        json_path = os.path.join(pdf_dir, json_filename)
        
        self.assertEqual(json_filename, "Bank_Statement_Jan2024.json")
        self.assertEqual(json_path, "/Users/testuser/Documents/Bank_Statement_Jan2024.json")

if __name__ == "__main__":
    unittest.main()
