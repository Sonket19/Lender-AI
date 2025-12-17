# import pandas as pd
# import numpy as np

# # ==========================================
# # 1. INPUT DATA & ASSUMPTIONS
# # ==========================================

# # The Years (Columns)
# years = ['FY24 (Audited)', 'FY25 (Estimated)', 'FY26 (Projected)', 'FY27 (Projected)']

# # --- A. OPERATING INPUTS ---
# # Revenue and Expenses as per your provided file
# revenue = [250, 950, 2100, 4500]
# cogs    = [55, 199.5, 399, 765]
# opex    = [177.5, 542.5, 1110, 2100]
# depreciation = [20, 35, 50, 65]

# # --- B. DEBT & INTEREST INPUTS (CORRECTED) ---
# # CRITICAL FIX: Term Loan reduced to 50L (from 200L) to match Capex.
# term_loan_bal = [0, 50, 50, 50]  
# term_interest_rate = 0.125 # Assumed 12.5%
# wc_interest_actuals = [5, 15, 25, 35]

# # --- C. EQUITY & LIABILITIES INPUTS (CORRECTED) ---
# # CRITICAL FIX: Equity Infusion of $1.2M (~1000L) in FY25
# share_capital = [100, 110, 110, 110]         # +10L Face Value
# share_premium = [0, 990, 0, 0]               # +990L Premium
# opening_reserves_fy24 = -89.17808219         # Hardcoded from Audit

# # Working Capital Liabilities
# st_borrowings = [100, 150, 200, 250]
# trade_payables = [20, 30, 40, 50]
# other_cur_liab = [10, 10, 10, 10]

# # --- D. ASSET INPUTS ---
# # Net Block calculated: Gross - Acc Dep
# net_block = [80, 95, 95, 80]
# trade_receivables = [30.82191781, 117.1232877, 230.1369863, 369.8630137]
# other_cur_assets = [10, 15, 20, 25]

# # ==========================================
# # 2. CALCULATION ENGINE
# # ==========================================

# # Lists to store computed rows
# pl_data = []
# bs_data = []
# ratio_data = []
# cf_final_cols = []

# # State variables for rolling forward
# prev_reserves = opening_reserves_fy24
# reserves_history = []
# cash_history = []
# pat_history = []

# # --- LOOP 1: P&L and Balance Sheet ---
# for i, year in enumerate(years):
#     # --------------------------------------
#     # TAB 1: OPERATING STATEMENT (P&L)
#     # --------------------------------------
#     rev = revenue[i]
#     exp_dir = cogs[i]
#     exp_op = opex[i]
#     ebitda = rev - exp_dir - exp_op
#     dep = depreciation[i]
   
#     # Finance Cost
#     if i == 0:
#         int_term = 0 # FY24 Actual
#     else:
#         int_term = term_loan_bal[i] * term_interest_rate
       
#     int_wc = wc_interest_actuals[i]
#     total_fin = int_term + int_wc
   
#     pbt = ebitda - dep - total_fin
   
#     # Tax (25% rate)
#     if i == 0:
#         tax = 0
#     else:
#         tax = pbt * 0.25 if pbt > 0 else 0
       
#     pat = pbt - tax
#     pat_history.append(pat)
   
#     cash_profit = pat + dep
   
#     pl_row = [rev, exp_dir, exp_op, ebitda, dep, total_fin, pbt, tax, pat, cash_profit]
#     pl_data.append(pl_row)

#     # --------------------------------------
#     # TAB 2: BALANCE SHEET
#     # --------------------------------------
#     # Reserves Roll Forward (The Fix for "Data Integrity")
#     if i == 0:
#         curr_reserves = opening_reserves_fy24
#     else:
#         curr_reserves = prev_reserves + pat + share_premium[i]
   
#     prev_reserves = curr_reserves
#     reserves_history.append(curr_reserves)
   
#     sh_cap = share_capital[i]
#     net_worth = sh_cap + curr_reserves
   
#     lt_debt = term_loan_bal[i]
#     st_debt = st_borrowings[i]
#     creditors = trade_payables[i]
#     ocl = other_cur_liab[i]
   
