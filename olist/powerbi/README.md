# Olist Delivery 360 — Power BI build files

Live report: https://app.powerbi.com/view?r=eyJrIjoiYzdmMWViOTgtN2Q2Mi00M2YxLTgzN2EtNWJiMzdiMGQ4ZjM2IiwidCI6ImM2ZTU0OWIzLTVmNDUtNDAzMi1hYWU5LWQ0MjQ0ZGM1YjJjNCJ9

| File | Use |
|---|---|
| `../sql/06_powerbi_views.sql` / `../mysql/06_powerbi_views.sql` | The 4 views Power BI imports (`pbi_delivery`, `pbi_order_seller`, `pbi_seller`, `pbi_first_order`) |
| `powerquery_mysql.m`, `powerquery_csv.m` | Power Query code for a MySQL source or CSV exports |
| `measures.dax` | Calculated tables, columns and all measures, with expected values |
| `Olist_Delivery_360_theme.json` | Report theme (View > Themes > Browse for themes) |
| `wireframes/*.png` | Page layouts on a 1920 × 1080 canvas, with positions |

Expected values (all years): 96,470 delivered orders · 6.77% late · avg review 2.27 late vs 4.29 on time ·
72.3% of late orders left the seller on time · SP → RJ = 17.7% of late orders. With Year = 2018 and BM = vs LY:
late 7.7% vs 3.5%, avg review 4.14 vs 4.23, bad reviews 13.4% vs 10.6%, avg days 12.1 vs 12.2.
