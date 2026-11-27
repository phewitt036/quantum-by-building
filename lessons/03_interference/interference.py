"""Lesson 3: interference. Quantum possibilities can cancel out, like noise-cancelling headphones.

Run on the local simulator (free, instant):
    python lessons/03_interference/interference.py

Send it to a real IBM quantum computer (needs a saved IBM account, see HARDWARE.md):
    python lessons/03_interference/interference.py --ibm
Then, once the job is done, check and chart the real results:
    python lessons/03_interference/interference.py --job <job-id>
"""

import argparse
import math
import sys
from pathlib import Path

from qiskit import QuantumCircuit

SHOTS = 4000
SEED = 2026
HERE = Path(__file__).parent
DIAL_DEGREES = list(range(0, 361, 30))  # 0, 30, 60, ... 360


# Why the barriers? Before a circuit runs on real hardware it's compiled ("transpiled") for
# that chip, and the compiler is smart: it spots that H followed by H does nothing and deletes
# both, so the chip would just measure a qubit that never moved. A barrier is a "don't merge
# gates across this line" marker, so the real qubit has to do the cancelling itself.


def build_spin_twice() -> QuantumCircuit:
    """Spin the coin, then spin it again. A normal coin would be 50/50. A qubit comes back to 0."""
    qc = QuantumCircuit(1, 1)
    qc.name = "spin-spin"
    qc.h(0)
    qc.barrier()  # stop the compiler from cancelling H-H itself; make the real qubit do it
    qc.h(0)
    qc.measure(0, 0)
    return qc


def build_flip_in_middle() -> QuantumCircuit:
    """Same, but with a Z gate in the middle, which flips the "wave" upside down. Now it comes back to 1."""
    qc = QuantumCircuit(1, 1)
    qc.name = "spin-Z-spin"
    qc.h(0)
    qc.barrier()
    qc.z(0)
    qc.barrier()
    qc.h(0)
    qc.measure(0, 0)
    return qc


def build_peek() -> QuantumCircuit:
    """Same as spin-spin, but we peek (measure) in the middle. Peeking ruins the cancelling: 50/50."""
    qc = QuantumCircuit(1, 2)  # bit 0 = what we saw when we peeked, bit 1 = the final answer
    qc.name = "peek"
    qc.h(0)
    qc.measure(0, 0)  # the peek
    qc.h(0)
    qc.measure(0, 1)  # the final answer
    return qc


def build_dial(degrees: int) -> QuantumCircuit:
    """A "dimmer switch" between the two spins. 0 degrees = full cancel, 180 = Z, 360 = back again."""
    qc = QuantumCircuit(1, 1)
    qc.name = f"dial-{degrees}"
    qc.h(0)
    qc.barrier()
    qc.p(math.radians(degrees), 0)  # phase gate: shifts the wave by this many degrees
    qc.barrier()
    qc.h(0)
    qc.measure(0, 0)
    return qc


def build_ready(bit: int) -> QuantumCircuit:
    """Control: set the qubit to 0 or 1 directly and read it. Measures the readout error alone."""
    qc = QuantumCircuit(1, 1)
    qc.name = f"ready-{bit}"
    if bit:
        qc.x(0)
    qc.measure(0, 0)
    return qc


def all_circuits() -> list[QuantumCircuit]:
    # Order matters: analyze() unpacks them in this order.
    return ([build_spin_twice(), build_flip_in_middle(), build_peek()]
            + [build_dial(d) for d in DIAL_DEGREES]
            + [build_ready(0), build_ready(1)])


def share(counts: dict, want) -> float:
    """Fraction of shots where want(bitstring) is true."""
    total = sum(counts.values())
    return sum(n for bits, n in counts.items() if want(bits)) / total


def theory_dial(degrees: int) -> float:
    """What a perfect machine gives for "chance of reading 1" at this dial setting."""
    return math.sin(math.radians(degrees) / 2) ** 2


