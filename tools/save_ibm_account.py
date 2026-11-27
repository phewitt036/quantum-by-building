"""One-time setup: save your IBM Quantum API key on THIS machine, outside the repo.

    python tools/save_ibm_account.py [crn:...]

Pass your Open Plan instance CRN on the command line to skip that question (the CRN is
not secret). It asks for the key with a hidden prompt, so the key never shows on screen, never lands
in your shell history, and is never written inside this repo. Qiskit stores it in
~/.qiskit/qiskit-ibm.json in your home folder. Run it once on each machine (Mac and x8).
"""

import sys
from getpass import getpass

from qiskit_ibm_runtime import QiskitRuntimeService


def main() -> None:
    token = getpass("Paste your IBM Quantum API key (hidden, press Enter): ").strip()
    if len(sys.argv) > 1:
        instance = sys.argv[1].strip()
    else:
        instance = input("Paste your Open Plan instance CRN (starts with 'crn:'): ").strip()
    if not token or not instance.startswith("crn:"):
        raise SystemExit("Need both the API key and a CRN starting with 'crn:'. Nothing saved.")
    QiskitRuntimeService.save_account(
        token=token,
        instance=instance,
        name="open",
        set_as_default=True,
        overwrite=True,
    )
    # Prove it works without printing the key: list the machines this account can use.
    names = [b.name for b in QiskitRuntimeService().backends(simulator=False)]
    print(f"Saved. Your account can use {len(names)} real quantum computers: {', '.join(names)}")


if __name__ == "__main__":
    main()
