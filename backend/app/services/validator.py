# backend/app/services/validator.py
"""IaC template validation.

Structural validation for Terraform (HCL), CloudFormation (YAML) and ARM
(JSON) templates, plus deterministic best-practice checks.  Parsing is done with
standard-library regex / json / yaml so the core works fully offline.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from ..models.generation import Provider, Target


@dataclass
class ValidationIssue:
    severity: str  # "error" | "warning" | "info"
    message: str
    line: Optional[int] = None
    column: Optional[int] = None
    rule: Optional[str] = None


@dataclass
class ValidationResult:
    valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    summary: str = ""

    @classmethod
    def from_issues(cls, issues: List[ValidationIssue]) -> "ValidationResult":
        has_error = any(i.severity == "error" for i in issues)
        summary = cls._summarize(issues)
        return cls(valid=not has_error, issues=issues, summary=summary)

    @staticmethod
    def _summarize(issues: List[ValidationIssue]) -> str:
        errors = sum(1 for i in issues if i.severity == "error")
        warnings = sum(1 for i in issues if i.severity == "warning")
        infos = sum(1 for i in issues if i.severity == "info")
        if not issues:
            return "No issues found."
        return f"{errors} error(s), {warnings} warning(s), {infos} info"


class Validator:
    """Validates IaC templates for the configured provider/target."""

    async def validate(
        self,
        template: str,
        provider: Optional[str],
        target: Optional[str],
    ) -> ValidationResult:
        fmt = self._detect_format(template, provider)
        if fmt == "terraform":
            return self._validate_terraform(template, target)
        if fmt == "cloudformation":
            return self._validate_cloudformation(template, target)
        if fmt == "arm":
            return self._validate_arm(template, target)
        return ValidationResult.from_issues([
            ValidationIssue("error", f"Unable to detect template format", rule="format_detection")
        ])

    # -- format detection -------------------------------------------------- #
    @staticmethod
    def _detect_format(template: str, provider: Optional[str]) -> str:
        provider = (provider or "").lower()
        if provider in ("terraform", "tf"):
            return "terraform"
        if provider in ("cloudformation", "cfn", "yaml", "yml"):
            return "cloudformation"
        if provider in ("arm", "azure", "json"):
            return "arm"
        stripped = template.lstrip()
        if stripped.startswith("{"):
            return "arm"
        if "AWSTemplateFormatVersion" in template or "Resources:" in template:
            return "cloudformation"
        if "resource \"" in template or "terraform" in template:
            return "terraform"
        return "terraform"

    # -- terraform (HCL) --------------------------------------------------- #
    @staticmethod
    def _line_of(template: str, needle: str) -> Optional[int]:
        idx = template.find(needle)
        if idx == -1:
            return None
        return template.count("\n", 0, idx) + 1

    def _validate_terraform(self, template: str, target: Optional[str]) -> ValidationResult:
        issues: List[ValidationIssue] = []
        text = template

        # Brute-balanced-brace check (comments stripped).
        code = re.sub(r"#(.*)", "", text)
        open_braces = code.count("{")
        close_braces = code.count("}")
        if open_braces != close_braces:
            issues.append(ValidationIssue(
                "error",
                f"Unbalanced braces: {open_braces} '{{' vs {close_braces} '}}'",
                line=1, rule="balanced_braces"))

        # Required structural blocks.
        if "terraform" not in code or "required_providers" not in code:
            issues.append(ValidationIssue("error", "Missing 'terraform { required_providers {} }' block", rule="required_providers"))
        else:
            match = re.search(r"required_providers\s*\{", code)
            if match:
                ln = code.count("\n", 0, match.start()) + 1
            else:
                ln = 1

        # Resource blocks.
        resources = list(re.finditer(r'resource\s+"([^"]+)"\s+"([^"]+)"\s*\{', code))
        if not resources:
            issues.append(ValidationIssue("error", "No resource blocks found", rule="no_resources"))
        else:
            target_prefix = {"aws": "aws_", "gcp": "google_", "azure": "azurerm_"}.get((target or "").lower(), None)
            seen_types: set = set()
            for m in resources:
                rtype, rname = m.group(1), m.group(2)
                seen_types.add(rtype)
                ln = code.count("\n", 0, m.start()) + 1
                if target_prefix and not rtype.startswith(target_prefix):
                    issues.append(ValidationIssue(
                        "warning",
                        f"Resource {rname!r} ({rtype}) does not match target prefix {target_prefix!r}",
                        line=ln, rule="provider_mismatch"))
                # Best-practice: open ingress.
                if "aws_security_group" in rtype and "0.0.0.0/0" in code:
                    issues.append(ValidationIssue(
                        "error", "Security group allows 0.0.0.0/0 ingress",
                        line=ln, rule="open_ingress"))
                # Best-practice: S3 without versioning.
                if rtype == "aws_s3_bucket" and "versioning" not in code.lower():
                    issues.append(ValidationIssue(
                        "warning", "S3 bucket has no versioning block",
                        line=ln, rule="s3_no_versioning"))
                # Best-practice: RDS without backup retention.
                if rtype == "aws_db_instance" and "backup_retention_period" not in code:
                    issues.append(ValidationIssue(
                        "warning", "RDS instance missing backup_retention_period",
                        line=ln, rule="rds_no_backup"))
                # Best-practice: RDS without multi_az when no HA context.
                if rtype == "aws_db_instance" and "multi_az" not in code and "ha" not in (target or "").lower():
                    issues.append(ValidationIssue(
                        "info", "RDS instance is not multi-AZ",
                        line=ln, rule="rds_not_multi_az"))

        # Provider block presence.
        provider_match = re.search(r'provider\s+"([^"]+)"', code)
        if not provider_match:
            issues.append(ValidationIssue("warning", "No provider block found", rule="no_provider_block"))

        return ValidationResult.from_issues(issues)

    # -- cloudformation (YAML) -------------------------------------------- #
    def _validate_cloudformation(self, template: str, target: Optional[str]) -> ValidationResult:
        import yaml  # local import
        issues: List[ValidationIssue] = []
        try:
            data = yaml.safe_load(template)
        except yaml.YAMLError as exc:  # type: ignore[name-defined]
            line = getattr(exc, "problem_mark", None)
            ln = line.line + 1 if line else 1
            return ValidationResult.from_issues([
                ValidationIssue("error", f"YAML parse error: {exc}", line=ln, rule="yaml_parse")
            ])
        if not isinstance(data, dict):
            return ValidationResult.from_issues([
                ValidationIssue("error", "Top-level CloudFormation template must be a mapping", rule="not_mapping")
            ])
        if "AWSTemplateFormatVersion" not in data:
            issues.append(ValidationIssue("warning", "Missing AWSTemplateFormatVersion", rule="missing_version"))
        resources = data.get("Resources")
        if not isinstance(resources, dict) or not resources:
            issues.append(ValidationIssue("error", "Missing or empty 'Resources' section", rule="missing_resources"))
        else:
            for name, res in resources.items():
                ln = self._line_of(template, f"{name}:")
                if not isinstance(res, dict):
                    issues.append(ValidationIssue("error", f"Resource {name!r} is not a mapping", rule="resource_not_mapping"))
                    continue
                if "Type" not in res:
                    issues.append(ValidationIssue("error", f"Resource {name!r} missing 'Type'", line=ln, rule="missing_type"))
                if "Properties" not in res:
                    issues.append(ValidationIssue("warning", f"Resource {name!r} missing 'Properties'", line=ln, rule="missing_properties"))
                rtype = res.get("Type", "")
                if rtype and not rtype.startswith("AWS::"):
                    issues.append(ValidationIssue("warning", f"Resource {name!r} type {rtype} is not an AWS type", line=ln, rule="non_aws_type"))
        if "Description" not in data:
            issues.append(ValidationIssue("info", "Template has no Description", rule="no_description"))
        return ValidationResult.from_issues(issues)

    # -- arm (JSON) -------------------------------------------------------- #
    def _validate_arm(self, template: str, target: Optional[str]) -> ValidationResult:
        issues: List[ValidationIssue] = []
        try:
            data = json.loads(template)
        except json.JSONDecodeError as exc:
            return ValidationResult.from_issues([
                ValidationIssue("error", f"JSON parse error: {exc}", line=exc.lineno, rule="json_parse")
            ])
        if not isinstance(data, dict):
            return ValidationResult.from_issues([
                ValidationIssue("error", "Top-level ARM template must be an object", rule="not_object")
            ])
        if "$schema" not in data:
            issues.append(ValidationIssue("error", "Missing '$schema'", rule="missing_schema"))
        if "contentVersion" not in data:
            issues.append(ValidationIssue("error", "Missing 'contentVersion'", rule="missing_content_version"))
        resources = data.get("resources")
        if not isinstance(resources, list) or not resources:
            issues.append(ValidationIssue("error", "Missing or empty 'resources' array", rule="missing_resources"))
        else:
            for i, res in enumerate(resources):
                if not isinstance(res, dict):
                    issues.append(ValidationIssue("error", f"Resource #{i} is not an object", rule="resource_not_object"))
                    continue
                for req in ("type", "name", "apiVersion"):
                    if req not in res:
                        issues.append(ValidationIssue("error", f"Resource #{i} missing '{req}'", rule=f"missing_{req}"))
                rtype = res.get("type", "")
                if rtype and not rtype.startswith("Microsoft."):
                    issues.append(ValidationIssue("warning", f"Resource #{i} type {rtype} is not Microsoft.*", rule="non_microsoft_type"))
        return ValidationResult.from_issues(issues)


validator = Validator()