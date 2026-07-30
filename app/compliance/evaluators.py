"""Reusable deterministic compliance evaluators."""

from __future__ import annotations

import re
from re import Pattern
from urllib.parse import urlparse

from app.compliance.engine import ComplianceEngine, RuleEvaluator
from app.compliance.models import (
    BrandRule,
    ComplianceFinding,
    ComplianceStatus,
    ReviewSubjectType,
)


def required_phrase_evaluator(required_phrase: str) -> RuleEvaluator:
    """Require a phrase to appear in the reviewed content."""

    cleaned_phrase = required_phrase.strip()

    if not cleaned_phrase:
        raise ValueError("required_phrase is required.")

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
                status=ComplianceStatus.COMPLIANT,
                message=f"Required phrase detected: '{cleaned_phrase}'.",
                evidence=[cleaned_phrase],
            )

        return ComplianceEngine.create_finding(
            rule=rule,
            subject_id=subject_id,
            subject_type=subject_type,
            status=ComplianceStatus.NON_COMPLIANT,
            message=f"Required phrase missing: '{cleaned_phrase}'.",
            recommendation=f"Add the required phrase: '{cleaned_phrase}'.",
        )

    return evaluate


def required_url_evaluator(required_url: str) -> RuleEvaluator:
    """Require an exact URL to appear in the reviewed content."""

    cleaned_url = required_url.strip()
    parsed_url = urlparse(cleaned_url)

    if not cleaned_url:
        raise ValueError("required_url is required.")

    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        raise ValueError("required_url must be a valid HTTP or HTTPS URL.")

    def evaluate(
        rule: BrandRule,
        subject_id: str,
        subject_type: ReviewSubjectType,
        content: str,
    ) -> ComplianceFinding:
        matched = cleaned_url.casefold() in content.casefold()

        if matched:
            return ComplianceEngine.create_finding(
                rule=rule,
                subject_id=subject_id,
                subject_type=subject_type,
                status=ComplianceStatus.COMPLIANT,
                message=f"Required URL detected: '{cleaned_url}'.",
                evidence=[cleaned_url],
            )

        return ComplianceEngine.create_finding(
            rule=rule,
            subject_id=subject_id,
            subject_type=subject_type,
            status=ComplianceStatus.NON_COMPLIANT,
            message=f"Required URL missing: '{cleaned_url}'.",
            recommendation=f"Add the required URL: '{cleaned_url}'.",
        )

    return evaluate


def maximum_length_evaluator(
    maximum: int,
    *,
    measurement: str = "characters",
) -> RuleEvaluator:
    """Enforce a maximum character or word count."""

    if maximum < 0:
        raise ValueError("maximum cannot be negative.")

    cleaned_measurement = measurement.strip().casefold()

    if cleaned_measurement not in {"characters", "words"}:
        raise ValueError("measurement must be either 'characters' or 'words'.")

    def evaluate(
        rule: BrandRule,
        subject_id: str,
        subject_type: ReviewSubjectType,
        content: str,
    ) -> ComplianceFinding:
        if cleaned_measurement == "characters":
            actual = len(content)
        else:
            actual = len(content.split())

        if actual <= maximum:
            return ComplianceEngine.create_finding(
                rule=rule,
                subject_id=subject_id,
                subject_type=subject_type,
                status=ComplianceStatus.COMPLIANT,
                message=(
                    f"Content length is within the {maximum} "
                    f"{cleaned_measurement} limit."
                ),
                evidence=[f"Actual {cleaned_measurement}: {actual}"],
            )

        return ComplianceEngine.create_finding(
            rule=rule,
            subject_id=subject_id,
            subject_type=subject_type,
            status=ComplianceStatus.NON_COMPLIANT,
            message=(
                f"Content contains {actual} {cleaned_measurement}, "
                f"exceeding the limit of {maximum}."
            ),
            evidence=[
                f"Actual {cleaned_measurement}: {actual}",
                f"Maximum {cleaned_measurement}: {maximum}",
            ],
            recommendation=(
                f"Reduce the content to no more than "
                f"{maximum} {cleaned_measurement}."
            ),
        )

    return evaluate


