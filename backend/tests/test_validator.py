# backend/tests/test_validator.py
"""Tests for the IaC structural + best-practice validator."""
import asyncio
import json

from app.services.validator import validator, ValidationResult, ValidationIssue
from app.services.generator import generator
from app.models.generation import Provider, Target


def _check(tpl, provider, target="aws"):
    return asyncio.run(validator.validate(tpl, provider, target))


# --- terraform -------------------------------------------------------------

TF_VALID = '''
terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}
provider "aws" { region = "us-east-1" }
resource "aws_vpc" "main" { cidr_block = "10.0.0.0/16" }
resource "aws_instance" "web" {
  ami           = "ami-0c02fb55956c7d316"
  instance_type = "t3.medium"
}
'''


def test_validate_terraform_valid_template():
    res = _check(TF_VALID, "terraform", "aws")
    assert res.valid
    assert res.summary.startswith("No issues")


def test_validate_terraform_unbalanced_braces():
    bad = TF_VALID + "resource \"aws_s3_bucket\" \"x\" { bucket = \"x\" "  # missing closing brace
    res = _check(bad, "terraform", "aws")
    assert not res.valid
    assert any(i.severity == "error" and "brace" in i.message.lower() for i in res.issues)


def test_validate_terraform_missing_required_providers():
    bad = 'resource "aws_instance" "web" { ami = "a"; instance_type = "t3.micro" }'
    res = _check(bad, "terraform", "aws")
    assert not res.valid
    assert any(i.rule == "required_providers" for i in res.issues)


def test_validate_terraform_open_security_group_error():
    bad = TF_VALID + '\nresource "aws_security_group" "bad" {\n  ingress {\n    from_port = 0\n    to_port = 0\n    cidr_blocks = ["0.0.0.0/0"]\n  }\n}\n'
    res = _check(bad, "terraform", "aws")
    assert not res.valid
    assert any(i.rule == "open_ingress" and i.severity == "error" for i in res.issues)


def test_validate_terraform_provider_mismatch_warning():
    bad = TF_VALID.replace("aws_vpc", "google_compute_network")
    res = _check(bad, "terraform", "aws")
    # mismatch is a warning, not an error -> still structurally valid
    assert res.valid
    assert any(i.rule == "provider_mismatch" for i in res.issues)


def test_validate_terraform_s3_without_versioning_warning():
    bad = TF_VALID + '\nresource "aws_s3_bucket" "assets" { bucket = "assets" }\n'
    res = _check(bad, "terraform", "aws")
    assert any(i.rule == "s3_no_versioning" for i in res.issues)


# --- cloudformation --------------------------------------------------------

CFN_VALID = '''
AWSTemplateFormatVersion: "2010-09-09"
Description: test
Resources:
  Web:
    Type: AWS::EC2::Instance
    Properties:
      ImageId: ami-0c02fb55956c7d316
      InstanceType: t3.medium
'''


def test_validate_cloudformation_valid():
    res = _check(CFN_VALID, "cloudformation", "aws")
    assert res.valid


def test_validate_cloudformation_missing_type():
    bad = CFN_VALID.replace("    Type: AWS::EC2::Instance\n", "")
    res = _check(bad, "cloudformation", "aws")
    assert not res.valid
    assert any(i.rule == "missing_type" for i in res.issues)


def test_validate_cloudformation_malformed_yaml():
    bad = "Resources:\n  Bad:\n   bad: : : indentation"
    res = _check(bad, "cloudformation", "aws")
    assert not res.valid
    assert any(i.rule == "yaml_parse" for i in res.issues)


# --- arm -------------------------------------------------------------------

ARM_VALID = json.dumps({
    "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
    "contentVersion": "1.0.0.0",
    "resources": [
        {"type": "Microsoft.Storage/storageAccounts", "apiVersion": "2021-04-01", "name": "stg"},
        {"type": "Microsoft.Compute/virtualMachines", "apiVersion": "2021-04-01", "name": "vm"},
    ],
})


def test_validate_arm_valid():
    res = _check(ARM_VALID, "arm", "azure")
    assert res.valid


def test_validate_arm_malformed_json():
    res = _check("{not valid json", "arm", "azure")
    assert not res.valid
    assert any(i.rule == "json_parse" for i in res.issues)


def test_validate_arm_missing_schema_and_contentversion():
    bad = json.dumps({"resources": [{"type": "Microsoft.Storage/storageAccounts"}]})
    res = _check(bad, "arm", "azure")
    assert not res.valid
    assert any(i.rule == "missing_schema" for i in res.issues)
    assert any(i.rule == "missing_content_version" for i in res.issues)


def test_validate_format_sniff_when_provider_none():
    # provider=None -> detect from content
    res = _check(ARM_VALID, None, "azure")
    assert res.valid
    res2 = _check('{"not a template": true}', None, "azure")
    # no recognizable format markers -> treated as arm, missing schema
    assert any(i.severity == "error" for i in res2.issues)


# --- end-to-end: generated templates always validate ----------------------

def test_generated_terraform_validates():
    desc = "3-tier web app, ALB, RDS postgres, S3, redis, k8s, queues"
    from app.services.generator import detect_components as dc
    comps = dc(desc)
    tpl = asyncio.run(generator.generate(desc, Provider.TERRAFORM, Target.AWS, components=comps, use_llm=False))
    res = _check(tpl, "terraform", "aws")
    assert res.valid


def test_generated_arm_validates():
    desc = "Azure AKS with VMSS, Redis cache, storage account and service bus queue"
    from app.services.generator import detect_components as dc
    comps = dc(desc)
    tpl = asyncio.run(generator.generate(desc, Provider.ARM, Target.AZURE, components=comps, use_llm=False))
    res = _check(tpl, "arm", "azure")
    assert res.valid