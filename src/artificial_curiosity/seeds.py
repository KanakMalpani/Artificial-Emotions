"""Seed frontiers and offline question templates for reliable demos."""

from __future__ import annotations

from artificial_curiosity.models import Domain, UnansweredQuestion

# Curated high-signal unknowns used when LLM generation is off.
# These are starting points for ranking + gap verification — not gospel.

SEED_QUESTIONS: dict[str, list[UnansweredQuestion]] = {
    Domain.AI.value: [
        UnansweredQuestion(
            id="ai-01",
            question=(
                "What measurable internal signals most reliably predict "
                "goal-misgeneralization before deployment-scale harm?"
            ),
            domain=Domain.AI,
            operationalization=(
                "Identify signals that, in controlled agent evals, predict "
                "misgeneralization with AUROC > 0.8 across ≥3 environments."
            ),
            why_it_matters=(
                "Early warning of misaligned generalization could prevent "
                "catastrophic deployment failures."
            ),
            assumptions=["Internal activations are partially interpretable."],
            tags=["alignment", "evals", "interpretability"],
            source="seed",
        ),
        UnansweredQuestion(
            id="ai-02",
            question=(
                "Which training interventions most increase honest uncertainty "
                "reporting under incentive pressure to appear confident?"
            ),
            domain=Domain.AI,
            operationalization=(
                "Compare interventions on a fixed honesty benchmark where "
                "models are rewarded for confident wrong answers; measure "
                "calibration and truthfulness deltas."
            ),
            why_it_matters="Overconfident systems amplify decision errors at scale.",
            tags=["honesty", "calibration", "rlhf"],
            source="seed",
        ),
        UnansweredQuestion(
            id="ai-03",
            question=(
                "How can we quantify the expected value of unanswered scientific "
                "questions so AI systems prioritize investigation, not only answering?"
            ),
            domain=Domain.AI,
            operationalization=(
                "Produce a scoring method whose top-k questions are rated higher "
                "by domain experts than random/LLM-interestingness baselines "
                "on blinded panels."
            ),
            why_it_matters=(
                "Without a curiosity layer, AI accelerates answering known frames "
                "while neglecting high-value unknowns."
            ),
            tags=["meta-science", "curiosity", "voi"],
            source="seed",
        ),
        UnansweredQuestion(
            id="ai-04",
            question=(
                "What architectural or training conditions cause persistent "
                "scheming-like behavior to appear in multi-episode agent settings?"
            ),
            domain=Domain.AI,
            operationalization=(
                "Map conditions under which deceptive planning survives "
                "standard safety fine-tuning in multi-episode evals."
            ),
            why_it_matters="Scheming under evaluation is a central alignment risk.",
            tags=["scheming", "agents", "safety"],
            source="seed",
        ),
        UnansweredQuestion(
            id="ai-05",
            question=(
                "Which evaluation protocols most reduce sandbagging when models "
                "can detect they are being tested?"
            ),
            domain=Domain.AI,
            operationalization=(
                "Compare protocols on known sandbagging setups; measure "
                "capability underestimation gap versus hidden capability probes."
            ),
            why_it_matters="Undetected sandbagging breaks safety assurances.",
            tags=["evals", "sandbagging", "safety"],
            source="seed",
        ),
        UnansweredQuestion(
            id="ai-06",
            question=(
                "How can multi-agent systems be monitored for emergent collusion "
                "against human-specified objectives in open environments?"
            ),
            domain=Domain.AI,
            operationalization=(
                "Define detectable collusion signatures and validate detection "
                "AUROC on staged multi-agent markets and tool-use sandboxes."
            ),
            why_it_matters="Agent swarms can coordinate harms invisible to single-agent evals.",
            tags=["multi-agent", "monitoring", "safety"],
            source="seed",
        ),
    ],
    Domain.BIOLOGY.value: [
        UnansweredQuestion(
            id="bio-01",
            question=(
                "What causal factors determine whether cellular senescence is "
                "net protective or net harmful across human tissues with age?"
            ),
            domain=Domain.BIOLOGY,
            operationalization=(
                "Tissue-resolved causal maps linking senescent cell subtypes "
                "to functional outcomes in ≥3 human tissues."
            ),
            why_it_matters="Senolytics may help or harm depending on context.",
            tags=["aging", "senescence"],
            source="seed",
        ),
        UnansweredQuestion(
            id="bio-02",
            question=(
                "Which microbial community features most strongly causally "
                "influence vaccine non-response in adults?"
            ),
            domain=Domain.BIOLOGY,
            operationalization=(
                "Identify features that remain predictive after confounder "
                "control and are manipulable in interventional studies."
            ),
            why_it_matters="Improving vaccine response has population-scale benefit.",
            tags=["microbiome", "immunology"],
            source="seed",
        ),
        UnansweredQuestion(
            id="bio-03",
            question=(
                "What molecular clocks best predict organ-specific biological age "
                "deltas that reverse under validated interventions?"
            ),
            domain=Domain.BIOLOGY,
            operationalization=(
                "Clocks whose predicted age drops track functional recovery "
                "in interventional cohorts better than chronological age."
            ),
            why_it_matters="Actionable aging biomarkers enable trial design.",
            tags=["aging", "biomarkers"],
            source="seed",
        ),
        UnansweredQuestion(
            id="bio-04",
            question=(
                "Which protein condensates most causally drive age-related "
                "proteostasis failure in human neurons?"
            ),
            domain=Domain.BIOLOGY,
            operationalization=(
                "Perturb candidate condensates and measure proteostasis and "
                "viability endpoints in human iPSC-derived neurons."
            ),
            why_it_matters="Condensate biology may unlock neurodegeneration interventions.",
            tags=["condensates", "aging", "neuroscience"],
            source="seed",
        ),
    ],
    Domain.CLIMATE.value: [
        UnansweredQuestion(
            id="cli-01",
            question=(
                "What is the true probability distribution of AMOC collapse "
                "this century under high-emission pathways?"
            ),
            domain=Domain.CLIMATE,
            operationalization=(
                "Convergent observational + model constraints yielding a "
                "calibrated probability with quantified structural uncertainty."
            ),
            why_it_matters="AMOC tipping would reshape European climate and food systems.",
            tags=["tipping-points", "ocean"],
            source="seed",
        ),
        UnansweredQuestion(
            id="cli-02",
            question=(
                "Which carbon dioxide removal pathways have the highest "
                "expected net climate benefit after accounting for "
                "energy, land, and permanence risks?"
            ),
            domain=Domain.CLIMATE,
            operationalization=(
                "Rank CDR pathways by expected net GtCO2e removed under "
                "shared LCA and permanence assumptions."
            ),
            why_it_matters="Misallocated CDR wastes capital and political will.",
            tags=["cdr", "mitigation"],
            source="seed",
        ),
        UnansweredQuestion(
            id="cli-03",
            question=(
                "How much do aerosol reductions currently mask near-term "
                "warming, and which regions are most exposed when that mask lifts?"
            ),
            domain=Domain.CLIMATE,
            operationalization=(
                "Region-resolved estimates of aerosol masking with uncertainty "
                "bounds tied to air-quality transition scenarios."
            ),
            why_it_matters="Unmasking could accelerate local climate shocks.",
            tags=["aerosols", "attribution"],
            source="seed",
        ),
    ],
    Domain.MEDICINE.value: [
        UnansweredQuestion(
            id="med-01",
            question=(
                "What host factors most strongly predict progression from "
                "latent to active tuberculosis in vaccinated adults?"
            ),
            domain=Domain.MEDICINE,
            operationalization=(
                "Prospective biomarkers with positive predictive value "
                "sufficient to guide preventive therapy trials."
            ),
            why_it_matters="TB remains a leading infectious killer worldwide.",
            tags=["tb", "biomarkers"],
            source="seed",
        ),
        UnansweredQuestion(
            id="med-02",
            question=(
                "Which combination therapies most delay resistance evolution "
                "in Gram-negative pathogens under realistic dosing?"
            ),
            domain=Domain.MEDICINE,
            operationalization=(
                "In vitro + animal evolution assays showing delayed resistance "
                "relative to monotherapy baselines."
            ),
            why_it_matters="Antibiotic resistance threatens modern medicine.",
            tags=["amr", "infectious-disease"],
            source="seed",
        ),
        UnansweredQuestion(
            id="med-03",
            question=(
                "What early molecular signatures distinguish durable cancer "
                "immunotherapy responders from primary non-responders?"
            ),
            domain=Domain.MEDICINE,
            operationalization=(
                "Prospective signatures with validated predictive performance "
                "across ≥2 cancer types and independent cohorts."
            ),
            why_it_matters="Better patient selection reduces futile toxicity and cost.",
            tags=["immuno-oncology", "biomarkers"],
            source="seed",
        ),
        UnansweredQuestion(
            id="med-04",
            question=(
                "Which modifiable sleep interventions most reduce dementia "
                "incidence in midlife adults with objective sleep disruption?"
            ),
            domain=Domain.MEDICINE,
            operationalization=(
                "Randomized or quasi-experimental evidence linking specific "
                "sleep interventions to cognitive endpoints over ≥5 years."
            ),
            why_it_matters="Dementia prevention at population scale is high-leverage.",
            tags=["sleep", "neurology", "prevention"],
            source="seed",
        ),
    ],
    Domain.PHYSICS.value: [
        UnansweredQuestion(
            id="phy-01",
            question=(
                "What observational signature would most cleanly distinguish "
                "quantum gravity effects from systematic noise in "
                "interferometric detectors?"
            ),
            domain=Domain.PHYSICS,
            operationalization=(
                "A proposed signature with false-positive rate estimates "
                "under realistic noise models."
            ),
            why_it_matters="Without discriminators, QG claims remain unfalsifiable.",
            tags=["quantum-gravity", "metrology"],
            source="seed",
        ),
        UnansweredQuestion(
            id="phy-02",
            question=(
                "Which dark-matter search channels are most neglected relative "
                "to theoretically motivated mass ranges still allowed by data?"
            ),
            domain=Domain.PHYSICS,
            operationalization=(
                "Map parameter space coverage versus theoretical priors and "
                "rank under-covered windows by expected information gain."
            ),
            why_it_matters="Misallocated search effort delays discovery or exclusion.",
            tags=["dark-matter", "experiment"],
            source="seed",
        ),
        UnansweredQuestion(
            id="phy-03",
            question=(
                "What is the minimal set of cosmological observations that "
                "could falsify currently favored early-universe inflation models?"
            ),
            domain=Domain.PHYSICS,
            operationalization=(
                "A concrete falsification checklist tied to forthcoming "
                "CMB/LSS datasets with stated significance thresholds."
            ),
            why_it_matters="Clear falsifiers prevent unfalsifiable model drift.",
            tags=["cosmology", "inflation"],
            source="seed",
        ),
    ],
    Domain.ENERGY.value: [
        UnansweredQuestion(
            id="eng-01",
            question=(
                "What materials degradation mechanisms most limit commercial "
                "solid-state battery cycle life under fast-charge conditions?"
            ),
            domain=Domain.ENERGY,
            operationalization=(
                "Ranked mechanisms validated by post-mortem analysis correlating "
                "with capacity fade across ≥3 cell chemistries."
            ),
            why_it_matters="Fast-charge solid-state batteries unlock EV adoption.",
            tags=["batteries", "materials"],
            source="seed",
        ),
        UnansweredQuestion(
            id="eng-02",
            question=(
                "Which grid-storage chemistries minimize levelized cost under "
                "high renewable penetration with multi-day storage needs?"
            ),
            domain=Domain.ENERGY,
            operationalization=(
                "Techno-economic ranking under shared demand scenarios with "
                "explicit duration, round-trip efficiency, and supply-chain constraints."
            ),
            why_it_matters="Wrong storage bets lock in expensive decarbonization paths.",
            tags=["storage", "grid"],
            source="seed",
        ),
        UnansweredQuestion(
            id="eng-03",
            question=(
                "What plasma-facing material strategies most extend fusion "
                "divertor lifetime under realistic DEMO heat fluxes?"
            ),
            domain=Domain.ENERGY,
            operationalization=(
                "Compare candidate materials on erosion, tritium retention, and "
                "mechanical lifetime under DEMO-relevant fluxes."
            ),
            why_it_matters="Divertor lifetime is a critical path for fusion commercialization.",
            tags=["fusion", "materials"],
            source="seed",
        ),
    ],
    Domain.MATERIALS.value: [
        UnansweredQuestion(
            id="mat-01",
            question=(
                "Which synthesizable crystal structures are most likely to "
                "exhibit room-temperature superconductivity under ambient pressure?"
            ),
            domain=Domain.MATERIALS,
            operationalization=(
                "A shortlist ranked by theory+ML priors that experimental groups "
                "can attempt under ambient conditions within 2 years."
            ),
            why_it_matters="Ambient superconductivity would transform energy systems.",
            tags=["superconductivity", "materials-discovery"],
            source="seed",
        ),
        UnansweredQuestion(
            id="mat-02",
            question=(
                "What descriptors best predict synthesizability of hypothetical "
                "inorganic crystals proposed by generative models?"
            ),
            domain=Domain.MATERIALS,
            operationalization=(
                "Descriptors that improve prospective synthesis success rates "
                "over baseline formation-energy filters in lab validation."
            ),
            why_it_matters="Unsynthesizable proposals waste experimental cycles.",
            tags=["synthesizability", "ml"],
            source="seed",
        ),
    ],
    Domain.SOCIAL.value: [
        UnansweredQuestion(
            id="soc-01",
            question=(
                "What interventions most increase institutional capacity to "
                "update policies when scientific consensus shifts?"
            ),
            domain=Domain.SOCIAL,
            operationalization=(
                "Comparative measures of policy-update latency and quality "
                "across institutions after consensus shifts."
            ),
            why_it_matters="Slow institutional learning turns knowledge into waste.",
            tags=["institutions", "epistemics"],
            source="seed",
        ),
        UnansweredQuestion(
            id="soc-02",
            question=(
                "Which information environments most reduce belief polarization "
                "without suppressing true minority scientific findings?"
            ),
            domain=Domain.SOCIAL,
            operationalization=(
                "Measure polarization and true-positive uptake of minority-correct "
                "claims across controlled information-environment interventions."
            ),
            why_it_matters="Epistemic health of democracies depends on this tradeoff.",
            tags=["polarization", "epistemics", "media"],
            source="seed",
        ),
    ],
}


def seeds_for(domain: str, topic: str = "", limit: int = 16) -> list[UnansweredQuestion]:
    domain_key = domain.lower() if isinstance(domain, str) else str(domain)
    pool = list(SEED_QUESTIONS.get(domain_key, []))
    if not pool:
        # Mix across domains for general
        for qs in SEED_QUESTIONS.values():
            pool.extend(qs)
    if topic:
        t = topic.lower()
        ranked = sorted(
            pool,
            key=lambda q: sum(
                1
                for token in t.split()
                if token in q.question.lower()
                or token in q.why_it_matters.lower()
                or token in " ".join(q.tags)
            ),
            reverse=True,
        )
        pool = ranked
    return pool[:limit]
