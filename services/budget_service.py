import datetime
import json
import os
import uuid
from bson.objectid import ObjectId
from services.mongodb_service import MongoDBService
from services.gemini_service import GeminiService

BUDGET_FALLBACK_FILE = os.path.expanduser("~/.statementforge_budgets.json")

class BudgetService:
    """
    Service for managing Monthly Salary & Budget Planner data.
    Provides persistence via local JSON fallback and optional MongoDB Atlas collection,
    calculates metrics, checks planning window lock status, computes financial performance score,
    clones previous month budget values, and integrates with Gemini AI for monthly analysis.
    """
    _local_budgets = {}
    _loaded = False

    @classmethod
    def _load_local_fallback(cls):
        if cls._loaded:
            return
        cls._loaded = True
        if os.path.exists(BUDGET_FALLBACK_FILE):
            try:
                with open(BUDGET_FALLBACK_FILE, "r", encoding="utf-8") as f:
                    cls._local_budgets = json.load(f)
            except Exception as e:
                print(f"BudgetService: Error loading fallback budgets: {e}")
                cls._local_budgets = {}

    @classmethod
    def _save_local_fallback(cls):
        try:
            with open(BUDGET_FALLBACK_FILE, "w", encoding="utf-8") as f:
                json.dump(cls._local_budgets, f, indent=4)
        except Exception as e:
            print(f"BudgetService: Error saving fallback budgets: {e}")

    @classmethod
    def _get_default_budget_template(cls, month_key):
        """Generates clean default data template for a new month (user-entered data only)."""
        return {
            "month_key": month_key,
            "locked": False,
            "manual_unlocked": False,
            "last_edited": "",
            "income": {
                "salary": 0.0,
                "other": 0.0
            },
            "fixed_expenses": [],
            "family_payments": [],
            "savings": 0.0,
            "category_budgets": [
                {"category": "Food", "planned": 0.0},
                {"category": "Travel", "planned": 0.0},
                {"category": "Shopping", "planned": 0.0},
                {"category": "Entertainment", "planned": 0.0},
                {"category": "Medical", "planned": 0.0},
                {"category": "Personal", "planned": 0.0},
                {"category": "Other", "planned": 0.0}
            ],
            "actual_expenses": []
        }

    @classmethod
    def get_user_months(cls, user_id):
        """Returns sorted list of month_key strings registered for user_id."""
        if not user_id:
            user_id = "default_user"
        user_id_str = str(user_id)
        
        cls._load_local_fallback()
        months = set()
        
        col = MongoDBService.get_db()
        if col is not None:
            try:
                records = list(col["budgets"].find({"user_id": user_id_str}, {"month_key": 1}))
                for r in records:
                    if "month_key" in r and r["month_key"]:
                        months.add(r["month_key"])
            except Exception as e:
                print(f"BudgetService: MongoDB months fetch error: {e}")

        prefix = f"{user_id_str}_"
        for k in cls._local_budgets.keys():
            if k.startswith(prefix):
                m_key = k[len(prefix):]
                months.add(m_key)
                
        # Ensure current month is present
        curr = datetime.datetime.now().strftime("%Y-%m")
        months.add(curr)
        
        return sorted(list(months))

    @classmethod
    def get_user_budget(cls, user_id, month_key=None):
        """Fetches budget data for user_id and month_key (e.g. '2026-08' or 'August 2026')."""
        if not user_id:
            user_id = "default_user"
        user_id_str = str(user_id)
        
        if not month_key:
            month_key = datetime.datetime.now().strftime("%Y-%m")
            
        cls._load_local_fallback()
        
        col = MongoDBService.get_db()
        budget_col = col["budgets"] if col is not None else None
        
        doc = None
        if budget_col is not None:
            try:
                doc = budget_col.find_one({"user_id": user_id_str, "month_key": month_key})
                if doc and "_id" in doc:
                    doc["_id"] = str(doc["_id"])
            except Exception as e:
                print(f"BudgetService: MongoDB budget fetch failed: {e}")

        if not doc:
            user_key = f"{user_id_str}_{month_key}"
            doc = cls._local_budgets.get(user_key)

        if not doc:
            # Instantiate default template
            doc = cls._get_default_budget_template(month_key)
            doc["user_id"] = user_id_str
            cls.save_user_budget(user_id_str, month_key, doc)

        return cls.calculate_monthly_summary(doc)

    @classmethod
    def save_user_budget(cls, user_id, month_key, budget_data):
        """Saves budget data to database / local file."""
        if not user_id:
            user_id = "default_user"
        user_id_str = str(user_id)
        
        budget_data["user_id"] = user_id_str
        budget_data["month_key"] = month_key
        budget_data["last_edited"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cls._load_local_fallback()
        
        # Prepare clean doc for saving without non-serializable ObjectId
        clean_doc = json.loads(json.dumps(budget_data, default=str))

        # 1. MongoDB Save
        col = MongoDBService.get_db()
        if col is not None:
            try:
                budget_col = col["budgets"]
                mongo_doc = clean_doc.copy()
                mongo_doc.pop("_id", None)
                budget_col.update_one(
                    {"user_id": user_id_str, "month_key": month_key},
                    {"$set": mongo_doc},
                    upsert=True
                )
            except Exception as e:
                print(f"BudgetService: Failed to save MongoDB budget: {e}")

        # 2. Local Fallback Save
        user_key = f"{user_id_str}_{month_key}"
        cls._local_budgets[user_key] = clean_doc
        cls._save_local_fallback()
        return True

    @classmethod
    def add_actual_expense(cls, user_id, month_key, expense_item):
        """Adds an expense item to the month's actual expenses."""
        budget = cls.get_user_budget(user_id, month_key)
        expenses = budget.get("raw_data", {}).get("actual_expenses", [])
        
        if "id" not in expense_item or not expense_item["id"]:
            expense_item["id"] = f"exp_{uuid.uuid4().hex[:6]}"
            
        if "amount" in expense_item:
            expense_item["amount"] = float(expense_item["amount"])
            
        expenses.append(expense_item)
        
        raw = budget["raw_data"]
        raw["actual_expenses"] = expenses
        cls.save_user_budget(user_id, month_key, raw)
        return True

    @classmethod
    def delete_actual_expense(cls, user_id, month_key, expense_id):
        """Removes an expense item by ID."""
        budget = cls.get_user_budget(user_id, month_key)
        raw = budget["raw_data"]
        expenses = raw.get("actual_expenses", [])
        raw["actual_expenses"] = [e for e in expenses if str(e.get("id")) != str(expense_id)]
        cls.save_user_budget(user_id, month_key, raw)
        return True

    @classmethod
    def set_planning_lock(cls, user_id, month_key, manual_unlocked=False):
        """Toggles manual edit state for locked monthly budget."""
        budget = cls.get_user_budget(user_id, month_key)
        raw = budget["raw_data"]
        raw["manual_unlocked"] = manual_unlocked
        cls.save_user_budget(user_id, month_key, raw)
        return True

    @classmethod
    def calculate_monthly_summary(cls, budget_doc):
        """
        Calculates all totals, planned vs actual comparison, category balances, warnings,
        score performance out of 100, and lock window status.
        """
        doc = budget_doc.copy()
        
        # 1. Income totals
        inc = doc.get("income", {})
        salary = float(inc.get("salary", 0.0))
        other_inc = float(inc.get("other", 0.0))
        total_income = salary + other_inc

        # 2. Fixed Expenses
        fixed_items = doc.get("fixed_expenses", [])
        total_fixed = sum(float(item.get("amount", 0.0)) for item in fixed_items)

        # 3. Family Payments
        family_items = doc.get("family_payments", [])
        total_family = sum(float(item.get("amount", 0.0)) for item in family_items)

        # 4. Planned Savings
        planned_savings = float(doc.get("savings", 0.0))

        # 5. Category Budgets & Actual Expenses
        cat_budgets = doc.get("category_budgets", [])
        actual_expenses = doc.get("actual_expenses", [])

        # Accumulate actual spend per category
        category_actuals = {}
        for exp in actual_expenses:
            cat = exp.get("category", "Other")
            amt = float(exp.get("amount", 0.0))
            category_actuals[cat] = category_actuals.get(cat, 0.0) + amt

        comparison_list = []
        total_planned_category = 0.0
        total_actual_category = 0.0

        for cb in cat_budgets:
            cat_name = cb.get("category", "Other")
            planned_val = float(cb.get("planned", 0.0))
            actual_val = category_actuals.get(cat_name, 0.0)
            diff = planned_val - actual_val
            remaining_val = diff
            
            total_planned_category += planned_val
            total_actual_category += actual_val

            if actual_val > planned_val:
                over_by = actual_val - planned_val
                status = "over"
                result_str = f"🔴 ₹{over_by:,.0f} Over"
                warning_msg = f"🔴 {cat_name} budget exceeded by ₹{over_by:,.0f}."
            elif diff < (planned_val * 0.1) and diff > 0:
                status = "warning"
                result_str = f"⚠️ ₹{diff:,.0f} Remaining"
                warning_msg = f"⚠️ You have only ₹{diff:,.0f} left in your {cat_name} budget."
            else:
                status = "under"
                result_str = f"🟢 ₹{diff:,.0f} Under"
                warning_msg = f"🟢 You saved ₹{diff:,.0f} from your {cat_name} budget."

            comparison_list.append({
                "category": cat_name,
                "planned": planned_val,
                "actual": actual_val,
                "remaining": remaining_val,
                "status": status,
                "result": result_str,
                "warning": warning_msg
            })

        # 6. Overall Monthly Totals
        total_planned_expenses = total_fixed + total_family + total_planned_category
        total_actual_expenses = total_fixed + total_family + total_actual_category
        
        # Remaining Monthly Budget
        remaining_monthly_budget = total_income - (total_actual_expenses + planned_savings)
        
        # Net Spend Difference vs Planned
        net_diff = total_actual_expenses - total_planned_expenses
        if net_diff > 0:
            summary_alert = f"🔴 You spent ₹{net_diff:,.0f} more than your planned expenses."
        elif net_diff < 0:
            summary_alert = f"🟢 You saved ₹{abs(net_diff):,.0f} compared to your planned expenses!"
        else:
            summary_alert = f"🟢 Your actual spending matched your planned budget exactly."

        # 7. Performance Score Calculation (out of 100)
        score = 100
        good_points = []
        attention_points = []

        if total_fixed > 0:
            good_points.append("🟢 Fixed expenses were managed as planned")
        if planned_savings > 0:
            good_points.append(f"🟢 Saved target of ₹{planned_savings:,.0f}")

        for comp in comparison_list:
            cat = comp["category"]
            if comp["status"] == "over":
                over_amt = comp["actual"] - comp["planned"]
                score -= min(15, int((over_amt / max(comp["planned"], 1)) * 20))
                attention_points.append(f"🔴 {cat} was over budget by ₹{over_amt:,.0f}")
            elif comp["status"] == "warning":
                score -= 3
                attention_points.append(f"⚠️ {cat} is close to exceeding its budget")
            else:
                saved = comp["planned"] - comp["actual"]
                good_points.append(f"🟢 {cat} spending was ₹{saved:,.0f} under budget")

        score = max(10, min(100, score))

        # 8. Check Planning Period Lock (1st - 7th of month)
        today = datetime.datetime.now()
        day_of_month = today.day
        is_planning_period = (1 <= day_of_month <= 7)
        manual_unlocked = doc.get("manual_unlocked", False)
        is_locked = (not is_planning_period) and (not manual_unlocked)

        return {
            "month_key": doc.get("month_key", ""),
            "user_id": doc.get("user_id", ""),
            "last_edited": doc.get("last_edited", ""),
            "is_planning_period": is_planning_period,
            "is_locked": is_locked,
            "manual_unlocked": manual_unlocked,
            "total_income": total_income,
            "total_fixed": total_fixed,
            "total_family": total_family,
            "planned_savings": planned_savings,
            "total_planned_category": total_planned_category,
            "total_planned_expenses": total_planned_expenses,
            "total_actual_expenses": total_actual_expenses,
            "remaining_monthly_budget": remaining_monthly_budget,
            "summary_alert": summary_alert,
            "performance_score": score,
            "good_points": good_points,
            "attention_points": attention_points,
            "comparison": comparison_list,
            "income": inc,
            "fixed_expenses": fixed_items,
            "family_payments": family_items,
            "category_budgets": cat_budgets,
            "actual_expenses": actual_expenses,
            "raw_data": doc
        }

    @classmethod
    def copy_to_next_month(cls, user_id, source_month_key, target_month_key, source_type="planned"):
        """Clones source month's planned or actual values into target_month_key."""
        source_summary = cls.get_user_budget(user_id, source_month_key)
        raw = source_summary["raw_data"]
        
        new_doc = {
            "month_key": target_month_key,
            "user_id": str(user_id),
            "locked": False,
            "manual_unlocked": False,
            "income": raw.get("income", {}).copy(),
            "fixed_expenses": raw.get("fixed_expenses", []).copy(),
            "family_payments": raw.get("family_payments", []).copy(),
            "savings": raw.get("savings", 0.0),
            "actual_expenses": []  # reset actual expenses for the new month
        }
        
        if source_type == "actual":
            # Set category budgets based on previous month's actual spending
            category_actuals = {}
            for exp in raw.get("actual_expenses", []):
                cat = exp.get("category", "Other")
                amt = float(exp.get("amount", 0.0))
                category_actuals[cat] = category_actuals.get(cat, 0.0) + amt

            cat_budgets = []
            for cb in raw.get("category_budgets", []):
                cat = cb.get("category", "Other")
                cat_budgets.append({
                    "category": cat,
                    "planned": category_actuals.get(cat, cb.get("planned", 0.0))
                })
            new_doc["category_budgets"] = cat_budgets
        else:
            new_doc["category_budgets"] = raw.get("category_budgets", []).copy()

        cls.save_user_budget(user_id, target_month_key, new_doc)
        return True

    @classmethod
    def generate_ai_summary(cls, user_id, month_key):
        """Uses GeminiService to analyze the monthly results and generate personalized financial insights."""
        summary = cls.get_user_budget(user_id, month_key)
        
        prompt = f"""
You are an expert personal financial advisor in StatementForge.
Analyze the following Monthly Salary & Budget Planner data for {month_key}:

Income & Spending Overview:
- Total Income: ₹{summary['total_income']:,.0f}
- Planned Expenses: ₹{summary['total_planned_expenses']:,.0f}
- Actual Expenses: ₹{summary['total_actual_expenses']:,.0f}
- Planned Savings: ₹{summary['planned_savings']:,.0f}
- Remaining Budget: ₹{summary['remaining_monthly_budget']:,.0f}
- Budget Performance Score: {summary['performance_score']}/100

Category Breakdown (Planned vs Actual):
"""
        for item in summary["comparison"]:
            prompt += f"- {item['category']}: Planned ₹{item['planned']:,.0f} | Actual ₹{item['actual']:,.0f} | Result: {item['result']}\n"

        prompt += """
Please provide a clear, professional, user-friendly AI Monthly Summary containing:
1. An executive 2-sentence breakdown of overall financial performance.
2. Specific highlights of which categories caused budget variance (over-budget vs savings).
3. 3 practical, actionable tips for next month to improve savings and control overspending.

Keep the response concise, encouraging, and cleanly formatted using HTML paragraphs (`<p>`), bullet points (`<ul><li>`), and bold text (`<strong>`). Do not include Markdown backticks or `<html>` root tags.
"""
        try:
            analysis = GeminiService._call_gemini(prompt, system_instruction="You are an encouraging expert personal financial consultant.")
            return analysis
        except Exception as e:
            print(f"BudgetService: AI Summary API call failed ({e}). Returning fallback AI insight.")
            
            # Local fallback AI insight
            over_items = [c for c in summary["comparison"] if c["status"] == "over"]
            under_items = [c for c in summary["comparison"] if c["status"] == "under"]
            
            over_desc = ", ".join([f"<strong>{c['category']}</strong> (exceeded by ₹{(c['actual']-c['planned']):,.0f})" for c in over_items]) if over_items else "None"
            under_desc = ", ".join([f"<strong>{c['category']}</strong>" for c in under_items]) if under_items else "None"

            return f"""
<div class="ai-summary-content">
    <p><strong>AI Executive Insight for {month_key}:</strong></p>
    <p>Your total spending was <strong>₹{summary['total_actual_expenses']:,.0f}</strong> against planned expenses of <strong>₹{summary['total_planned_expenses']:,.0f}</strong>. Your monthly performance score is <strong>{summary['performance_score']}/100</strong>.</p>
    
    <p><strong>Key Drivers:</strong></p>
    <ul>
        <li>Over-budget categories needing attention: {over_desc}.</li>
        <li>Categories successfully kept under budget: {under_desc}.</li>
    </ul>

    <p><strong>Actionable Tips for Next Month:</strong></p>
    <ul>
        <li>Set up weekly spending alerts for high-variance categories like Shopping and Travel.</li>
        <li>Automate your Planned Savings transfer (₹{summary['planned_savings']:,.0f}) on payday (1st of the month).</li>
        <li>Use the Next Month Budget feature to adjust category limits based on your actual spending patterns.</li>
    </ul>
</div>
"""
