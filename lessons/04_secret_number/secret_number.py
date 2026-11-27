"""Lesson 4: recover a hidden number with one question (Bernstein–Vazirani).

Run on the local simulator:
    python lessons/04_secret_number/secret_number.py

Submit to a real IBM quantum computer (see HARDWARE.md):
    python lessons/04_secret_number/secret_number.py --ibm

Check and chart a finished hardware job:
    python lessons/04_secret_number/secret_number.py --job <job-id>
"""

import argparse
import sys
from pathlib import Path

from qiskit import QuantumCircuit

SECRET = "10110"
SHOTS = 1000
SEED = 2026
HERE = Path(__file__).parent


def build_circuit(secret: str = SECRET) -> QuantumCircuit:
    """Ask the oracle once and read the hidden bits."""
    if not 4 <= len(secret) <= 6 or set(secret) - {"0", "1"}:
        raise ValueError("The secret must be 4 to 6 bits (only 0s and 1s).")

    width = len(secret)
    helper = width
    qc = QuantumCircuit(width + 1, width, name="secret-number")

    qc.x(helper)
    qc.h(range(width + 1))
    qc.barrier()

    # The oracle flips the helper once per matching 1. In this setup those
    # flips mark the waves instead. Qiskit prints bit 0 on the right.
    for qubit, bit in enumerate(reversed(secret)):
        if bit == "1":
            qc.cx(qubit, helper)
    qc.barrier()  # Keep the oracle separate from the two Hadamard stages.

    qc.h(range(width))
    qc.measure(range(width), range(width))
    return qc


def run_simulator(circuit: QuantumCircuit) -> dict[str, int]:
    from qiskit_aer import AerSimulator

    result = AerSimulator().run(circuit, shots=SHOTS, seed_simulator=SEED).result()
    return result.get_counts()


def check(counts: dict[str, int], real_hardware: bool, secret: str = SECRET) -> bool:
    """The simulator must always recover the secret. On hardware it must lead."""
    total = sum(counts.values())
    hits = counts.get(secret, 0)
    best_other = max((count for bits, count in counts.items() if bits != secret), default=0)
    if real_hardware:
        ok = hits > best_other
        requirement = "must beat every other result"
    else:
        ok = total > 0 and hits == total
        requirement = "need 100%"

    print(f"  Hidden number {secret} appeared in {hits} of {total} shots ({requirement}).")
    print("CHECK PASSED" if ok else "CHECK FAILED")
    return ok


def report_results(counts: dict[str, int], real_hardware: bool) -> int:
    filename = "hardware_results.png" if real_hardware else "simulator_results.png"
    where = "real hardware" if real_hardware else "the local simulator"
    print(f"Results from {sum(counts.values())} shots on {where}:")
    print(f"  {dict(sorted(counts.items()))}")

    if counts:
        from qiskit.visualization import plot_histogram

        figure = plot_histogram(counts, title=f"Secret number on {where}")
        figure.savefig(HERE / filename, bbox_inches="tight")
        print(f"Chart saved to {filename}")

    return 0 if check(counts, real_hardware) else 1


def submit_to_ibm(circuit: QuantumCircuit) -> None:
    """Submit a job, print its ID, and leave it in the queue."""
    from qiskit.transpiler import generate_preset_pass_manager
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2

    service = QiskitRuntimeService()
    backend = service.least_busy(
        operational=True, simulator=False, min_num_qubits=circuit.num_qubits
    )
    pm = generate_preset_pass_manager(backend=backend, optimization_level=2)
    job = SamplerV2(mode=backend).run([pm.run(circuit)], shots=SHOTS)
    job_id = job.job_id()
    print(f"Submitted to {backend.name}. Job ID: {job_id}")
    print(f"When it's done:  python lessons/04_secret_number/secret_number.py --job {job_id}")


def fetch_job(job_id: str) -> int:
    from qiskit_ibm_runtime import QiskitRuntimeService

    job = QiskitRuntimeService().job(job_id)
    status = job.status()
    if status != "DONE":
        print(f"Job {job_id} is {status}.")
        return 1 if status in ("ERROR", "CANCELLED") else 0

    counts = job.result()[0].data.c.get_counts()
    return report_results(counts, real_hardware=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--ibm", action="store_true", help="submit to a real IBM quantum computer")
    mode.add_argument("--job", metavar="JOB_ID", help="check and chart a finished hardware job")
    args = parser.parse_args()

    if args.job:
        return fetch_job(args.job)

    circuit = build_circuit()
    print(circuit.draw(output="text"))
    if args.ibm:
        submit_to_ibm(circuit)
        return 0

    return report_results(run_simulator(circuit), real_hardware=False)


if __name__ == "__main__":
    sys.exit(main())
