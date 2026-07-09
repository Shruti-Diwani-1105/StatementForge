# 🚀 StatementForge – Automated Bank Statement Parser and Accounting Hub

StatementForge is a modern **cross-platform desktop application** built with **Python** and **PyQt6** that automates the extraction, verification, and conversion of bank statement transactions into clean, standardized Excel reports.

The application is designed to reduce manual data entry, improve accuracy, and simplify financial statement processing for accountants, businesses, and individuals.

---

## ✨ Features

- 📄 Multi-Bank Statement Support
- 🤖 AI-Based Bank Statement Detection
- 🔍 OCR Support for Scanned PDFs (Tesseract OCR)
- 📑 Digital PDF Parsing (pdfplumber)
- 📊 Automatic Excel Report Generation
- 📈 AI Financial Report Generator
- 💰 GST Report Generator
- 📤 Tally Export Support
- 📧 Email Excel Reports
- 🔄 Duplicate Transaction Detection
- 📂 Statement History Management
- 👤 Secure User Authentication
- ☁ MongoDB Atlas Integration
- 💻 Modern PyQt6 Desktop Interface
- 🌙 Offline Processing
- ⚡ Fast & Accurate Transaction Extraction

---

## 🛠 Tech Stack

| Category | Technology |
|----------|------------|
| Language | Python 3.12+ |
| GUI | PyQt6 |
| Styling | Qt Style Sheets (QSS) |
| OCR | Tesseract OCR |
| Image Processing | OpenCV |
| PDF Extraction | pdfplumber |
| Excel Generation | openpyxl |
| Database | MongoDB Atlas |
| Database Driver | pymongo |
| Password Hashing | bcrypt |
| Charts | Matplotlib |
| Reports | ReportLab |
| IDE | Visual Studio Code |
| Version Control | Git & GitHub |

---

## 📂 Project Structure

```text
StatementForge/
│
├── assets/
│   ├── icons/
│   ├── images/
│   └── logo.png
│
├── controllers/
├── database/
├── models/
├── services/
├── styles/
├── ui/
├── utils/
├── widgets/
│
├── main.py
├── requirements.txt
└── README.md
```

---

## 🏗 Application Workflow

```text
Splash Screen
      │
      ▼
Welcome Screen
      │
      ▼
Login / Register
      │
      ▼
Dashboard
      │
      ▼
Upload Bank Statement
      │
      ▼
AI Bank Detection
      │
      ▼
PDF Parsing / OCR
      │
      ▼
Transaction Extraction
      │
      ▼
Preview Transactions
      │
      ▼
Generate Excel
      │
      ▼
Save Excel
      │
      ▼
History Saved
```

---

## 📋 Supported Features

### User Module
- User Registration
- Secure Login
- Password Encryption
- Profile Management
- Session Management

### Statement Module
- Upload PDF Statement
- Automatic Bank Detection
- OCR Support
- Digital PDF Support
- Transaction Preview

### Reports
- Excel Export
- AI Financial Report
- GST Report
- Duplicate Transaction Report
- Tally Export

### Dashboard
- Statistics
- Recent Activity
- Statement History
- Reports Summary

---

## 🏦 Supported Banks

- SBI
- HDFC Bank
- ICICI Bank
- Axis Bank
- Bank of Baroda
- Kotak Mahindra Bank
- Canara Bank
- Punjab National Bank
- Union Bank of India
- Indian Bank
- IDBI Bank
- Federal Bank
- IndusInd Bank
- AU Small Finance Bank
- Yes Bank

---

## ⚙ Installation

Clone the repository

```bash
git clone https://github.com/yourusername/StatementForge.git
```

Move into the project folder

```bash
cd StatementForge
```

Install dependencies

```bash
pip install -r requirements.txt
```

Run the application

```bash
python main.py
```

---

## 📦 Required Packages

```text
PyQt6
opencv-python
pdfplumber
pytesseract
openpyxl
pymongo
bcrypt
reportlab
matplotlib
Pillow
python-dotenv
```

---

## ☁ MongoDB Atlas Configuration

Create a `.env` file in the project root.

```env
MONGODB_URI=your_mongodb_connection_string
DATABASE_NAME=statementforge
```

Example

```env
MONGODB_URI=mongodb+srv://username:password@statementforge-cluster.mongodb.net/?retryWrites=true&w=majority
DATABASE_NAME=statementforge
```

---

## 🗂 Database Collections

```text
statementforge
│
├── users
├── statements
├── transactions
├── reports
├── ai_reports
├── gst_reports
├── login_history
├── activity_logs
└── settings
```

---

## 🎯 Future Enhancements

- AI Transaction Categorization
- Fraud Detection
- Multi-language Support
- Dark Mode
- Cloud Backup
- Password Protected PDF Support
- Drag & Drop PDF Upload
- PDF Report Generation
- Multiple Statement Merge
- Analytics Dashboard

---

## 👨‍💻 Author

**Kinjal Rajyaguru**

**Shruti Diwani**

**Priyanshi Prajapati**

**Sneha Vasava**


Final Year Project

**StatementForge – Automated Bank Statement Parser and Accounting Hub**

Domain: **FinTech & Business Automation**

---

## 📄 License

This project is developed for educational and academic purposes.

---

## ⭐ If you like this project

Give this repository a ⭐ on GitHub.
