"""Milestone M6, kept at its published path.

The measurement moved into `agentic_dataset.authorized_recall`, which has no
dependency on the control plane so that the metric can be adopted without the
architecture. This is a shim so the command in `docs/runs/` keeps working, and
so there is exactly one implementation of the experiment.

    python -m agentic_dataset.authorized_recall
"""

from agentic_dataset.authorized_recall.experiment import main

if __name__ == "__main__":
    main()
