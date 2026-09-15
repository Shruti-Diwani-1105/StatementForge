# 🚀 StatementForge – Automated Bank Statement Parser and Accounting Hub

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![GUI Framework](https://img.shields.io/badge/GUI-PyQt6-green.svg)](https://pypi.org/project/PyQt6/)
[![Database](https://img.shields.io/badge/Database-MongoDB%20Atlas-forestgreen.svg)](https://www.mongodb.com/cloud/atlas)
[![License](https://img.shields.io/badge/license-Academic%20%2F%20Educational-orange.svg)](#-license)

**StatementForge** is a modern **cross-platform desktop application** built with **Python** and **PyQt6** that automates the extraction, verification, and conversion of bank statement transactions into clean, standardized Excel reports.

The application is designed to reduce manual data entry, improve accuracy, and simplify financial statement processing for accountants, businesses, and individuals.

---

## 📌 Table of Contents

- [✨ Features](#-features)
- [🛠 Tech Stack](#-tech-stack)
- [📂 Project Structure](#-project-structure)
- [🏗 Application Workflow](#-application-workflow)
- [📋 Supported Features](#-supported-features)
- [🏦 Supported Banks](#-supported-banks)
- [⚙ Installation](#-installation)
- [☁ MongoDB Atlas Configuration](#-mongodb-atlas-configuration)
- [🗂 Database Collections](#-database-collections)
- [🎯 Future Enhancements](#-future-enhancements)
- [👨‍💻 Team & Authors](#-team--authors)
- [📄 License](#-license)

---

## ✨ Features

- 📄 **Multi-Bank Statement Support**: Seamlessly processes statements from 15+ leading Indian banks.
- 🤖 **AI-Based Bank Detection**: Automatically detects bank provider format and transaction structure.
- 🔍 **Scanned PDF OCR Engine**: Integrated **Tesseract OCR** and **OpenCV** image processing for scanned PDFs.
- 📑 **Digital PDF Extraction**: Native text and layout extraction using **pdfplumber**.
- 📊 **Automatic Excel Report Generation**: Generates standardized multi-sheet Excel reports via **openpyxl**.
- 📈 **AI Financial Report Generator**: Produces automated financial health insights, summaries, and metrics.
- 📤 **Tally Export Support**: Formats data for direct import into Tally ERP/Prime.
- 📧 **Email Integration**: Automated dispatch with attached financial reports.
- 🔄 **Duplicate Transaction Finder**: Identifies duplicate transactions across statements.
- 📂 **Statement History & Auditing**: Local and MongoDB cloud statement tracking.
- 👤 **Secure User Authentication**: Bcrypt password encryption and session management.
- ☁ **MongoDB Atlas Integration**: Cloud data persistence and history logs.

---

## 🛠 Tech Stack

| Category | Technology | Description |
| :--- | :--- | :--- |
| **Language** | Python 3.10+ | Core Application Backend |
| **GUI Framework** | PyQt6 | Modern Desktop Interface |
| **Styling & Web Engine** | QSS & PyQt6 WebEngine | Custom SaaS Layouts & Styling |
| **PDF Extraction** | pdfplumber | Native PDF Document Parsing |
| **OCR Engine** | Tesseract OCR & OpenCV | Scanned Image / PDF Preprocessing |
| **Excel Generation** | openpyxl | Automated Excel Report Synthesis |
| **Database** | MongoDB Atlas (`pymongo`) | Cloud Data Persistence |
| **Security** | bcrypt | Password Hashing & Keyring Encryption |
| **Visualizations** | Matplotlib | Financial Summary Charts & Graphs |
| **PDF Export** | ReportLab & QTextDocument | High-Resolution PDF Exports |

---

## 📂 Project Structure

```text
StatementForge/
│
├── assets/                  # Icons, branding images, and logos
├── controllers/             # Business logic and application controllers
├── database/                # MongoDB repository access layer & models
├── models/                  # Core data models and schemas
├── parser/                  # Bank statement PDF parsers & OCR engine
├── services/                # Email, AI summary, and export services
├── styles/                  # Qt Style Sheets (QSS)
├── ui/                      # PyQt6 UI screens & composer dialogs
├── utils/                   # Helper utilities and session managers
├── web/                     # Embedded HTML/JS dashboard & templates
├── widgets/                 # Custom reusable PyQt6 widgets
│
├── main.py                  # Main Application Entry Point
├── cli.py                   # Command Line Interface runner
├── requirements.txt         # Required Python packages
└── README.md                # Project documentation
```

---

## 🏗 Application Workflow

```text
               +-----------------------+
               |     Splash Screen     |
               +-----------+-----------+
                           |
                           v
               +-----------------------+
               |    Welcome Screen     |
               +-----------+-----------+
                           |
                           v
               +-----------------------+
               |   Login / Register    |
               +-----------+-----------+
                           |
                           v
               +-----------------------+
               |       Dashboard       |
               +-----------+-----------+
                           |
                           v
               +-----------------------+
               | Upload Bank Statement |
               +-----------+-----------+
                           |
                           v
               +-----------------------+
               |   AI Bank Detection   |
               +-----------+-----------+
                           |
                           v
               +-----------------------+
               |   PDF Parsing / OCR   |
               +-----------+-----------+
                           |
                           v
               +-----------------------+
               | Transaction Extraction|
               +-----------+-----------+
                           |
                           v
               +-----------------------+
               | Preview Transactions  |
               +-----------+-----------+
                           |
                           v
               +-----------------------+
               | Generate & Save Excel |
               +-----------+-----------+
                           |
                           v
               +-----------------------+
               | Saved to History & DB |
               +-----------------------+
```

---

## 📋 Supported Features

### 👤 User Module
- User Registration & Authentication
- Password Hashing (`bcrypt`)
- Profile Management & Credential Security
- Session Persistence

### 📄 Statement & Parsing Module
- PDF Bank Statement Upload
- Automatic Bank Format Detection
- Digital PDF & Scanned OCR Engine
- Interactive Transaction Grid & Editing

### 📊 Reports & Exports
- Excel Export (`.xlsx`)
- AI Financial Analysis Report
- GST Reconciliation Report
- Duplicate Transaction Detection Report
- Tally ERP Format Export
- Automated Email Center Dispatch

---

## 🏦 Supported Banks

- SBI (State Bank of India)
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

### 1. Clone the repository

```bash
git clone https://github.com/Shruti-Diwani-1105/StatementForge.git
cd StatementForge
```

### 2. Set up virtual environment (Recommended)

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the application

```bash
python main.py
```

---

## 📦 Required Packages

```text
PyQt6
PyQt6-WebEngine
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
keyring
```

---

## ☁ MongoDB Atlas Configuration

Create a `.env` file in the project root directory:

```env
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority
DATABASE_NAME=statementforge
```

---

## 🗂 Database Collections

```text
statementforge
│
├── users                # Registered application accounts
├── statements           # Uploaded statement metadata
├── transactions         # Parsed transaction line items
├── reports              # Generated report logs
├── ai_reports           # AI summary & analysis records
├── gst_reports          # GST calculation logs
├── login_history        # Audit logs for user logins
├── activity_logs       # User action logs
└── settings             # System & user preference settings
```

---

## 🎯 Future Enhancements

- [ ] AI Automated Transaction Categorization
- [ ] Fraud & Anomalous Spiking Detection
- [ ] Multi-Currency Conversion Support
- [ ] Cloud Backup & Sync
- [ ] Password-Protected PDF Auto-Decrypt
- [ ] Multi-Statement Batch Merging

---

## 👨‍💻 Team & Authors

**Final Year Engineering Project**  
**Domain**: FinTech & Business Automation  

- **Kinjal Rajyaguru** ([@kinjalrajyaguru27](https://github.com/kinjalrajyaguru27))
- **Shruti Diwani** ([@Shruti-diwani11](https://github.com/Shruti-diwani11))
- **Priyanshi Prajapati**
- **Sneha Vasava**

---

## 📄 License

This project is developed for educational, academic, and demonstration purposes.

---

## ⭐ Support

If you find **StatementForge** useful, please give this repository a ⭐ on GitHub!