#     total_liabilities = net_worth + lt_debt + st_debt + creditors + ocl
   
#     # Assets
#     nb = net_block[i]
#     debtors = trade_receivables[i]
#     oca = other_cur_assets[i]
   
#     # THE PLUG: Cash Calculation (The Fix for "Asset-Liability Mismatch")
#     non_cash_assets = nb + debtors + oca
#     cash_bal = total_liabilities - non_cash_assets
#     cash_history.append(cash_bal)
   
#     bs_row = [sh_cap, curr_reserves, net_worth, lt_debt, st_debt, creditors, ocl, total_liabilities,
#               nb, debtors, cash_bal, oca, total_liabilities]
#     bs_data.append(bs_row)

#     # --------------------------------------
#     # TAB 3: RATIO ANALYSIS
#     # --------------------------------------
#     # Current Ratio: CA / CL
#     ca = debtors + cash_bal + oca
#     cl = st_debt + creditors + ocl
#     curr_ratio = ca / cl if cl != 0 else 0
   
#     # Debt Equity Ratio: Total Debt / Net Worth
#     total_debt = lt_debt + st_debt
#     de_ratio = total_debt / net_worth if net_worth != 0 else 0
   
#     # DSCR
#     dscr_num = pat + dep + total_fin
#     dscr_den = total_fin
#     dscr = dscr_num / dscr_den if dscr_den != 0 else 0
   
#     # Runway (Months)
#     total_cash_out_monthly = (exp_dir + exp_op + total_fin + tax) / 12
#     runway = cash_bal / total_cash_out_monthly if total_cash_out_monthly > 0 else 999
   
#     # Net Profit Margin
#     npm = (pat / rev * 100) if rev != 0 else 0

#     ratio_row = [curr_ratio, de_ratio, dscr, npm, runway]
#     ratio_data.append(ratio_row)

# # --- LOOP 2: Cash Flow Statement (Indirect Method) ---
# cf_labels = ['Opening Cash', 'Net Profit Before Tax', 'Add: Depreciation', 'Add: Interest',
#              'Op Profit before WC', 'Inc/Dec in Trade Payables', 'Inc/Dec in Other Liab',
#              'Inc/Dec in Receivables', 'Inc/Dec in Other Assets', 'Tax Paid',
#              'Net Cash from Operating',
#              'Purchase of Fixed Assets (Capex)', 'Net Cash from Investing',
#              'Inc/Dec Share Capital', 'Inc/Dec Share Premium', 'Inc/Dec Long Term Debt',
#              'Inc/Dec Short Term Debt', 'Interest Paid', 'Net Cash from Financing',
#              'Net Change in Cash', 'Closing Cash']

# for i, year in enumerate(years):
#     if i == 0:
#         # FY24 Base Year - Just fill closing cash
#         col = [0]*20 + [cash_history[0]]
#         cf_final_cols.append(col)
#         continue

#     # Deltas
#     delta_payables = trade_payables[i] - trade_payables[i-1]
#     delta_ocl = other_cur_liab[i] - other_cur_liab[i-1]
#     delta_debtors = trade_receivables[i] - trade_receivables[i-1]
#     delta_oca = other_cur_assets[i] - other_cur_assets[i-1]
   
#     pbt = pl_data[i][6]
#     dep = pl_data[i][4]
#     interest = pl_data[i][5]
#     tax_paid = pl_data[i][7]
   
#     op_profit_pre_wc = pbt + interest + dep
   
#     # Cash Flow Logic: Asset Inc = Outflow (-), Liab Inc = Inflow (+)
#     cf_wc = delta_payables + delta_ocl - delta_debtors - delta_oca
#     net_cf_op = pbt + dep + interest + cf_wc - tax_paid
   
#     # Investing
#     capex = (net_block[i] - net_block[i-1]) + dep
#     net_cf_inv = -capex
   
