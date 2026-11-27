"""Lesson 2: quantum dice. A coin spinning in the air, and dice built from them.

Run on the local simulator (free, instant):
    python lessons/02_quantum_dice/dice.py

Send it to a real IBM quantum computer (needs a saved IBM account, see HARDWARE.md):
    python lessons/02_quantum_dice/dice.py --ibm
"""

import argparse
import sys
from collections import Counter
from pathlib import Path

from qiskit import QuantumCircuit

SHOTS = 4000  # how many times we toss the coin / roll the die
SEED = 2026   # fixed seed so the simulator gives the same "random" results every run
HERE = Path(__file__).parent


def build_coin() -> QuantumCircuit:
    """One qubit, one Hadamard: a perfectly fair coin."""
    qc = QuantumCircuit(1, 1)
    qc.name = "coin"
    qc.h(0)          # spin the coin: now it's 50% 0 and 50% 1 at the same time
    qc.measure(0, 0)  # catch it: it picks 0 or 1, at random
    return qc


def build_d8() -> QuantumCircuit:
    """Three fair coins side by side = a random 3-bit number = an 8-sided die (0 to 7)."""
    qc = QuantumCircuit(3, 3)
    qc.name = "d8"
    qc.h([0, 1, 2])  # spin all three coins
    qc.measure([0, 1, 2], [0, 1, 2])
    return qc


def d6_from_d8(rolls: list[int]) -> list[int]:
    """Turn 8-sided rolls into 6-sided rolls: throw away 6 and 7, then shift 0-5 up to 1-6.

    Throwing away is done in plain Python after the run. If the d8 is fair, every d6 face
    stays equally likely. (It can't fix a loaded d8; the d6 inherits the lean.)
    """
    return [r + 1 for r in rolls if r < 6]


def check(coin: Counter, d8: Counter, d6: Counter, real_hardware: bool) -> bool:
    """Works if every face comes up about equally often."""
    ok = True
    # On a simulator the only wobble is chance. Real hardware has small gate and
    # measurement errors that can make a qubit lean toward 0 or 1, so it gets wider limits.
    lo_coin, hi_coin = (0.40, 0.60) if real_hardware else (0.45, 0.55)
    lo_d8, hi_d8 = (0.07, 0.18) if real_hardware else (0.09, 0.16)
    lo_d6, hi_d6 = (0.10, 0.24) if real_hardware else (0.12, 0.22)
    for name, counts, faces, lo, hi in [
        ("coin", coin, range(2), lo_coin, hi_coin),
        ("d8", d8, range(8), lo_d8, hi_d8),
        ("d6", d6, range(1, 7), lo_d6, hi_d6),
    ]:
        total = sum(counts.values())
        shares = {f: counts.get(f, 0) / total for f in faces}
        extra = set(counts) - set(faces)
        face_ok = all(lo <= s <= hi for s in shares.values()) and not extra
        ok &= face_ok
        spread = ", ".join(f"{f}: {s:.1%}" for f, s in shares.items())
        print(f"  [{name}] {spread}  (each needs {lo:.0%}-{hi:.0%}) -> {'ok' if face_ok else 'FAIL'}")
    return ok


def save_chart(coin: Counter, d8: Counter, d6: Counter, title: str, path: Path) -> None:
    """Draw the three bar charts side by side, with a dashed line where perfectly even would be."""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.2))
    for ax, (name, counts, faces) in zip(axes, [
        ("Coin (1 qubit)", coin, range(2)),
        ("8-sided die (3 qubits)", d8, range(8)),
        ("6-sided die (d8 with 6 and 7 thrown away)", d6, range(1, 7)),
    ]):
        ax.bar([str(f) for f in faces], [counts.get(f, 0) for f in faces], color="#4c72b0")
        ax.axhline(sum(counts.values()) / len(faces), color="#c44e52", linestyle="--",
                   linewidth=1, label="perfectly even")
        ax.set_title(name, fontsize=10)
    axes[0].set_ylabel("how many times")
    axes[0].legend(fontsize=8)
    fig.suptitle(title, fontsize=11)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    print(f"Chart saved to {path}")


def run_simulator(circuits: list[QuantumCircuit]) -> list[list[int]]:
    """Return every single shot as a number, in the order they came out."""
    from qiskit_aer import AerSimulator

    result = AerSimulator().run(circuits, shots=SHOTS, seed_simulator=SEED, memory=True).result()
    return [[int(bits, 2) for bits in result.get_memory(i)] for i in range(len(circuits))]


def submit_to_ibm(circuits: list[QuantumCircuit]) -> None:
    """Send both circuits to the least busy real IBM machine, print the job ID and exit."""
    from qiskit.transpiler import generate_preset_pass_manager
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2

    service = QiskitRuntimeService()  # reads the saved account; the key is never printed
    backend = service.least_busy(operational=True, simulator=False, min_num_qubits=3)
    pm = generate_preset_pass_manager(backend=backend, optimization_level=1)
    job = SamplerV2(mode=backend).run([pm.run(qc) for qc in circuits], shots=SHOTS)
    print(f"Submitted to {backend.name}. Job ID: {job.job_id()}")
    print("Results come back in this order: 1 = coin, 2 = d8 (bits read as a number 0-7).")
    print(f"Check on it later with:  python tools/get_job.py {job.job_id()}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--ibm", action="store_true", help="submit to a real IBM quantum computer")
    args = parser.parse_args()

    circuits = [build_coin(), build_d8()]
    for qc in circuits:
        print(f"Circuit '{qc.name}':")
        print(qc.draw(output="text"))

    if args.ibm:
        submit_to_ibm(circuits)
        return 0

    coin_shots, d8_shots = run_simulator(circuits)
    d6_shots = d6_from_d8(d8_shots)
    coin, d8, d6 = Counter(coin_shots), Counter(d8_shots), Counter(d6_shots)

    print(f"Simulator, {SHOTS} shots each:")
    print(f"  first 20 coin tosses: {' '.join(map(str, coin_shots[:20]))}")
    print(f"  first 20 d6 rolls:    {' '.join(map(str, d6_shots[:20]))}")
    print(f"  coin: {dict(sorted(coin.items()))}")
    print(f"  d8:   {dict(sorted(d8.items()))}")
    print(f"  d6:   {dict(sorted(d6.items()))}  "
          f"(kept {len(d6_shots)} of {SHOTS} d8 rolls, {len(d6_shots) / SHOTS:.0%})")

    save_chart(coin, d8, d6, "Quantum dice on the simulator", HERE / "simulator_results.png")

    ok = check(coin, d8, d6, real_hardware=False)
    print("CHECK PASSED" if ok else "CHECK FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
