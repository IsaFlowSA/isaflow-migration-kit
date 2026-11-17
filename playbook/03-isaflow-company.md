# 03 — Create the company in IsaFlow

**Goal:** the company exists in IsaFlow, the agent's MCP connection points at it, and its id is recorded.

1. Check whether the IsaFlow MCP has a tool that creates companies. If not, the person uses the IsaFlow app's
   onboarding wizard. Give them every field from the company's `AGENTS.md` (name, registration, VAT, income tax,
   year-end, addresses, directors). If you can drive their browser and they are signed in, you may fill the wizard,
   but **they** click the final create.
2. The person connects the MCP server (`isaflow-<short>`) and, in the sign-in window, **chooses the new company**.
3. Call `list_companies` and `company_profile`. Name, VAT number and year-end must match the brief. Record the
   company id in `AGENTS.md` and `data/company.json`.
4. Create the financial years the migration needs, aligned to the company's year-end (from the opening date to the
   current year). Some IsaFlow versions do this in the app (Accounting → Financial Years); note in the brief how
   the year label maps to dates.
5. Look at the chart of accounts IsaFlow created (`list_gl_accounts`). Save the code → id map to
   `data/account_ids.json`.

**Stop:** report the company id, the years created and the chart, before step 04.
