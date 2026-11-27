"""Lesson 7: how many qubits can we link? Lesson 1's magic coins, but a whole row of them.

Run on the local simulators (free): a perfect one, and a noisy copy of ibm_marrakesh:
    python lessons/07_linking_many/ghz.py

Send it to a real IBM quantum computer (two jobs: plain, and with twirling on):
    python lessons/07_linking_many/ghz.py --ibm
Then, once both are done, check and chart the real results:
    python lessons/07_linking_many/ghz.py --job
Add --chain to --ibm to use one hand-picked best line of qubits and go up to 40.
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
SIZES = [2, 4, 8, 12, 16, 20, 24, 28]  # how many qubits to link
SIM_SIZES = [2, 4, 8, 12]  # the noisy simulator gets slow beyond this
CHAIN_SIZES = [4, 8, 12, 16, 20, 24, 28, 32, 40]  # sizes for the hand-picked-chain run


def build_ghz(n: int, sideways: bool) -> QuantumCircuit:
    """Link n qubits so they all agree: all 0s or all 1s (a "GHZ state").

    Start in the middle and spread the link outward in both directions at once, like
    passing a message down a line from the centre. That takes about n/2 steps instead of n.
    """
    qc = QuantumCircuit(n, n)
    qc.name = f"ghz{n}-{'sideways' if sideways else 'straight'}"
    mid = n // 2
    qc.h(mid)
    left, right = mid, mid
    while left > 0 or right < n - 1:
        if right < n - 1:
            qc.cx(right, right + 1)
            right += 1
        if left > 0:
            qc.cx(left, left - 1)
            left -= 1
    qc.barrier()  # keep the "sideways" turn separate from the linking
    if sideways:
        qc.h(range(n))
    qc.measure(range(n), range(n))
    return qc


def circuits_for(sizes) -> list[QuantumCircuit]:
    return [build_ghz(n, s) for n in sizes for s in (False, True)]


# ---------- scoring ----------

def all_agree(counts: dict, n: int) -> float:
    """Straight: share of shots where every qubit agreed (all 0s or all 1s)."""
    total = sum(counts.values())
    return (counts.get("0" * n, 0) + counts.get("1" * n, 0)) / total


def even_minus_odd(counts: dict) -> float:
    """Sideways: (share with an even number of 1s) minus (share with an odd number).
    For a perfect GHZ state measured sideways, every shot has an even number of 1s: +1."""
    total = sum(counts.values())
    return sum(n if bits.count("1") % 2 == 0 else -n for bits, n in counts.items()) / total


def link_score(straight: dict, sideways: dict, n: int) -> float:
    """A guaranteed-minimum score for how well all n qubits are linked.

    score = all-agree share + half the sideways even-minus-odd - 1/2.
    On a perfect machine it's 1. The real link quality (the "GHZ fidelity") is always at least
    this big, so a score above 0.5 proves all n qubits are linked as one group, not just in
    smaller pieces. (This is a standard test, the Toth-Guhne entanglement witness. The simpler
    average of the two numbers is NOT a safe minimum: in the sideways test, other combinations
    of qubits can leak in and make it look better than it is.) It can go below 0, which just
    means "this test proves nothing".
    """
    return all_agree(straight, n) + even_minus_odd(sideways) / 2 - 0.5


def score_wobble(straight: dict, sideways: dict, n: int) -> float:
    """How much the link score wobbles from chance alone (one standard error), given the shots."""
    a, e = all_agree(straight, n), even_minus_odd(sideways)
    shots = sum(straight.values())
    return math.sqrt((a * (1 - a) + (1 - e * e) / 4) / shots)


def analyze(counts: list[dict], sizes, label: str) -> list[float]:
    out, wob = [], []
    print(f"  {label}:")
    print("     qubits:          " + "".join(f"{n:>7d}" for n in sizes))
    ag, eo = [], []
    for i, n in enumerate(sizes):
        st, sw = counts[2 * i], counts[2 * i + 1]
        ag.append(all_agree(st, n))
        eo.append(even_minus_odd(sw))
        out.append(link_score(st, sw, n))
        wob.append(score_wobble(st, sw, n))
    print("     all agree:       " + "".join(f"{v:7.1%}" for v in ag))
    print("     sideways even-odd:" + "".join(f"{v:7.2f}" for v in eo))
    print("     link score:      " + "".join(f"{v:7.1%}" for v in out))
    print("     chance wobble ±: " + "".join(f"{v:7.1%}" for v in wob))
    # "Proven" = above 50% by more than 2 wobbles, so chance alone would almost never do it.
    proven = [n for n, s, w in zip(sizes, out, wob) if s - 2 * w > 0.5]
    print(f"     largest group proven linked (score above 50% by more than 2 wobbles): "
          f"{max(proven) if proven else 'none'} qubits")
    return out


def save_chart(series: dict, title: str, path: Path) -> None:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return
    fig, ax = plt.subplots(figsize=(7, 3.8))
    styles = {"perfect simulator": ("#999999", "--", "none"), "noisy simulator": ("#55a868", "-", "^"),
              "plain": ("#4c72b0", "-", "o"), "twirling on": ("#8172b3", "-", "v")}
    for name, (sizes, ys) in series.items():
        color, ls, marker = styles.get(name, ("#dd8452", "-", "o"))
        ys = [max(y, 0.0) for y in ys]  # below 0 just means "proves nothing"; show as 0
        ax.plot(sizes, ys, color=color, linestyle=ls, marker=marker, label=name)
    ax.axhline(0.5, color="#c44e52", linewidth=1, linestyle="--",
               label="above this line = all qubits proven linked")
    ax.set_xlabel("number of qubits linked together")
    ax.set_ylabel("link score (guaranteed minimum)")
    ax.set_ylim(-0.05, 1.05)
    ax.set_title(title, fontsize=11)
    ax.legend(fontsize=7, loc="lower left")
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    print(f"Chart saved to {path}")


# ---------- simulators ----------

def simulate() -> int:
    from qiskit.transpiler import generate_preset_pass_manager
    from qiskit_aer import AerSimulator
    from qiskit_aer.noise import NoiseModel
    from qiskit_ibm_runtime.fake_provider import FakeMarrakesh

    # "Matrix product state" is a simulator method that handles many qubits cheaply when,
    # as here, the state isn't too complicated.
    perfect_sim = AerSimulator(method="matrix_product_state")
    big = circuits_for(SIZES)
    res = perfect_sim.run(big, shots=SHOTS, seed_simulator=SEED).result()
    perfect = [res.get_counts(i) for i in range(len(big))]

    fake = FakeMarrakesh()
    small = circuits_for(SIM_SIZES)
    pm = generate_preset_pass_manager(backend=fake, optimization_level=2)
    isa = [pm.run(qc) for qc in small]
    noisy_sim = AerSimulator(method="matrix_product_state",
                             noise_model=NoiseModel.from_backend(fake))
    res = noisy_sim.run(isa, shots=SHOTS, seed_simulator=SEED).result()
    noisy = [res.get_counts(i) for i in range(len(isa))]

    print(f"Simulators, {SHOTS} shots each:")
    ideal = analyze(perfect, SIZES, "perfect simulator")
    rough = analyze(noisy, SIM_SIZES, "noisy simulator (copies ibm_marrakesh's published error rates)")
    save_chart({"perfect simulator": (SIZES, ideal), "noisy simulator": (SIM_SIZES, rough)},
               "Linking many qubits, on the simulators", HERE / "simulator_results.png")

    ok = (all(math.isclose(s, 1.0) for s in ideal)  # the circuit is right at every size
          and rough[-1] < rough[0])                  # noise costs more as the group grows
    print("  need: perfect simulator 100% at every size; noisy score lower for 12 qubits than for 2")
    print("CHECK PASSED" if ok else "CHECK FAILED")
    return 0 if ok else 1


# ---------- real hardware ----------

def best_chain(backend, length: int, beam: int = 300, avoid=()) -> list[int]:
    """Find a line of `length` physically connected qubits with the lowest published errors.

    Each step along the line costs its two-qubit gate error, and each qubit costs half its
    readout error. A "beam search" keeps the best few hundred partial lines at each step.
    """
    target = backend.target
    gate = next(g for g in ("cz", "ecr", "cx") if g in target.operation_names)
    props = backend.properties()

    def cost_q(q):
        return -0.5 * math.log(1 - min(props.readout_error(q), 0.5))

    edges = {}
    for (a, b), ip in target[gate].items():
        if ip is not None and ip.error is not None and ip.error < 0.5:
            c = -math.log(1 - ip.error)
            edges.setdefault(a, {})[b] = min(c, edges.get(a, {}).get(b, c))
            edges.setdefault(b, {})[a] = min(c, edges.get(b, {}).get(a, c))
    for q in avoid:  # qubits we've measured to be bad, whatever the published numbers say
        for nb in edges.pop(q, {}):
            edges.get(nb, {}).pop(q, None)
    paths = [(cost_q(q), [q]) for q in edges]
    for _ in range(length - 1):
        grown = [(c + w + cost_q(n), path + [n])
                 for c, path in paths for n, w in edges[path[-1]].items() if n not in path]
        paths = sorted(grown)[:beam]
    return paths[0][1]


def submit_to_ibm(chain: bool, avoid=(), sizes=None, variants=("plain", "twirl")) -> None:
    from qiskit.transpiler import generate_preset_pass_manager
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2

    service = QiskitRuntimeService()  # reads the saved account; the key is never printed
    sizes = sizes or (CHAIN_SIZES if chain else SIZES)
    backend = service.least_busy(operational=True, simulator=False, min_num_qubits=max(sizes))
    circs = circuits_for(sizes)
    if chain:
        # One hand-picked line; every group is the middle stretch of it, so each bigger
        # group contains the smaller ones and a bad qubit shows up as a clear step.
        line = best_chain(backend, max(max(sizes), max(CHAIN_SIZES)), avoid=avoid)
        print(f"Hand-picked line of {len(line)} qubits: {line}")
        isa = []
        for qc in circs:
            n = qc.num_qubits
            start = (len(line) - n) // 2
            pm = generate_preset_pass_manager(backend=backend, optimization_level=2,
                                              initial_layout=line[start:start + n])
            isa.append(pm.run(qc))
    else:
        line = None
        pm = generate_preset_pass_manager(backend=backend, optimization_level=2)
        isa = [pm.run(qc) for qc in circs]
    for qc, c in zip(circs[::2], isa[::2]):
        two_q = sum(v for op, v in c.count_ops().items() if op in ("cz", "ecr", "cx"))
        print(f"  {qc.name:16s} {two_q:3d} two-qubit gates, depth {c.depth()}")
    ids = {}
    for key, twirl in (("plain", False), ("twirl", True)):
        if key not in variants:
            continue
        sampler = SamplerV2(mode=backend)
        sampler.options.twirling.enable_gates = twirl
        sampler.options.twirling.enable_measure = twirl
        ids[key] = sampler.run(isa, shots=SHOTS).job_id()
    LAST_JOB.write_text(json.dumps({"backend": backend.name, "chain": line, "sizes": sizes,
                                    "avoid": list(avoid), **ids}))
    print(f"Submitted {len(ids)} job(s) of {len(isa)} circuits to {backend.name}.")
    print("When both are done:  python lessons/07_linking_many/ghz.py --job")


def fetch_jobs() -> int:
    from qiskit_ibm_runtime import QiskitRuntimeService

    if not LAST_JOB.exists():
        print("No saved job. Run with --ibm first.")
        return 1
    info = json.loads(LAST_JOB.read_text())
    sizes = info.get("sizes", SIZES)
    service = QiskitRuntimeService()
    results = {}
    for key, label in (("plain", "plain"), ("twirl", "twirling on")):
        if key not in info:
            continue
        job = service.job(info[key])
        status = job.status()
        if status != "DONE":
            print(f"The {key} job is {status}. Try again later.")
            return 0 if status not in ("ERROR", "CANCELLED") else 1
        counts = [r.data.c.get_counts() for r in job.result()]
        results[label] = analyze(counts, sizes, label)
    how = "one hand-picked line of qubits" if info.get("chain") else "qubits picked per size"
    print(f"(on {info['backend']}, {how}, {SHOTS} shots each)")
    name = ("hardware_chain_repeat_results.png" if info.get("avoid") and "plain" not in info else
            "hardware_chain_avoid_results.png" if info.get("avoid") else
            "hardware_chain_results.png" if info.get("chain") else "hardware_results.png")
    if info.get("avoid"):
        how += f", avoiding qubit(s) {info['avoid']}"
    save_chart({k: (sizes, v) for k, v in results.items()},
               f"Linking many qubits on {info['backend']} ({how})", HERE / name)

    best = max(results.values(), key=lambda v: sum(s > 0.5 for s in v))
    ok = best[0] > 0.5 and best[-1] < best[0]  # small groups link; bigger groups are harder
    print("  need: 2 qubits proven linked, and the score falls as the group grows")
    print("CHECK PASSED" if ok else "CHECK FAILED")
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--ibm", action="store_true", help="submit both jobs to a real IBM machine")
    mode.add_argument("--job", action="store_true", help="check and chart the last submitted jobs")
    parser.add_argument("--chain", action="store_true",
                        help="with --ibm: use one hand-picked best line of qubits, sizes up to 40")
    parser.add_argument("--sizes", type=int, nargs="*", metavar="N", help="with --ibm: group sizes to try")
    parser.add_argument("--twirl-only", action="store_true", help="with --ibm: send only the twirled job")
    parser.add_argument("--avoid", type=int, nargs="*", default=[], metavar="QUBIT",
                        help="with --chain: physical qubits to leave out (e.g. ones weak_link.py flagged)")
    args = parser.parse_args()
    if args.job:
        return fetch_jobs()
    print(build_ghz(8, False).draw(output="text", fold=-1))
    if args.ibm:
        submit_to_ibm(args.chain, args.avoid, args.sizes,
                      ("twirl",) if args.twirl_only else ("plain", "twirl"))
        return 0
    return simulate()


if __name__ == "__main__":
    sys.exit(main())
