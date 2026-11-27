"""Lesson 6: real machines are noisy. Watch noise pile up, and try three ways to fight it.

Run on the local simulators (free, instant): a perfect one, and a "noisy" one that copies
the published error rates of IBM's ibm_marrakesh chip:
    python lessons/06_noise/noise.py

Send it to a real IBM quantum computer (four jobs: IBM's two noise reducers off, each alone, both):
    python lessons/06_noise/noise.py --ibm
Then, once the jobs are done, check and chart the real results:
    python lessons/06_noise/noise.py --job
"""

import argparse
import json
import math
import sys
from pathlib import Path

from qiskit import QuantumCircuit

SHOTS = 4000
SEED = 2026
HERE = Path(__file__).parent
LAST_JOB = HERE / ".last_job.json"  # job IDs + qubits from the last --ibm run (not committed)
PAIRS = [0, 5, 10, 20, 40, 80]  # how many "do-nothing" CNOT pairs to add
# The same circuits, sent as four jobs: IBM's two noise reducers off, each one alone, and both.
VARIANTS = {
    "plain": {"dd": False, "twirl": False, "label": "plain"},
    "dd": {"dd": True, "twirl": False, "label": "dynamical decoupling only"},
    "twirl": {"dd": False, "twirl": True, "label": "twirling only"},
    "both": {"dd": True, "twirl": True, "label": "both reducers on"},
}


def build_bell(pairs: int, sideways: bool) -> QuantumCircuit:
    """Lesson 1's magic coins, plus `pairs` pairs of CNOTs that cancel out (so, in theory, nothing)."""
    qc = QuantumCircuit(2, 2)
    qc.name = f"{pairs}pairs-{'sideways' if sideways else 'straight'}"
    qc.h(0)
    qc.cx(0, 1)
    for _ in range(pairs):
        # Two CNOTs in a row undo each other. The barriers stop the compiler from deleting
        # them (lesson 3), so the chip really runs every one.
        qc.barrier()
        qc.cx(0, 1)
        qc.barrier()
        qc.cx(0, 1)
    qc.barrier()
    if sideways:
        qc.h([0, 1])
    qc.measure([0, 1], [0, 1])
    return qc


def build_ready(bits: str) -> QuantumCircuit:
    """Control: set the two qubits straight to `bits` and read them. Measures readout error."""
    qc = QuantumCircuit(2, 2)
    qc.name = f"ready-{bits}"
    for q, b in enumerate(reversed(bits)):  # Qiskit: bit 0 on the right
        if b == "1":
            qc.x(q)
    qc.measure([0, 1], [0, 1])
    return qc


READY = ["00", "01", "10", "11"]


def all_circuits() -> list[QuantumCircuit]:
    # Order matters: analyze() unpacks them in this order.
    bells = [build_bell(p, s) for p in PAIRS for s in (False, True)]
    return bells + [build_ready(b) for b in READY]


# ---------- turning counts into a score ----------

def probs(counts: dict) -> dict:
    total = sum(counts.values())
    return {b: counts.get(b, 0) / total for b in READY}


def readout_matrix(ready_counts: list[dict]) -> list[list[float]]:
    """M[read][set]: how often we read `read` when the qubits were set to `set`."""
    cols = [probs(c) for c in ready_counts]
    return [[cols[j][READY[i]] for j in range(4)] for i in range(4)]


def solve(m: list[list[float]], v: list[float]) -> list[float]:
    """Solve m·x = v (4×4) by Gaussian elimination. Tiny, so no numpy needed."""
    a = [row[:] + [v[i]] for i, row in enumerate(m)]
    n = len(a)
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(a[r][col]))
        a[col], a[piv] = a[piv], a[col]
        for r in range(n):
            if r != col:
                f = a[r][col] / a[col][col]
                a[r] = [x - f * y for x, y in zip(a[r], a[col])]
    return [a[i][n] / a[i][i] for i in range(n)]


def correct_readout(p: dict, m: list[list[float]]) -> dict:
    """Undo known misreads: find the true odds that, after misreading, give what we saw.
    Small negative results (from shot noise) are clipped to 0 and the rest rescaled."""
    x = [max(0.0, v) for v in solve(m, [p[b] for b in READY])]
    total = sum(x)
    return {b: v / total for b, v in zip(READY, x)}


def agreement(p: dict) -> float:
    return p["00"] + p["11"]


def scores(bell_counts: list[dict], m=None) -> list[float]:
    """Agreement score per depth: average of straight and sideways matching.
    Perfect magic coins score 100%. Above 75% proves the coins are still quantum-linked (no
    pair of pre-agreed ordinary coins can match that often both ways). 50% = no matching at all."""
    out = []
    for i in range(len(PAIRS)):
        ps = [probs(c) for c in bell_counts[2 * i: 2 * i + 2]]
        if m is not None:
            ps = [correct_readout(p, m) for p in ps]
        out.append(sum(agreement(p) for p in ps) / 2)
    return out


