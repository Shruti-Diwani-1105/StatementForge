import sys
sys.path.append('.')
from PyQt6.QtWidgets import QApplication
from ui.upload_statement import UploadStatementWidget

app = QApplication([])
widget = UploadStatementWidget()
widget.file_path = "dummy.pdf"
widget.detected_bank = "HDFC Bank"
widget.page_count = 17
try:
    widget.start_processing_flow()
    print("start_processing_flow completed successfully without NameError!")
except Exception as e:
    import traceback
    traceback.print_exc()
