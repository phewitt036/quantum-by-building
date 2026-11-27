"""Lesson 7, part 2: measure the real link quality of a big group with a phase sweep.

ghz.py's score is a cautious *minimum*. This measures the actual link quality ("GHZ fidelity",
to the nearest GHZ state, allowing any phase twist between all-0s and all-1s) of n qubits:
  - straight: how often all n agree (all 0s or all 1s),
  - a "phase sweep": turn every qubit by the same small angle, then look sideways, at many
    angles. A linked group makes the even-minus-odd count wiggle exactly n times per full
    turn. Only the whole group's all-0s/all-1s link makes that fast a wiggle; groups that
    aren't fully linked can still make a faint one, so we combine its size with the
    all-agree share.

  link quality = (all-agree share) / 2 + (size of the n-times wiggle) / 2
  Above 50% (by more than 2 chance wobbles) proves all n qubits are linked as one group.

    python lessons/07_linking_many/parity_sweep.py            # simulator check
    python lessons/07_linking_many/parity_sweep.py --ibm      # sizes 16 and 20, about 50 s
    python lessons/07_linking_many/parity_sweep.py --ibm --avoid 90   # leave out bad qubits
    python lessons/07_linking_many/parity_sweep.py --job
"""

import argparse
import cmath
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import ghz as L  # noqa: E402  (lesson 7's circuits and helpers)

SIZES = [16, 20]
SHOTS = 2000
SEED = 2026
LAST_JOB = HERE / ".last_parity_job.json"


def angles(n: int) -> list[float]:
    """2n+2 evenly spaced angles around the circle: enough to tell the n-times wiggle apart
    from every slower one."""
    m = 2 * n + 2
    return [2 * math.pi * j / m for j in range(m)]


def build_turned(n: int, phi: float):
    """GHZ, then turn every qubit by phi (a phase turn), then look sideways."""
    from qiskit import QuantumCircuit

    base = L.build_ghz(n, sideways=False)
    qc = QuantumCircuit(n, n, name=f"ghz{n}-phi{phi:.3f}")
    qc.compose(base.remove_final_measurements(inplace=False), inplace=True)
    qc.p(phi, range(n))
    qc.barrier()
    qc.h(range(n))
    qc.measure(range(n), range(n))
    return qc


def circuits_for(sizes) -> list:
    out = []
    for n in sizes:
        out.append(L.build_ghz(n, sideways=False))
        out += [build_turned(n, phi) for phi in angles(n)]
    return out


def quality(counts: list[dict], sizes) -> list[dict]:
    """Turn the counts into link quality per size."""
    res, i = [], 0
    for n in sizes:
        a = L.all_agree(counts[i], n)
        i += 1
        phis = angles(n)
        parities = [L.even_minus_odd(c) for c in counts[i:i + len(phis)]]
        i += len(phis)
        # The n-times wiggle's size: the matching "frequency component" of the sweep.
        wiggle = abs(sum(p * cmath.exp(-1j * n * phi) for p, phi in zip(parities, phis)) / len(phis))
        shots = sum(counts[i - 1].values())
        # Chance wobble (one standard error) of the quality, from the shot counts.
        wob = math.sqrt(a * (1 - a) / shots / 4
                        + sum(1 - p * p for p in parities) / len(parities) / (2 * len(phis) * shots))
        res.append({"n": n, "agree": a, "wiggle": 2 * wiggle, "quality": a / 2 + wiggle,
                    "wobble": wob, "parities": parities, "phis": phis})
    return res


def report(res: list[dict], where: str) -> None:
    print(f"Phase sweep on {where}:")
    for r in res:
        print(f"   {r['n']:2d} qubits: all agree {r['agree']:.1%}, n-times wiggle size {r['wiggle']:.2f}"
              f"  ->  link quality {r['quality']:.1%} ± {r['wobble']:.1%}"
              f"  ({'proven linked' if r['quality'] - 2 * r['wobble'] > 0.5 else 'not proven'})")


def save_chart(res: list[dict], where: str, path: Path) -> None:
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, len(res), figsize=(5 * len(res), 3.4), squeeze=False)
    for ax, r in zip(axes[0], res):
        deg = [math.degrees(p) for p in r["phis"]]
        ax.plot(deg, r["parities"], "o", color="#4c72b0", label="measured")
        fine = [i * 360 / 400 for i in range(401)]
        # best-fitting n-times wiggle, for the eye
        comp = sum(p * cmath.exp(-1j * r["n"] * phi) for p, phi in zip(r["parities"], r["phis"])) / len(r["phis"])
        ax.plot(fine, [2 * abs(comp) * math.cos(r["n"] * math.radians(d) + cmath.phase(comp)) for d in fine],
                color="#c44e52", linewidth=1, label=f"{r['n']}-times wiggle")
        ax.set_title(f"{r['n']} qubits: link quality {r['quality']:.0%}", fontsize=10)
        ax.set_xlabel("turn angle (degrees)")
        ax.set_ylabel("sideways even - odd")
        ax.set_ylim(-1.05, 1.05)
        ax.legend(fontsize=7, loc="lower right")
    fig.suptitle(f"Phase sweep on {where}", fontsize=11)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    print(f"Chart saved to {path}")


