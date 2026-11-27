# Running on a real IBM quantum computer

IBM's **Open Plan** is free: up to **10 minutes of quantum-computer time per rolling 28 days**
(checked against IBM's docs 2026-11-26). Lesson 1 uses a few seconds of it, so there's
plenty to learn with.

## 1. Make the account (Patrick does this, once)

1. Create an IBM Cloud account: <https://cloud.ibm.com/registration>.
   **If it asks for a credit card or for you to pick a paid plan, stop and check before
   entering anything.** The Open Plan itself is free. IBM's docs don't say whether a card is
   needed just to verify the account.
2. Log in to IBM Quantum Platform: <https://quantum.cloud.ibm.com>.
3. Pick region **us-east** in the header (Open Plan instances can only be made there).
4. **Instances → Create instance**: give it a name, choose the **Open** plan, then
   Next → Next → Create instance.
5. From the dashboard, **create an API key** (44 characters). Treat it like a password.
6. On the Instances page, hover over your instance's **CRN** and click to copy it.

## 2. Save the key on each machine (once per machine)

From the repo folder, with the project's Python environment active:

```bash
python tools/save_ibm_account.py
```

It asks for the key with a **hidden prompt**, so the key never shows on screen and never
lands in your shell history. Qiskit saves it to `~/.qiskit/qiskit-ibm.json` in your home
folder, **outside this repo**. If it worked, it lists the quantum computers you can use.

Rules:
- Never paste the key into a chat with Claude or ChatGPT, a file in this repo, or a commit.
- The `.gitignore` blocks `.env` files and `qiskit-ibm.json` as a backstop.
- If the key ever leaks, delete it on the IBM dashboard and make a new one.
- An environment variable works too (`QISKIT_IBM_TOKEN`, plus `QISKIT_IBM_INSTANCE`
  for the CRN), but the saved file is simpler.

## 3. Send a lesson to the real machine

```bash
python lessons/01_bell_state/bell.py --ibm
```

This picks the least busy real machine, rewrites the circuit for that chip's wiring, sends
it, prints a **job ID** and exits. It doesn't sit and wait.

## 4. Get the results later

Real machines have a queue. The wait might be seconds or hours.

```bash
python tools/get_job.py <job-id>
```

It says `QUEUED` / `RUNNING` until the job is done, then prints the counts.
You can also watch the job on the IBM Quantum dashboard under **Workloads**.

**Long waits:** the job runs at IBM, not on your computer, so closing the laptop doesn't
stop it. The job ID is all you need to fetch the results from any machine with the
account saved. An always-on machine is handy for checking in later.

## Setting up a Windows machine (Git Bash)

```bash
git clone https://github.com/phewitt036/quantum-by-building.git
cd quantum-by-building
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
python lessons/01_bell_state/bell.py
```

**Save the key from PowerShell, not Git Bash.** Git Bash's window can't hide typed
input for Windows Python, so the hidden key prompt may hang or show the key. In PowerShell:

```powershell
cd ~\quantum-by-building
.venv\Scripts\python tools\save_ibm_account.py
```
