"""Recompute lesson 7's phase-sweep results from the published data, no IBM account needed.

The files in data/ hold, for each real-hardware sweep: the machine, the physical qubits, the
straight-measurement totals (all 0s, all 1s, shots), and the even/odd counts after each turn
angle. That's everything the link-quality formula and its cautious lower bound use.

    python lessons/07_linking_many/recompute.py
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import parity_repeat as R  # noqa: E402
import parity_sweep as P  # noqa: E402

DATA = HERE / "data"


def straight_counts(t: dict, n: int) -> dict:
    """Rebuild just enough of a count table: all-0s, all-1s, and 'anything else'."""
    rest = t["shots"] - t["all0"] - t["all1"]
    return {"0" * n: t["all0"], "1" * n: t["all1"], "01" + "0" * (n - 2): rest}


def angle_counts(e: dict, n: int) -> dict:
    """An even-parity and an odd-parity stand-in carry the only thing the sweep uses."""
    return {"0" * n: e["even"], "1" + "0" * (n - 1): e["odd"]}


def main() -> int:
    ok = True
    for path in sorted(DATA.glob("run*.json")):
        d = json.loads(path.read_text())
        print(f"{path.name}: {d['experiment']} on {d['backend']}, {d['date_central']} Central")
        for g in d["groups"]:
            n = g["qubits_n"]
            print(f"   all circuits on the same physical qubits: {g['all_circuits_same_qubits']}")
            if "sideways_after_turn_with_z" in g:  # run 6: repeat + control
                counts = []
                for plain, z in zip([g["straight"]] + g["sideways_after_turn"],
                                    [g["straight_with_z"]] + g["sideways_after_turn_with_z"]):
                    if "all0" in plain:
                        counts += [straight_counts(plain, n), straight_counts(z, n)]
                    else:
                        counts += [angle_counts(plain, n), angle_counts(z, n)]
                R.report(counts, d["backend"])
            else:
                counts = [straight_counts(g["straight"], n)] + [angle_counts(e, n) for e in g["sideways_after_turn"]]
                P.report(P.quality(counts, [n]), d["backend"])
        ok &= all(g["all_circuits_same_qubits"] for g in d["groups"])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
