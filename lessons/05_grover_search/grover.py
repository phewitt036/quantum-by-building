"""Lesson 5: Grover's search. Find the one prize among identical closed boxes.

Run on the local simulator (free, instant):
    python lessons/05_grover_search/grover.py

Send it to a real IBM quantum computer (needs a saved IBM account, see HARDWARE.md):
    python lessons/05_grover_search/grover.py --ibm
Then, once the job is done, check and chart the real results:
    python lessons/05_grover_search/grover.py --job <job-id>
"""

import argparse
import math
import sys
from pathlib import Path

from qiskit import QuantumCircuit

SHOTS = 4000
SEED = 2026
HERE = Path(__file__).parent
PRIZE_4 = "11"    # the prize box among 4 boxes (2 qubits)
PRIZE_8 = "101"   # the prize box among 8 boxes (3 qubits)
ROUNDS_8 = [0, 1, 2, 3]  # how many "mark and boost" rounds to try with 8 boxes

# Barriers ("don't merge gates across this line") separate the stages. Without them the
# compiler can merge a whole tiny circuit into one block and rebuild it as "just set the
# answer", so the chip would never actually search. Lesson 3 learned this the hard way.


def mark(qc: QuantumCircuit, prize: str) -> None:
    """The oracle: flip the wave of the prize box upside down, leave every other box alone.

    It's a "multi-controlled Z": Z only when every qubit is 1. X gates around it turn
    "every qubit is 1" into "the qubits spell the prize".
    """
    n = qc.num_qubits
    flip = [q for q, bit in enumerate(reversed(prize)) if bit == "0"]  # Qiskit: bit 0 on the right
    if flip:
        qc.x(flip)
    qc.h(n - 1)
    qc.mcx(list(range(n - 1)), n - 1)  # with the H's around it, this acts as a multi-controlled Z
    qc.h(n - 1)
    if flip:
        qc.x(flip)


def boost(qc: QuantumCircuit) -> None:
    """The diffuser: "flip every box around the average". The marked box, now below average,
    gets pushed far above it; the rest shrink a little."""
    n = qc.num_qubits
    qc.h(range(n))
    qc.x(range(n))
    qc.h(n - 1)
    qc.mcx(list(range(n - 1)), n - 1)
    qc.h(n - 1)
    qc.x(range(n))
    qc.h(range(n))


def build_grover(prize: str, rounds: int) -> QuantumCircuit:
    n = len(prize)
    qc = QuantumCircuit(n, n)
    qc.name = f"{n}q-{rounds}rounds"
    qc.h(range(n))  # open every box a crack: all boxes equally likely
    for _ in range(rounds):
        qc.barrier()
        mark(qc, prize)
        qc.barrier()
        boost(qc)
    qc.barrier()
    qc.measure(range(n), range(n))
    return qc


def build_ready(prize: str) -> QuantumCircuit:
    """Control: set the qubits straight to the prize and read them. Measures readout error alone."""
    n = len(prize)
    qc = QuantumCircuit(n, n)
    qc.name = f"ready-{prize}"
    ones = [q for q, bit in enumerate(reversed(prize)) if bit == "1"]
    if ones:
        qc.x(ones)
    qc.measure(range(n), range(n))
    return qc


def all_circuits() -> list[QuantumCircuit]:
    # Order matters: analyze() unpacks them in this order.
    return ([build_grover(PRIZE_4, 1)]
            + [build_grover(PRIZE_8, k) for k in ROUNDS_8]
            + [build_ready(PRIZE_8)])


def theory(n_boxes: int, rounds: int) -> float:
    """Chance of finding the prize on a perfect machine after this many rounds."""
    angle = math.asin(1 / math.sqrt(n_boxes))
    return math.sin((2 * rounds + 1) * angle) ** 2


def strictly_top(counts: dict, bits: str) -> bool:
    """True only if `bits` came up more often than every other answer (a tie doesn't count)."""
    mine = counts.get(bits, 0)
    return all(n < mine for b, n in counts.items() if b != bits)


def share(counts: dict, bits: str) -> float:
    return counts.get(bits, 0) / sum(counts.values())


