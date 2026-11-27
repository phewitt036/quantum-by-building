# quantum-by-building

Learning quantum computing the way I learned Salesforce and Postgres: by building small,
working things and writing down what each one taught me.

Each lesson is one short Python program using [Qiskit](https://www.ibm.com/quantum/qiskit),
IBM's open-source quantum SDK. Every lesson:

1. starts with a **plain-English analogy** for the quantum idea, before any code,
2. runs on a **local simulator** (free and instant) and **checks itself** (`CHECK PASSED`),
3. then runs on a **real IBM quantum computer** through IBM's free Open Plan, and compares
   the noisy real-world results to the perfect simulated ones.

## Lessons

| # | Lesson | Quantum idea | Status |
|---|---|---|---|
| 1 | [Two magic coins](lessons/01_bell_state/) | Entanglement (Bell state) | ✅ simulator · ✅ hardware (ibm_marrakesh) |
| 2 | [Quantum dice](lessons/02_quantum_dice/) | Superposition and measurement | ✅ simulator · ✅ hardware (ibm_marrakesh) |
| 3 | [Cancelling waves](lessons/03_interference/) | Interference | ✅ simulator · ✅ hardware (ibm_marrakesh) |
| 4 | Guess the secret number in one try | Bernstein–Vazirani | planned |
| 5 | Find the needle | Grover's search | planned |
| 6 | Real machines are noisy | Noise and error mitigation | planned |

## Run it

```bash
python3 -m venv .venv && source .venv/bin/activate   # Windows Git Bash: source .venv/Scripts/activate
pip install -r requirements.txt
python lessons/01_bell_state/bell.py
```

To run on real IBM hardware, see [HARDWARE.md](HARDWARE.md). Your IBM API key is saved in
your home folder, never in this repo.

The roadmap and the rules for building each lesson are in [PLAN-qiskit.md](PLAN-qiskit.md).
