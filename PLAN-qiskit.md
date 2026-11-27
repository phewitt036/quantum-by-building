# PLAN: quantum-by-building

Planned on Opus with Patrick, 2026-11-26. This file is the brief for any later session
(Claude on Sonnet, Codex, ChatGPT). It stands on its own, so read it fully before building.

## Goal

Patrick learns quantum computing hands-on by building small Qiskit programs. He isn't a
physicist or a pro developer. Each program runs first on a local simulator, then on a real
IBM quantum computer through IBM Quantum's **free Open Plan** (10 min of QPU time per rolling
28 days). The repo is **public** on GitHub (`phewitt036/quantum-by-building`) and doubles as a
portfolio piece, so it has to read well to a stranger: clean code, honest results, plain writing.

Done for the whole project: lessons 1–6 each run on the simulator with `CHECK PASSED`, have
been run at least once on real hardware with the real counts recorded in the lesson README,
and lesson 6 has a short write-up comparing simulator vs hardware.

## Layout

```
README.md                 public front page: what this is, lesson table, how to run
PLAN-qiskit.md            this file
HARDWARE.md               IBM account setup, saving the key, sending jobs, fetching results
requirements.txt          qiskit, qiskit-aer, qiskit-ibm-runtime, matplotlib
.gitignore                .venv, .env*, qiskit-ibm.json, .qiskit/
lessons/NN_name/
    <name>.py             the program: build_circuit(), check(), --ibm flag
    README.md             analogy first, then the code walk-through, real output, what it means
    simulator_results.png chart from the simulator run (committed)
    hardware_results.png  chart from the real-hardware run, once there is one (committed)
tools/
    save_ibm_account.py   one-time hidden-prompt key save to ~/.qiskit/qiskit-ibm.json
    get_job.py            fetch a hardware job's status and counts by job ID
```

Python lives in `.venv/` (not committed). The repo sits with Patrick's other code repos on
each machine (`~/projects/` on the Mac, the home folder on x8).

## The lesson pattern (every lesson follows it)

1. **Analogy first.** The lesson README opens with an everyday picture (coins, dice, waves,
   a guessing game) before any jargon. Introduce at most 2–3 new words, in a small table.
2. **One small program** with the same shape as `lessons/01_bell_state/bell.py`:
   `build_circuit()`, `run_simulator()`, `submit_to_ibm()` (submits, prints the job ID, exits,
   never waits on the queue), and `check()`, which prints `CHECK PASSED` / `CHECK FAILED` and
   sets the exit code. Keep the classical register named `c` (the default) so
   `tools/get_job.py` can read the counts.
3. **Real output pasted into the README**, with the date, then "what that means" in plain words.
4. **Hardware run** later: paste the real counts next to the simulator's and explain the difference.

## Lessons

| # | Folder | Analogy → idea | Program | How we know it works (`check()`) |
|---|---|---|---|---|
| 1 | `01_bell_state` | Two magic coins that always match, even turned sideways → **entanglement** | H + CNOT on 2 qubits, measured straight and sideways (H on both before measuring) | Sim: only `00`/`11` in both versions, each 40–60%. Hardware: ≥90% matching. **DONE on sim and on ibm_marrakesh 2026-11-26 (91.7% / 96.4% matching).** |
| 2 | `02_quantum_dice` | A coin spinning in the air → **superposition, measurement** (**DONE on sim and ibm_marrakesh 2026-11-26; hardware die was slightly loaded**) | 1 qubit H = fair coin; 3 qubits H = an 8-sided die; a d6 by throwing away shots that read 6 or 7 (in Python, after the run) and mapping 0–5 to 1–6 | Each of the 8 outcomes 9–16% over 4000 shots; d6 rolls only 1–6 |
| 3 | `03_interference` | Noise-cancelling headphones → **interference** | H then H returns to 0; add a Z in between and it returns to 1 | H-H gives `0` 100% on sim; H-Z-H gives `1` 100% |
| 4 | `04_secret_number` | Guess a hidden number with one question instead of one per digit → **Bernstein–Vazirani** | Hide a 4–6 bit string in an oracle and recover it in one run | Most common result equals the hidden string (sim: 100%) |
| 5 | `05_grover_search` | Finding the one prize in a row of identical closed boxes without opening them one by one → **Grover's search** | 2–3 qubit Grover for a marked item | Sim: 2 qubits 100%, 3 qubits ≥ 90% (≈94.5% expected). Hardware: marked item is the most common result (expect well under 90%) |
| 6 | `06_noise` | A recording with static → **noise and error mitigation** | Rerun lessons 1 and 5 on hardware and compare. Mitigation: SamplerV2 only offers `dynamical_decoupling` and `twirling` options (readout/resilience options belong to EstimatorV2), so start with those. **STOP AND ASK** before switching to Estimator or adding another package | Write-up table: sim vs raw hardware vs with DD/twirling |

Order: 1 → 2 → 3 → 4 → 5 → 6. Each builds on the previous one's words.
Hardware runs can happen any time after a lesson passes on the simulator. Batch them to
save Open Plan minutes.

## How each step is verified

- `python lessons/NN_name/<name>.py` → ends with `CHECK PASSED`, exit code 0.
- After a hardware run, `python tools/get_job.py <id>` shows `DONE` and counts, and the
  lesson's README gets those counts.
- Before each commit: `git status` shows no `.env`, `qiskit-ibm.json` or key-like strings.
  Quick scan: `git diff --cached | grep -iE "token|apikey|crn:v1"` should match only
  docs and variable names, never a value.

## Rules that matter

- **The IBM API key is Patrick's alone.** He creates the account and key himself. Never
  ask for it, print it, log it, or commit it. Code reads it only through
  `QiskitRuntimeService()` (the saved file `~/.qiskit/qiskit-ibm.json` or `QISKIT_IBM_TOKEN`).
  `tools/save_ibm_account.py` uses a hidden prompt; he runs it himself in his own terminal.
  Don't print job metadata or the CRN either: it identifies his account.
- **Money:** the Open Plan is free. If IBM ever asks for a card, a paid plan, or offers a
  paid upgrade, **STOP AND ASK** Patrick. Never pick a non-Open plan.
- **Public repo:** nothing personal, no IP addresses or homelab hostnames with ports, no
  family details, no school work. This repo isn't one of the four that deploy on push, so
  push freely after each piece (commit + push as you go).
- **Long runs start from x8** (Patrick's always-on PC). Hardware queue waits can be hours.
  Submit from there, or just submit and fetch later by job ID from either machine.
- **Plain language.** Patrick isn't a physicist. Analogy before code, short sentences, no
  equations unless a lesson truly needs one (then explain it in words too).
- **Models:** the code calls no AI model, so `common/models.json` doesn't apply.
- **Handoff note:** keep Patrick's private handoff note for this project current (status,
  next lesson) so other assistants can follow along. No secrets, CRNs or job IDs there.
- **Commits use the GitHub noreply email** (set in this repo's local git config). On a new
  clone, set it again before the first commit so a personal email never lands in public history.
- **Simulator runs use a fixed seed** (`seed_simulator`) so pasted output and charts match reruns.

## STOP AND ASK

- Anything IBM asks during signup beyond the free Open Plan (card, paid plan, upgrade).
- Before spending more than ~2 minutes of QPU time in one go (big shot counts, many circuits).
- Whether to opt in to IBM's extra-minutes promo (an extra 180 min over 12 months for active
  Open Plan users, per IBM's docs). It's his account and terms.
- Adding notebooks (Jupyter) or a published site (GitHub Pages) for the portfolio. Scripts +
  READMEs is the plan until he says otherwise.
- Changing the lesson list or order.
