PROCUREAI FMCG - MODEL RESULTS (Power BI Project)
==================================================

1. Unzip so this folder is  C:\ProcureAI\   with the CSVs in  C:\ProcureAI\data\
2. Double-click  ProcureAI_Model_Results.pbip  (latest Power BI Desktop; File > Options > Preview features >
   "Power BI Project (.pbip) save option" and "Store reports using enhanced metadata format (PBIR)" switched on).
   The report opens with empty visuals: a project stores no data.
3. Home > Refresh. Loading takes under a minute.
   Data somewhere else? Home > Transform data > Edit parameters > DataFolder (full path ending with \) > OK > Apply changes.
4. Optional: File > Save as > ProcureAI_Model_Results.pbix for a single file, then publish.
   No PBIP support? Open ProcureAI_Model_Results.pbit instead (same model and pages); it asks for DataFolder.

Check after refresh (data\expected_values.json has the full list):
  Invoice risk:  model 92.6% of 1,546 flagged are real; best rules 74.6% of 1,707
  Late delivery: 66.8% of flagged POs (3 days before) arrive late; test late rate 36.9%
  Contract:      64 / 68, 0 wrong answers, 6 / 6 refusals

Pages: Home, Invoice risk, Late delivery, Contract assistant, About.
All data is synthetic. Rebuild everything with the scripts in evidence/procureai (see build/README.md).