def loss_per_cnot(sc: list[float]) -> float:
    """Fit score - 50% = A·r^n (n = extra CNOTs) and return 1 - r: the share of the remaining
    agreement (above coin-flip level) lost per extra CNOT. Uses points clearly above 50%.
    Only meaningful when the fade is steady; for an accelerating fade it's a rough average."""
    pts = [(2 * p, math.log(s - 0.5)) for p, s in zip(PAIRS, sc) if s - 0.5 > 0.02]
    if len(pts) < 2:
        return float("nan")
    n = len(pts)
    mx = sum(x for x, _ in pts) / n
    my = sum(y for _, y in pts) / n
    slope = sum((x - mx) * (y - my) for x, y in pts) / sum((x - mx) ** 2 for x, _ in pts)
    return 1 - math.exp(slope)


# ---------- report ----------

def report(label: str, bell_counts: list[dict], ready_counts: list[dict]) -> dict:
    m = readout_matrix(ready_counts)
    raw = scores(bell_counts)
    fixed = scores(bell_counts, m)
    misread = 1 - sum(m[i][i] for i in range(4)) / 4
    print(f"  {label}:")
    print(f"     average misread on the 4 controls: {misread:.1%}")
    print("     extra CNOTs:     " + "".join(f"{2 * p:>7d}" for p in PAIRS))
    print("     agreement:       " + "".join(f"{s:7.1%}" for s in raw))
    print("     misreads undone: " + "".join(f"{s:7.1%}" for s in fixed))
    lpc = loss_per_cnot(fixed)
    print(f"     agreement lost per extra CNOT (after undoing misreads; rough if the fade isn't steady): {lpc:.2%}")
    return {"raw": raw, "fixed": fixed, "misread": misread, "loss_per_cnot": lpc}


def save_chart(series: dict, title: str, path: Path) -> None:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return
    x = [2 * p for p in PAIRS]
    fig, ax = plt.subplots(figsize=(7, 3.8))
    styles = {"perfect simulator": ("#999999", "--", "none"),
              "plain": ("#4c72b0", "-", "o"),
              "plain, misreads undone": ("#4c72b0", ":", "s"),
              "dynamical decoupling only": ("#55a868", "-", "^"),
              "twirling only": ("#8172b3", "-", "v"),
              "both reducers on": ("#dd8452", "-", "o")}
    for name, ys in series.items():
        color, ls, marker = styles.get(name, ("#55a868", "-", "o"))
        ax.plot(x, ys, color=color, linestyle=ls, marker=marker, label=name)
    ax.axhline(0.75, color="#555555", linewidth=1, linestyle="-.",
               label="above 75% = provably linked (unlinked qubits can't exceed it)")
    ax.axhline(0.5, color="#c44e52", linewidth=1, linestyle="--",
               label="independent coin flips (50%)")
    ax.set_xlabel("extra do-nothing CNOT gates")
    ax.set_ylabel("agreement score")
    ax.set_ylim(0.45, 1.02)
    ax.set_title(title, fontsize=11)
    ax.legend(fontsize=7, loc="lower left")
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    print(f"Chart saved to {path}")


# ---------- simulators ----------

def run(sim, circuits) -> list[dict]:
    result = sim.run(circuits, shots=SHOTS, seed_simulator=SEED).result()
    return [result.get_counts(i) for i in range(len(circuits))]


def simulate() -> int:
    from qiskit_aer import AerSimulator
    from qiskit_ibm_runtime.fake_provider import FakeMarrakesh

    circuits = all_circuits()
    n_bell = 2 * len(PAIRS)

    perfect = run(AerSimulator(), circuits)
    ideal = scores(perfect[:n_bell])

    fake = FakeMarrakesh()
    isa = compile_for(fake, circuits)
    noisy = run(AerSimulator.from_backend(fake), isa)

    print(f"Simulators, {SHOTS} shots each:")
    print("  perfect simulator agreement: " + " ".join(f"{s:.1%}" for s in ideal))
    r = report("noisy simulator (copies ibm_marrakesh's published error rates)",
               noisy[:n_bell], noisy[n_bell:])
    save_chart({"perfect simulator": ideal, "plain": r["raw"],
                "plain, misreads undone": r["fixed"]},
               "Noise piling up (noisy simulator based on ibm_marrakesh)",
               HERE / "simulator_results.png")

    ok = (all(math.isclose(s, 1.0) for s in ideal)                       # the pairs really do nothing
          and r["raw"][-1] < r["raw"][0] - 0.05                # noise grows with more gates
          and r["fixed"][0] > r["raw"][0])                     # undoing misreads raises it
    print("  need: perfect simulator 100% at every depth; noisy score drops by more than "
          "5 points from 0 to 160 CNOTs; undoing misreads raises the starting score")
    print("CHECK PASSED" if ok else "CHECK FAILED")
    return 0 if ok else 1


