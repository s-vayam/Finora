# Finora — AI Financial Co-Pilot for International Trade

> **Finora** is an HCI-focused fintech prototype for international trade finance, combining invoice tracking, FX risk analysis, cash-flow forecasting, trade document management, and an AI-assisted financial co-pilot.  
> **Visual Design Direction:** Inspired by modern premium fintech interfaces (Pro Finance aesthetic) featuring warm off-white surfaces, crisp black typography, and vivid neon-lime highlights.  
> **Course Project:** Human-Computer Interaction (HCI) Prototype  
> **Fictional Company:** Meridian Textiles Pvt Ltd (Ahmedabad, Gujarat, India)  
> **Base Currency:** INR (₹)  
> **Conversion Benchmark Rates:** USD = ₹85, EUR = ₹99, GBP = ₹113

---

## 1. Colour System & Application

| Token | Hex Code | Visual Application |
|---|---|---|
| **Neon Lime** | `#D9F83F` | Primary action buttons (`Mark as Paid`, `Send`), active chart bars (Inflows), key highlights, and button focus states. |
| **Soft Lime** | `#ECF9A8` | Highlighted subtle pills (`Pro Prototype`), active company selector pill, suggested prompt chips. |
| **Warm Off-White** | `#F5F5F2` | Main page canvas background, table headers, and secondary section containers. |
| **White** | `#FFFFFF` | Primary card surfaces, data tables, and modal dialogs. |
| **Near-Black** | `#111111` | Headings, large numeric values, active navigation items, out-of-flow chart bars, and selective dark feature panels. |
| **Secondary Grey** | `#8B8D86` | Secondary labels, timestamps, table column headers, and inactive icon states. |
| **Borders** | `#E7E7E2` | Thin, crisp dividers, card outlines, and table row separators. |
| **Success Green** | `#39765A` | Reconciled/Paid status badges and positive financial deltas. |
| **Warning Amber** | `#A87524` | Approaching maturity items (`Due soon`) and Month 3 working capital deficit banner. |
| **Critical Red** | `#B94A48` | Overdue invoice alerts (`$18,600`) and missing customs paperwork. |

---

## 2. Implemented Screens & Features

1. **Overview Dashboard (`/overview`):**
   - Clean white KPI cards with thin `#E7E7E2` borders and bold `#111111` metrics.
   - **Selective Dark Card:** High-impact `#111111` panel for the *Co-Pilot Operational Insight* with neon-lime `#D9F83F` accents.
   - **Cash Flow Chart:** Recharts bar & line chart featuring neon lime `#D9F83F` for Inflows, near-black `#111111` for Outflows, and a dashed line for cumulative liquidity.
   - **FX Exposure Breakdown:** Progress bars with neon-lime indicators.
   - **Upcoming Invoices Table:** Compact, high-contrast table with view actions.

2. **Invoices & Payments (`/invoices`):**
   - Search across buyers, invoice IDs, and consignments.
   - Status filters (*All*, *Overdue*, *Due soon*, *Upcoming*, *Paid*) and currency filters (*USD*, *EUR*, *GBP*).
   - Column sorting by Due Date, Amount, and Customer.
   - Detail modal with full shipment telemetry.
   - Simulated `Mark as Paid` action with confirmation dialog, updating local state, recalculating overdue totals, and triggering a toast.

3. **FX Risk Analysis (`/fx-risk`):**
   - Benchmark rate cards (USD ₹85, EUR ₹99, GBP ₹113) with visible illustrative disclaimer.
   - Currency exposure breakdown ($58k USD, €22k EUR, £9k GBP) with previous cycle comparison.
   - **Interactive Sensitivity Calculator:** Quick presets (`-5%`, `-2%`, `0%`, `+2%`, `+5%`), slider, and an impactful dark panel (`#111111`) displaying recalculated INR value in neon-lime.

4. **Cash Flow Forecast (`/cash-flow`):**
   - KPI metrics: Opening Liquidity (`₹24.8L`), Period Inflows, Outflows, and Closing Balance.
   - Working capital attention banner for Month 3 (Jan 2027) net deficit of `-₹1.0L`.
   - Toggle between 3-Month View and 6-Month Full Forecast.
   - Unified monthly breakdown table and dual-axis chart.

5. **Trade Documents (`/documents`):**
   - Statutory paperwork tracking: Commercial Invoice, Ocean Bill of Lading, Certificate of Origin, Packing List, Shipping Bill, Insurance Policy, and Inspection Certificate.
   - Status filters (*Missing*, *Pending*, *Complete*).
   - Missing document clearance warning for Hamburg consignment.
   - Document Detail Modal with simulated verification action.

6. **AI Financial Co-Pilot (`/copilot`):**
   - Clean, minimalist chat vessel with suggested prompt chips in soft lime (`#ECF9A8`).
   - Dynamic contextual answers based on active application state (e.g. reflects when an invoice is marked as paid).
   - Clear conversation button and action links into specific modules.

---

## 3. Running the Prototype

```bash
# Start Vite development server
npm run dev -- --host 127.0.0.1 --port 3000
```
Open **[http://127.0.0.1:3000](http://127.0.0.1:3000)** in your browser.