def forbidden_regex_evaluator(
    pattern: str | Pattern[str],
    *,
    flags: int = re.IGNORECASE,
) -> RuleEvaluator:
    """Reject content matching a forbidden regular expression."""

    compiled_pattern = _compile_pattern(pattern, flags)

    def evaluate(
        rule: BrandRule,
        subject_id: str,
        subject_type: ReviewSubjectType,
        content: str,
    ) -> ComplianceFinding:
        matches = [
            match.group(0)
            for match in compiled_pattern.finditer(content)
            if match.group(0)
        ]
        evidence = _deduplicate(matches)

        if evidence:
            return ComplianceEngine.create_finding(
                rule=rule,
                subject_id=subject_id,
                subject_type=subject_type,
                status=ComplianceStatus.NON_COMPLIANT,
                message=(
                    f"Content matched forbidden pattern "
                    f"'{compiled_pattern.pattern}'."
                ),
                evidence=evidence,
                recommendation="Remove or replace the matched content.",
            )

        return ComplianceEngine.create_finding(
            rule=rule,
            subject_id=subject_id,
            subject_type=subject_type,
            status=ComplianceStatus.COMPLIANT,
            message=(
                f"Content did not match forbidden pattern "
                f"'{compiled_pattern.pattern}'."
            ),
        )

    return evaluate


def maximum_keyword_count_evaluator(
    keyword: str,
    maximum: int,
) -> RuleEvaluator:
    """Limit case-insensitive whole-word keyword occurrences."""

    cleaned_keyword = keyword.strip()

    if not cleaned_keyword:
        raise ValueError("keyword is required.")

    if maximum < 0:
        raise ValueError("maximum cannot be negative.")

    compiled_pattern = re.compile(
        rf"(?<!\w){re.escape(cleaned_keyword)}(?!\w)",
        re.IGNORECASE,
    )

    def evaluate(
        rule: BrandRule,
        subject_id: str,
        subject_type: ReviewSubjectType,
        content: str,
    ) -> ComplianceFinding:
        matches = compiled_pattern.findall(content)
        actual = len(matches)

        if actual <= maximum:
            return ComplianceEngine.create_finding(
                rule=rule,
                subject_id=subject_id,
                subject_type=subject_type,
                status=ComplianceStatus.COMPLIANT,
                message=(
                    f"Keyword '{cleaned_keyword}' appears {actual} time(s), "
                    f"within the limit of {maximum}."
                ),
                evidence=[f"Occurrences: {actual}"],
            )

        return ComplianceEngine.create_finding(
            rule=rule,
            subject_id=subject_id,
            subject_type=subject_type,
            status=ComplianceStatus.NON_COMPLIANT,
            message=(
                f"Keyword '{cleaned_keyword}' appears {actual} time(s), "
                f"exceeding the limit of {maximum}."
            ),
            evidence=[
                f"Keyword: {cleaned_keyword}",
                f"Occurrences: {actual}",
                f"Maximum occurrences: {maximum}",
            ],
            recommendation=(
                f"Reduce '{cleaned_keyword}' usage to no more than "
                f"{maximum} occurrence(s)."
            ),
        )

    return evaluate


def _compile_pattern(
    pattern: str | Pattern[str],
    flags: int,
) -> Pattern[str]:
    if isinstance(pattern, re.Pattern):
        return pattern

    cleaned_pattern = pattern.strip()

    if not cleaned_pattern:
        raise ValueError("pattern is required.")

    try:
        return re.compile(cleaned_pattern, flags)
    except re.error as error:
        raise ValueError(f"Invalid regular expression: {error}") from error


def _deduplicate(values: list[str]) -> list[str]:
    results: list[str] = []
    seen: set[str] = set()

    for value in values:
        marker = value.casefold()

        if marker not in seen:
            seen.add(marker)
            results.append(value)

    return results