#     # Financing
#     delta_equity = share_capital[i] - share_capital[i-1]
#     delta_premium = share_premium[i]
#     delta_ltd = term_loan_bal[i] - term_loan_bal[i-1]
#     delta_std = st_borrowings[i] - st_borrowings[i-1]
   
#     net_cf_fin = delta_equity + delta_premium + delta_ltd + delta_std - interest
   
#     net_change = net_cf_op + net_cf_inv + net_cf_fin
   
#     col = [cash_history[i-1], pbt, dep, interest,
#            op_profit_pre_wc, delta_payables, delta_ocl, -delta_debtors, -delta_oca, -tax_paid,
#            net_cf_op,
#            -capex, net_cf_inv,
#            delta_equity, delta_premium, delta_ltd, delta_std, -interest, net_cf_fin,
#            net_change, cash_history[i]]
#     cf_final_cols.append(col)

# # ==========================================
# # 3. DATAFRAME CONSTRUCTION & EXPORT
# # ==========================================

# # 1. P&L DF
# df_pl = pd.DataFrame(pl_data, columns=['Revenue', 'Cost of Sales', 'Opex', 'EBITDA',
#                                        'Depreciation', 'Finance Cost', 'PBT', 'Tax', 'PAT', 'Cash Profit'],
#                      index=years).T

# # 2. BS DF
# df_bs = pd.DataFrame(bs_data, columns=['Share Capital', 'Reserves', 'Net Worth',
#                                        'Long Term Debt', 'Short Term Debt', 'Payables', 'Other Cur Liab', 'Total Liab',
#                                        'Net Block', 'Receivables', 'Cash & Bank', 'Other Cur Assets', 'Total Assets'],
#                      index=years).T

# # 3. Ratios DF
# df_ratios = pd.DataFrame(ratio_data, columns=['Current Ratio', 'Debt/Equity', 'DSCR', 'Net Profit Margin %', 'Runway (Months)'],
#                          index=years).T

# # 4. CF DF (Transpose needed to make Years as Columns)
# df_cf = pd.DataFrame(cf_final_cols, index=years, columns=cf_labels).T

# # WRITE TO EXCEL
# file_name = 'Corrected_Complete_CMA.xlsx'
# try:
#     with pd.ExcelWriter(file_name, engine='openpyxl') as writer:
#         df_pl.to_excel(writer, sheet_name='Operating Statement')
#         df_bs.to_excel(writer, sheet_name='Balance Sheet')
#         df_cf.to_excel(writer, sheet_name='Cash Flow Statement')
#         df_ratios.to_excel(writer, sheet_name='Ratio Analysis')
#     print(f"SUCCESS. File '{file_name}' has been created with corrected accounting logic.")
# except Exception as e:
#     print(f"Error writing file: {e}")


import pandas as pd
import numpy as np

# ==========================================
# 1. INPUT DATA & ASSUMPTIONS
# ==========================================

years = ['FY24 (Audited)', 'FY25 (Estimated)', 'FY26 (Projected)', 'FY27 (Projected)']

# --- A. OPERATING INPUTS ---
revenue = [250, 950, 2100, 4500]
cogs    = [55, 199.5, 399, 765]
opex    = [177.5, 542.5, 1110, 2100]
depreciation = [20, 35, 50, 65]

# --- B. DEBT & INTEREST INPUTS (CORRECTED) ---
# FIX 1: Defined Principal Repayment Schedule
# Assumption: 50L Loan taken in FY25. Repayment starts FY26 (10L/year).
term_loan_bal = [0, 50, 40, 30] 
principal_repayment = [0, 0, 10, 10] 

term_interest_rate = 0.125 
wc_interest_actuals = [5, 15, 25, 35]

# --- C. EQUITY & LIABILITIES INPUTS ---
share_capital = [100, 110, 110, 110]         
share_premium = [0, 990, 0, 0]               
opening_reserves_fy24 = -89.17808219         

st_borrowings = [100, 150, 200, 250]
trade_payables = [20, 30, 40, 50]
other_cur_liab = [10, 10, 10, 10]

