# Start here

## What you need

- **An AI agent that can work on your computer**: read and write files, run commands, and use MCP.
  Examples: Claude Code (or Claude Desktop → Code), OpenAI Codex, Cursor. ChatGPT in the browser can explain the
  steps but cannot do the migration.
- **Python 3.11 or newer** installed.
- **Access you sign in to yourself**: IsaFlow (a login that can create or open the company), Sage One for that
  company, the company's email (for documents), and its bank statements.
- **This kit** on your computer: `git clone https://github.com/IsaFlowSA/isaflow-migration-kit`
  (or download the ZIP from GitHub and unzip it).

## Get IsaFlow access first

The agent works inside IsaFlow, so you need an IsaFlow login before step 03:

- **Migrating your own company:** register at https://app.isaflow.co.za/register (free trial; plans at
  https://app.isaflow.co.za/pricing). The onboarding wizard creates the company — step 03 walks you through it.
- **Migrating a company for someone else** (e.g. as their accountant): the company's IsaFlow account owner gives
  you access to their company, or registers it and lets you sign in to connect the agent. Never ask for or share
  their password — each person signs in themselves.

## How to start

1. Open your agent **on your own computer** (in Claude's desktop app: Code → "This computer"; a cloud environment
   cannot see your files or your browser sign-ins). Use the folder that holds your company folders, e.g. `D:\Clients`.
2. Paste the prompt below as it is — no blanks to fill in. The agent asks you about your setup, the kit, the
   company and your access, one question at a time.
3. When the agent asks, **open a new session in the company's `04_Finance\Agentic_Accounting` folder**, connect
   IsaFlow there (`templates/mcp/README.md`), and paste the prompt again. It carries on from where it stopped — you
   can paste it again at any time.

You will be asked to sign in yourself and to make a few decisions (opening date, anything that doesn't tie).
The agent never types passwords.

## The prompt

```
I want to migrate a company from Sage One to IsaFlow using the isaflow-migration-kit
(https://github.com/IsaFlowSA/isaflow-migration-kit). Assume I have not done this before.

Before doing anything else, check and ask me, one question at a time:
1. Environment: which agent and machine this is, whether you can read/write files, run commands, use MCP and
   drive a browser, and whether Python 3.11+ is installed (check it yourself).
2. The kit: look for it on this computer. If it is not there, ask me where to put it and clone it
   (or tell me how to download the ZIP).
3. The company: its full registered name, and where company folders live (suggest the current folder).
   Check whether it already has a folder and a brief (AGENTS.md or CLAUDE.md in 04_Finance\Agentic_Accounting).
4. Access: whether I have an IsaFlow login, whether the company already exists in IsaFlow, whether the IsaFlow
   MCP is connected, and whether I can sign in to the company's Sage One, email and bank statements.

Then read AGENTS.md in the kit and follow it, including every hard rule. Tell me in a few lines what you found
and which playbook step we start at: step 01 if there is no folder, otherwise continue from the brief's progress
table (if the brief is an older CLAUDE.md, add the kit's progress table to it). Never type a password - I sign
in myself. Confirm the company with list_companies before any posting. Stop wherever the playbook says to stop for me.
```
