"""Argparse for form-only worksheets and ranked-set lenses.

``critique-brief``, ``stance``, ``imagine``, ``decompose``, ``voi-worksheet``,
``surprise-worksheet``. None of these re-rank; VOI is not EVSI.
"""

from __future__ import annotations

import argparse

from artificial_emotions.models import Domain

__all__ = ["add_worksheet_parsers"]


def add_worksheet_parsers(sub: argparse._SubParsersAction) -> None:
    critique_p = sub.add_parser(
        "critique-brief",
        help="Form-only critique of a brief/ops (does not re-rank)",
    )
    critique_p.add_argument("--question", default="")
    critique_p.add_argument("--ops", default="", dest="operationalization")
    critique_p.add_argument("--brief", default="")
    critique_p.add_argument("--why", default="", dest="why_it_matters")
    critique_p.add_argument("--json", action="store_true")

    stance_p = sub.add_parser(
        "stance",
        help="Ask a different question of a ranked set (doubt, safety, focus, close, taste, survey)",
    )
    stance_p.add_argument(
        "stance_name",
        nargs="?",
        default="list",
        help="Stance name, or omit to list them",
    )
    stance_p.add_argument("--domain", default="ai", choices=[d.value for d in Domain])
    stance_p.add_argument("--topic", default="")
    stance_p.add_argument("--n", type=int, default=6)
    stance_p.add_argument("--profile", default="humanity_default")
    stance_p.add_argument("--literature", action="store_true")
    stance_p.add_argument("--json", action="store_true")

    imagine_p = sub.add_parser(
        "imagine",
        help=(
            "Generate quarantined imagined content "
            "(premortem, harm_scenario, rehearsal, eulogy, reformulation, "
            "counterfactual, transfer); offline, never ranked"
        ),
    )
    imagine_p.add_argument(
        "imagine_kind",
        nargs="?",
        default="list",
        help=(
            "Imagination kind (premortem|harm_scenario|rehearsal|eulogy|"
            "reformulation|counterfactual|transfer), or omit to list"
        ),
    )
    imagine_p.add_argument("--domain", default="ai", choices=[d.value for d in Domain])
    imagine_p.add_argument("--topic", default="")
    imagine_p.add_argument("--n", type=int, default=6)
    imagine_p.add_argument("--profile", default="humanity_default")
    imagine_p.add_argument(
        "--literature",
        action="store_true",
        help="Optional literature for the ranking step only; generators stay offline",
    )
    imagine_p.add_argument(
        "--corpus",
        default="",
        help="Local corpus (year+concepts JSON) — required for transfer",
    )
    imagine_p.add_argument(
        "--seed",
        default="",
        help="Seed concept for transfer (e.g. 'Fish oil')",
    )
    imagine_p.add_argument("--json", action="store_true")

    decompose_p = sub.add_parser(
        "decompose",
        help="Open one unknown into sub-questions, a first step, and falsifiers (never an answer)",
    )
    decompose_p.add_argument("question", help="The unknown to open up")
    decompose_p.add_argument(
        "--ops",
        default="",
        dest="operationalization",
        help="How you'd know it was answered; numeric criteria become falsifiers",
    )
    decompose_p.add_argument("--domain", default="ai", choices=[d.value for d in Domain])
    decompose_p.add_argument(
        "--depth",
        type=int,
        default=1,
        choices=[1, 2, 3],
        help="1 = one layer; 2-3 also split mechanism and confound",
    )
    decompose_p.add_argument("--answerability", type=float, default=None)
    decompose_p.add_argument("--tractability", type=float, default=None)
    decompose_p.add_argument("--risk", type=float, default=None)
    decompose_p.add_argument("--json", action="store_true")

    voi_p = sub.add_parser(
        "voi-worksheet",
        help="Fill VOI worksheet metadata (not computed EVSI)",
    )
    voi_p.add_argument("--question-id", default=None)
    voi_p.add_argument("--question", default="")
    voi_p.add_argument("--ops", default="", dest="operationalization")
    voi_p.add_argument("--profile", default=None)
    voi_p.add_argument("--domain", default="")
    voi_p.add_argument("--json", action="store_true")

    surprise_p = sub.add_parser(
        "surprise-worksheet",
        help="Fill Bayesian-surprise belief-shift worksheet (not EVSI / not axis rename)",
    )
    surprise_p.add_argument("--question-id", default=None)
    surprise_p.add_argument("--profile", default=None, dest="profile_name")
    surprise_p.add_argument("--predicted-surprise", type=float, default=None)
    surprise_p.add_argument("--pilot-result", default="")
    surprise_p.add_argument("--belief-shift", type=int, default=None)
    surprise_p.add_argument("--note", default="", dest="crude_update_note")
    surprise_p.add_argument("--json", action="store_true")
