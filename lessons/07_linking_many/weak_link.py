"""Lesson 7, diagnostic: find the weak link in the hand-picked line of qubits.

After `ghz.py --ibm --chain`, this tests the same line piece by piece:
  - every neighbouring pair gets its own two-coin link test (lesson 1, scored as in lesson 6),
  - every qubit gets a reading test (set all to 0 and read; set all to 1 and read).

    python lessons/07_linking_many/weak_link.py --ibm    # one job, about 30 seconds
    python lessons/07_linking_many/weak_link.py --job    # report when done
"""

import argparse
import json
import sys
from pathlib import Path

from qiskit import QuantumCircuit

HERE = Path(__file__).parent
CHAIN_JOB = HERE / ".last_job.json"         # written by ghz.py --ibm --chain
LAST_JOB = HERE / ".last_weak_link_job.json"
SHOTS = 1000


def pair_circuit(sideways: bool) -> QuantumCircuit:
    qc = QuantumCircuit(2, 2)
    qc.h(0)
    qc.cx(0, 1)
    qc.barrier()
    if sideways:
        qc.h([0, 1])
    qc.measure([0, 1], [0, 1])
    return qc


def readout_circuit(n: int, ones: bool) -> QuantumCircuit:
    qc = QuantumCircuit(n, n)
    if ones:
        qc.x(range(n))
    qc.measure(range(n), range(n))
    return qc


def submit() -> None:
    from qiskit.transpiler import generate_preset_pass_manager
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2

    info = json.loads(CHAIN_JOB.read_text())
    line = info.get("chain")
    if not line:
        raise SystemExit("Run ghz.py --ibm --chain first.")
    backend = QiskitRuntimeService().backend(info["backend"])
    isa = []
    for a, b in zip(line, line[1:]):
        pm = generate_preset_pass_manager(backend=backend, optimization_level=2, initial_layout=[a, b])
        isa += [pm.run(pair_circuit(False)), pm.run(pair_circuit(True))]
    pm = generate_preset_pass_manager(backend=backend, optimization_level=2, initial_layout=line)
    isa += [pm.run(readout_circuit(len(line), False)), pm.run(readout_circuit(len(line), True))]
    job = SamplerV2(mode=backend).run(isa, shots=SHOTS)
    LAST_JOB.write_text(json.dumps({"backend": backend.name, "line": line, "job": job.job_id()}))
    print(f"Submitted {len(isa)} circuits to {backend.name}.")
    print("When done:  python lessons/07_linking_many/weak_link.py --job")


def fetch() -> int:
    from qiskit_ibm_runtime import QiskitRuntimeService

    info = json.loads(LAST_JOB.read_text())
    service = QiskitRuntimeService()
    job = service.job(info["job"])
    if job.status() != "DONE":
        print(f"Job is {job.status()}. Try again later.")
        return 0
    line = info["line"]
    counts = [r.data.c.get_counts() for r in job.result()]
    props = service.backend(info["backend"]).properties()

    def agree(c):
        t = sum(c.values())
        return (c.get("00", 0) + c.get("11", 0)) / t

    print(f"Weak-link test on {info['backend']}, {SHOTS} shots per circuit")
    print("Pair link scores (100% perfect; above 75% proves a quantum link):")
    pair_scores = []
    for i, (a, b) in enumerate(zip(line, line[1:])):
        s = (agree(counts[2 * i]) + agree(counts[2 * i + 1])) / 2
        pair_scores.append((s, a, b, i))
        flag = "   <-- weak" if s < 0.9 else ""
        print(f"   position {i:2d}-{i + 1:2d}  qubits {a:3d}-{b:3d}: {s:6.1%}{flag}")

    zeros, ones = counts[-2], counts[-1]
    n = len(line)

    def bit_ok(c, pos, want):
        t = sum(c.values())
        return sum(v for bits, v in c.items() if bits[n - 1 - pos] == want) / t

    print("Reading test per qubit (correct when set to 0 / set to 1; IBM's published readout error):")
    for pos, q in enumerate(line):
        z, o = bit_ok(zeros, pos, "0"), bit_ok(ones, pos, "1")
        flag = "   <-- weak" if min(z, o) < 0.9 else ""
        print(f"   position {pos:2d}  qubit {q:3d}: {z:6.1%} / {o:6.1%}   (published {props.readout_error(q):.1%}){flag}")
    worst = sorted(pair_scores)[:3]
    print("Weakest pairs: " + ", ".join(f"{a}-{b} ({s:.1%}, position {i})" for s, a, b, i in worst))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--ibm", action="store_true")
    mode.add_argument("--job", action="store_true")
    args = parser.parse_args()
    if args.ibm:
        submit()
        return 0
    return fetch()


if __name__ == "__main__":
    sys.exit(main())
