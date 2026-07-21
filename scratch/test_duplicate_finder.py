import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.duplicate_finder_service import DuplicateFinderService

def run_tests():
    print("==================================================")
    print("  Testing DuplicateFinderService Core Engine")
    print("==================================================")

    # Sample test dataset with exact, potential, and clean transactions
    sample_txs = [
        # Exact Duplicates (Row 1 & 2)
        {"date": "10/05/2026", "narration": "UPI/123456789/AMAZON PAY", "debit": "1500.00", "credit": "", "balance": "45000.00", "ref_no": "123456789"},
        {"date": "10/05/2026", "narration": "UPI/123456789/AMAZON PAY", "debit": "1500.00", "credit": "", "balance": "45000.00", "ref_no": "123456789"},

        # Potential / Fuzzy Match (Row 3 & 4) - Same date & amount, slightly different narration
        {"date": "12/05/2026", "narration": "POS SWIPE STARBUCKS COFFEE MUMBAI", "debit": "450.00", "credit": "", "balance": "44550.00", "ref_no": "POS9981"},
        {"date": "12/05/2026", "narration": "POS SWIPE STARBUCKS COFFEE", "debit": "450.00", "credit": "", "balance": "44100.00", "ref_no": "POS9982"},

        # Time-Window Match (Row 5 & 6) - Same amount within 1 day
        {"date": "15/05/2026", "narration": "NET BANKING NEFT REF12345", "debit": "25000.00", "credit": "", "balance": "19100.00", "ref_no": "REF12345"},
        {"date": "16/05/2026", "narration": "NET BANKING NEFT REF12345", "debit": "25000.00", "credit": "", "balance": "-5900.00", "ref_no": "REF12345"},

        # Unique Genuine Transaction (Row 7)
        {"date": "18/05/2026", "narration": "SALARY CREDIT TECH CORP", "debit": "", "credit": "85000.00", "balance": "79100.00", "ref_no": "SAL001"}
    ]

    # Test single statement analysis
    result = DuplicateFinderService.analyze_statement(sample_txs, {
        "exact_match": True,
        "potential_match": True,
        "date_window_days": 2,
        "similarity_threshold": 0.70
    })

    stats = result["stats"]
    clusters = result["clusters"]

    print(f"Total Transactions Scanned: {stats['total_transactions']}")
    print(f"Duplicate Clusters Found: {stats['duplicate_clusters']}")
    print(f"Excess Entries Flagged: {stats['excess_entries']}")
    print(f"Flagged Debit Amount: ₹ {stats['flagged_debit_sum']:,.2f}")
    print(f"Cleanliness Score: {stats['cleanliness_score']}%")

    assert stats["total_transactions"] == 7, "Total transactions count mismatch"
    assert stats["duplicate_clusters"] == 3, f"Expected 3 clusters, got {stats['duplicate_clusters']}"

    print("\n--- Identified Clusters ---")
    for c in clusters:
        print(f"[{c['id']}] {c['match_type']} ({c['confidence']}%): {c['reason']} - Items: {len(c['items'])}")

    # Test auto resolution strategy
    decisions = DuplicateFinderService.apply_auto_resolution(clusters, strategy="keep_first")
    removals = [k for k, v in decisions.items() if v == "remove"]
    assert len(removals) == 3, f"Expected 3 entries marked for removal, got {len(removals)}"
    print(f"\nAuto-resolution 'keep_first' marked {len(removals)} entries for deletion.")

    # Test Excel Report export
    output_report = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_audit_report.xlsx")
    DuplicateFinderService.export_duplicate_report(clusters, stats, output_report)
    assert os.path.exists(output_report), "Excel report file was not created"
    print(f"\nSuccessfully generated Excel audit report: {output_report}")

    print("\n==================================================")
    print("  ALL DUPLICATE FINDER ENGINE TESTS PASSED!")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
