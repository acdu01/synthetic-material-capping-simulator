#!/usr/bin/env python3
"""Simulate stakeholder outcomes for a synthetic material capping program.

The model is intentionally simple and transparent. It reads the stakeholder
requirements from `requirements_table.csv`, then runs a scenario-based policy
simulation to show how a cap, exemptions, training, labeling, and support
programs might perform over time.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def num(value: float) -> str:
    return f"{value:.2f}"


@dataclass(frozen=True)
class RequirementRow:
    section: str
    party: str
    need: str
    requirement: str
    metric: str
    target_range: str
    rationale: str
    ethics: str


@dataclass(frozen=True)
class Policy:
    name: str
    phase_in_years: int
    start_cap: float
    end_cap: float
    training_investment: float
    transparency_investment: float
    small_business_support: float
    exemption_generosity: float
    verified_badge_strength: float
    discount_subsidy: float
    durability_investment: float
    alternative_fiber_investment: float
    workforce_support: float
    enforcement_strength: float
    microfiber_controls: float


@dataclass(frozen=True)
class MetricCheck:
    party: str
    label: str
    metric_name: str
    target_year: int
    comparator: str
    target_value: float
    formatter: Callable[[float], str]

    def evaluate(self, history: list[dict[str, float]]) -> tuple[bool, float]:
        year_index = min(self.target_year, len(history)) - 1
        actual = history[year_index][self.metric_name]
        if self.comparator == ">=":
            passed = actual >= self.target_value
        elif self.comparator == "<=":
            passed = actual <= self.target_value
        else:
            raise ValueError(f"Unsupported comparator: {self.comparator}")
        return passed, actual


@dataclass(frozen=True)
class CheckResult:
    check: MetricCheck
    passed: bool
    actual: float


SUMMARY_METRICS = [
    ("effective_synthetic_share", "Effective synthetic share", pct),
    ("consumer_price_increase", "Consumer price increase", pct),
    ("discount_price_increase", "Discount price increase", pct),
    ("durability_improvement", "Durability improvement", pct),
    ("fiber_disclosure_rate", "Fiber disclosure rate", pct),
    ("fossil_fuel_reduction", "Fossil fuel reduction", pct),
    ("microfiber_reduction", "Microfiber reduction", pct),
    ("textile_waste_reduction", "Textile waste reduction", pct),
    ("workers_retained", "Worker retention", pct),
]

CHART_METRICS = [
    ("synthetic_cap_limit", "Cap", "#24577a"),
    ("effective_synthetic_share", "Actual synthetic share", "#cb5a2d"),
    ("consumer_price_increase", "Consumer price increase", "#b98c14"),
    ("durability_improvement", "Durability improvement", "#2d7d46"),
    ("fossil_fuel_reduction", "Fossil fuel reduction", "#6e4ea1"),
]


SCENARIOS = {
    "balanced": Policy(
        name="balanced",
        phase_in_years=5,
        start_cap=0.70,
        end_cap=0.35,
        training_investment=0.82,
        transparency_investment=0.86,
        small_business_support=0.78,
        exemption_generosity=0.75,
        verified_badge_strength=0.72,
        discount_subsidy=0.72,
        durability_investment=0.76,
        alternative_fiber_investment=0.84,
        workforce_support=0.74,
        enforcement_strength=0.78,
        microfiber_controls=0.68,
    ),
    "aggressive": Policy(
        name="aggressive",
        phase_in_years=4,
        start_cap=0.70,
        end_cap=0.25,
        training_investment=0.78,
        transparency_investment=0.88,
        small_business_support=0.62,
        exemption_generosity=0.50,
        verified_badge_strength=0.80,
        discount_subsidy=0.45,
        durability_investment=0.86,
        alternative_fiber_investment=0.90,
        workforce_support=0.60,
        enforcement_strength=0.88,
        microfiber_controls=0.82,
    ),
    "market-light": Policy(
        name="market-light",
        phase_in_years=6,
        start_cap=0.70,
        end_cap=0.45,
        training_investment=0.58,
        transparency_investment=0.70,
        small_business_support=0.74,
        exemption_generosity=0.86,
        verified_badge_strength=0.60,
        discount_subsidy=0.82,
        durability_investment=0.58,
        alternative_fiber_investment=0.62,
        workforce_support=0.72,
        enforcement_strength=0.62,
        microfiber_controls=0.54,
    ),
}


def load_requirements(csv_path: Path) -> list[RequirementRow]:
    rows: list[RequirementRow] = []
    current_section = "Primary Party"
    current_party = ""

    with csv_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        header = [column.strip() for column in next(reader)]
        header_map = {name: index for index, name in enumerate(header)}

        for raw_row in reader:
            if not any(cell.strip() for cell in raw_row):
                continue

            row = [cell.strip() for cell in raw_row]
            first_cell = row[0]
            if first_cell in {"Primary Party", "Secondary Party"}:
                current_section = first_cell
                current_party = ""
                continue

            if first_cell:
                current_party = first_cell

            rows.append(
                RequirementRow(
                    section=current_section,
                    party=current_party,
                    need=row[header_map["Need"]],
                    requirement=row[header_map["Requirement"]],
                    metric=row[header_map["Metric"]],
                    target_range=row[header_map["Target Range"]],
                    rationale=row[header_map["Rationale"]],
                    ethics=row[header_map["Ethics"]],
                )
            )

    return rows


def cap_for_year(policy: Policy, year: int) -> float:
    if year >= policy.phase_in_years:
        return policy.end_cap
    reduction = (policy.start_cap - policy.end_cap) * (year / policy.phase_in_years)
    return policy.start_cap - reduction


def simulate(policy: Policy, years: int) -> list[dict[str, float]]:
    history: list[dict[str, float]] = []
    alt_supply = 0.30
    training_coverage = 0.35
    identification_accuracy = 0.62
    compliant_capacity = 0.25
    consumer_price_index = 100.0
    discount_price_index = 100.0
    durability_index = 100.0
    fossil_fuel_index = 100.0
    microfiber_index = 100.0
    textile_waste_index = 100.0
    workers_retained = 0.91

    for year in range(1, years + 1):
        cap_limit = cap_for_year(policy, year)
        strictness = clamp((policy.start_cap - cap_limit) / max(policy.start_cap - policy.end_cap, 0.01), 0.0, 1.0)

        alt_supply = clamp(
            alt_supply
            + 0.10 * policy.alternative_fiber_investment
            + 0.03 * policy.training_investment
            - 0.015 * strictness,
            0.0,
            1.0,
        )
        training_coverage = clamp(
            training_coverage
            + 0.12 * policy.training_investment
            + 0.04 * policy.small_business_support,
            0.0,
            1.0,
        )
        identification_accuracy = clamp(
            identification_accuracy
            + 0.05 * policy.training_investment
            + 0.04 * policy.transparency_investment,
            0.0,
            1.0,
        )
        compliant_capacity = clamp(
            compliant_capacity
            + 0.11 * policy.alternative_fiber_investment
            + 0.05 * policy.enforcement_strength
            - 0.01 * strictness,
            0.0,
            1.0,
        )

        annual_price_pressure = 0.4 * strictness + 0.25 * (1.0 - alt_supply)
        annual_support_relief = 0.32 * policy.discount_subsidy + 0.28 * policy.small_business_support
        annual_general_price_change = clamp(0.6 + 1.7 * annual_price_pressure - 1.0 * annual_support_relief, -0.5, 2.5)
        annual_discount_price_change = clamp(0.5 + 1.9 * annual_price_pressure - 1.25 * policy.discount_subsidy, -0.5, 2.2)
        consumer_price_index *= 1.0 + annual_general_price_change / 100.0
        discount_price_index *= 1.0 + annual_discount_price_change / 100.0

        durability_gain = 1.1 + 2.3 * policy.durability_investment + 0.7 * alt_supply - 0.2 * strictness
        durability_index *= 1.0 + durability_gain / 100.0

        synthetic_share = clamp(cap_limit + 0.10 * policy.exemption_generosity * (1.0 - policy.enforcement_strength), 0.0, 1.0)
        fossil_fuel_drop = 0.7 + 1.7 * strictness + 1.1 * policy.alternative_fiber_investment
        microfiber_drop = 0.5 + 1.2 * strictness + 1.6 * policy.microfiber_controls
        waste_drop = 0.2 + 1.0 * policy.durability_investment + 0.6 * policy.training_investment
        fossil_fuel_index *= 1.0 - fossil_fuel_drop / 100.0
        microfiber_index *= 1.0 - microfiber_drop / 100.0
        textile_waste_index *= 1.0 - waste_drop / 100.0

        workers_retained = clamp(
            workers_retained
            + 0.015 * policy.workforce_support
            - 0.010 * strictness
            + 0.004 * policy.phase_in_years,
            0.75,
            0.995,
        )

        guidance_availability = clamp(0.48 + 0.50 * policy.training_investment + 0.18 * policy.small_business_support, 0.0, 1.0)
        mentorship_resources = max(0.0, 0.2 + 1.2 * policy.training_investment + 0.5 * policy.small_business_support)
        experienced_cost_reduction = clamp(0.05 + 0.13 * alt_supply + 0.07 * policy.small_business_support - 0.04 * strictness, 0.0, 0.30)
        customer_visit_lift = clamp(0.01 + 0.12 * policy.verified_badge_strength + 0.07 * policy.transparency_investment + 0.03 * strictness, 0.0, 0.35)
        compliance_cost_pct = clamp(0.055 + 0.028 * strictness - 0.022 * policy.small_business_support - 0.012 * policy.transparency_investment, 0.01, 0.09)
        reporting_days = clamp(2.4 + 0.9 * strictness - 1.4 * policy.transparency_investment - 0.7 * policy.small_business_support, 0.25, 4.0)
        chain_visibility = clamp(0.50 + 0.35 * policy.transparency_investment + 0.16 * policy.enforcement_strength, 0.0, 1.0)
        quality_variance = clamp(0.11 - 0.03 * policy.transparency_investment - 0.025 * policy.small_business_support, 0.02, 0.15)
        luxury_compliance = clamp(0.42 + 0.30 * strictness + 0.16 * alt_supply + 0.12 * policy.durability_investment, 0.0, 1.0)
        luxury_labeling = clamp(0.62 + 0.28 * policy.transparency_investment + 0.12 * policy.enforcement_strength, 0.0, 1.0)
        discount_price_increase = discount_price_index / 100.0 - 1.0
        discount_satisfaction = clamp(0.72 + 0.10 * policy.discount_subsidy + 0.08 * policy.durability_investment - 0.55 * discount_price_increase, 0.0, 1.0)
        general_price_increase = consumer_price_index / 100.0 - 1.0
        fiber_disclosure = clamp(0.46 + 0.35 * policy.transparency_investment + 0.24 * policy.enforcement_strength, 0.0, 1.0)
        exemption_pathway_coverage = clamp(0.30 + 0.90 * policy.exemption_generosity, 0.0, 1.0)
        viable_pathways = max(1.0, min(5.0, 1.0 + round(3.0 * alt_supply + policy.exemption_generosity)))
        compliant_production_lines = clamp(0.28 + 0.44 * alt_supply + 0.16 * strictness, 0.0, 1.0)
        retraining_region_coverage = clamp(0.30 + 0.85 * policy.workforce_support, 0.0, 1.0)
        auditability = clamp(0.45 + 0.30 * policy.transparency_investment + 0.26 * policy.enforcement_strength, 0.0, 1.0)
        public_reporting = clamp(0.48 + 0.22 * policy.transparency_investment + 0.28 * policy.enforcement_strength, 0.0, 1.0)

        history.append(
            {
                "year": year,
                "synthetic_cap_limit": cap_limit,
                "effective_synthetic_share": synthetic_share,
                "mentorship_resources_per_month": mentorship_resources,
                "guidance_availability": guidance_availability,
                "beginner_compliance_knowledge": training_coverage,
                "fast_fashion_identification_accuracy": identification_accuracy,
                "experienced_sourcing_cost_reduction": experienced_cost_reduction,
                "exemption_pathway_coverage": exemption_pathway_coverage,
                "customer_visit_lift": customer_visit_lift,
                "compliance_cost_pct_revenue": compliance_cost_pct,
                "reporting_days": reporting_days,
                "chain_visibility": chain_visibility,
                "quality_score_variance": quality_variance,
                "luxury_inventory_compliance": luxury_compliance,
                "luxury_labeling_rate": luxury_labeling,
                "discount_price_increase": discount_price_increase,
                "discount_affordable_options": viable_pathways,
                "discount_customer_satisfaction": discount_satisfaction,
                "consumer_price_increase": general_price_increase,
                "durability_improvement": durability_index / 100.0 - 1.0,
                "fiber_disclosure_rate": fiber_disclosure,
                "published_standards_coverage": 1.0,
                "compliant_category_exemptions": exemption_pathway_coverage,
                "viable_pathways": viable_pathways,
                "compliant_production_lines": compliant_production_lines,
                "workers_retained": workers_retained,
                "retraining_region_coverage": retraining_region_coverage,
                "fossil_fuel_reduction": 1.0 - fossil_fuel_index / 100.0,
                "microfiber_reduction": 1.0 - microfiber_index / 100.0,
                "textile_waste_reduction": 1.0 - textile_waste_index / 100.0,
                "auditability": auditability,
                "public_reporting_rate": public_reporting,
            }
        )

    return history


def build_checks(requirements: list[RequirementRow], policy: Policy) -> list[MetricCheck]:
    spec_by_need: dict[tuple[str, str], dict[str, object]] = {
        ("Beginner Vintage Clothes Curators", "Pricing the clothes"): {
            "metric_name": "mentorship_resources_per_month",
            "target_year": 1,
            "comparator": ">=",
            "target_value": 1.0,
            "formatter": num,
        },
        ("Beginner Vintage Clothes Curators", "Learn how to source sustainable materials and build compliant collections"): {
            "metric_name": "guidance_availability",
            "target_year": 1,
            "comparator": ">=",
            "target_value": 1.0,
            "formatter": pct,
        },
        ("Beginner Vintage Clothes Curators", "Knowledge in identifying fast fashion"): {
            "metric_name": "fast_fashion_identification_accuracy",
            "target_year": 2,
            "comparator": ">=",
            "target_value": 0.80,
            "formatter": pct,
        },
        ("Experienced Vintage Clothing Curator", "Cheaper access to sustainable goods"): {
            "metric_name": "experienced_sourcing_cost_reduction",
            "target_year": 3,
            "comparator": ">=",
            "target_value": 0.15,
            "formatter": pct,
        },
        ("Experienced Vintage Clothing Curator", "Maintain creative flexibility while adapting to new sourcing expectations"): {
            "metric_name": "exemption_pathway_coverage",
            "target_year": 2,
            "comparator": ">=",
            "target_value": 1.0,
            "formatter": pct,
        },
        ("Individual Shop Owners", "Customer Traffic"): {
            "metric_name": "customer_visit_lift",
            "target_year": 3,
            "comparator": ">=",
            "target_value": 0.15,
            "formatter": pct,
        },
        ("Individual Shop Owners", "Manage compliance without overwhelming administrative cost"): {
            "metric_name": "compliance_cost_pct_revenue",
            "target_year": 3,
            "comparator": "<=",
            "target_value": 0.05,
            "formatter": pct,
        },
        ("Chain Shop Owners", "Mass-produced & sustainable goods"): {
            "metric_name": "chain_visibility",
            "target_year": 3,
            "comparator": ">=",
            "target_value": 0.90,
            "formatter": pct,
        },
        ("Chain Shop Owners", "Control over quality of goods that are cheaply accessible"): {
            "metric_name": "quality_score_variance",
            "target_year": 3,
            "comparator": "<=",
            "target_value": 0.05,
            "formatter": pct,
        },
        ("Luxury Curators", "Preserve quality, performance, and brand identity"): {
            "metric_name": "luxury_inventory_compliance",
            "target_year": 3,
            "comparator": ">=",
            "target_value": 0.80,
            "formatter": pct,
        },
        ("Luxury Curators", "Product knowledge"): {
            "metric_name": "luxury_labeling_rate",
            "target_year": 3,
            "comparator": ">=",
            "target_value": 0.90,
            "formatter": pct,
        },
        ("Discount Curators", "Cheap suppliers"): {
            "metric_name": "discount_price_increase",
            "target_year": 3,
            "comparator": "<=",
            "target_value": 0.10,
            "formatter": pct,
        },
        ("Discount Curators", "Price-quality balance"): {
            "metric_name": "discount_customer_satisfaction",
            "target_year": 3,
            "comparator": ">=",
            "target_value": 0.80,
            "formatter": pct,
        },
        ("Personal Collector / Buyers", "Affordable access to clothes"): {
            "metric_name": "consumer_price_increase",
            "target_year": 3,
            "comparator": "<=",
            "target_value": 0.10,
            "formatter": pct,
        },
        ("Personal Collector / Buyers", "Access to durable clothes"): {
            "metric_name": "durability_improvement",
            "target_year": 5,
            "comparator": ">=",
            "target_value": 0.20,
            "formatter": pct,
        },
        ("Personal Collector / Buyers", "Clear product information"): {
            "metric_name": "fiber_disclosure_rate",
            "target_year": 2,
            "comparator": ">=",
            "target_value": 1.0,
            "formatter": pct,
        },
        ("Apparel Manufacturers", "Predictable regulation"): {
            "metric_name": "published_standards_coverage",
            "target_year": policy.phase_in_years,
            "comparator": ">=",
            "target_value": 1.0,
            "formatter": pct,
        },
        ("Apparel Manufacturers", "Flexibility in design/performance"): {
            "metric_name": "compliant_category_exemptions",
            "target_year": 2,
            "comparator": ">=",
            "target_value": 1.0,
            "formatter": pct,
        },
        ("Apparel Manufacturers", "Feasible production changes"): {
            "metric_name": "viable_pathways",
            "target_year": 3,
            "comparator": ">=",
            "target_value": 3.0,
            "formatter": num,
        },
        ("Apparel Manufacturers", "Job stability"): {
            "metric_name": "retraining_region_coverage",
            "target_year": 3,
            "comparator": ">=",
            "target_value": 1.0,
            "formatter": pct,
        },
        ("Environmental Organizations", "Lower fossil fuel dependence"): {
            "metric_name": "fossil_fuel_reduction",
            "target_year": 5,
            "comparator": ">=",
            "target_value": 0.15,
            "formatter": pct,
        },
        ("Environmental Organizations", "Reduced microfiber pollution"): {
            "metric_name": "microfiber_reduction",
            "target_year": 5,
            "comparator": ">=",
            "target_value": 0.20,
            "formatter": pct,
        },
        ("Environmental Organizations", "Lower textile waste burden"): {
            "metric_name": "textile_waste_reduction",
            "target_year": 10,
            "comparator": ">=",
            "target_value": 0.20,
            "formatter": pct,
        },
        ("Government Policymakers", "Enforceable standard"): {
            "metric_name": "auditability",
            "target_year": 2,
            "comparator": ">=",
            "target_value": 1.0,
            "formatter": pct,
        },
        ("Government Policymakers", "Enforceable public accountability"): {
            "metric_name": "public_reporting_rate",
            "target_year": 2,
            "comparator": ">=",
            "target_value": 1.0,
            "formatter": pct,
        },
    }

    checks: list[MetricCheck] = []
    for row in requirements:
        spec = spec_by_need.get((row.party, row.need))
        if not spec:
            if row.party == "Individual Shop Owners" and row.need == "Manage compliance without overwhelming administrative cost":
                checks.append(
                    MetricCheck(
                        party=row.party,
                        label=f"{row.need} ({row.metric.split(',')[1].strip()})",
                        metric_name="reporting_days",
                        target_year=3,
                        comparator="<=",
                        target_value=1.0,
                        formatter=num,
                    )
                )
            elif row.party == "Discount Curators" and row.need == "Cheap suppliers":
                checks.append(
                    MetricCheck(
                        party=row.party,
                        label=f"{row.need} (affordable compliant fabric options)",
                        metric_name="discount_affordable_options",
                        target_year=3,
                        comparator=">=",
                        target_value=3.0,
                        formatter=num,
                    )
                )
            continue

        checks.append(
            MetricCheck(
                party=row.party,
                label=row.need,
                metric_name=spec["metric_name"],  # type: ignore[arg-type]
                target_year=spec["target_year"],  # type: ignore[arg-type]
                comparator=spec["comparator"],  # type: ignore[arg-type]
                target_value=spec["target_value"],  # type: ignore[arg-type]
                formatter=spec["formatter"],  # type: ignore[arg-type]
            )
        )

    return checks


def policy_outline(policy: Policy) -> list[str]:
    return [
        (
            f"Phase in a cap from {pct(policy.start_cap)} synthetic content to "
            f"{pct(policy.end_cap)} over {policy.phase_in_years} years."
        ),
        (
            f"Fund retailer training/support at {pct(policy.training_investment)} intensity "
            f"with small-business relief at {pct(policy.small_business_support)}."
        ),
        (
            f"Require strong disclosure/reporting at {pct(policy.transparency_investment)} "
            f"and enforcement at {pct(policy.enforcement_strength)}."
        ),
        (
            f"Allow targeted exemptions at {pct(policy.exemption_generosity)} for functional "
            "garments while preserving category-specific standards."
        ),
        (
            f"Offset affordability risk with discount subsidies at {pct(policy.discount_subsidy)} "
            f"and verified-store incentives at {pct(policy.verified_badge_strength)}."
        ),
        (
            f"Back manufacturing transition with alternative-fiber investment at "
            f"{pct(policy.alternative_fiber_investment)} and workforce support at {pct(policy.workforce_support)}."
        ),
    ]


def summarize_requirements(requirements: list[RequirementRow]) -> str:
    parties = sorted({row.party for row in requirements})
    sections = sorted({row.section for row in requirements})
    return (
        f"Loaded {len(requirements)} requirements across {len(parties)} stakeholder groups "
        f"and {len(sections)} sections."
    )


def evaluate_checks(history: list[dict[str, float]], checks: list[MetricCheck]) -> list[CheckResult]:
    return [CheckResult(check=check, passed=passed, actual=actual) for check in checks for passed, actual in [check.evaluate(history)]]


def summarize_metrics(history: list[dict[str, float]]) -> list[tuple[str, str]]:
    final = history[-1]
    return [(label, formatter(final[key])) for key, label, formatter in SUMMARY_METRICS]


def format_check_result(result: CheckResult) -> str:
    target = result.check.formatter(result.check.target_value)
    actual_str = result.check.formatter(result.actual)
    return f"- {result.check.party}: {result.check.label} -> {actual_str} vs target {result.check.comparator} {target}"


def attainment_score(result: CheckResult) -> float:
    target = max(result.check.target_value, 1e-9)
    actual = max(result.actual, 0.0)
    if result.check.comparator == ">=":
        return clamp(actual / target, 0.0, 1.2)
    return clamp(target / max(actual, 1e-9), 0.0, 1.2)


def render(history: list[dict[str, float]], checks: list[MetricCheck], requirements: list[RequirementRow], policy: Policy) -> str:
    results = evaluate_checks(history, checks)
    passed_checks = [format_check_result(result) for result in results if result.passed]
    failed_checks = [format_check_result(result) for result in results if not result.passed]
    pass_rate = len(passed_checks) / len(results) if results else 0.0
    lines = [
        "Synthetic Material Capping Policy Simulation",
        "===========================================",
        summarize_requirements(requirements),
        f"Scenario: {policy.name}",
        "",
        "Policy sketch:",
        *[f"- {line}" for line in policy_outline(policy)],
        "",
        f"{len(history)}-year outlook:",
        *[f"- {label}: {value}" for label, value in summarize_metrics(history)],
        "",
        f"Requirement pass rate: {len(passed_checks)}/{len(results)} ({pct(pass_rate)})",
        "",
        "Missed or at-risk targets:",
    ]

    if failed_checks:
        lines.extend(failed_checks)
    else:
        lines.append("- None")

    if passed_checks:
        lines.extend(
            [
                "",
                "Targets currently met:",
                *passed_checks[:10],
            ]
        )

    return "\n".join(lines)


def print_yearly_table(history: list[dict[str, float]]) -> str:
    columns = [
        ("year", "Year"),
        ("synthetic_cap_limit", "Cap"),
        ("consumer_price_increase", "ConsumerPrice"),
        ("durability_improvement", "Durability"),
        ("fossil_fuel_reduction", "FossilFuel"),
        ("microfiber_reduction", "Microfiber"),
    ]
    header = " | ".join(name.ljust(13) for _, name in columns)
    divider = "-+-".join("-" * 13 for _ in columns)
    rows = [header, divider]
    for row in history:
        values = []
        for key, _ in columns:
            value = row[key]
            if key == "year":
                values.append(str(int(value)).ljust(13))
            else:
                values.append(pct(value).ljust(13))
        rows.append(" | ".join(values))
    return "\n".join(rows)


def analyze_policy(requirements: list[RequirementRow], policy: Policy, years: int) -> tuple[list[dict[str, float]], list[MetricCheck], list[CheckResult]]:
    history = simulate(policy, max(years, 10))
    trimmed_history = history[:years]
    checks = build_checks(requirements, policy)
    results = evaluate_checks(trimmed_history, checks)
    return trimmed_history, checks, results


def launch_gui(csv_path: Path) -> None:
    import tkinter as tk
    from tkinter import ttk

    requirements = load_requirements(csv_path)

    class PolicyDashboard:
        slider_specs = [
            ("phase_in_years", "Phase-in years", 3, 10, 1),
            ("end_cap", "Final cap (%)", 15, 60, 1),
            ("training_investment", "Training intensity (%)", 20, 100, 1),
            ("transparency_investment", "Transparency (%)", 20, 100, 1),
            ("small_business_support", "Small-business support (%)", 20, 100, 1),
            ("exemption_generosity", "Exemption generosity (%)", 0, 100, 1),
            ("verified_badge_strength", "Verified badge effect (%)", 0, 100, 1),
            ("discount_subsidy", "Discount subsidy (%)", 0, 100, 1),
            ("durability_investment", "Durability investment (%)", 0, 100, 1),
            ("alternative_fiber_investment", "Alternative fiber investment (%)", 0, 100, 1),
            ("workforce_support", "Workforce transition support (%)", 0, 100, 1),
            ("enforcement_strength", "Enforcement strength (%)", 0, 100, 1),
            ("microfiber_controls", "Microfiber controls (%)", 0, 100, 1),
        ]

        def __init__(self, root: tk.Tk) -> None:
            self.root = root
            self.root.title("Synthetic Material Capping Dashboard")
            self.root.geometry("1440x920")
            self.root.minsize(1180, 760)
            self.root.configure(bg="#f3efe4")

            style = ttk.Style()
            style.theme_use("clam")
            style.configure("TFrame", background="#f3efe4")
            style.configure("Panel.TFrame", background="#fffaf2")
            style.configure("Card.TFrame", background="#fff6dc")
            style.configure("Header.TLabel", background="#f3efe4", foreground="#243646", font=("TkDefaultFont", 16, "bold"))
            style.configure("Subhead.TLabel", background="#f3efe4", foreground="#51606b", font=("TkDefaultFont", 10))
            style.configure("Panel.TLabel", background="#fffaf2", foreground="#243646")
            style.configure("CardTitle.TLabel", background="#fff6dc", foreground="#6b5130", font=("TkDefaultFont", 9, "bold"))
            style.configure("CardValue.TLabel", background="#fff6dc", foreground="#243646", font=("TkDefaultFont", 14, "bold"))
            style.configure("Accent.TButton", background="#24577a", foreground="#ffffff")
            style.map("Accent.TButton", background=[("active", "#1f4b69")])
            style.configure("Treeview", rowheight=24, fieldbackground="#fffdf8", background="#fffdf8", foreground="#243646")
            style.configure("Treeview.Heading", background="#e7dcc4", foreground="#243646", font=("TkDefaultFont", 9, "bold"))

            self.scenario_var = tk.StringVar(value="balanced")
            self.years_var = tk.IntVar(value=10)
            self.slider_vars: dict[str, tk.DoubleVar] = {}
            self.slider_value_labels: dict[str, ttk.Label] = {}
            self.summary_labels: dict[str, ttk.Label] = {}
            self.pass_rate_var = tk.StringVar()
            self.summary_text_var = tk.StringVar()
            self.policy_notes_var = tk.StringVar()
            self.refresh_job: str | None = None
            self.chart_canvas: tk.Canvas | None = None
            self.results_tree: ttk.Treeview | None = None
            self.yearly_tree: ttk.Treeview | None = None
            self.requirements_tree: ttk.Treeview | None = None

            self._build_layout()
            self.apply_scenario()

        def _build_layout(self) -> None:
            shell = ttk.Frame(self.root, padding=16)
            shell.pack(fill="both", expand=True)
            shell.columnconfigure(1, weight=1)
            shell.rowconfigure(0, weight=1)

            controls = ttk.Frame(shell, style="Panel.TFrame", padding=14)
            controls.grid(row=0, column=0, sticky="nsw", padx=(0, 16))
            controls.rowconfigure(3, weight=1)

            ttk.Label(controls, text="Policy Studio", style="Header.TLabel").grid(row=0, column=0, sticky="w")
            ttk.Label(
                controls,
                text="Tune the cap policy and inspect stakeholder tradeoffs from the requirements table.",
                style="Subhead.TLabel",
                wraplength=280,
                justify="left",
            ).grid(row=1, column=0, sticky="w", pady=(2, 12))

            preset_row = ttk.Frame(controls, style="Panel.TFrame")
            preset_row.grid(row=2, column=0, sticky="ew", pady=(0, 12))
            preset_row.columnconfigure(0, weight=1)
            preset_row.columnconfigure(1, weight=1)
            ttk.Label(preset_row, text="Scenario preset", style="Panel.TLabel").grid(row=0, column=0, sticky="w")
            scenario_box = ttk.Combobox(
                preset_row,
                textvariable=self.scenario_var,
                values=sorted(SCENARIOS),
                state="readonly",
            )
            scenario_box.grid(row=1, column=0, sticky="ew", pady=(4, 0), padx=(0, 8))
            scenario_box.bind("<<ComboboxSelected>>", lambda _event: self.apply_scenario())
            ttk.Label(preset_row, text="Display years", style="Panel.TLabel").grid(row=0, column=1, sticky="w")
            year_box = ttk.Spinbox(preset_row, from_=5, to=10, textvariable=self.years_var, width=8, command=self.refresh)
            year_box.grid(row=1, column=1, sticky="ew", pady=(4, 0))
            self.years_var.trace_add("write", lambda *_args: self.schedule_refresh())

            scroll_host = ttk.Frame(controls, style="Panel.TFrame")
            scroll_host.grid(row=3, column=0, sticky="nsew")
            scroll_host.rowconfigure(0, weight=1)
            scroll_host.columnconfigure(0, weight=1)
            controls_canvas = tk.Canvas(scroll_host, bg="#fffaf2", highlightthickness=0, width=300)
            controls_canvas.grid(row=0, column=0, sticky="nsew")
            controls_scroll = ttk.Scrollbar(scroll_host, orient="vertical", command=controls_canvas.yview)
            controls_scroll.grid(row=0, column=1, sticky="ns")
            controls_canvas.configure(yscrollcommand=controls_scroll.set)
            controls_inner = ttk.Frame(controls_canvas, style="Panel.TFrame", padding=(0, 0, 6, 0))
            controls_canvas.create_window((0, 0), window=controls_inner, anchor="nw", tags="controls_inner")
            controls_inner.bind(
                "<Configure>",
                lambda _event: controls_canvas.configure(scrollregion=controls_canvas.bbox("all")),
            )
            controls_canvas.bind(
                "<Configure>",
                lambda event: controls_canvas.itemconfigure("controls_inner", width=event.width),
            )

            for row_index, (field, label, minimum, maximum, step) in enumerate(self.slider_specs):
                var = tk.DoubleVar()
                self.slider_vars[field] = var
                block = ttk.Frame(controls_inner, style="Panel.TFrame", padding=(0, 6))
                block.grid(row=row_index, column=0, sticky="ew")
                block.columnconfigure(0, weight=1)
                value_label = ttk.Label(block, text="", style="Panel.TLabel")
                value_label.grid(row=0, column=1, sticky="e")
                self.slider_value_labels[field] = value_label
                ttk.Label(block, text=label, style="Panel.TLabel").grid(row=0, column=0, sticky="w")
                scale = tk.Scale(
                    block,
                    from_=minimum,
                    to=maximum,
                    resolution=step,
                    orient="horizontal",
                    variable=var,
                    showvalue=False,
                    bg="#fffaf2",
                    troughcolor="#d7c8aa",
                    highlightthickness=0,
                    activebackground="#24577a",
                    command=lambda _value, name=field, out=value_label: self._on_slider_change(name, out),
                )
                scale.grid(row=1, column=0, columnspan=2, sticky="ew")
                self._update_slider_label(field, value_label)

            action_row = ttk.Frame(controls, style="Panel.TFrame")
            action_row.grid(row=4, column=0, sticky="ew", pady=(12, 0))
            action_row.columnconfigure(0, weight=1)
            action_row.columnconfigure(1, weight=1)
            ttk.Button(action_row, text="Apply preset", command=self.apply_scenario).grid(row=0, column=0, sticky="ew", padx=(0, 6))
            ttk.Button(action_row, text="Refresh", style="Accent.TButton", command=self.refresh).grid(row=0, column=1, sticky="ew")

            content = ttk.Frame(shell)
            content.grid(row=0, column=1, sticky="nsew")
            content.columnconfigure(0, weight=1)
            content.rowconfigure(2, weight=1)

            header = ttk.Frame(content)
            header.grid(row=0, column=0, sticky="ew")
            header.columnconfigure(0, weight=1)
            ttk.Label(header, text="Synthetic Material Capping Program", style="Header.TLabel").grid(row=0, column=0, sticky="w")
            ttk.Label(header, textvariable=self.summary_text_var, style="Subhead.TLabel").grid(row=1, column=0, sticky="w", pady=(4, 0))
            ttk.Label(header, textvariable=self.pass_rate_var, style="Subhead.TLabel").grid(row=0, column=1, sticky="e")

            cards = ttk.Frame(content)
            cards.grid(row=1, column=0, sticky="ew", pady=(16, 16))
            for index, (_key, label, _formatter) in enumerate(SUMMARY_METRICS[:6]):
                card = ttk.Frame(cards, style="Card.TFrame", padding=12)
                card.grid(row=0, column=index, sticky="nsew", padx=(0, 10 if index < 5 else 0))
                cards.columnconfigure(index, weight=1)
                ttk.Label(card, text=label, style="CardTitle.TLabel", wraplength=140, justify="left").pack(anchor="w")
                value = ttk.Label(card, text="--", style="CardValue.TLabel")
                value.pack(anchor="w", pady=(8, 0))
                self.summary_labels[label] = value

            lower = ttk.Panedwindow(content, orient="vertical")
            lower.grid(row=2, column=0, sticky="nsew")

            chart_panel = ttk.Frame(lower, style="Panel.TFrame", padding=12)
            chart_panel.columnconfigure(0, weight=1)
            chart_panel.rowconfigure(1, weight=1)
            ttk.Label(chart_panel, text="Trajectory View", style="Panel.TLabel").grid(row=0, column=0, sticky="w")
            self.chart_canvas = tk.Canvas(chart_panel, bg="#fffdf8", highlightthickness=0, height=300)
            self.chart_canvas.grid(row=1, column=0, sticky="nsew", pady=(8, 0))
            lower.add(chart_panel, weight=3)

            notebook = ttk.Notebook(lower)
            lower.add(notebook, weight=4)

            results_frame = ttk.Frame(notebook, padding=8)
            results_frame.rowconfigure(0, weight=1)
            results_frame.columnconfigure(0, weight=1)
            self.results_tree = ttk.Treeview(
                results_frame,
                columns=("party", "need", "status", "actual", "target", "year"),
                show="headings",
            )
            for column, title, width in [
                ("party", "Stakeholder", 210),
                ("need", "Need", 320),
                ("status", "Status", 90),
                ("actual", "Actual", 100),
                ("target", "Target", 120),
                ("year", "Check year", 90),
            ]:
                self.results_tree.heading(column, text=title)
                self.results_tree.column(column, width=width, anchor="w")
            self.results_tree.grid(row=0, column=0, sticky="nsew")
            results_scroll = ttk.Scrollbar(results_frame, orient="vertical", command=self.results_tree.yview)
            results_scroll.grid(row=0, column=1, sticky="ns")
            self.results_tree.configure(yscrollcommand=results_scroll.set)
            notebook.add(results_frame, text="Requirement checks")

            yearly_frame = ttk.Frame(notebook, padding=8)
            yearly_frame.rowconfigure(0, weight=1)
            yearly_frame.columnconfigure(0, weight=1)
            self.yearly_tree = ttk.Treeview(
                yearly_frame,
                columns=("year", "cap", "share", "price", "durability", "fossil", "microfiber"),
                show="headings",
            )
            for column, title, width in [
                ("year", "Year", 60),
                ("cap", "Cap", 90),
                ("share", "Actual share", 110),
                ("price", "Consumer price", 110),
                ("durability", "Durability", 100),
                ("fossil", "Fossil reduction", 110),
                ("microfiber", "Microfiber reduction", 130),
            ]:
                self.yearly_tree.heading(column, text=title)
                self.yearly_tree.column(column, width=width, anchor="center")
            self.yearly_tree.grid(row=0, column=0, sticky="nsew")
            yearly_scroll = ttk.Scrollbar(yearly_frame, orient="vertical", command=self.yearly_tree.yview)
            yearly_scroll.grid(row=0, column=1, sticky="ns")
            self.yearly_tree.configure(yscrollcommand=yearly_scroll.set)
            notebook.add(yearly_frame, text="Yearly metrics")

            requirements_frame = ttk.Frame(notebook, padding=8)
            requirements_frame.rowconfigure(0, weight=1)
            requirements_frame.columnconfigure(0, weight=1)
            self.requirements_tree = ttk.Treeview(
                requirements_frame,
                columns=("party", "need", "target", "ethics"),
                show="headings",
            )
            for column, title, width in [
                ("party", "Stakeholder", 210),
                ("need", "Need", 280),
                ("target", "Target range", 240),
                ("ethics", "Ethics", 320),
            ]:
                self.requirements_tree.heading(column, text=title)
                self.requirements_tree.column(column, width=width, anchor="w")
            self.requirements_tree.grid(row=0, column=0, sticky="nsew")
            req_scroll = ttk.Scrollbar(requirements_frame, orient="vertical", command=self.requirements_tree.yview)
            req_scroll.grid(row=0, column=1, sticky="ns")
            self.requirements_tree.configure(yscrollcommand=req_scroll.set)
            notebook.add(requirements_frame, text="Requirements source")

            notes = ttk.Label(
                content,
                textvariable=self.policy_notes_var,
                style="Subhead.TLabel",
                justify="left",
                wraplength=980,
            )
            notes.grid(row=3, column=0, sticky="ew", pady=(12, 0))

        def _update_slider_label(self, field: str, label: ttk.Label) -> None:
            value = self.slider_vars[field].get()
            if field == "phase_in_years":
                label.config(text=str(int(round(value))))
            else:
                label.config(text=f"{value:.0f}%")

        def _on_slider_change(self, field: str, label: ttk.Label) -> None:
            self._update_slider_label(field, label)
            self.schedule_refresh()

        def schedule_refresh(self) -> None:
            if self.refresh_job is not None:
                self.root.after_cancel(self.refresh_job)
            self.refresh_job = self.root.after(120, self.refresh)

        def _policy_from_controls(self) -> Policy:
            return Policy(
                name=f"{self.scenario_var.get()} custom",
                phase_in_years=int(round(self.slider_vars["phase_in_years"].get())),
                start_cap=0.70,
                end_cap=self.slider_vars["end_cap"].get() / 100.0,
                training_investment=self.slider_vars["training_investment"].get() / 100.0,
                transparency_investment=self.slider_vars["transparency_investment"].get() / 100.0,
                small_business_support=self.slider_vars["small_business_support"].get() / 100.0,
                exemption_generosity=self.slider_vars["exemption_generosity"].get() / 100.0,
                verified_badge_strength=self.slider_vars["verified_badge_strength"].get() / 100.0,
                discount_subsidy=self.slider_vars["discount_subsidy"].get() / 100.0,
                durability_investment=self.slider_vars["durability_investment"].get() / 100.0,
                alternative_fiber_investment=self.slider_vars["alternative_fiber_investment"].get() / 100.0,
                workforce_support=self.slider_vars["workforce_support"].get() / 100.0,
                enforcement_strength=self.slider_vars["enforcement_strength"].get() / 100.0,
                microfiber_controls=self.slider_vars["microfiber_controls"].get() / 100.0,
            )

        def apply_scenario(self) -> None:
            policy = SCENARIOS[self.scenario_var.get()]
            for field, _label, _minimum, _maximum, _step in self.slider_specs:
                value = getattr(policy, field)
                if field == "phase_in_years":
                    self.slider_vars[field].set(value)
                elif field == "end_cap":
                    self.slider_vars[field].set(value * 100.0)
                else:
                    self.slider_vars[field].set(value * 100.0)
                self._update_slider_label(field, self.slider_value_labels[field])
            self.refresh()

        def refresh(self) -> None:
            self.refresh_job = None
            years = int(self.years_var.get())
            policy = self._policy_from_controls()
            history, _checks, results = analyze_policy(requirements, policy, years)
            passed = sum(1 for result in results if result.passed)
            self.summary_text_var.set(summarize_requirements(requirements))
            avg_attainment = sum(attainment_score(result) for result in results) / len(results) if results else 0.0
            self.pass_rate_var.set(
                f"Requirement pass rate: {passed}/{len(results)} ({pct(passed / len(results) if results else 0.0)})"
                f"   |   Average target attainment: {pct(avg_attainment)}"
            )
            self.policy_notes_var.set("Policy sketch: " + " ".join(policy_outline(policy)))

            for label, value in summarize_metrics(history)[:6]:
                self.summary_labels[label].config(text=value)

            self._draw_chart(history)
            self._populate_results(results)
            self._populate_years(history)
            self._populate_requirements()

        def _draw_chart(self, history: list[dict[str, float]]) -> None:
            if self.chart_canvas is None:
                return
            import tkinter.font as tkfont

            canvas = self.chart_canvas
            canvas.delete("all")
            canvas.update_idletasks()
            width = max(canvas.winfo_width(), 720)
            height = max(canvas.winfo_height(), 280)
            left = 72
            right = 20
            bottom = 62
            legend_font = tkfont.nametofont("TkDefaultFont")
            available_legend_width = max(width - left - right, 240)
            current_row_width = 0
            legend_rows = 1
            for _metric_name, label, color in CHART_METRICS:
                item_width = 26 + legend_font.measure(label)
                if current_row_width and current_row_width + item_width > available_legend_width:
                    legend_rows += 1
                    current_row_width = 0
                current_row_width += item_width + 22
            top = 24 + (legend_rows * 20)
            plot_width = width - left - right
            plot_height = height - top - bottom
            canvas.create_rectangle(0, 0, width, height, fill="#fffdf8", outline="")
            canvas.create_text(
                left + plot_width / 2,
                height - 18,
                text="Year",
                fill="#243646",
                font=("TkDefaultFont", 9, "bold"),
            )
            canvas.create_text(
                18,
                top + plot_height / 2,
                text="Metric value (%)",
                angle=90,
                fill="#243646",
                font=("TkDefaultFont", 9, "bold"),
            )

            for tick in range(0, 101, 20):
                y = top + plot_height - (tick / 100.0) * plot_height
                canvas.create_line(left, y, width - right, y, fill="#e4d7c4")
                canvas.create_text(left - 10, y, text=f"{tick}%", anchor="e", fill="#6a7883", font=("TkDefaultFont", 8))

            if len(history) == 1:
                x_positions = [left + plot_width / 2]
            else:
                x_positions = [left + index * plot_width / (len(history) - 1) for index in range(len(history))]

            canvas.create_line(left, top, left, height - bottom, fill="#60707c", width=1)
            canvas.create_line(left, height - bottom, width - right, height - bottom, fill="#60707c", width=1)

            for x, row in zip(x_positions, history):
                canvas.create_text(x, height - bottom + 16, text=str(int(row["year"])), anchor="n", fill="#6a7883", font=("TkDefaultFont", 8))

            legend_x = left
            legend_y = 10
            current_row_width = 0
            for metric_name, label, color in CHART_METRICS:
                item_width = 26 + legend_font.measure(label)
                if current_row_width and current_row_width + item_width > available_legend_width:
                    legend_x = left
                    legend_y += 20
                    current_row_width = 0
                points: list[float] = []
                for x, row in zip(x_positions, history):
                    value = clamp(row[metric_name], 0.0, 1.0)
                    y = top + plot_height - value * plot_height
                    points.extend([x, y])
                if len(points) >= 4:
                    canvas.create_line(*points, fill=color, width=2, smooth=True)
                for x, row in zip(x_positions, history):
                    value = clamp(row[metric_name], 0.0, 1.0)
                    y = top + plot_height - value * plot_height
                    canvas.create_oval(x - 2, y - 2, x + 2, y + 2, fill=color, outline=color)
                canvas.create_rectangle(legend_x, legend_y, legend_x + 10, legend_y + 10, fill=color, outline="")
                canvas.create_text(legend_x + 16, legend_y + 5, text=label, anchor="w", fill="#243646", font=("TkDefaultFont", 8))
                legend_x += item_width + 22
                current_row_width += item_width + 22

        def _populate_results(self, results: list[CheckResult]) -> None:
            if self.results_tree is None:
                return
            tree = self.results_tree
            for item in tree.get_children():
                tree.delete(item)
            for result in sorted(results, key=lambda item: (item.passed, item.check.party, item.check.label)):
                status = "Pass" if result.passed else "Risk"
                actual = result.check.formatter(result.actual)
                target = f"{result.check.comparator} {result.check.formatter(result.check.target_value)}"
                tree.insert("", "end", values=(result.check.party, result.check.label, status, actual, target, result.check.target_year))

        def _populate_years(self, history: list[dict[str, float]]) -> None:
            if self.yearly_tree is None:
                return
            tree = self.yearly_tree
            for item in tree.get_children():
                tree.delete(item)
            for row in history:
                tree.insert(
                    "",
                    "end",
                    values=(
                        int(row["year"]),
                        pct(row["synthetic_cap_limit"]),
                        pct(row["effective_synthetic_share"]),
                        pct(row["consumer_price_increase"]),
                        pct(row["durability_improvement"]),
                        pct(row["fossil_fuel_reduction"]),
                        pct(row["microfiber_reduction"]),
                    ),
                )

        def _populate_requirements(self) -> None:
            if self.requirements_tree is None or self.requirements_tree.get_children():
                return
            for row in requirements:
                self.requirements_tree.insert("", "end", values=(row.party, row.need, row.target_range, row.ethics))

    try:
        root = tk.Tk()
    except tk.TclError as exc:
        raise SystemExit(f"Unable to launch Tkinter GUI: {exc}") from exc
    PolicyDashboard(root)
    root.mainloop()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=Path("requirements_table.csv"), help="Path to the requirements CSV.")
    parser.add_argument("--scenario", choices=sorted(SCENARIOS), default="balanced", help="Policy scenario to simulate.")
    parser.add_argument("--years", type=int, default=10, help="Number of years to simulate.")
    parser.add_argument("--show-yearly", action="store_true", help="Print the yearly trajectory table.")
    parser.add_argument("--gui", action="store_true", help="Launch a Tkinter dashboard.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.gui:
        launch_gui(args.csv)
        return

    requirements = load_requirements(args.csv)
    policy = SCENARIOS[args.scenario]
    history, checks, _results = analyze_policy(requirements, policy, args.years)
    print(render(history, checks, requirements, policy))
    if args.show_yearly:
        print()
        print(print_yearly_table(history))


if __name__ == "__main__":
    main()
