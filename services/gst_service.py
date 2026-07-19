import re
import datetime
import os
from services.history_service import HistoryService
from settings.settings_service import SettingsService

class GSTService:
    """Classifies transactions and calculates GST (CGST/SGST/IGST) amounts locally or using AI."""
    
    DEFAULT_GST_RATE = 0.18  # 18% standard GST for banking & services in India

    GST_KEYWORDS = [
        "gst", "cgst", "sgst", "igst", "tax", "fee", "chg", "charge",
        "commission", "comm.", "invoice", "bill", "service"
    ]

    CATEGORIES = {
        "Bank Charges": ["chg", "charge", "fee", "comm", "commission", "annual chg", "maintenance", "card chg", "interest charge", "processing fee", "service tax"],
        "Processing Fees": ["proc fee", "processing fee", "loan proc", "proc. fee", "documentation charge"],
        "Service Charges": ["service chg", "serv chg", "service charge", "handling"],
        "Courier Charges": ["courier", "speed post", "dhl", "fedex", "blue dart", "postal", "postage"],
        "Office Expenses": ["stationery", "office", "pantry", "furniture", "xerox", "print", "supplies"],
        "Utilities": ["electricity", "water", "bill", "bsnl", "airtel", "jio", "power", "telecom", "recharge", "broadband"],
        "Software Subscription": ["microsoft", "google", "aws", "adobe", "github", "subscription", "zoom", "slack", "saas", "godaddy", "domain", "hosting"],
        "Vendor Payment": ["neft", "rtgs", "imap", "imps", "to ", "transfer to", "pymt", "payment to", "vendor", "purchase", "supplier", "settlement"],
        "Fuel": ["fuel", "petrol", "hpcl", "bpcl", "iocl", "shell", "cng", "service station"],
        "Travel": ["uber", "ola", "travel", "flight", "irctc", "hotel", "stay", "cab", "taxi", "makemytrip", "yatra", "indigo"],
    }

    PERSONAL_KEYWORDS = [
        "netflix", "spotify", "zomato", "swiggy", "starbucks", "movie", "cinema", 
        "mall", "grocery", "supermarket", "dmart", "amazon retail", "myntra", 
        "personal", "paytm spend", "bazaar", "club", "dining", "pub", "restaurant"
    ]

    KNOWN_VENDORS = {
        "hdfc": "HDFC Bank",
        "icici": "ICICI Bank",
        "sbi": "State Bank of India",
        "axis": "Axis Bank",
        "kotak": "Kotak Mahindra Bank",
        "uber": "Uber",
        "ola": "Ola Cabs",
        "amazon": "Amazon",
        "google": "Google Cloud / Workspace",
        "aws": "Amazon Web Services",
        "microsoft": "Microsoft",
        "adobe": "Adobe Systems",
        "github": "GitHub",
        "zoom": "Zoom Video Communications",
        "airtel": "Bharti Airtel",
        "jio": "Reliance Jio",
        "hpcl": "Hindustan Petroleum",
        "bpcl": "Bharat Petroleum",
        "iocl": "Indian Oil Corporation",
        "irctc": "IRCTC",
        "blue dart": "Blue Dart Express",
        "dhl": "DHL Express",
        "fedex": "FedEx",
    }

    @classmethod
    def is_gst_applicable(cls, narration: str) -> bool:
        """Determines if a transaction narration likely includes GST."""
        narration_lower = narration.lower()
        return any(kw in narration_lower for kw in cls.GST_KEYWORDS)

    @classmethod
    def classify_category(cls, narration: str) -> str:
        """Classifies a transaction into a business category based on narration keywords."""
        narration_lower = narration.lower()
        for category, keywords in cls.CATEGORIES.items():
            if any(kw in narration_lower for kw in keywords):
                return category
        return "Miscellaneous"

    @classmethod
    def detect_vendor(cls, narration: str) -> str:
        """Extracts and normalizes the vendor name from the transaction narration."""
        narration_lower = narration.lower()
        
        # Check against known vendors
        for kw, name in cls.KNOWN_VENDORS.items():
            if kw in narration_lower:
                return name
        
        # Heuristics for UPI narration: UPI/Name/ID
        upi_match = re.search(r'upi/([^/]+)', narration_lower)
        if upi_match:
            vendor = upi_match.group(1).replace("to ", "").strip()
            return vendor.upper()
            
        # POS transaction
        pos_match = re.search(r'pos\s+([^/]+)', narration_lower)
        if pos_match:
            return pos_match.group(1).strip().upper()
            
        # Clean up some common prefixes
        cleaned = re.sub(r'^(neft|rtgs|imps|transfer|chg|pymt|payment|val)\s*[-/:]?\s*', '', narration_lower)
        # Take the first 3 words
        words = cleaned.split()
        if words:
            return " ".join(words[:2]).upper()
            
        return "Unknown Vendor"

    @classmethod
    def is_business_transaction(cls, narration: str) -> bool:
        """Determines if a transaction is business or personal."""
        narration_lower = narration.lower()
        if any(kw in narration_lower for kw in cls.PERSONAL_KEYWORDS):
            return False
        return True

    @classmethod
    def detect_gst_rate(cls, category: str, narration: str) -> float:
        """Determines the GST rate (0% to 28%) dynamically based on keywords or category."""
        narration_lower = narration.lower()
        cat_lower = category.lower()
        
        # Check explicit rates in narration first (e.g. "GST 18%", "GST 5%", "CGST @9%")
        rate_match = re.search(r'(?:gst|cgst|sgst|rate)\s*@?\s*(\d+(?:\.\d+)?)\s*%', narration_lower)
        if rate_match:
            try:
                return float(rate_match.group(1)) / 100.0
            except:
                pass
                
        if "cgst 9" in narration_lower or "sgst 9" in narration_lower or "cgst @ 9" in narration_lower:
            return 0.18
        if "cgst 2.5" in narration_lower or "sgst 2.5" in narration_lower or "cgst @ 2.5" in narration_lower:
            return 0.05
        if "cgst 6" in narration_lower or "sgst 6" in narration_lower or "cgst @ 6" in narration_lower:
            return 0.12
        if "cgst 14" in narration_lower or "sgst 14" in narration_lower or "cgst @ 14" in narration_lower:
            return 0.28

        # Fallback based on category
        if cat_lower in ("fuel", "utilities"):
            return 0.00  # often zero-rated or outside GST scope
        elif cat_lower == "travel":
            return 0.05  # 5% GST on passenger transport services
        elif cat_lower in ("bank charges", "processing fees", "service charges", "software subscription", "office expenses", "courier charges", "vendor payment"):
            return 0.18
        
        return cls.DEFAULT_GST_RATE

    @classmethod
    def is_itc_eligible(cls, category: str, is_business: bool) -> bool:
        """Determines if Input Tax Credit is claimable under Indian GST rules."""
        if not is_business:
            return False
        cat_lower = category.lower()
        # Blocked credits under Section 17(5) of CGST Act (e.g. food/beverages, personal fuel)
        if cat_lower in ("fuel", "personal"):
            return False
        return True

    @classmethod
    def calculate_gst_breakdown(cls, amount: float, rate: float, narration: str) -> dict:
        """Calculates Base Value and GST components (CGST, SGST, IGST)."""
        if amount <= 0:
            return {"base_value": 0.0, "cgst": 0.0, "sgst": 0.0, "igst": 0.0, "total_gst": 0.0}

        # Calculate GST and Base taxable value (amount = base_value * (1 + rate))
        base_value = amount / (1.0 + rate)
        total_gst = amount - base_value

        # Heuristic for IGST (Interstate) vs CGST+SGST (Intrastate)
        if "igst" in narration.lower() or "interstate" in narration.lower():
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
        """Processes raw bank transactions and builds a detailed GST ledger using local rules or AI."""
        if not transactions:
            return []

        try:
            from services.gemini_service import GeminiService
            api_key = GeminiService.get_api_key()
            if api_key and api_key.strip():
                ai_ledger = GeminiService.analyze_gst_transactions(transactions)
                if ai_ledger:
                    return ai_ledger
        except Exception as e:
            print(f"GSTService: AI Analysis failed, falling back to local engine. Error: {e}")

        gst_ledger = []

        # Sort transactions by date if possible
        def get_date_key(tx):
            d_str = tx.get("date", "")
            try:
                for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y"):
                    try:
                        return datetime.datetime.strptime(d_str, fmt)
                    except:
                        pass
            except:
                pass
            return datetime.datetime.min
            
        sorted_txs = sorted(transactions, key=get_date_key)

        for tx in sorted_txs:
            narration = tx.get("narration", "")
            debit = tx.get("debit", 0.0)
            credit = tx.get("credit", 0.0)

            # Safely parse debit and credit
            try:
                debit_val = float(str(debit).replace(",", "").strip()) if debit else 0.0
            except:
                debit_val = 0.0

            try:
                credit_val = float(str(credit).replace(",", "").strip()) if credit else 0.0
            except:
                credit_val = 0.0

            # Determine type and amount
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

            # Classifications
            category = cls.classify_category(narration)
            vendor = cls.detect_vendor(narration)
            is_business = cls.is_business_transaction(narration)
            
            # Change category if it's personal
            if not is_business:
                category = "Personal"
                
            rate = cls.detect_gst_rate(category, narration)
            itc_eligible = cls.is_itc_eligible(category, is_business)

            # If GST keyword is present or we assume rate > 0 is GST-applicable
            gst_applicable = cls.is_gst_applicable(narration) or (rate > 0 and is_business)
            
            # Calculate tax breakdown
            if gst_applicable:
                breakdown = cls.calculate_gst_breakdown(amount, rate, narration)
            else:
                breakdown = {
                    "base_value": amount, "cgst": 0.0, "sgst": 0.0, "igst": 0.0, "total_gst": 0.0
                }

            # Setup basic confidence
            confidence = 90.0 if cls.is_gst_applicable(narration) else 75.0
            if category == "Miscellaneous":
                confidence -= 15.0

            gst_ledger.append({
                "date": tx.get("date", ""),
                "narration": narration,
                "type": tx_type,
                "category": category,
                "vendor": vendor,
                "total_amount": amount,
                "base_value": breakdown["base_value"],
                "gst_rate": rate,
                "cgst": breakdown["cgst"],
                "sgst": breakdown["sgst"],
                "igst": breakdown["igst"],
                "total_gst": breakdown["total_gst"],
                "itc_eligible": "Yes" if (itc_eligible and breakdown["total_gst"] > 0) else "No",
                "is_business": is_business,
                "confidence": confidence,
                "status": "Verified" if confidence >= 85 else "Estimated",
                "is_duplicate": False,
                "is_missing_invoice": False
            })

        # Post-process: Detect duplicate entries
        # Duplicate = same date, same amount, same narration (or very similar)
        for i in range(len(gst_ledger)):
            tx_i = gst_ledger[i]
            for j in range(i + 1, len(gst_ledger)):
                tx_j = gst_ledger[j]
                if tx_i["date"] == tx_j["date"] and abs(tx_i["total_amount"] - tx_j["total_amount"]) < 0.01 and tx_i["type"] == tx_j["type"]:
                    # Match narrations roughly
                    w1 = set(tx_i["narration"].lower().split())
                    w2 = set(tx_j["narration"].lower().split())
                    intersection = w1.intersection(w2)
                    if len(intersection) >= min(len(w1), len(w2)) * 0.6:
                        tx_i["is_duplicate"] = True
                        tx_j["is_duplicate"] = True

        # Post-process: Detect missing invoice candidates
        # Missing invoice = Business transaction, GST paid > 0, but no receipt keyword like "INV", "BILL", "TAX" or reference numbers
        for tx in gst_ledger:
            if tx["is_business"] and tx["total_gst"] > 0:
                narr_lower = tx["narration"].lower()
                has_invoice_ref = any(term in narr_lower for term in ["inv", "bill", "invoice", "tax invoice", "receipt", "ref:", "no:"])
                # Also bank charges never have invoice details in narration, so exclude them
                if not has_invoice_ref and tx["category"] != "Bank Charges":
                    tx["is_missing_invoice"] = True

        return gst_ledger

    @classmethod
    def mask_account_number(cls, acc_num: str) -> str:
        """Masks sensitive account numbers showing only final 4 digits."""
        if not acc_num or acc_num.lower() in ("unknown", "n/a"):
            return "XXXX5678"
        acc_clean = re.sub(r'[^a-zA-Z0-9]', '', acc_num)
        if len(acc_clean) <= 4:
            return f"XXXX{acc_clean}"
        return f"XXXX{acc_clean[-4:]}"

    @classmethod
    def detect_period_from_transactions(cls, transactions: list, default_period: str) -> str:
        """Determines the statement period dynamically from transaction dates if missing."""
        if default_period and default_period.lower() not in ("unknown", "n/a", "unknown period") and "-" in default_period:
            return default_period
            
        dates = []
        for tx in transactions:
            d_str = tx.get("date")
            if d_str:
                for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y", "%d-%b-%Y", "%d %b %Y"):
                    try:
                        dt = datetime.datetime.strptime(d_str.strip(), fmt)
                        dates.append(dt)
                        break
                    except:
                        pass
        if dates:
            dates.sort()
            min_date = dates[0].strftime("%d-%b-%Y")
            max_date = dates[-1].strftime("%d-%b-%Y")
            return f"{min_date} to {max_date}"
            
        return default_period or "Unknown Statement Period"

    @classmethod
    def detect_bank_name(cls, bank_name: str, transactions: list) -> str:
        """Detects the bank name from transaction narration if missing."""
        if bank_name and bank_name.lower() not in ("unknown bank", "unknown", "n/a"):
            return bank_name
            
        narration_text = " ".join([tx.get("narration", "").lower() for tx in transactions])
        if "hdfc" in narration_text:
            return "HDFC Bank"
        elif "icici" in narration_text:
            return "ICICI Bank"
        elif "sbi" in narration_text or "state bank" in narration_text:
            return "State Bank of India"
        elif "axis" in narration_text:
            return "Axis Bank"
        elif "kotak" in narration_text:
            return "Kotak Mahindra Bank"
        elif "idfc" in narration_text:
            return "IDFC First Bank"
        elif "yesb" in narration_text or "yes bank" in narration_text:
            return "Yes Bank"
            
        return "Standard Bank"

    @classmethod
    def generate_gst_report_html(cls, payload: dict, gst_ledger: list) -> str:
        """Generates a professional, self-contained HTML document for the GST report."""
        transactions = payload.get("transactions", [])
        
        # Meta values
        bank_name = cls.detect_bank_name(payload.get("bank_name"), transactions)
        account_holder = payload.get("account_holder") or "Corporate Account Holder"
        account_number = cls.mask_account_number(payload.get("account_number"))
        period = cls.detect_period_from_transactions(transactions, payload.get("period"))
        gen_time = datetime.datetime.now().strftime("%Y-%m-%d %I:%M %p")
        ai_ver = "StatementForge AI Tax Engine v2.1 (Flash)"

        # Metrics calculations
        total_scanned = len(transactions)
        gst_applicable_txs = [tx for tx in gst_ledger if tx["total_gst"] > 0]
        gst_applicable_count = len(gst_applicable_txs)
        
        est_business_expenses = sum(tx["total_amount"] for tx in gst_ledger if tx["is_business"])
        est_gst_paid = sum(tx["total_gst"] for tx in gst_ledger if "Debit" in tx["type"])
        est_gst_collected = sum(tx["total_gst"] for tx in gst_ledger if "Credit" in tx["type"])
        
        cgst_total = sum(tx["cgst"] for tx in gst_ledger)
        sgst_total = sum(tx["sgst"] for tx in gst_ledger)
        igst_total = sum(tx["igst"] for tx in gst_ledger)
        
        est_itc = sum(tx["total_gst"] for tx in gst_ledger if tx["itc_eligible"] == "Yes" and "Debit" in tx["type"])
        
        duplicate_count = sum(1 for tx in gst_ledger if tx["is_duplicate"])
        missing_invoice_count = sum(1 for tx in gst_ledger if tx["is_missing_invoice"])
        
        avg_confidence = sum(tx["confidence"] for tx in gst_ledger) / len(gst_ledger) if gst_ledger else 100.0

        # Monthly chart values
        monthly_gst = {}
        for tx in gst_ledger:
            date_str = tx["date"]
            month = "Unknown"
            for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y"):
                try:
                    dt = datetime.datetime.strptime(date_str, fmt)
                    month = dt.strftime("%b %Y")
                    break
                except:
                    pass
            monthly_gst[month] = monthly_gst.get(month, 0.0) + tx["total_gst"]

        # Category chart values
        cat_gst = {}
        for tx in gst_ledger:
            cat = tx["category"]
            cat_gst[cat] = cat_gst.get(cat, 0.0) + tx["total_gst"]

        # Vendor analysis calculations
        vendor_data = {}
        for tx in gst_ledger:
            ven = tx["vendor"]
            if ven not in vendor_data:
                vendor_data[ven] = {
                    "count": 0, "total": 0.0, "gst": 0.0, "dates": []
                }
            vendor_data[ven]["count"] += 1
            vendor_data[ven]["total"] += tx["total_amount"]
            vendor_data[ven]["gst"] += tx["total_gst"]
            vendor_data[ven]["dates"].append(tx["date"])

        sorted_vendors = []
        for ven, metrics in vendor_data.items():
            latest_date = "N/A"
            parsed_dates = []
            for d in metrics["dates"]:
                for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y"):
                    try:
                        parsed_dates.append(datetime.datetime.strptime(d, fmt))
                        break
                    except:
                        pass
            if parsed_dates:
                latest_date = max(parsed_dates).strftime("%d-%b-%Y")
                
            sorted_vendors.append({
                "name": ven,
                "count": metrics["count"],
                "total": metrics["total"],
                "gst": metrics["gst"],
                "last_date": latest_date
            })
        sorted_vendors.sort(key=lambda x: x["gst"], reverse=True)

        # Build Month Chart HTML
        monthly_gst_html = ""
        max_monthly = max(monthly_gst.values()) if monthly_gst else 1.0
        for m, val in sorted(monthly_gst.items()):
            pct = (val / max_monthly * 100) if max_monthly > 0 else 0.0
            monthly_gst_html += f"""
            <tr>
                <td style="width: 25%;"><strong>{m}</strong></td>
                <td style="width: 60%;">
                    <div class="progress-bar-container">
                        <div class="progress-bar-fill" style="width: {pct}%; background-color: #2563EB;"></div>
                    </div>
                </td>
                <td style="width: 15%; text-align: right;">₹ {val:,.2f}</td>
            </tr>
            """

        # Build Category Chart HTML
        cat_gst_html = ""
        max_cat = max(cat_gst.values()) if cat_gst else 1.0
        for cat, val in sorted(cat_gst.items(), key=lambda x: x[1], reverse=True):
            if val == 0: continue
            pct = (val / max_cat * 100) if max_cat > 0 else 0.0
            cat_gst_html += f"""
            <tr>
                <td style="width: 25%;"><strong>{cat}</strong></td>
                <td style="width: 60%;">
                    <div class="progress-bar-container">
                        <div class="progress-bar-fill" style="width: {pct}%; background-color: #059669;"></div>
                    </div>
                </td>
                <td style="width: 15%; text-align: right;">₹ {val:,.2f}</td>
            </tr>
            """

        # Top Vendors HTML
        vendor_chart_html = ""
        max_vendor_gst = max(v["gst"] for v in sorted_vendors) if sorted_vendors else 1.0
        for v in sorted_vendors[:5]:
            if v["gst"] == 0: continue
            pct = (v["gst"] / max_vendor_gst * 100) if max_vendor_gst > 0 else 0.0
            vendor_chart_html += f"""
            <tr>
                <td style="width: 25%;"><strong>{v["name"]}</strong></td>
                <td style="width: 60%;">
                    <div class="progress-bar-container">
                        <div class="progress-bar-fill" style="width: {pct}%; background-color: #D97706;"></div>
                    </div>
                </td>
                <td style="width: 15%; text-align: right;">₹ {v["gst"]:,.2f}</td>
            </tr>
            """

        # Distribution percentages
        total_tax = cgst_total + sgst_total + igst_total
        cgst_pct = round((cgst_total / total_tax * 100), 1) if total_tax > 0 else 50.0
        sgst_pct = round((sgst_total / total_tax * 100), 1) if total_tax > 0 else 50.0
        igst_pct = round((igst_total / total_tax * 100), 1) if total_tax > 0 else 0.0

        # Expense Breakdown percentages
        total_exp = est_business_expenses + sum(tx["total_amount"] for tx in gst_ledger if not tx["is_business"])
        bus_pct = round((est_business_expenses / total_exp * 100), 1) if total_exp > 0 else 100.0
        pers_pct = round(100.0 - bus_pct, 1)

        # Build alerts HTML
        alerts_html = ""
        low_conf_txs = [tx for tx in gst_ledger if tx["confidence"] < 70]
        high_gst_txs = [tx for tx in gst_ledger if tx["total_gst"] > 5000]

        if duplicate_count > 0:
            alerts_html += f"""
            <div class="alert-box alert-warning">
                <strong>⚠ Possible Duplicate Transaction:</strong> Identified {duplicate_count} double-entry candidates occurring on identical dates and amounts. Verify before claiming credit.
            </div>
            """
        if missing_invoice_count > 0:
            alerts_html += f"""
            <div class="alert-box alert-warning">
                <strong>⚠ Missing GST Invoice:</strong> Flagged {missing_invoice_count} transactions that are eligible business expenses but lack explicit invoice numbers in their bank narrates.
            </div>
            """
        if len(low_conf_txs) > 0:
            alerts_html += f"""
            <div class="alert-box alert-warning">
                <strong>⚠ Low OCR / AI Confidence:</strong> Found {len(low_conf_txs)} transactions with low classification confidence. Manual category reviews recommended.
            </div>
            """
        if len(high_gst_txs) > 0:
            alerts_html += f"""
            <div class="alert-box alert-danger">
                <strong>⚠ High GST Amount:</strong> Found {len(high_gst_txs)} transactions with GST charges exceeding ₹5,000. Verify the supplier's GSTR-1 filings.
            </div>
            """
        if not alerts_html:
            alerts_html = """
            <div class="alert-box alert-success">
                <strong>✓ Reconciliation Status Clean:</strong> No critical anomalies or double-entry duplicates detected in this statement period.
            </div>
            """

        # Build vendor table rows HTML
        vendor_table_rows = ""
        for v in sorted_vendors[:10]:
            vendor_table_rows += f"""
            <tr>
                <td><strong>{v["name"]}</strong></td>
                <td style="text-align: center;">{v["count"]}</td>
                <td style="text-align: right;">₹ {v["total"]:,.2f}</td>
                <td style="text-align: right; color: #B45309; font-weight: bold;">₹ {v["gst"]:,.2f}</td>
                <td style="text-align: center;">{v["last_date"]}</td>
            </tr>
            """

        # Build Transaction Table rows
        tx_rows_html = ""
        for tx in gst_ledger:
            is_warning = tx["confidence"] < 70 or tx["is_duplicate"] or tx["is_missing_invoice"]
            row_style = 'style="background-color: #FEF3C7;"' if is_warning else ""
            itc_color = "#059669" if tx["itc_eligible"] == "Yes" else "#DC2626"
            
            tx_rows_html += f"""
            <tr {row_style}>
                <td style="text-align: center;">{tx["date"]}</td>
                <td>{tx["narration"]}</td>
                <td><span class="badge" style="background-color: #F1F5F9; color: #475569;">{tx["category"]}</span></td>
                <td>{tx["vendor"]}</td>
                <td style="text-align: right;">₹ {tx["total_amount"]:,.2f}</td>
                <td style="text-align: right;">₹ {tx["base_value"]:,.2f}</td>
                <td style="text-align: center;">{tx["gst_rate"]*100:.0f}%</td>
                <td style="text-align: right; color: #64748B;">₹ {tx["cgst"]:,.2f}</td>
                <td style="text-align: right; color: #64748B;">₹ {tx["sgst"]:,.2f}</td>
                <td style="text-align: right; color: #64748B;">₹ {tx["igst"]:,.2f}</td>
                <td style="text-align: right; font-weight: bold;">₹ {tx["total_gst"]:,.2f}</td>
                <td style="text-align: center; color: {itc_color}; font-weight: bold;">{tx["itc_eligible"]}</td>
                <td style="text-align: center;">
                    <div style="font-size: 11px; font-weight: bold; color: {'#16A34A' if tx['confidence'] >= 85 else '#D97706'};">
                        {tx["confidence"]:.0f}%
                    </div>
                </td>
                <td style="text-align: center;">
                    <span class="badge" style="background-color: {'#D1FAE5' if tx['status'] == 'Verified' else '#FFFBEB'}; color: {'#065F46' if tx['status'] == 'Verified' else '#B45309'}; border: 1px solid {'#A7F3D0' if tx['status'] == 'Verified' else '#FCD34D'};">
                        {tx["status"]}
                    </span>
                </td>
            </tr>
            """

        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        @page {{
            size: A4 landscape;
            margin: 10mm;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            color: #1E293B;
            background-color: #F8FAFC;
            margin: 0;
            padding: 15px;
            font-size: 12px;
            line-height: 1.4;
        }}
        .report-container {{
            max-width: 100%;
            margin: 0 auto;
            background-color: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 12px;
            padding: 24px;
        }}
        .report-header {{
            border-bottom: 2px solid #0037b0;
            padding-bottom: 12px;
            margin-bottom: 20px;
        }}
        .report-header-table {{
            width: 100%;
            border-collapse: collapse;
            border: none;
        }}
        .report-header-table td {{
            padding: 4px 8px;
            border: none;
            vertical-align: top;
        }}
        .report-title-block h1 {{
            font-family: Georgia, serif;
            font-size: 22px;
            font-weight: bold;
            color: #0F172A;
            margin: 0;
        }}
        .report-subtitle {{
            font-size: 10px;
            color: #D97706;
            margin-top: 4px;
            margin-bottom: 0;
            text-transform: uppercase;
            letter-spacing: 1px;
            font-weight: 700;
        }}
        .meta-label {{
            font-size: 10px;
            font-weight: bold;
            color: #64748B;
            text-transform: uppercase;
        }}
        .meta-val {{
            font-size: 12px;
            font-weight: bold;
            color: #1E293B;
        }}
        .section-title {{
            font-family: Georgia, serif;
            font-size: 15px;
            font-weight: bold;
            color: #0F172A;
            border-left: 4px solid #D97706;
            padding-left: 8px;
            margin-top: 24px;
            margin-bottom: 12px;
        }}
        
        .metric-table {{
            width: 100%;
            border-collapse: separate;
            border-spacing: 12px;
            margin-bottom: 16px;
        }}
        .metric-card {{
            background-color: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 8px;
            padding: 10px 12px;
            text-align: left;
            vertical-align: top;
            width: 25%;
        }}
        .card-blue {{ border-top: 3px solid #2563EB; background: #EFF6FF; }}
        .card-green {{ border-top: 3px solid #16A34A; background: #F0FDF4; }}
        .card-orange {{ border-top: 3px solid #D97706; background: #FFFBEB; }}
        .card-red {{ border-top: 3px solid #DC2626; background: #FEF2F2; }}
        .card-purple {{ border-top: 3px solid #8B5CF6; background: #F5F3FF; }}
        
        .card-label {{
            font-size: 9px;
            font-weight: bold;
            color: #64748B;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 3px;
        }}
        .card-value {{
            font-size: 18px;
            font-weight: bold;
            color: #0F172A;
        }}
        
        .alert-box {{
            padding: 10px 14px;
            border-radius: 6px;
            margin-bottom: 10px;
            font-size: 11px;
        }}
        .alert-warning {{
            background-color: #FFFBEB;
            border-left: 4px solid #D97706;
            color: #92400E;
        }}
        .alert-danger {{
            background-color: #FEF2F2;
            border-left: 4px solid #DC2626;
            color: #991B1B;
        }}
        .alert-success {{
            background-color: #ECFDF5;
            border-left: 4px solid #10B981;
            color: #065F46;
        }}

        .data-table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 16px;
            font-size: 11px;
        }}
        .data-table th {{
            background-color: #FFFBEB;
            color: #B45309;
            font-weight: 700;
            border: 1px solid #FDE68A;
            padding: 6px 8px;
            text-align: left;
        }}
        .data-table td {{
            padding: 6px 8px;
            border: 1px solid #E2E8F0;
            color: #334155;
            vertical-align: middle;
        }}
        .data-table tr:nth-child(even) {{
            background-color: #F9FAFB;
        }}
        .badge {{
            display: inline-block;
            padding: 2px 5px;
            font-size: 9px;
            font-weight: 700;
            border-radius: 4px;
            text-transform: uppercase;
        }}
        
        .progress-bar-container {{
            background-color: #E2E8F0;
            border-radius: 3px;
            height: 6px;
            width: 100%;
            overflow: hidden;
        }}
        .progress-bar-fill {{
            height: 100%;
            border-radius: 3px;
        }}
        
        .footer-disclaimer {{
            border-top: 1px dashed #CBD5E1;
            padding-top: 10px;
            margin-top: 24px;
            font-size: 9px;
            color: #64748B;
            text-align: justify;
            line-height: 1.4;
        }}
    </style>
</head>
<body>
    <div class="report-container">
        <!-- HEADER SECTION -->
        <div class="report-header">
            <table class="report-header-table">
                <tr>
                    <td style="width: 55%;" class="report-title-block">
                        <h1>AI-Generated GST Reconciliation & Analysis Report</h1>
                        <div class="report-subtitle">Estimated via AI transaction pattern audits • Not official filing documentation</div>
                    </td>
                    <td style="width: 45%;">
                        <table style="width: 100%; border: none;">
                            <tr>
                                <td class="meta-label">Account Holder:</td>
                                <td class="meta-val">{account_holder}</td>
                                <td class="meta-label">Generated On:</td>
                                <td class="meta-val">{gen_time}</td>
                            </tr>
                            <tr>
                                <td class="meta-label">Bank Name:</td>
                                <td class="meta-val">{bank_name}</td>
                                <td class="meta-label">Statement Period:</td>
                                <td class="meta-val">{period}</td>
                            </tr>
                            <tr>
                                <td class="meta-label">Account Number:</td>
                                <td class="meta-val">{account_number}</td>
                                <td class="meta-label">AI Engine Version:</td>
                                <td class="meta-val" style="font-size: 10px; color: #2563EB;">{ai_ver}</td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
        </div>

        <!-- EXECUTIVE SUMMARY DASHBOARD -->
        <div class="section-title">Executive Summary Dashboard</div>
        <table class="metric-table" style="margin-left: -12px; margin-right: -12px;">
            <tr>
                <td class="metric-card card-blue">
                    <div class="card-label">Total Scanned</div>
                    <div class="card-value">{total_scanned} txn</div>
                </td>
                <td class="metric-card card-green">
                    <div class="card-label">GST Applicable</div>
                    <div class="card-value">{gst_applicable_count} txn</div>
                </td>
                <td class="metric-card card-blue">
                    <div class="card-label">Estimated Expenses</div>
                    <div class="card-value">₹ {est_business_expenses:,.2f}</div>
                </td>
                <td class="metric-card card-orange">
                    <div class="card-label">Estimated GST Paid</div>
                    <div class="card-value">₹ {est_gst_paid:,.2f}</div>
                </td>
            </tr>
            <tr>
                <td class="metric-card card-orange">
                    <div class="card-label">CGST Total</div>
                    <div class="card-value">₹ {cgst_total:,.2f}</div>
                </td>
                <td class="metric-card card-orange">
                    <div class="card-label">SGST Total</div>
                    <div class="card-value">₹ {sgst_total:,.2f}</div>
                </td>
                <td class="metric-card card-orange">
                    <div class="card-label">IGST Total</div>
                    <div class="card-value">₹ {igst_total:,.2f}</div>
                </td>
                <td class="metric-card card-green">
                    <div class="card-label">Estimated ITC</div>
                    <div class="card-value">₹ {est_itc:,.2f}</div>
                </td>
            </tr>
            <tr>
                <td class="metric-card card-red">
                    <div class="card-label">Duplicates Flagged</div>
                    <div class="card-value">{duplicate_count} entries</div>
                </td>
                <td class="metric-card card-orange">
                    <div class="card-label">Missing Invoices</div>
                    <div class="card-value">{missing_invoice_count} candidates</div>
                </td>
                <td class="metric-card card-purple" colspan="2" style="width: 50%;">
                    <div class="card-label">AI Confidence Score</div>
                    <div class="card-value">{avg_confidence:.1f}%</div>
                </td>
            </tr>
        </table>

        <!-- RECONCILIATION ALERTS -->
        <div class="section-title">Intelligent Audit Alerts</div>
        {alerts_html}

        <!-- CHARTS & DISTRIBUTION -->
        <table style="width: 100%; border-collapse: collapse; margin-top: 15px; margin-bottom: 15px;">
            <tr>
                <td style="width: 48%; padding-right: 15px; vertical-align: top;">
                    <div class="section-title" style="margin-top: 0;">GST Distribution by Category</div>
                    <table style="width: 100%; font-size: 11px;">
                        {cat_gst_html}
                    </table>
                    
                    <div class="section-title" style="margin-top: 20px;">Top Vendors by GST Volume</div>
                    <table style="width: 100%; font-size: 11px;">
                        {vendor_chart_html}
                    </table>
                </td>
                <td style="width: 4%; border-right: 1px dashed #CBD5E1;"></td>
                <td style="width: 48%; padding-left: 20px; vertical-align: top;">
                    <div class="section-title" style="margin-top: 0;">CGST vs SGST vs IGST Share</div>
                    <table style="width: 100%; border-collapse: collapse; margin-bottom: 15px;">
                        <tr>
                            <td colspan="3" style="padding-bottom: 5px;">
                                <div style="background-color: #E2E8F0; border-radius: 4px; height: 20px; width: 100%; overflow: hidden; display: table; table-layout: fixed;">
                                    {"<div style='display: table-cell; background-color: #3B82F6; width: " + str(cgst_pct) + "%; text-align: center; color: white; font-size: 9px; font-weight: bold; vertical-align: middle;'>CGST (" + str(cgst_pct) + "%)</div>" if cgst_total > 0 else ""}
                                    {"<div style='display: table-cell; background-color: #10B981; width: " + str(sgst_pct) + "%; text-align: center; color: white; font-size: 9px; font-weight: bold; vertical-align: middle;'>SGST (" + str(sgst_pct) + "%)</div>" if sgst_total > 0 else ""}
                                    {"<div style='display: table-cell; background-color: #F59E0B; width: " + str(igst_pct) + "%; text-align: center; color: white; font-size: 9px; font-weight: bold; vertical-align: middle;'>IGST (" + str(igst_pct) + "%)</div>" if igst_total > 0 else ""}
                                </div>
                            </td>
                        </tr>
                        <tr>
                            <td style="font-size: 10px; color: #3B82F6; font-weight: bold;">CGST Paid: ₹ {cgst_total:,.2f}</td>
                            <td style="font-size: 10px; color: #10B981; font-weight: bold; text-align: center;">SGST Paid: ₹ {sgst_total:,.2f}</td>
                            <td style="font-size: 10px; color: #F59E0B; font-weight: bold; text-align: right;">IGST Paid: ₹ {igst_total:,.2f}</td>
                        </tr>
                    </table>

                    <div class="section-title" style="margin-top: 15px;">Business vs Personal Expense Split</div>
                    <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                        <tr>
                            <td colspan="2" style="padding-bottom: 5px;">
                                <div style="background-color: #E2E8F0; border-radius: 4px; height: 20px; width: 100%; overflow: hidden; display: table; table-layout: fixed;">
                                    {"<div style='display: table-cell; background-color: #1E3A8A; width: " + str(bus_pct) + "%; text-align: center; color: white; font-size: 9px; font-weight: bold; vertical-align: middle;'>Business (" + str(bus_pct) + "%)</div>" if est_business_expenses > 0 else ""}
                                    {"<div style='display: table-cell; background-color: #EC4899; width: " + str(pers_pct) + "%; text-align: center; color: white; font-size: 9px; font-weight: bold; vertical-align: middle;'>Personal (" + str(pers_pct) + "%)</div>" if (total_exp - est_business_expenses) > 0 else ""}
                                </div>
                            </td>
                        </tr>
                        <tr>
                            <td style="font-size: 10px; color: #1E3A8A; font-weight: bold;">Business: ₹ {est_business_expenses:,.2f}</td>
                            <td style="font-size: 10px; color: #EC4899; font-weight: bold; text-align: right;">Personal/Other: ₹ {(total_exp - est_business_expenses):,.2f}</td>
                        </tr>
                    </table>

                    <div class="section-title" style="margin-top: 15px;">GST Incurred by Month</div>
                    <table style="width: 100%; font-size: 11px;">
                        {monthly_gst_html}
                    </table>
                </td>
            </tr>
        </table>

        <!-- VENDOR ANALYSIS -->
        <div class="section-title">Vendor Summary Analysis</div>
        <table class="data-table">
            <thead>
                <tr>
                    <th style="width: 35%;">Vendor Name</th>
                    <th style="width: 15%; text-align: center;">Transactions</th>
                    <th style="width: 20%; text-align: right;">Total Amount Scanned</th>
                    <th style="width: 15%; text-align: right;">Estimated GST Paid</th>
                    <th style="width: 15%; text-align: center;">Last Transaction Date</th>
                </tr>
            </thead>
            <tbody>
                {vendor_table_rows}
            </tbody>
        </table>

        <!-- DETAILED TRANSACTION TABLE -->
        <div class="section-title">Detailed Tax Reconciliation Ledger</div>
        <table class="data-table">
            <thead>
                <tr>
                    <th style="width: 8%; text-align: center;">Date</th>
                    <th style="width: 20%;">Transaction Description / Narration</th>
                    <th style="width: 10%;">Category</th>
                    <th style="width: 12%;">Vendor</th>
                    <th style="width: 9%; text-align: right;">Total Amount</th>
                    <th style="width: 9%; text-align: right;">Taxable Value</th>
                    <th style="width: 5%; text-align: center;">Rate</th>
                    <th style="width: 7%; text-align: right;">CGST</th>
                    <th style="width: 7%; text-align: right;">SGST</th>
                    <th style="width: 7%; text-align: right;">IGST</th>
                    <th style="width: 9%; text-align: right;">Total GST</th>
                    <th style="width: 6%; text-align: center;">ITC Claim</th>
                    <th style="width: 5%; text-align: center;">AI Conf</th>
                    <th style="width: 7%; text-align: center;">Status</th>
                </tr>
            </thead>
            <tbody>
                {tx_rows_html}
            </tbody>
        </table>

        <!-- GST SUMMARY TOTALS -->
        <div class="section-title">GST Summary Totals</div>
        <table class="data-table" style="background-color: #FFFBEB; border: 2px solid #FDE68A;">
            <tbody>
                <tr>
                    <td><strong>Total Taxable Value:</strong></td>
                    <td style="text-align: right; font-weight: bold;">₹ {sum(tx["base_value"] for tx in gst_ledger):,.2f}</td>
                    <td><strong>Total CGST Paid:</strong></td>
                    <td style="text-align: right; font-weight: bold; color: #3B82F6;">₹ {cgst_total:,.2f}</td>
                </tr>
                <tr>
                    <td><strong>Total SGST Paid:</strong></td>
                    <td style="text-align: right; font-weight: bold; color: #10B981;">₹ {sgst_total:,.2f}</td>
                    <td><strong>Total IGST Paid:</strong></td>
                    <td style="text-align: right; font-weight: bold; color: #F59E0B;">₹ {igst_total:,.2f}</td>
                </tr>
                <tr>
                    <td><strong>Total GST Incurred:</strong></td>
                    <td style="text-align: right; font-weight: bold; font-size: 13px;">₹ {est_gst_paid:,.2f}</td>
                    <td><strong>Estimated ITC Claimable:</strong></td>
                    <td style="text-align: right; font-weight: bold; font-size: 13px; color: #16A34A;">₹ {est_itc:,.2f}</td>
                </tr>
                <tr>
                    <td><strong>Estimated Output GST:</strong></td>
                    <td style="text-align: right; font-weight: bold; color: #DC2626;">₹ {est_gst_collected:,.2f}</td>
                    <td><strong>Net Estimated GST Position:</strong></td>
                    <td style="text-align: right; font-weight: bold; font-size: 13px; color: {'#16A34A' if (est_itc - est_gst_collected) >= 0 else '#DC2626'};">
                        ₹ {abs(est_itc - est_gst_collected):,.2f} {( "Refund/Asset" if (est_itc - est_gst_collected) >= 0 else "Payable/Liability" )}
                    </td>
                </tr>
            </tbody>
        </table>

        <!-- REPORT FOOTER -->
        <div class="footer-disclaimer">
            <strong>Disclaimer:</strong> This report has been generated automatically by StatementForge using AI-assisted transaction analysis. GST values are estimated based on available bank statement data and transaction patterns. This report should not be used as an official GST filing document. Users should verify all GST values against tax invoices before statutory filing.
        </div>
    </div>
</body>
</html>
"""
        return html_content
