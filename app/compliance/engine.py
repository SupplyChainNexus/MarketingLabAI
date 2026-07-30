"""Compliance evaluation orchestration."""

from __future__ import annotations

from collections.abc import Callable
from uuid import uuid4

from app.compliance.models import (
    BrandRule,
    ComplianceFinding,
    ComplianceReport,
    ComplianceStatus,
    ReviewSubjectType,
    current_utc_timestamp,
)
from app.compliance.repository import BrandRuleRepository

RuleEvaluator = Callable[
    [BrandRule, str, ReviewSubjectType, str],
    ComplianceFinding,
]


class ComplianceEngine:
    """Evaluate marketing content against active brand rules."""

    def __init__(
        self,
        repository: BrandRuleRepository,
        evaluators: dict[str, RuleEvaluator] | None = None,
    ) -> None:
        self.repository = repository
        self.evaluators = dict(evaluators or {})

    def register_evaluator(
        self,
        rule_id: str,
        evaluator: RuleEvaluator,
    ) -> None:
        """Register or replace an evaluator for a rule."""

        cleaned_rule_id = rule_id.strip()

        if not cleaned_rule_id:
            raise ValueError("rule_id is required.")

        self.evaluators[cleaned_rule_id] = evaluator

    def evaluate(
        self,
        *,
        brand_id: str,
        subject_id: str,
        subject_type: ReviewSubjectType | str,
        content: str,
    ) -> ComplianceReport:
        """Evaluate one marketing asset and return a completed report."""

        cleaned_brand_id = brand_id.strip()
        cleaned_subject_id = subject_id.strip()

        if not cleaned_brand_id:
            raise ValueError("brand_id is required.")

        if not cleaned_subject_id:
            raise ValueError("subject_id is required.")

        converted_subject_type = ReviewSubjectType(subject_type)
        rules = [
            rule
            for rule in self.repository.list_for_brand(cleaned_brand_id)
            if rule.applies_to(converted_subject_type)
        ]

        report = ComplianceReport(
            report_id=str(uuid4()),
            brand_id=cleaned_brand_id,
            subject_id=cleaned_subject_id,
            subject_type=converted_subject_type,
            ruleset_version=self._ruleset_version(rules),
        )

        for rule in rules:
            evaluator = self.evaluators.get(rule.rule_id)

            if evaluator is None:
                finding = self._missing_evaluator_finding(
                    rule=rule,
                    subject_id=cleaned_subject_id,
                    subject_type=converted_subject_type,
                )
            else:
                finding = evaluator(
                    rule,
                    cleaned_subject_id,
                    converted_subject_type,
                    content,
                )
                self._validate_finding(
                    finding=finding,
                    rule=rule,
                    subject_id=cleaned_subject_id,
                    subject_type=converted_subject_type,
                )

            report.add_finding(finding)

        report.status = self._report_status(report.findings)
        report.summary = self._summary(report)
        report.completed_at = current_utc_timestamp()

        return report

    @staticmethod
    def create_finding(
        *,
        rule: BrandRule,
        subject_id: str,
        subject_type: ReviewSubjectType,
        status: ComplianceStatus,
        message: str,
        evidence: list[str] | None = None,
        recommendation: str = "",
    ) -> ComplianceFinding:
        """Create a finding linked to a rule and review subject."""

        return ComplianceFinding(
            finding_id=str(uuid4()),
            rule_id=rule.rule_id,
            subject_id=subject_id,
            subject_type=subject_type,
            status=status,
            severity=rule.severity,
            evaluation_method=rule.evaluation_method,
            message=message,
            evidence=evidence or [],
            recommendation=recommendation,
        )

    @classmethod
    def _missing_evaluator_finding(
        cls,
        *,
        rule: BrandRule,
        subject_id: str,
        subject_type: ReviewSubjectType,
    ) -> ComplianceFinding:
        return cls.create_finding(
            rule=rule,
            subject_id=subject_id,
            subject_type=subject_type,
            status=ComplianceStatus.REQUIRES_REVIEW,
            message=f"Rule '{rule.name}' requires an evaluator.",
            recommendation="Configure an evaluator or complete a manual review.",
        )

    @staticmethod
    def _validate_finding(
        *,
        finding: ComplianceFinding,
        rule: BrandRule,
        subject_id: str,
        subject_type: ReviewSubjectType,
    ) -> None:
        if finding.rule_id != rule.rule_id:
            raise ValueError(
                f"Evaluator for '{rule.rule_id}' returned a finding "
                "for a different rule."
            )

        if finding.subject_id != subject_id:
            raise ValueError(
                f"Evaluator for '{rule.rule_id}' returned a finding "
                "for a different subject."
            )

        if finding.subject_type != subject_type:
            raise ValueError(
                f"Evaluator for '{rule.rule_id}' returned a finding "
                "for a different subject type."
            )

    @staticmethod
    def _report_status(
        findings: list[ComplianceFinding],
    ) -> ComplianceStatus:
        if not findings:
            return ComplianceStatus.COMPLIANT

        if any(
            finding.status == ComplianceStatus.NON_COMPLIANT for finding in findings
        ):
            return ComplianceStatus.NON_COMPLIANT

        if any(
            finding.status
            in {
                ComplianceStatus.PENDING,
                ComplianceStatus.REQUIRES_REVIEW,
            }
            for finding in findings
        ):
            return ComplianceStatus.REQUIRES_REVIEW

        return ComplianceStatus.COMPLIANT

    @staticmethod
    def _ruleset_version(rules: list[BrandRule]) -> str:
        return ",".join(
            f"{rule.rule_id}:v{rule.version}"
            for rule in sorted(rules, key=lambda item: item.rule_id)
        )

    @staticmethod
    def _summary(report: ComplianceReport) -> str:
        total = len(report.findings)
        non_compliant = sum(
            finding.status == ComplianceStatus.NON_COMPLIANT
            for finding in report.findings
        )
        review = sum(
            finding.status
            in {
                ComplianceStatus.PENDING,
                ComplianceStatus.REQUIRES_REVIEW,
            }
            for finding in report.findings
        )
        compliant = sum(
            finding.status == ComplianceStatus.COMPLIANT for finding in report.findings
        )

        return (
            f"Evaluated {total} rule(s): {compliant} compliant, "
            f"{non_compliant} non-compliant, {review} requiring review."
        )


def prohibited_phrase_evaluator(
    prohibited_phrase: str,
) -> RuleEvaluator:
    """Build a deterministic evaluator for a prohibited phrase."""

    cleaned_phrase = prohibited_phrase.strip()

    if not cleaned_phrase:
        raise ValueError("prohibited_phrase is required.")

    def evaluate(
        rule: BrandRule,
        subject_id: str,
        subject_type: ReviewSubjectType,
        content: str,
    ) -> ComplianceFinding:
        matched = cleaned_phrase.casefold() in content.casefold()

        if matched:
            return ComplianceEngine.create_finding(
                rule=rule,
                subject_id=subject_id,
                subject_type=subject_type,
                status=ComplianceStatus.NON_COMPLIANT,
                message=f"Prohibited phrase detected: '{cleaned_phrase}'.",
                evidence=[cleaned_phrase],
                recommendation="Remove or replace the prohibited phrase.",
            )

        return ComplianceEngine.create_finding(
            rule=rule,
            subject_id=subject_id,
            subject_type=subject_type,
            status=ComplianceStatus.COMPLIANT,
            message=f"Prohibited phrase not detected: '{cleaned_phrase}'.",
        )

    return evaluate
