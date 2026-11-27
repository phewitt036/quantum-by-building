"""Lesson 1: the Bell state, two "magic coins" that always land the same way.

Run on the local simulator (free, instant):
    python lessons/01_bell_state/bell.py

Send it to a real IBM quantum computer (needs a saved IBM account, see HARDWARE.md):
    python lessons/01_bell_state/bell.py --ibm
"""

import argparse
import sys
from pathlib import Path

from qiskit import QuantumCircuit

SHOTS = 1000  # how many times we run each circuit, like flipping the coin pair 1000 times
SEED = 2026   # fixed seed so the simulator gives the same "random" results every run
HERE = Path(__file__).parent


def build_circuit(sideways: bool = False) -> QuantumCircuit:
    """Make the magic-coin pair. With sideways=True, look at both coins from a different angle."""
    qc = QuantumCircuit(2, 2)  # 2 qubits (the coins), 2 classical bits (where we write results)
    qc.name = "sideways" if sideways else "straight"
    qc.h(0)        # Hadamard: put coin 0 "in the air", 50/50 heads or tails
    qc.cx(0, 1)    # CNOT: tie coin 1 to coin 0, so whatever 0 lands on, 1 matches
    if sideways:
        qc.h([0, 1])  # turn BOTH coins sideways before looking (measure in another "direction")
    qc.measure([0, 1], [0, 1])  # catch both coins and write down what they show
    return qc


def check(name: str, counts: dict, shots: int, real_hardware: bool) -> bool:
    """Works if the coins (almost) always match, about half 00 and half 11."""
    matched = counts.get("00", 0) + counts.get("11", 0)
    match_rate = matched / shots
    share_00 = counts.get("00", 0) / max(matched, 1)
    # A simulator is perfect, so mismatches (01/10) must be zero.
    # Real hardware is noisy, so allow some mismatches.
    min_match = 0.90 if real_hardware else 1.0
    ok = match_rate >= min_match and 0.40 <= share_00 <= 0.60
    print(f"  [{name}] coins matched {match_rate:.1%} (need >= {min_match:.0%}); "
          f"00 was {share_00:.1%} of the matches (need 40-60%) -> {'ok' if ok else 'FAIL'}")
    return ok


def run_simulator(circuits: list[QuantumCircuit]) -> list[dict]:
    from qiskit_aer import AerSimulator

    result = AerSimulator().run(circuits, shots=SHOTS, seed_simulator=SEED).result()
    return [result.get_counts(i) for i in range(len(circuits))]


def submit_to_ibm(circuits: list[QuantumCircuit]) -> None:
    """Send both circuits to the least busy real IBM machine, print the job ID and exit.

    Queue waits can be minutes to hours, so we don't sit and wait here.
    Fetch the result later with:  python tools/get_job.py <job-id>
    """
    from qiskit.transpiler import generate_preset_pass_manager
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2

    # Reads the saved account from ~/.qiskit/qiskit-ibm.json (or QISKIT_IBM_TOKEN).
    # The key is never printed or stored in this repo.
    service = QiskitRuntimeService()
    backend = service.least_busy(operational=True, simulator=False, min_num_qubits=2)
    # "Transpile": rewrite our circuits using the gates and wiring this chip actually has.
    pm = generate_preset_pass_manager(backend=backend, optimization_level=1)
    job = SamplerV2(mode=backend).run([pm.run(qc) for qc in circuits], shots=SHOTS)
    print(f"Submitted to {backend.name}. Job ID: {job.job_id()}")
    print("Results come back in this order: 1 = straight, 2 = sideways.")
    print(f"Check on it later with:  python tools/get_job.py {job.job_id()}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--ibm", action="store_true", help="submit to a real IBM quantum computer")
    args = parser.parse_args()

    circuits = [build_circuit(), build_circuit(sideways=True)]
    for qc in circuits:
        print(f"Circuit '{qc.name}':")
        print(qc.draw(output="text"))

    if args.ibm:
        submit_to_ibm(circuits)
        return 0

    all_counts = run_simulator(circuits)
    print(f"Results from {SHOTS} runs each on the local simulator:")
    for qc, counts in zip(circuits, all_counts):
        print(f"  [{qc.name}] {dict(sorted(counts.items()))}")

    try:
        from qiskit.visualization import plot_histogram

        plot_histogram(all_counts, legend=[qc.name for qc in circuits],
                       title="Bell state on the simulator").savefig(
            HERE / "simulator_results.png", bbox_inches="tight")
        print(f"Chart saved to {HERE / 'simulator_results.png'}")
    except ImportError:
        pass

    ok = all(check(qc.name, c, SHOTS, real_hardware=False) for qc, c in zip(circuits, all_counts))
    print("CHECK PASSED" if ok else "CHECK FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
