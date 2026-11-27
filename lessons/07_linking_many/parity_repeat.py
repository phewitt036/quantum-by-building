"""Lesson 7, part 3: repeat the 16-qubit phase sweep, with a built-in "known unlinked" control.

Repeats run 5 (parity_sweep.py) for 16 qubits on the SAME machine and SAME physical qubits,
with the same twirling settings. In the same job, every circuit also runs a second time with
a Z gate on one qubit right after the linking. That flips the sign of the whole-group link, so
pooling the shots with and without the Z cancels it exactly: the pooled results come from a
plain mix of "all 0s" and "all 1s" with no quantum link at all. It's a control: its n-times
wiggle should vanish and it must not come out "proven".

    python lessons/07_linking_many/parity_repeat.py           # simulator check
    python lessons/07_linking_many/parity_repeat.py --ibm     # about 45 s of quantum time
    python lessons/07_linking_many/parity_repeat.py --job
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import ghz as L  # noqa: E402
import parity_sweep as P  # noqa: E402

N = 16
SHOTS = 2000  # same as run 5
SEED = 2026
# Run 5's machine and physical qubits, from the published data (not from a local job file,
# which a later run can overwrite).
ORIGINAL = HERE / "data" / "run5_sweep_marrakesh.json"
CONTROL_WIGGLE_MAX = 0.05  # the control's 16-times wiggle must stay below this (simulator and hardware)
LAST_JOB = HERE / ".last_repeat_job.json"


def circuits(n: int = N) -> list:
    """Interleaved: [straight, straight+Z, angle0, angle0+Z, angle1, angle1+Z, ...]."""
    from qiskit import QuantumCircuit

    plain = [L.build_ghz(n, sideways=False)] + [P.build_turned(n, phi) for phi in P.angles(n)]
    out = []
    for qc in plain:
        z = qc.copy_empty_like(name=qc.name + "+Z")
        linked = False
        for inst in qc.data:
            # Insert the Z after the last linking CNOT, before anything else happens.
            if not linked and inst.operation.name in ("p", "barrier", "h", "measure") and any(
                    i.operation.name == "cx" for i in z.data):
                z.z(0)
                linked = True
            z.append(inst)
        out += [qc, z]
    return out


def pooled_and_plain(counts: list[dict]):
    plain = counts[0::2]
    pooled = [Counter(a) + Counter(b) for a, b in zip(counts[0::2], counts[1::2])]
    return plain, [dict(c) for c in pooled]


def report(counts: list[dict], where: str) -> list[dict]:
    plain, pooled = pooled_and_plain(counts)
    rep = P.quality(plain, [N])[0]
    ctl = P.quality(pooled, [N])[0]
    print(f"Repeat on {where}, {N} qubits:")
    print(f"   repeat:  all agree {rep['agree']:.1%}, wiggle size {rep['wiggle']:.3f}  ->  "
          f"link quality {rep['quality']:.1%}, cautious lower bound {rep['lower']:.1%}  "
          f"({'proven' if rep['lower'] > 0.5 else 'not proven'})")
    print(f"   control: all agree {ctl['agree']:.1%}, wiggle size {ctl['wiggle']:.3f}  ->  "
          f"link quality {ctl['quality']:.1%}, cautious lower bound {ctl['lower']:.1%}  "
          f"({'proven' if ctl['lower'] > 0.5 else 'not proven'})  [should be NOT proven, wiggle ~0]")
    return [rep, ctl]


def simulate() -> int:
    from qiskit_aer import AerSimulator

    circs = circuits()
    r = AerSimulator(method="matrix_product_state").run(circs, shots=SHOTS, seed_simulator=SEED).result()
    rep, ctl = report([r.get_counts(i) for i in range(len(circs))], "the perfect simulator")
    ok = rep["lower"] > 0.95 and ctl["lower"] < 0.5 and ctl["wiggle"] < CONTROL_WIGGLE_MAX
    print(f"  need: repeat proven (lower bound > 95%); control not proven, with its wiggle under {CONTROL_WIGGLE_MAX}")
    print("CHECK PASSED" if ok else "CHECK FAILED")
    return 0 if ok else 1


def original_layout():
    """Backend and physical qubits (in virtual-qubit order) used for 16 qubits in run 5."""
    from qiskit_ibm_runtime import QiskitRuntimeService

    data = json.loads(ORIGINAL.read_text())
    group = next(g for g in data["groups"] if g["qubits_n"] == N)
    return QiskitRuntimeService(), data["backend"], group["physical_qubits"]


def submit(dry_run: bool) -> None:
    from qiskit.transpiler import generate_preset_pass_manager
    from qiskit_ibm_runtime import SamplerV2

    service, name, layout = original_layout()
    backend = service.backend(name)
    pm = generate_preset_pass_manager(backend=backend, optimization_level=2, initial_layout=layout)
    isa = [pm.run(qc) for qc in circuits()]
    sets = {frozenset(L.measured_qubits(c)) for c in isa}
    if sets != {frozenset(layout)}:
        raise SystemExit("Some circuits didn't land on the original qubits; not submitting.")
    print(f"{len(isa)} circuits x {SHOTS} shots on {name}, original qubits {layout}")
    if dry_run:
        return
    sampler = SamplerV2(mode=backend)
    sampler.options.twirling.enable_gates = True    # same settings as run 5
    sampler.options.twirling.enable_measure = True
    job = sampler.run(isa, shots=SHOTS)
    LAST_JOB.write_text(json.dumps({"backend": name, "layout": layout, "job": job.job_id()}))
    print("Submitted. When done:  python lessons/07_linking_many/parity_repeat.py --job")


def fetch() -> int:
    from qiskit_ibm_runtime import QiskitRuntimeService

    if not LAST_JOB.exists():
        print("No saved job. Run with --ibm first.")
        return 1
    info = json.loads(LAST_JOB.read_text())
    job = QiskitRuntimeService().job(info["job"])
    if job.status() != "DONE":
        print(f"Job is {job.status()}. Try again later.")
        return 0
    ran = [item.circuit for item in job.inputs["quantum_program"].items]
    same = len({frozenset(L.measured_qubits(c)) for c in ran}) == 1
    print(f"All {len(ran)} circuits read the same physical qubits: {'yes' if same else 'NO - not valid'}")
    rep, ctl = report([r.data.c.get_counts() for r in job.result()], info["backend"])
    control_ok = ctl["lower"] < 0.5 and ctl["wiggle"] < CONTROL_WIGGLE_MAX
    print(f"   control behaved (not proven, wiggle under {CONTROL_WIGGLE_MAX}): {'yes' if control_ok else 'NO'}")
    ok = same and rep["lower"] > 0.5 and control_ok
    print(f"  need: same qubits throughout; repeat proven; control not proven with its wiggle under {CONTROL_WIGGLE_MAX}")
    print("CHECK PASSED" if ok else "CHECK FAILED")
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--ibm", action="store_true")
    mode.add_argument("--dry-run", action="store_true", help="compile for the original qubits, don't submit")
    mode.add_argument("--job", action="store_true")
    args = parser.parse_args()
    if args.ibm or args.dry_run:
        submit(dry_run=args.dry_run)
        return 0
    if args.job:
        return fetch()
    return simulate()


if __name__ == "__main__":
    sys.exit(main())