def simulate() -> int:
    from qiskit_aer import AerSimulator

    sim = AerSimulator(method="matrix_product_state")
    circs = circuits_for(SIZES)
    r = sim.run(circs, shots=SHOTS, seed_simulator=SEED).result()
    res = quality([r.get_counts(i) for i in range(len(circs))], SIZES)
    report(res, "the perfect simulator")
    save_chart(res, "the perfect simulator", HERE / "parity_simulator_results.png")
    # Second check: a noisy 8-qubit case where the exact answer can be computed directly.
    from qiskit.quantum_info import DensityMatrix, Statevector, state_fidelity
    from qiskit_aer.noise import NoiseModel, depolarizing_error

    n = 8
    nm = NoiseModel()
    nm.add_all_qubit_quantum_error(depolarizing_error(0.03, 2), ["cx"])
    noisy = AerSimulator(method="density_matrix", noise_model=nm)
    small = circuits_for([n])
    r = noisy.run(small, shots=20000, seed_simulator=SEED).result()
    est = quality([r.get_counts(i) for i in range(len(small))], [n])[0]
    bare = L.build_ghz(n, sideways=False).remove_final_measurements(inplace=False)
    with_save = bare.copy()
    with_save.save_density_matrix()
    rho = DensityMatrix(noisy.run(with_save).result().data()["density_matrix"])
    exact = state_fidelity(rho, Statevector(bare))
    print(f"  noisy 8-qubit test: sweep estimate {est['quality']:.1%} ± {est['wobble']:.1%}, "
          f"exact answer {exact:.1%}")

    ok = (all(abs(x["quality"] - 1) < 0.03 for x in res)
          and abs(est["quality"] - exact) < 3 * est["wobble"] + 0.005)
    print("  need: link quality within 3 points of 100% for every size on the perfect simulator, "
          "and the noisy 8-qubit estimate within 3 wobbles of the exact answer")
    print("CHECK PASSED" if ok else "CHECK FAILED")
    return 0 if ok else 1


def submit(avoid=()) -> None:
    from qiskit.transpiler import generate_preset_pass_manager
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2

    backend = QiskitRuntimeService().least_busy(operational=True, simulator=False, min_num_qubits=max(SIZES))
    line = L.best_chain(backend, max(SIZES), avoid=avoid)
    circs = circuits_for(SIZES)
    isa = []
    for qc in circs:
        n = qc.num_qubits
        start = (len(line) - n) // 2
        pm = generate_preset_pass_manager(backend=backend, optimization_level=2,
                                          initial_layout=line[start:start + n])
        isa.append(pm.run(qc))
    sampler = SamplerV2(mode=backend)
    sampler.options.twirling.enable_gates = True
    sampler.options.twirling.enable_measure = True
    job = sampler.run(isa, shots=SHOTS)
    LAST_JOB.write_text(json.dumps({"backend": backend.name, "line": line, "sizes": SIZES,
                                    "job": job.job_id()}))
    print(f"Submitted {len(isa)} circuits to {backend.name} (twirling on), line {line}.")
    print("When done:  python lessons/07_linking_many/parity_sweep.py --job")


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
    sizes = info.get("sizes", SIZES)
    counts = [r.data.c.get_counts() for r in job.result()]
    res = quality(counts, sizes)
    report(res, info["backend"])
    # For comparison: ghz.py's cautious quick score from the same data (angle 0 = plain sideways).
    for r in res:
        a, e0 = r["agree"], r["parities"][0]
        shots = sum(counts[0].values())
        q, w = a + e0 / 2 - 0.5, math.sqrt((a * (1 - a) + (1 - e0 * e0) / 4) / shots)
        print(f"   ({r['n']} qubits, same data, cautious quick score: {q:.1%} ± {w:.1%})")
    save_chart(res, info["backend"], HERE / "parity_hardware_results.png")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--ibm", action="store_true")
    mode.add_argument("--job", action="store_true")
    parser.add_argument("--avoid", type=int, nargs="*", default=[], metavar="QUBIT",
                        help="with --ibm: physical qubits to leave out (e.g. ones weak_link.py flagged)")
    args = parser.parse_args()
    if args.ibm:
        submit(args.avoid)
        return 0
    if args.job:
        return fetch()
    return simulate()


if __name__ == "__main__":
    sys.exit(main())
