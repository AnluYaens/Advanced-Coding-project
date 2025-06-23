import pandas as pd
from src.core.database import insert_payment_safe

def load_bank_statement_csv(file_path):
    """
    Load bank statement data from CSV file and insert each expense.
    
    Returns:
        dict: {"imported": int, "failed": int, "errors": list}
    """
    
    result = {"imported": 0, "failed": 0, "errors": []}
    imported_expenses = []

    try:
        # Read CSV with error handling
        try:
            df = pd.read_csv(file_path, encoding='utf-8')
        except UnicodeDecodeError:
            # Try latin-1 if UTF-8 fails
            df = pd.read_csv(file_path, encoding='latin-1')
        
        # --- validate required columns ---
        df.columns = df.columns.str.strip() # Removes spaces

        # Map common column names
        column_mappings = {
            'amount': ['Amount', 'Monto', 'Value', 'Valor'],
            'category': ['Category', 'Categoría', 'Type', 'Tipo'],
            'description': ['Description', 'Descripción', 'Detail', 'Detalle'],
            'date': ['Date', 'Fecha', 'Transaction Date', 'Fecha Transacción']
        }
        
        # Find the correct columns
        found_columns =  {}
        for key, possible_names in column_mappings.items():
            for col in df.columns:
                if col in possible_names or col.lower() in [n.lower() for n in possible_names]:
                    found_columns[key] = col
                    break
        
        # Verify we have all necessary columns
        missing = [k for k in ['amount', 'category', 'description', 'date'] if k not in found_columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")
        
        # Process each row
        for idx, row in df.iterrows():
            try:
                # Extract and clean data
                amount_str = str(row[found_columns['amount']]).strip()
                # Handle different number formats (1,234.56 or 1.234,56)
                amount_str = amount_str.replace('$', '').replace('€', '').strip()
                if ',' in amount_str and '.' in amount_str:
                    # Determine which is the decimal separator
                    if amount_str.rindex(',') > amount_str.rindex(','):
                        # European format: 1.234,56
                        amount_str = amount_str.replace('.', '').replace(',', '.')
                    else:
                        # American format: 1,234.56
                        amount_str = amount_str.replace(',', '')
                else:
                    # Only commas or dots
                    amount_str = amount_str.replace(',', '.')

                amount = float(amount_str)

                # --- Validate amount ---
                if amount <= 0:
                    result['failed'] += 1
                    result['errors'].append(f"Row {idx+1}: Invalid amount {amount}")
                    continue

                category = str(row[found_columns['category']]).strip()
                if not category or category.lower() == 'nan':
                    category = "Other"

                description = str(row[found_columns['description']]).strip()
                if description.lower() == "nan":
                    description = ""

                date_str = str(row[found_columns['date']]).strip()

                # Use safe version that handles multiple date formats
                inserted = insert_payment_safe(amount, category, description,date_str)
                imported_expenses.append(inserted)

                

                result["imported"] += 1

            except Exception as e:
                result["failed"] += 1
                result["errors"].append(f"Row {idx+1}: {str(e)}")
        
        print(f"[IMPORT PDF] Completed: {result['imported']} imported, {result['failed']} failed")

        result["expenses"] = imported_expenses
        return result

    except Exception as e:
        result["errors"].append(f"Failed to read CSV file: {str(e)}")
        
        return result