def analyze(all_counts: list[dict], real_hardware: bool, where: str) -> bool:
    four, *eight, ready = all_counts
    found4 = share(four, PRIZE_4)
    found8 = [share(c, PRIZE_8) for c in eight]
    top8 = [max(c, key=c.get) for c in eight]
    readout_ok = share(ready, PRIZE_8)

    print(f"Results on {where}, {SHOTS} shots each:")
    print(f"  4 boxes, 1 round  -> prize {PRIZE_4} found {found4:.1%} "
          f"(perfect: {theory(4, 1):.0%}; guessing: 25%)")
    print(f"  8 boxes (prize {PRIZE_8}; guessing: 12.5%):")
    for k, got, top in zip(ROUNDS_8, found8, top8):
        print(f"     {k} rounds: prize found {got:6.1%}  vs perfect {theory(8, k):6.1%}"
              f"   (most common answer: {top})")
    print(f"  control      -> set straight to {PRIZE_8} and read: correct {readout_ok:.1%}")

    if real_hardware:
        # Noisy hardware: the search must still clearly work, not match the perfect numbers.
        ok = (strictly_top(four, PRIZE_4) and strictly_top(eight[2], PRIZE_8)
              and found8[2] > max(found8[0], found8[1], found8[3]))
        print("  need: prize is the clear top answer (no ties) for 4 boxes and for 8 boxes at "
              "2 rounds, and 2 rounds beats 0, 1 and 3 rounds")
    else:
        gaps = [abs(got - theory(8, k)) for got, k in zip(found8, ROUNDS_8)]
        ok = found4 == 1.0 and found8[2] >= 0.90 and max(gaps) <= 0.03
        print(f"  need: 4 boxes 100%, 8 boxes at 2 rounds >= 90%, every round within 3 points "
              f"of perfect (biggest gap {max(gaps):.1%})")

    save_chart(found8, f"Grover's search, 8 boxes, on {where}",
               HERE / ("hardware_results.png" if real_hardware else "simulator_results.png"))
    print("CHECK PASSED" if ok else "CHECK FAILED")
    return ok


def save_chart(found8: list[float], title: str, path: Path) -> None:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return
    fig, ax = plt.subplots(figsize=(6.5, 3.6))
    x = list(range(len(ROUNDS_8)))
    ax.bar([i - 0.2 for i in x], [theory(8, k) for k in ROUNDS_8], width=0.4,
           color="#dddddd", edgecolor="#999999", label="perfect machine")
    ax.bar([i + 0.2 for i in x], found8, width=0.4, color="#4c72b0", label="measured")
    ax.axhline(1 / 8, color="#c44e52", linestyle="--", linewidth=1, label="blind guess (1 in 8)")
    ax.set_xticks(x, [f"{k} rounds" for k in ROUNDS_8])
    ax.set_ylabel(f"chance of finding the prize ({PRIZE_8})")
    ax.set_ylim(0, 1.05)
    ax.set_title(title, fontsize=11)
    ax.legend(fontsize=8, loc="upper left")
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    print(f"Chart saved to {path}")


def run_simulator(circuits: list[QuantumCircuit]) -> list[dict]:
    from qiskit_aer import AerSimulator

    result = AerSimulator().run(circuits, shots=SHOTS, seed_simulator=SEED).result()
    return [result.get_counts(i) for i in range(len(circuits))]


def compile_for(backend, circuits: list[QuantumCircuit]) -> list[QuantumCircuit]:
    """Compile for the chip. All 8-box circuits share the same 3 physical qubits."""
    from qiskit.transpiler import generate_preset_pass_manager

    pm = generate_preset_pass_manager(backend=backend, optimization_level=2)
    four = pm.run(circuits[0])
    qubits = pm.run(circuits[3]).layout.final_index_layout()  # pick qubits for 2 rounds
    pinned = generate_preset_pass_manager(backend=backend, optimization_level=2,
                                          initial_layout=qubits)
    return [four] + [pinned.run(qc) for qc in circuits[1:]]


def submit_to_ibm(circuits: list[QuantumCircuit]) -> None:
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2

    service = QiskitRuntimeService()  # reads the saved account; the key is never printed
    backend = service.least_busy(operational=True, simulator=False, min_num_qubits=3)
    isa = compile_for(backend, circuits)
    for qc, c in zip(circuits, isa):
        print(f"  {qc.name:12s} -> {c.count_ops().get('cz', 0):3d} two-qubit gates on qubits "
              f"{c.layout.final_index_layout()}")
    job = SamplerV2(mode=backend).run(isa, shots=SHOTS)
    print(f"Submitted {len(isa)} circuits to {backend.name}. Job ID: {job.job_id()}")
    print(f"When it's done:  python lessons/05_grover_search/grover.py --job {job.job_id()}")


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
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--ibm", action="store_true", help="submit to a real IBM quantum computer")
    mode.add_argument("--job", metavar="JOB_ID", help="check and chart a finished hardware job")
    args = parser.parse_args()

    if args.job:
        return fetch_job(args.job)

    circuits = all_circuits()
    for qc in (circuits[0], circuits[2]):  # 4 boxes, and 8 boxes with 1 round
        print(f"Circuit '{qc.name}':")
        print(qc.draw(output="text", fold=-1))

    if args.ibm:
        submit_to_ibm(circuits)
        return 0

    return 0 if analyze(run_simulator(circuits), real_hardware=False, where="the simulator") else 1


if __name__ == "__main__":
    sys.exit(main())
