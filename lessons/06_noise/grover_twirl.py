"""Lesson 6, extra: does twirling rescue lesson 5's search on real hardware?

Runs lesson 5's 8-box Grover circuits (0-3 rounds) as four jobs on the same qubits: plain,
twirling of the final reading only, twirling of the two-qubit gates only, and both. Twirling
was the noise reducer that worked in noise.py.

    python lessons/06_noise/grover_twirl.py --ibm     # submit both jobs
    python lessons/06_noise/grover_twirl.py --job     # check and chart them when done

(There's no simulator mode: lesson 5 already covers the simulator.)
"""

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "05_grover_search"))
import grover as G  # noqa: E402  (lesson 5's circuits and theory)

LAST_JOB = HERE / ".last_grover_job.json"  # job IDs + qubits (not committed)
# key: (twirl the two-qubit gates, twirl the final reading)
VARIANTS = {"plain": (False, False), "measure": (False, True), "gates": (True, False), "both": (True, True)}
LABELS = {"plain": "plain", "measure": "reading twirled", "gates": "gates twirled", "both": "both twirled"}


def circuits():
    return [G.build_grover(G.PRIZE_8, k) for k in G.ROUNDS_8] + [G.build_ready(G.PRIZE_8)]


def submit() -> None:
    from qiskit.transpiler import generate_preset_pass_manager
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2

    backend = QiskitRuntimeService().least_busy(operational=True, simulator=False, min_num_qubits=3)
    circs = circuits()
    pm = generate_preset_pass_manager(backend=backend, optimization_level=2)
    qubits = pm.run(circs[2]).layout.final_index_layout()
    pinned = generate_preset_pass_manager(backend=backend, optimization_level=2, initial_layout=qubits)
    isa = [pinned.run(qc) for qc in circs]
    ids = {}
    for key, (gates, measure) in VARIANTS.items():
        sampler = SamplerV2(mode=backend)
        sampler.options.twirling.enable_gates = gates
        sampler.options.twirling.enable_measure = measure
        ids[key] = sampler.run(isa, shots=G.SHOTS).job_id()
    LAST_JOB.write_text(json.dumps({"backend": backend.name, "qubits": qubits, **ids}))
    print(f"Submitted {len(ids)} jobs to {backend.name}, qubits {qubits}.")
    print("When done:  python lessons/06_noise/grover_twirl.py --job")


def fetch() -> int:
    from qiskit_ibm_runtime import QiskitRuntimeService

    if not LAST_JOB.exists():
        print("No saved job. Run with --ibm first.")
        return 1
    info = json.loads(LAST_JOB.read_text())
    service = QiskitRuntimeService()
    found = {}
    for key in VARIANTS:
        job = service.job(info[key])
        if job.status() != "DONE":
            print(f"The {key} job is {job.status()}. Try again later.")
            return 0
        counts = [r.data.c.get_counts() for r in job.result()]
        found[key] = [G.share(c, G.PRIZE_8) for c in counts[:-1]]
        found[key + "_ready"] = G.share(counts[-1], G.PRIZE_8)

    print(f"Lesson 5's search on {info['backend']}, qubits {info['qubits']}, {G.SHOTS} shots each:")
    print("   rounds:     " + "".join(f"{k:>9d}" for k in G.ROUNDS_8))
    print("   perfect:    " + "".join(f"{G.theory(8, k):9.1%}" for k in G.ROUNDS_8))
    for key in VARIANTS:
        print(f"   {LABELS[key] + ':':16s}" + "".join(f"{v:9.1%}" for v in found[key])
              + f"     readout control {found[key + '_ready']:.1%}")
    save_chart(found, info["backend"])

    ok = found["both"][2] > found["both"][0] and found["both"][2] > found["both"][3]
    print("  need: with both twirled, 2 rounds still beats 0 and 3 rounds (the search still works)")
    print("CHECK PASSED" if ok else "CHECK FAILED")
    return 0 if ok else 1


def save_chart(found: dict, backend: str) -> None:
    import matplotlib.pyplot as plt

    x = list(range(len(G.ROUNDS_8)))
    w = 0.16
    fig, ax = plt.subplots(figsize=(7, 3.6))
    ax.bar([i - 2 * w for i in x], [G.theory(8, k) for k in G.ROUNDS_8], width=w,
           color="#dddddd", edgecolor="#999999", label="perfect machine")
    colors = {"plain": "#4c72b0", "measure": "#55a868", "gates": "#dd8452", "both": "#8172b3"}
    for j, key in enumerate(VARIANTS):
        ax.bar([i + (j - 1) * w for i in x], found[key], width=w, color=colors[key], label=LABELS[key])
    ax.axhline(1 / 8, color="#c44e52", linestyle="--", linewidth=1, label="blind guess (1 in 8)")
    ax.set_xticks(x, [f"{k} rounds" for k in G.ROUNDS_8])
    ax.set_ylabel(f"chance of finding the prize ({G.PRIZE_8})")
    ax.set_ylim(0, 1.05)
    ax.set_title(f"Lesson 5's search with and without twirling, {backend}", fontsize=10)
    ax.legend(fontsize=7, loc="upper left")
    fig.tight_layout()
    path = HERE / "grover_twirl_results.png"
    fig.savefig(path, bbox_inches="tight")
    print(f"Chart saved to {path}")


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
