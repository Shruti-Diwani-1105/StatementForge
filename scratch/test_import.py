import sys
sys.path.append('.')
try:
    from ui.upload_statement import UploadStatementWidget
    print("UploadStatementWidget imported successfully!")
    print("HistoryService in globals:", "HistoryService" in globals())
    import ui.upload_statement
    print("HistoryService in ui.upload_statement:", hasattr(ui.upload_statement, "HistoryService"))
except Exception as e:
    import traceback
    traceback.print_exc()