# ---------- real hardware ----------

def compile_for(backend, circuits):
    """Compile, with every circuit on the same two physical qubits."""
    from qiskit.transpiler import generate_preset_pass_manager

    pm = generate_preset_pass_manager(backend=backend, optimization_level=2)
    qubits = pm.run(circuits[0]).layout.final_index_layout()
    pinned = generate_preset_pass_manager(backend=backend, optimization_level=2,
                                          initial_layout=qubits)
    return [pinned.run(qc) for qc in circuits]


def submit_to_ibm() -> None:
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2

    service = QiskitRuntimeService()  # reads the saved account; the key is never printed
    backend = service.least_busy(operational=True, simulator=False, min_num_qubits=2)
    circuits = all_circuits()
    isa = compile_for(backend, circuits)
    qubits = isa[0].layout.final_index_layout()
    deepest = isa[2 * len(PAIRS) - 1]
    two_q = sum(n for op, n in deepest.count_ops().items() if op in ("cz", "ecr", "cx"))
    print(f"Using qubits {qubits} on {backend.name}. Deepest circuit has {two_q} two-qubit gates.")

    job_ids = {}
    for key, v in VARIANTS.items():
        sampler = SamplerV2(mode=backend)
        sampler.options.dynamical_decoupling.enable = v["dd"]  # keep idle qubits "busy"
        sampler.options.twirling.enable_gates = v["twirl"]     # scramble errors into plain noise
        sampler.options.twirling.enable_measure = v["twirl"]
        job_ids[key] = sampler.run(isa, shots=SHOTS).job_id()

    LAST_JOB.write_text(json.dumps({"backend": backend.name, "qubits": qubits, **job_ids}))
    print(f"Submitted {len(job_ids)} jobs of {len(isa)} circuits each.")
    print("When they're all done:  python lessons/06_noise/noise.py --job")


def fetch_jobs() -> int:
    from qiskit_ibm_runtime import QiskitRuntimeService

    if not LAST_JOB.exists():
        print("No saved job. Run with --ibm first.")
        return 1
    info = json.loads(LAST_JOB.read_text())
    service = QiskitRuntimeService()
    jobs = {k: service.job(info[k]) for k in VARIANTS if k in info}
    for k, job in jobs.items():
        status = job.status()
        if status != "DONE":
            print(f"The {k} job is {status}. Try again later.")
            return 0 if status not in ("ERROR", "CANCELLED") else 1

    n_bell = 2 * len(PAIRS)
    backend = service.backend(info["backend"])
    q = info["qubits"]
    gate = next((g for g in ("cz", "ecr", "cx") if g in backend.target.operation_names), None)
    table = backend.target[gate] if gate else {}
    cz_error = table.get(tuple(q)) or table.get(tuple(reversed(q)))
    print(f"Results on {info['backend']}, qubits {q}, {SHOTS} shots each:")
    if cz_error is not None and cz_error.error is not None:
        print(f"  IBM's published error for one two-qubit gate on these qubits: {cz_error.error:.2%}")

    results = {}
    for k, job in jobs.items():
        counts = [r.data.c.get_counts() for r in job.result()]
        results[k] = report(VARIANTS[k]["label"], counts[:n_bell], counts[n_bell:])

    series = {VARIANTS[k]["label"]: results[k]["raw"] for k in results}
    save_chart(series, f"Noise piling up on {info['backend']}, qubits {q}",
               HERE / "hardware_results.png")

    p = results["plain"]
    ok = (p["raw"][0] >= 0.85                      # the magic coins work at the start
          and p["raw"][-1] < p["raw"][0] - 0.05    # and noise visibly grows with more gates
          and p["fixed"][0] > p["raw"][0])         # undoing misreads raises it
    print("  need: plain score >= 85% with no extra gates, dropping by more than 5 points by "
          "160 extra gates, and undoing misreads raises the starting score")
    print("CHECK PASSED" if ok else "CHECK FAILED")
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--ibm", action="store_true", help="submit the four jobs to a real IBM machine")
    mode.add_argument("--job", action="store_true", help="check and chart the last submitted jobs")
    args = parser.parse_args()

    if args.job:
        return fetch_jobs()
    print(build_bell(1, False).draw(output="text"))
    if args.ibm:
        submit_to_ibm()
        return 0
    return simulate()


if __name__ == "__main__":
    sys.exit(main())
