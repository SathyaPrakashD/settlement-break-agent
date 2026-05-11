"""Layer 3: LLM-as-judge pairwise eval.

Compares the system's remediation against a human reference remediation for
each golden case. Uses a DIFFERENT model family as judge (Gemini 2.5 Pro)
than the synthesiser (Gemini 2.0 Flash) to reduce self-preference bias.

Pairwise design choices:
  - Order randomisation: each case is judged twice, with A and B positions
    swapped, to control for position bias.
  - "Tie" is an allowed verdict — not every difference is meaningful.
  - The judge reasons step-by-step before verdict to reduce snap judgements.

──────────────────────────────────────────────────────────────────────────────
TODO(sathya): implement run_synthesis_judge().

This is more advanced than the basic synthesiser. Suggested sequence:
  1. First, implement Synthesizer.synthesize() in src/sba/synthesis/synthesizer.py
  2. Then come back here

When you implement:
  - Use the judge_model from settings (default: gemini-2.5-pro)
  - For each golden case, run the synthesiser to get a candidate remediation
  - Construct a pairwise prompt: "Given this break, which remediation is better,
    A or B, or tied?" with the human reference as one and the system output as
    the other
  - Run TWICE per case with A/B order swapped
  - Aggregate: wins / ties / losses for the system

Reference for pairwise judging design:
  Zheng et al. "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena" (2023)
──────────────────────────────────────────────────────────────────────────────
"""


def run_synthesis_judge() -> dict[str, float]:
    """Run pairwise LLM-as-judge over the golden set.

    Returns:
        {
          "win_rate": fraction of cases where system's remediation was preferred,
          "tie_rate": fraction of ties,
          "loss_rate": fraction where human reference was preferred,
        }
    """
    # TODO(sathya): implement
    return {
        "win_rate": 0.0,
        "tie_rate": 0.0,
        "loss_rate": 0.0,
        "_status": "not implemented",  # type: ignore[dict-item]
    }
