# Finora — Zero Projected Inflows Investigation Report

**Document:** `zero_projected_inflows_investigation.md`  
**Application:** Finora — AI Financial Co-Pilot for International Trade  
**As-Of Reference Date:** `2026-11-05`  
**Forecast Horizon:** 30 Days (`2026-11-05` to `2026-12-05`)  
**Status:** Complete & Mathematically Reconciled  

---

## 1. Executive Summary & Core Finding

During dashboard evaluation, the Cash Flow Forecast reported:
- **Opening Liquidity:** ₹25.0 L – ₹50.0 L (based on configured snapshot)
- **Projected Inflows:** **₹0.0 L**
- **Projected Outflows:** **₹39.4 L** (`3,944,727.52 INR`)
- **Closing Liquidity:** Deficit roll-forward matching exact net outflows
- **Overdue Invoices Warning:** *26 unpaid invoices totaling ₹39,00,163.99 INR have past-due collection dates and are excluded from future cash inflows.*

### The Bottom Line
**₹0.0 L projected inflows is 100% mathematically and financially correct for the current state of the dataset.**

There is no algorithmic failure, no data leakage, and no accidental exclusion of valid invoices. The engine operates exactly according to enterprise cash-accounting standards: **an invoice whose due date and ML-predicted payment date are 8 to 11 months in the past cannot be assumed to miraculously settle within the next 30 days without an explicit, verified repayment promise from the customer.**

---

## 2. Complete Inspection of All 26 Unpaid Invoices

The operational database contains 899 total invoices, of which 873 are fully paid and settled, and **26 invoices remain unpaid (`OPEN`)**, totaling **₹39,00,163.99 INR**.

Below is the complete audit record of all 26 unpaid invoices:

| # | Invoice ID | Customer | Invoice Date | Due Date | Currency | Amount (INR) | Payment Terms | Overdue Gap (Days) |
| :- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `INV-000867` | CUST055 | 2025-11-16 | 2025-12-16 | INR | ₹1,14,084.19 | Net 30 | 324 days overdue |
| 2 | `INV-000853` | CUST058 | 2025-11-12 | 2025-12-27 | INR | ₹96,261.98 | Net 45 | 313 days overdue |
| 3 | `INV-000878` | CUST008 | 2025-12-15 | 2025-12-30 | INR | ₹32,685.26 | Net 15 | 310 days overdue |
| 4 | `INV-000895` | CUST046 | 2025-12-20 | 2026-01-04 | INR | ₹81,615.81 | Net 15 | 305 days overdue |
| 5 | `INV-000899` | CUST046 | 2025-12-22 | 2026-01-06 | INR | ₹80,973.48 | Net 15 | 303 days overdue |
| 6 | `INV-000883` | CUST040 | 2025-12-09 | 2026-01-08 | INR | ₹79,392.44 | Net 30 | 301 days overdue |
| 7 | `INV-000885` | CUST027 | 2025-12-25 | 2026-01-09 | INR | ₹1,41,326.21 | Net 15 | 300 days overdue |
| 8 | `INV-000889` | CUST059 | 2025-12-25 | 2026-01-09 | INR | ₹33,482.09 | Net 15 | 300 days overdue |
| 9 | `INV-000898` | CUST036 | 2025-12-12 | 2026-01-11 | INR | ₹1,09,247.56 | Net 30 | 298 days overdue |
| 10 | `INV-000882` | CUST046 | 2025-12-27 | 2026-01-11 | INR | ₹1,77,478.44 | Net 15 | 298 days overdue |
| 11 | `INV-000888` | CUST054 | 2025-12-14 | 2026-01-13 | INR | ₹3,79,691.46 | Net 30 | 296 days overdue |
| 12 | `INV-000891` | CUST039 | 2025-12-14 | 2026-01-13 | INR | ₹2,86,244.25 | Net 30 | 296 days overdue |
| 13 | `INV-000886` | CUST029 | 2025-12-29 | 2026-01-13 | INR | ₹1,02,707.37 | Net 15 | 296 days overdue |
| 14 | `INV-000855` | CUST018 | 2025-11-15 | 2026-01-14 | INR | ₹3,62,750.87 | Net 60 | 295 days overdue |
| 15 | `INV-000858` | CUST012 | 2025-11-15 | 2026-01-14 | INR | ₹1,96,059.59 | Net 60 | 295 days overdue |
| 16 | `INV-000865` | CUST025 | 2025-11-21 | 2026-01-20 | INR | ₹3,36,818.63 | Net 60 | 289 days overdue |
| 17 | `INV-000897` | CUST041 | 2025-12-23 | 2026-01-22 | INR | ₹92,636.02 | Net 30 | 287 days overdue |
| 18 | `INV-000880` | CUST019 | 2025-12-26 | 2026-01-25 | INR | ₹1,24,369.99 | Net 30 | 284 days overdue |
| 19 | `INV-000876` | CUST030 | 2025-12-28 | 2026-01-27 | INR | ₹53,188.35 | Net 30 | 282 days overdue |
| 20 | `INV-000884` | CUST026 | 2025-12-28 | 2026-01-27 | INR | ₹69,766.32 | Net 30 | 282 days overdue |
| 21 | `INV-000894` | CUST021 | 2025-12-28 | 2026-01-27 | INR | ₹1,36,826.65 | Net 30 | 282 days overdue |
| 22 | `INV-000892` | CUST009 | 2025-12-05 | 2026-02-03 | INR | ₹84,173.13 | Net 60 | 275 days overdue |
| 23 | `INV-000877` | CUST031 | 2025-12-20 | 2026-02-03 | INR | ₹1,64,708.24 | Net 45 | 275 days overdue |
| 24 | `INV-000887` | CUST009 | 2025-12-17 | 2026-02-15 | INR | ₹2,01,259.60 | Net 60 | 263 days overdue |
| 25 | `INV-000896` | CUST009 | 2025-12-22 | 2026-02-20 | INR | ₹3,06,394.45 | Net 60 | 258 days overdue |
| 26 | `INV-000893` | CUST033 | 2025-12-24 | 2026-02-22 | INR | ₹56,021.61 | Net 60 | 256 days overdue |
| **TOTAL** | — | — | — | — | **INR** | **₹39,00,163.99** | — | **Avg: 290 days** |