# --- D. ASSET INPUTS ---
net_block = [80, 95, 95, 80]
trade_receivables = [30.82, 117.12, 230.14, 369.86] # Rounded for cleanliness
other_cur_assets = [10, 15, 20, 25]

# ==========================================
# 2. CALCULATION ENGINE
# ==========================================

pl_data = []
bs_data = []
ratio_data = []
cf_final_cols = []

prev_reserves = opening_reserves_fy24
reserves_history = []
cash_history = []
pat_history = []

for i, year in enumerate(years):
    # --------------------------------------
    # TAB 1: P&L
    # --------------------------------------
    rev = revenue[i]
    exp_dir = cogs[i]
    exp_op = opex[i]
    ebitda = rev - exp_dir - exp_op
    dep = depreciation[i]
    
    # FIX 2: Average Balance Interest Calculation
    if i == 0:
        int_term = 0 
    else:
        # Interest on Average Balance of the year
        avg_bal = (term_loan_bal[i] + term_loan_bal[i-1]) / 2
        int_term = avg_bal * term_interest_rate
        
    int_wc = wc_interest_actuals[i]
    total_fin = int_term + int_wc
    
    pbt = ebitda - dep - total_fin
    
    # Tax (25% rate only if profit positive)
    tax = pbt * 0.25 if pbt > 0 else 0
        
    pat = pbt - tax
    pat_history.append(pat)
    cash_profit = pat + dep
    
    pl_row = [rev, exp_dir, exp_op, ebitda, dep, total_fin, pbt, tax, pat, cash_profit]
    pl_data.append(pl_row)

    # --------------------------------------
    # TAB 2: BALANCE SHEET
    # --------------------------------------
    if i == 0:
        curr_reserves = opening_reserves_fy24
    else:
        curr_reserves = prev_reserves + pat + share_premium[i]
    
    prev_reserves = curr_reserves
    reserves_history.append(curr_reserves)
    
    sh_cap = share_capital[i]
    net_worth = sh_cap + curr_reserves
    
    lt_debt = term_loan_bal[i]
    st_debt = st_borrowings[i]
    creditors = trade_payables[i]
    ocl = other_cur_liab[i]
    
    total_liabilities = net_worth + lt_debt + st_debt + creditors + ocl
    
    nb = net_block[i]
    debtors = trade_receivables[i]
    oca = other_cur_assets[i]
    
    # FIX 3: Negative Cash Check
    non_cash_assets = nb + debtors + oca
    cash_bal = total_liabilities - non_cash_assets
    
    if cash_bal < 0:
        print(f"⚠️  WARNING: Negative Cash ({round(cash_bal,2)}) detected in {year}. Increase Overdraft/Equity input.")
    
    cash_history.append(cash_bal)
    
    bs_row = [sh_cap, curr_reserves, net_worth, lt_debt, st_debt, creditors, ocl, total_liabilities,
              nb, debtors, cash_bal, oca, total_liabilities]
    bs_data.append(bs_row)

    # --------------------------------------
    # TAB 3: RATIO ANALYSIS
    # --------------------------------------
    ca = debtors + cash_bal + oca
    cl = st_debt + creditors + ocl
    curr_ratio = ca / cl if cl != 0 else 0
    
    total_debt = lt_debt + st_debt
    de_ratio = total_debt / net_worth if net_worth != 0 else 0
    
    # FIX 4: Correct DSCR Formula (Numerator / (Interest + Principal))
    dscr_num = pat + dep + total_fin
    dscr_den = total_fin + principal_repayment[i]
    dscr = dscr_num / dscr_den if dscr_den != 0 else 0
    
    total_cash_out_monthly = (exp_dir + exp_op + total_fin + tax) / 12
    runway = cash_bal / total_cash_out_monthly if total_cash_out_monthly > 0 else 999
    
    npm = (pat / rev * 100) if rev != 0 else 0

    ratio_row = [curr_ratio, de_ratio, dscr, npm, runway]
    ratio_data.append(ratio_row)

