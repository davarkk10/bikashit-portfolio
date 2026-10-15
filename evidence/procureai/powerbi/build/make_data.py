"""Write the model-result CSVs (with date keys) into <pbip>/model_results."""
import os, shutil, sys
import pandas as pd
S, O = sys.argv[1], sys.argv[2]
os.makedirs(O, exist_ok=True)
key = lambda s: pd.to_datetime(s).dt.strftime('%Y%m%d').astype(int)
fi = pd.read_csv(f'{S}/fact_invoice.csv'); fi.insert(2, 'date_key', key(fi.invoice_date)); fi.to_csv(f'{O}/invoice_risk_scores.csv', index=False)
fp = pd.read_csv(f'{S}/fact_po.csv'); fp.insert(1, 'order_date_key', key(fp.order_date)); fp.to_csv(f'{O}/po_delay_scores.csv', index=False)
for a, b in [('model_results', 'model_results'), ('invoice_catch', 'invoice_condition_catch'), ('driver_importance', 'delay_drivers'),
             ('contract_qa', 'contract_qa'), ('expected_values', 'expected_values')]:
    ext = '.json' if a == 'expected_values' else '.csv'
    shutil.copy(f'{S}/{a}{ext}', f'{O}/{b}{ext}')
print(sorted(os.listdir(O)))
