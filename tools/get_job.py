"""Check on a job sent to a real IBM quantum computer, and show its results when done.

    python tools/get_job.py <job-id>

Uses the saved account in ~/.qiskit/qiskit-ibm.json (or QISKIT_IBM_TOKEN). Prints no secrets.
"""

import sys

from qiskit_ibm_runtime import QiskitRuntimeService


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    job = QiskitRuntimeService().job(sys.argv[1])
    status = job.status()
    print(f"Job {job.job_id()} on {job.backend().name}: {status}")
    if status in ("ERROR", "CANCELLED"):
        print(f"The job did not finish: {job.error_message() or status}")
        return 1
    if status != "DONE":
        print("Still waiting in line or running. Run this again later.")
        return 0

    # One job can hold several circuits; show each one's results in order.
    for i, result in enumerate(job.result(), start=1):
        # Our lessons name the classical register "c" (the default for QuantumCircuit(n, n)).
        counts = result.data.c.get_counts()
        total = sum(counts.values())
        print(f"Circuit {i}: {total} runs on real hardware")
        for bits, n in sorted(counts.items(), key=lambda kv: -kv[1]):
            print(f"  {bits}: {n:5d}  ({n / total:.1%})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