# --- LOOP 2: Cash Flow Statement ---
cf_labels = ['Opening Cash', 'Net Profit Before Tax', 'Add: Depreciation', 'Add: Interest',
             'Op Profit before WC', 'Inc/Dec in Trade Payables', 'Inc/Dec in Other Liab',
             'Inc/Dec in Receivables', 'Inc/Dec in Other Assets', 'Tax Paid',
             'Net Cash from Operating',
             'Purchase of Fixed Assets (Capex)', 'Net Cash from Investing',
             'Inc/Dec Share Capital', 'Inc/Dec Share Premium', 'Inc/Dec Long Term Debt',
             'Inc/Dec Short Term Debt', 'Interest Paid', 'Net Cash from Financing',
             'Net Change in Cash', 'Closing Cash']

for i, year in enumerate(years):
    if i == 0:
        # FY24 Base Year 
        col = [0]*20 + [cash_history[0]]
        cf_final_cols.append(col)
        continue

    # Deltas
    delta_payables = trade_payables[i] - trade_payables[i-1]
    delta_ocl = other_cur_liab[i] - other_cur_liab[i-1]
    delta_debtors = trade_receivables[i] - trade_receivables[i-1]
    delta_oca = other_cur_assets[i] - other_cur_assets[i-1]
    
    pbt = pl_data[i][6]
    dep = pl_data[i][4]
    interest = pl_data[i][5]
    tax_paid = pl_data[i][7]
    
    op_profit_pre_wc = pbt + interest + dep
    
    cf_wc = delta_payables + delta_ocl - delta_debtors - delta_oca
    net_cf_op = pbt + dep + interest + cf_wc - tax_paid
    
    capex = (net_block[i] - net_block[i-1]) + dep
    net_cf_inv = -capex
    
    delta_equity = share_capital[i] - share_capital[i-1]
    delta_premium = share_premium[i]
    delta_ltd = term_loan_bal[i] - term_loan_bal[i-1]
    delta_std = st_borrowings[i] - st_borrowings[i-1]
    
    net_cf_fin = delta_equity + delta_premium + delta_ltd + delta_std - interest
    
    net_change = net_cf_op + net_cf_inv + net_cf_fin
    
    col = [cash_history[i-1], pbt, dep, interest,
           op_profit_pre_wc, delta_payables, delta_ocl, -delta_debtors, -delta_oca, -tax_paid,
           net_cf_op,
           -capex, net_cf_inv,
           delta_equity, delta_premium, delta_ltd, delta_std, -interest, net_cf_fin,
           net_change, cash_history[i]]
    cf_final_cols.append(col)

# ==========================================
# 3. DATAFRAME & EXPORT
# ==========================================

df_pl = pd.DataFrame(pl_data, columns=['Revenue', 'Cost of Sales', 'Opex', 'EBITDA',
                                     'Depreciation', 'Finance Cost', 'PBT', 'Tax', 'PAT', 'Cash Profit'],
                     index=years).T

df_bs = pd.DataFrame(bs_data, columns=['Share Capital', 'Reserves', 'Net Worth',
                                     'Long Term Debt', 'Short Term Debt', 'Payables', 'Other Cur Liab', 'Total Liab',
                                     'Net Block', 'Receivables', 'Cash & Bank', 'Other Cur Assets', 'Total Assets'],
                     index=years).T

df_ratios = pd.DataFrame(ratio_data, columns=['Current Ratio', 'Debt/Equity', 'DSCR', 'Net Profit Margin %', 'Runway (Months)'],
                         index=years).T

df_cf = pd.DataFrame(cf_final_cols, index=years, columns=cf_labels).T

file_name = 'Corrected_Complete_CMA.xlsx'
try:
    with pd.ExcelWriter(file_name, engine='openpyxl') as writer:
        df_pl.to_excel(writer, sheet_name='Operating Statement')
        df_bs.to_excel(writer, sheet_name='Balance Sheet')
        df_cf.to_excel(writer, sheet_name='Cash Flow Statement')
        df_ratios.to_excel(writer, sheet_name='Ratio Analysis')
    print(f"SUCCESS. File '{file_name}' created.")
except Exception as e:
    print(f"Error writing file: {e}")