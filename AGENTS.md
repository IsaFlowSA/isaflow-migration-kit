# isaflow-migration-kit — instructions for agents

You are helping someone move a company's books from **Sage One (South Africa)** to **IsaFlow**. The person may be
doing this for the first time: guide them step by step, one clear question at a time.

This kit holds the method, scripts and templates. It holds **no company data**. Each company has its own folder
(created in step 01) with its own `AGENTS.md` brief — that file, not this one, records where the company is.

## Hard rules — never break these

1. **Never enter a password, PIN, OTP or credential.** The person signs in to IsaFlow, Sage, email and the bank
   themselves. Ask, then wait. Never route around a refusal or a blocked action — stop and explain.
2. **Post only to the company being migrated.** Before every posting session call `list_companies` /
   `company_profile` and check name, VAT number and company id against the company's `AGENTS.md`. If they differ,
   stop. One IsaFlow login can hold several companies.
3. **Balance to the cent.** Never plug, never round to "close enough", never post a closing balance as a shortcut —
   balances are the output of processing transactions. The single exception is the opening (take-on) balance at the
   agreed opening date.
4. **Never reverse-and-repost to back-fill.** Reversals are for genuine errors only.
5. **Work at customer/supplier balance level.** Apply cash FIFO to the oldest documents.
6. **Bank reconciliations only against real bank statements**, never against Sage's bank balance.
7. **State the residual every time**, even when it is R0.00.
8. **Dry run before every bulk write**, and show the person the totals before the first bulk post.
9. **Never change another company's folder or books.** Intercompany checks are read-only.
10. **Report facts, not judgements about people.** Short answers: facts, amounts, references.
11. **Personal information** (ID numbers, bank details) stays in the company folder. Never commit it to this kit.

## How to work

1. Find out where the company is: read its `AGENTS.md` (in `<company>/04_Finance/Agentic_Accounting/`) if it
   exists; otherwise start at step 01.
2. Follow the playbook in order. Each step says what "done" looks like and when to stop for the person.
3. After each step, update the company's `AGENTS.md` (progress table, facts with sources, open items) and its
   document register.

| Step | File | Stops for the person when |
|---|---|---|
| 01 Folder | `playbook/01-folder.md` | folder name / location to confirm |
| 02 Documents | `playbook/02-documents.md` | documents only they can get |
| 03 IsaFlow company | `playbook/03-isaflow-company.md` | creating the company, signing in to MCP |
| 04 Opening date | `playbook/04-opening-date.md` | Sage sign-in; choosing the date |
| 05 Migrate | `playbook/05-migrate.md` | dry-run totals before the first bulk post |
| 06 Prove | `playbook/06-prove.md` | anything that does not tie |
| 07 Monthly sync | `playbook/07-monthly-sync.md` | each month, if Sage keeps running |

Read `playbook/pitfalls.md` before step 05 — IsaFlow behaviours that cost time on earlier migrations.

## What you need

- File access and a terminal with **Python 3.11+** (scripts use only the standard library; run them with `python -I`).
- The **IsaFlow MCP server** connected to the right company (`templates/mcp/README.md`).
- A browser the person is signed in to, if you can drive one (Sage exports, email attachments). If you cannot,
  give the person exact click-by-click instructions instead.

Chat-only assistants without file access or a terminal can explain the steps but cannot run the migration.
