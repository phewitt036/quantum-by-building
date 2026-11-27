"""How often would each proof rule wrongly call an UNLINKED 16-qubit state "proven"?

This is the simulation behind lesson 7's "about 13% -> about 2%". It needs no quantum
computer and no Qiskit: it draws shot counts directly, with the same numbers of angles and
shots as the real runs, and applies both rules from parity_sweep.py.

The hardest case is a state that sits exactly on the 50% line without being linked: a plain
mix of "all 0s" and "all 1s" (all agree = 100%, no whole-group wiggle at all). Its true link
quality is exactly 50%, so any "proven" verdict is a false positive. A few other unlinked
states on the line are included too.

    python lessons/07_linking_many/false_positive_sim.py        # 20,000 trials per case, seed 2026
"""

import sys

import numpy as np

N_QUBITS = 16
ANGLES = 2 * N_QUBITS + 2   # the sweep's 34 turn angles
SHOTS = 2000                # shots per circuit, as in the real sweeps
TRIALS = 20_000
SEED = 2026

# Unlinked states exactly on the 50% line: (all-agree share A, whole-group coherence |c|),
# with A/2 + |c| = 0.5. The first is the hardest case.
CASES = [(1.0, 0.0), (0.8, 0.1), (0.654, 0.173), (0.5, 0.25)]


def trial_rates(rng, a_true: float, c_true: float, theta: float = 0.3):
    phis = 2 * np.pi * np.arange(ANGLES) / ANGLES
    p_true = 2 * c_true * np.cos(N_QUBITS * phis + theta)           # true even-minus-odd per angle
    a = rng.binomial(SHOTS, a_true, size=TRIALS) / SHOTS            # measured all-agree share
    even = rng.binomial(SHOTS, (1 + p_true) / 2, size=(TRIALS, ANGLES)) / SHOTS
    p = 2 * even - 1                                                # measured even-minus-odd
    c_hat = (p * np.exp(-1j * N_QUBITS * phis)).sum(axis=1) / ANGLES
    wiggle = np.abs(c_hat)
    quality = a / 2 + wiggle

    # Old rule: estimate minus 2 "wobbles" above 50% (ignores that the wiggle is fitted).
    wob_old = np.sqrt(a * (1 - a) / SHOTS / 4 + (1 - p * p).mean(axis=1) / (2 * ANGLES * SHOTS))
    old = np.mean(quality - 2 * wob_old > 0.5)

    # New rule (parity_sweep.quality): 2 wobbles off the all-agree share, 2 generous wobbles off the wiggle.
    sd_a = np.sqrt(a * (1 - a) / SHOTS)
    sd_c = np.sqrt(((1 - p * p) / SHOTS).sum(axis=1)) / ANGLES
    lower = (a - 2 * sd_a) / 2 + wiggle - 2 * sd_c
    new = np.mean(lower > 0.5)
    return old, new


def main() -> int:
    rng = np.random.default_rng(SEED)
    print(f"Unlinked {N_QUBITS}-qubit states on the 50% line; {TRIALS:,} simulated runs each, "
          f"{ANGLES} angles x {SHOTS} shots, seed {SEED}.")
    print("Share of runs wrongly called 'proven':")
    results = []
    for a_true, c_true in CASES:
        old, new = trial_rates(rng, a_true, c_true)
        results.append((old, new))
        print(f"   all agree {a_true:5.1%}, coherence {c_true:.3f}:   old rule {old:6.2%}   new rule {new:6.2%}")
    worst_old = max(r[0] for r in results)
    worst_new = max(r[1] for r in results)
    print(f"Worst case: old rule {worst_old:.2%}, new rule {worst_new:.2%}")
    ok = worst_new < 0.03
    print("  need: new rule under 3% in every case")
    print("CHECK PASSED" if ok else "CHECK FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
