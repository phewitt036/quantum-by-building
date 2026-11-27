# PLAN: quantum-by-building

Planned on Opus with Patrick, 2026-11-26. This file is the brief for any later session
(Claude on Sonnet, Codex, ChatGPT). It stands on its own, so read it fully before building.

## Goal

Patrick learns quantum computing hands-on by building small Qiskit programs. He isn't a
physicist or a pro developer. Each program runs first on a local simulator, then on a real
IBM quantum computer through IBM Quantum's **free Open Plan** (10 min of QPU time per rolling
28 days). The repo is **public** on GitHub (`phewitt036/quantum-by-building`) and doubles as a
portfolio piece, so it has to read well to a stranger: clean code, honest results, plain writing.

Done for the whole project: lessons 1–7 each run on the simulator with `CHECK PASSED`, have
been run at least once on real hardware with the real counts recorded in the lesson README,
and lesson 6 has a short write-up comparing simulator vs hardware. **Met on 2026-11-27.**

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
| 3 | `03_interference` | Noise-cancelling headphones → **interference** (**DONE on sim and ibm_marrakesh 2026-11-26 after a thrown-out run and a failed one; added a "peek" circuit and a phase dial sweep, and a `--job <id>` flag that checks hardware results automatically. Reuse that pattern in later lessons**) | H then H returns to 0; add a Z in between and it returns to 1 | H-H gives `0` 100% on sim; H-Z-H gives `1` 100% |
| 4 | `04_secret_number` | Guess a hidden number with one question instead of one per digit → **Bernstein–Vazirani** (**DONE: built by ChatGPT, reviewed and run on ibm_fez by Claude 2026-11-26, 91.6%**) | Hide a 4–6 bit string in an oracle and recover it in one run | Most common result equals the hidden string (sim: 100%) |
| 5 | `05_grover_search` | Finding the one prize in a row of identical closed boxes without opening them one by one → **Grover's search** (**DONE on sim and ibm_fez 2026-11-26: 4 boxes 96.3%, 8 boxes 78.5% at 2 rounds; reviewed by ChatGPT and merged 2026-11-27**) | 2–3 qubit Grover for a marked item | Sim: 2 qubits 100%, 3 qubits ≥ 90% (≈94.5% expected). Hardware: marked item is the most common result (expect well under 90%) |
| 6 | `06_noise` | A recording with static → **noise and error mitigation** (**DONE 2026-11-26, reviewed by ChatGPT and merged 2026-11-27: Bell pair + 0–160 cancelling CNOTs, four jobs (plain / DD / twirling / both) on ibm_fez, plus lesson 5's search with/without twirling on ibm_kingston and ibm_fez. Twirling kept the Bell link provable (82% vs 65% plain at 160 CNOTs); DD did nothing here; on the search, twirling only helped where readout was poor**) | Rerun lessons 1 and 5 on hardware and compare. Mitigation: SamplerV2 only offers `dynamical_decoupling` and `twirling` options (readout/resilience options belong to EstimatorV2), so start with those. **STOP AND ASK** before switching to Estimator or adding another package | Write-up table: sim vs raw hardware vs with DD/twirling |
| 7 | `07_linking_many` | A row of dominoes → **GHZ states, entanglement witnesses, phase sweep** (added 2026-11-26 at Patrick's "keep going until the IBM time is used") | Middle-out GHZ up to 40 qubits; Tóth–Gühne witness; hand-picked chains; weak-link diagnostic; parity-oscillation fidelity | Sim: 100% to 28 qubits; noisy sim decreasing. Hardware: 12 qubits proven by witness (fez), **16 proven by phase sweep** on ibm_marrakesh (lower bound 53.4%) and again on fresh qubits on ibm_fez 2026-11-27 (57.1%); a same-qubit repeat after recalibration fell short (46.9%) and its built-in control behaved (wiggle 0.007) |

Order: 1 → 2 → 3 → 4 → 5 → 6 → 7. Each builds on the previous one's words. Lesson 7 was added
on 2026-11-26 beyond the original six. **All seven are done, reviewed and on main (2026-11-27).**
Hardware runs can happen any time after a lesson passes on the simulator. Batch them to
save Open Plan minutes.

## How each step is verified

- `python lessons/NN_name/<name>.py` → ends with `CHECK PASSED`, exit code 0.
- After a hardware run, check it the way that lesson's script supports, then paste the
  counts into its README:
  - **Lessons 1–2:** `python tools/get_job.py <id>` shows `DONE` and the counts.
  - **Lessons 3–5:** `python lessons/NN_name/<name>.py --job <id>` reruns `check()` with
    hardware thresholds.
  - **Lessons 6–7:** `--job` with no ID. These scripts save their job IDs in a git-ignored
    `.last_*.json` file next to the script. Each new `--ibm` run of the same script overwrites
    that file, so check each run before starting the next.
- Offline checks that need no IBM account: `lessons/07_linking_many/recompute.py` rebuilds
  lesson 7's phase-sweep bounds from the published `data/`, and `false_positive_sim.py`
  reruns the false-positive simulation behind the proof rule.
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
- **Hardware compile rules (learned in lesson 3):** put `qc.barrier()` between gates that
  the compiler could merge or cancel (H-H, H-P-H), or the chip never runs them. Use
  `optimization_level=2` so the compiler picks the best-calibrated qubits; level 1 put a
  one-qubit job on qubit 0 and it came out much noisier. Before calling a hardware result
  meaningful, transpile against `FakeFez` and check the gates are still there.
- **Never call a group "linked" from a plain average of straight + sideways for more than 2 qubits.** Use the Tóth–Gühne witness (all-agree + ½·parity − ½) or a parity-oscillation fidelity, and require a 2-standard-error margin (lesson 7).
- **Give each new lesson a `--job` mode** that fetches a finished hardware job and runs the
  same `check()` with hardware thresholds, instead of eyeballing counts. Lessons 3–5 take
  the job ID (`--job <id>`). Lessons 6–7 store their IDs in a git-ignored `.last_*.json`
  and take plain `--job`. Prefer the lesson 6–7 style for multi-job experiments. Never
  commit job IDs; publish summary counts instead (lesson 7's `data/`).
- **Simulator runs use a fixed seed** (`seed_simulator`) so pasted output and charts match reruns.

## STOP AND ASK

- Anything IBM asks during signup beyond the free Open Plan (card, paid plan, upgrade).
- Before spending more than ~2 minutes of QPU time in one go (big shot counts, many circuits).
- Whether to opt in to IBM's extra-minutes promo (an extra 180 min over 12 months for active
  Open Plan users, per IBM's docs). It's his account and terms.
- Adding notebooks (Jupyter) or a published site (GitHub Pages) for the portfolio. Scripts +
  READMEs is the plan until he says otherwise.
- Changing the lesson list or order.
