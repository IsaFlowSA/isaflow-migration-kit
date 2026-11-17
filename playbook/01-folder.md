# 01 — Company folder

**Goal:** the company has its own folder, outside the kit, with the standard layout and a brief.

1. Ask the person for: the company's registered name, a short lowercase name (e.g. `example`), and where company
   folders live (e.g. `D:\Clients`).
2. Look for an existing folder there — check spelling variants, trading names and abbreviations. If one exists,
   use it and keep everything in it.
3. Run:
   ```
   python -I <kit>/scripts/scaffold.py --root "<clients folder>" --name "<registered name>" --short <short>
   ```
   It creates what is missing and never overwrites. Layout:
   ```
   <company>/
     00_Document_Register.md
     01_Corporate/{CIPC, Shareholding, Compliance}   02_Tax/SARS   03_Directors_ID
     04_Finance/AFS
     04_Finance/Agentic_Accounting/        <- the agent's working folder from now on
       AGENTS.md  CLAUDE.md                <- company brief (CLAUDE.md just points to AGENTS.md)
       data/{company.json, state.json, account_ids.json, customer_ids.json, supplier_ids.json}
       Bank Statements/  Source Documents/Sage exports/  Suppliers/  Customers/  Payroll/  Financials/  outputs/
     05_Legal   08_To_Review
   ```
4. Set up the IsaFlow MCP connection in `04_Finance/Agentic_Accounting` for the person's agent
   (`templates/mcp/README.md`). Name the server `isaflow-<short>`. Don't connect it yet — that is step 03.

**Stop:** tell the person to open a **new agent session in `<company>/04_Finance/Agentic_Accounting`** (so the
brief and MCP config load) and paste the starter prompt again.