---

## 3. Why Predicted Collection Dates Are in the Past

Finora's Phase 3 ML Payment Risk Engine predicts two values for an invoice:
1. **Late Probability ($P_{\text{late}}$):** The likelihood that the customer fails to pay on or before `due_date`.
2. **Conditional Delay ($\Delta_{\text{days}}$):** The expected number of delay days *if* the payment is late.

The nominal predicted payment date is computed as:
$$\text{Estimated Payment Date} = \text{due\_date} + (P_{\text{late}} \times \Delta_{\text{days}})$$

For example, on diagnostic invoice `INV-000853`:
- `due_date`: `2025-12-27`
- $P_{\text{late}}$: `0.6232` (62.3%)
- $\Delta_{\text{days}}$: `7.15 days`
- Expected Delay: $0.6232 \times 7.15 \approx 4.46\text{ days}$
- Estimated Payment Date: `2025-12-31`

### Timeline Comparison
- **Estimated Payment Date:** `2025-12-31`
- **Current Operating Date (`as_of_date`):** `2026-11-05`
- **Elapsed Time:** 310 calendar days in the past!

Even for the latest invoice in the dataset (`INV-000893`, due `2026-02-22`):
- Nominal due date: `2026-02-22`
- Even with an extreme 60-day delay: `2026-04-23`
- Still **196 days prior to November 5, 2026**!

---

## 4. Verification of the Probability-Weighted Collection Engine

The collection forecasting service (`backend/app/services/collection_forecasting_service.py`) executes the following logic for each unpaid invoice:
1. **On-Time Split:** $\text{ontime\_amount} = \text{outstanding} \times (1 - P_{\text{late}})$ assigned to `due_date`.
2. **Late Split:** $\text{late\_amount} = \text{outstanding} \times P_{\text{late}}$ assigned to $\text{due\_date} + \Delta_{\text{days}}$.
3. **Overdue Safety Gate:**
   ```python
   if late_date < as_of_date:
       unresolved_overdue.append({
           "invoice_id": inv.invoice_id,
           "status": "OVERDUE_UNRESOLVED",
           "reason": "Nominal predicted payment date and due date are both in the past."
       })
       total_overdue_unresolved += outstanding
       continue
   ```

Because both `ontime_date` and `late_date` are strictly `< as_of_date` for every single one of the 26 unpaid invoices:
- Zero events are scheduled between `2026-11-05` and `2026-12-05`.
- All 26 invoices are routed to `unresolved_overdue`.
- Projected Inflows strictly equal **₹0.00**.

---

## 5. Verification of Manual Collection Overrides

Finora provides the official mechanism for finance managers to restore an overdue invoice to the rolling forecast when a customer agrees to a new payment date: **Manual Collection Forecast Overrides**.

### Live System Verification
To verify this mechanism, a diagnostic execution was conducted:
1. **Invoice:** `INV-000853` (Outstanding: `₹96,261.98 INR`)
2. **Customer Action:** Buyer CUST058 confirmed a wire transfer scheduled for **November 20, 2026**.
3. **Endpoint Called:** `POST /api/v1/cashflow/collection-overrides`
   ```json
   {
     "company_id": "FINORA_DEMO",
     "invoice_id": "INV-000853",
     "expected_collection_date": "2026-11-20",
     "notes": "Customer CUST058 confirmed wire transfer for Nov 20"
   }
   ```
4. **Resulting Forecast:**
   - **Projected Inflows (30-day):** Immediately shifted from **₹0.00** to **₹96,261.98 INR**!
   - **Scheduled Events:** `1` event scheduled on `2026-11-20` with probability `1.00`.
   - **Overdue Unresolved Invoices:** Decreased from `26` to `25`.
   - **Overdue Amount:** Decreased from `₹39,00,163.99` to `₹38,03,902.01`.
5. **Rollback:** The test override was deactivated to preserve clean operational data.

---

## 6. Finance Manager Operational Protocol

When managing overdue export invoices in Finora, finance managers should follow this standard operating procedure:

```
[Invoice Status: Overdue]
          │
          ▼
[Contact Buyer / Account Team]
          │
          ├── Customer confirms settlement date? 
          │         │
          │         ├── YES ──► Create Manual Collection Override:
          │         │           POST /api/v1/cashflow/collection-overrides
          │         │           - Target Date: Agreed date
          │         │           - Notes: Buyer agreement reference
          │         │           ► Inflow immediately appears in Cash Flow Forecast
          │         │
          │         └── NO ───► Do NOT override.
          │                     Invoice remains in "Overdue Receivables" list.
          │                     Triggers Liquidity Alert ALT-OVERDUE.
          │                     Working capital reserve is protected.
```

---

## 7. Conclusion

| Question | Assessment |
| :--- | :--- |
| **Is ₹0.0 L projected inflows a bug?** | **No.** It is the mathematically and financially correct calculation. |
| **Are eligible invoices excluded?** | **No.** Every invoice is evaluated; all 26 unpaid invoices are >250 days overdue. |
| **Can overdue receivables be converted to inflows?** | **Yes**, via `POST /api/v1/cashflow/collection-overrides` when a valid promise date exists. |