def analyze(all_counts: list[dict], real_hardware: bool, where: str) -> bool:
    spin_spin, flip, peek, *dial, ready0, ready1 = all_counts
    # A perfect simulator should hit the exact answer every time; real hardware gets some slack.
    need_exact = 0.90 if real_hardware else 1.0
    lo_peek, hi_peek = (0.40, 0.60) if real_hardware else (0.45, 0.55)
    max_gap = 0.10 if real_hardware else 0.05

    zeros = share(spin_spin, lambda b: b == "0")
    ones = share(flip, lambda b: b == "1")
    peek_zero = share(peek, lambda b: b[0] == "0")  # leftmost character = bit 1 = final answer
    dial_ones = [share(c, lambda b: b == "1") for c in dial]
    gaps = [abs(got - theory_dial(d)) for got, d in zip(dial_ones, DIAL_DEGREES)]

    print(f"Results on {where}, {SHOTS} shots each:")
    print(f"  spin-spin    -> 0 came back {zeros:.1%} of the time (need >= {need_exact:.0%})")
    print(f"  spin-Z-spin  -> 1 came back {ones:.1%} of the time (need >= {need_exact:.0%})")
    print(f"  peek         -> final answer 0 was {peek_zero:.1%} (need {lo_peek:.0%}-{hi_peek:.0%}, a coin flip)")
    print("  dial         -> chance of reading 1 at each setting (measured vs perfect):")
    for d, got in zip(DIAL_DEGREES, dial_ones):
        print(f"       {d:3d} degrees: {got:6.1%}  vs  {theory_dial(d):6.1%}")
    print(f"     biggest gap from perfect: {max(gaps):.1%} (need <= {max_gap:.0%})")
    # Controls: how often the machine misreads a qubit we set directly (no interference involved).
    misread0 = share(ready0, lambda b: b == "1")
    misread1 = share(ready1, lambda b: b == "0")
    print(f"  controls     -> set to 0, read as 1: {misread0:.1%};  set to 1, read as 0: {misread1:.1%}")
    print(f"     (compare: spin-spin missed by {1 - zeros:.1%}, spin-Z-spin missed by {1 - ones:.1%})")

    ok = (zeros >= need_exact and ones >= need_exact
          and lo_peek <= peek_zero <= hi_peek and max(gaps) <= max_gap)
    save_chart(dial_ones, f"The interference dial on {where}",
               HERE / ("hardware_results.png" if real_hardware else "simulator_results.png"))
    print("CHECK PASSED" if ok else "CHECK FAILED")
    return ok


def save_chart(dial_ones: list[float], title: str, path: Path) -> None:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return
    smooth = list(range(0, 361, 2))
    fig, ax = plt.subplots(figsize=(7, 3.6))
    ax.plot(smooth, [theory_dial(d) for d in smooth], color="#c44e52", linestyle="--",
            linewidth=1, label="perfect machine")
    ax.plot(DIAL_DEGREES, dial_ones, "o", color="#4c72b0", label="measured")
    ax.set_xticks(range(0, 361, 60))
    ax.set_xlabel("dial setting (degrees of phase shift between the two spins)")
    ax.set_ylabel("chance of reading 1")
    ax.set_ylim(-0.05, 1.05)
    ax.set_title(title, fontsize=11)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    print(f"Chart saved to {path}")


def run_simulator(circuits: list[QuantumCircuit]) -> list[dict]:
    from qiskit_aer import AerSimulator

    result = AerSimulator().run(circuits, shots=SHOTS, seed_simulator=SEED).result()
    return [result.get_counts(i) for i in range(len(circuits))]


def submit_to_ibm(circuits: list[QuantumCircuit]) -> None:
    from qiskit.transpiler import generate_preset_pass_manager
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2

    service = QiskitRuntimeService()  # reads the saved account; the key is never printed
    backend = service.least_busy(operational=True, simulator=False, min_num_qubits=1)
    # Level 2 makes the compiler choose the qubit with the best measured error rates.
    # (Level 1 put a one-qubit circuit on qubit 0 by default, and our first real run there
    # came out much noisier.) The barriers still stop it from cancelling gates itself.
    pm = generate_preset_pass_manager(backend=backend, optimization_level=2)
    qubit = pm.run(circuits[0]).layout.final_index_layout()[0]
    # Pin every circuit to that same physical qubit, so the controls and the dial are comparable.
    pm = generate_preset_pass_manager(backend=backend, optimization_level=2, initial_layout=[qubit])
    isa = [pm.run(qc) for qc in circuits]
    assert all(c.layout.final_index_layout()[0] == qubit for c in isa), "circuits landed on different qubits"
    job = SamplerV2(mode=backend).run(isa, shots=SHOTS)
    print(f"Submitted {len(circuits)} circuits to {backend.name}, qubit {qubit}. Job ID: {job.job_id()}")
    print(f"When it's done:  python lessons/03_interference/interference.py --job {job.job_id()}")


def fetch_job(job_id: str) -> int:
    from qiskit_ibm_runtime import QiskitRuntimeService

    job = QiskitRuntimeService().job(job_id)
    status = job.status()
    if status != "DONE":
        print(f"Job {job_id} is {status}. Try again later.")
        return 0 if status not in ("ERROR", "CANCELLED") else 1
    all_counts = [r.data.c.get_counts() for r in job.result()]
    return 0 if analyze(all_counts, real_hardware=True, where=job.backend().name) else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--ibm", action="store_true", help="submit to a real IBM quantum computer")
    parser.add_argument("--job", metavar="JOB_ID", help="check and chart a finished hardware job")
    args = parser.parse_args()

    if args.job:
        return fetch_job(args.job)

    circuits = all_circuits()
    for qc in circuits[:4]:  # the dial circuits all look like dial-0, so show just one
        print(f"Circuit '{qc.name}':")
        print(qc.draw(output="text"))

    if args.ibm:
        submit_to_ibm(circuits)
        return 0

    return 0 if analyze(run_simulator(circuits), real_hardware=False, where="the simulator") else 1


if __name__ == "__main__":
    sys.exit(main())
