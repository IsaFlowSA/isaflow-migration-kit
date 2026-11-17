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

1. Decide where company folders live, e.g. `D:\Clients`. Each company gets its own folder there.
2. Open your agent with the **kit folder** as the working folder.
3. Paste the prompt below, with the company name and your clients folder filled in.
4. After step 01 the agent asks you to **open a new session in the company's `04_Finance\Agentic_Accounting`
   folder**, connect IsaFlow there (`templates/mcp/README.md`), and paste the prompt again. It carries on from where
   it stopped — you can paste it again at any time.

You will be asked to sign in yourself and to make a few decisions (opening date, anything that doesn't tie).
The agent never types passwords.

## The prompt

```
I want to migrate <COMPANY NAME> from Sage One to IsaFlow, using the isaflow-migration-kit.
Kit folder: <PATH TO KIT>
Company folders live in: <CLIENTS FOLDER>

Read AGENTS.md in the kit and follow it, including every hard rule. Then work out where we are: if the company
already has a folder with an AGENTS.md brief, read it and continue from its progress table; otherwise start at
playbook step 01. Guide me step by step - assume I have not done this before. Ask one clear question at a time,
and stop wherever the playbook says to stop for me.
```
