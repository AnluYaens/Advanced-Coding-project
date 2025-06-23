import pdfplumber
import re
from src.core.database import insert_payment_safe

def load_bank_statement_pdf(file_path):
    """
    Load bank statement data from a PDF file.
    Supports both structured tables and plain text formats.

    Args:
        file_path (str): Path to the PDF file.
        insert_payment_func (callable): Function to insert each payment into the database.

    Returns:
        dict: Summary of the import process: {"imported": int, "failed": int, "errors": list}
    """
    result = {"imported": 0, "failed": 0, "errors": []}
    imported_expenses = []
    
    try:
        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                table = page.extract_table()

                if table and len(table) >= 2:
                    # --- Structured table mode ---
                    headers = [str(h).strip().lower() for h in table[0]]
                    rows = table[1:]

                    column_mappings = {
                        'date': ['date', 'transaction date'],
                        'description': ['description', 'details'],
                        'category': ['category', 'type'],
                        'amount': ['amount', 'value', 'debit', 'credit']
                    }

                    col_index = {}
                    for key, possible_names in column_mappings.items():
                        for i, header in enumerate(headers):
                            if header in possible_names:
                                col_index[key] = i
                                break

                    if 'amount' not in col_index or 'date' not in col_index:
                        result["errors"].append(f"Page {page_num}: Missing required columns")
                        continue

                    for row_num, row in enumerate(rows, 1):
                        try:
                            amount_str = str(row[col_index['amount']]).replace('$', '').replace('€', '').replace(',', '').strip()
                            amount = float(amount_str)
                            if amount <= 0:
                                continue

                            date_str = str(row[col_index['date']]).strip()
                            category = row[col_index.get('category', '')] or "Other"
                            description = row[col_index.get('description', '')] or ""

                            inserted = insert_payment_safe(amount, category, description, date_str)
                            imported_expenses.append(inserted)
                            result["imported"] += 1
                        except Exception as e:
                            result["failed"] += 1
                            result["errors"].append(f"Page {page_num} Row {row_num}: {e}")
                else:
                    # --- Fallback plain text mode ---
                    lines = page.extract_text().split('\n')
                    pattern = r"(\d{4}-\d{2}-\d{2})\s+(.+?)\s+\$([\d\.]+)"

                    for line_num, line in enumerate(lines, 1):
                        match = re.search(pattern, line)
                        if not match:
                            continue

                        try:
                            date_str = match.group(1)
                            description = match.group(2).strip()
                            amount = float(match.group(3))
                            if amount <= 0:
                                continue

                            desc_lower = description.lower()
                            if "grocery" in desc_lower or "aldi" in desc_lower or "lidl" in desc_lower:
                                category = "Groceries"
                            elif "entertainment" in desc_lower or "cinema" in desc_lower or "netflix" in desc_lower:
                                category = "Entertainment"
                            elif "amazon" in desc_lower or "electronics" in desc_lower:
                                category = "Electronics"
                            else:
                                category = "Other"
                            
                            inserted = insert_payment_safe(amount, category, description, date_str)
                            imported_expenses.append(inserted)
                            result["imported"] += 1
                        except Exception as e:
                            result["failed"] += 1
                            result["errors"].append(f"Line {line_num}: {e}")

        print(f"[IMPORT PDF] Completed: {result['imported']} imported, {result['failed']} failed")

    except Exception as e:
        error = f"Failed to read PDF: {e}"
        result["errors"].append(error)
        print(f"[IMPORT PDF ERROR] {error}")

    result["expenses"] = imported_expenses
    return result