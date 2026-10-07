#!/usr/bin/env python3
# cloud-infra-planner — Generates production-grade Terraform, CloudFormation, or ARM templates from natural language descriptions, with validation, cost estimation, and module composition.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm_client import LLM
import json, os, re, sys, time, statistics
from datetime import datetime, timedelta

PROVIDER_RESOURCES = {
    "aws": {
        "compute": "aws_instance / aws_launch_template",
        "load_balancer": "aws_lb (ALB) / aws_lb_listener",
        "database": "aws_db_instance (RDS)",
        "cache": "aws_elasticache_replication_group",
        "storage": "aws_s3_bucket",
        "queue": "aws_sqs_queue / aws_sns_topic",
        "serverless": "aws_lambda_function / aws_api_gateway_rest_api",
        "no_sql": "aws_dynamodb_table",
        "network": "aws_vpc / aws_subnet / aws_security_group / aws_route_table",
        "k8s": "aws_eks_cluster",
    },
    "gcp": {
        "compute": "google_compute_instance / google_compute_instance_template",
        "load_balancer": "google_compute_region_url_map / google_compute_forwarding_rule",
        "database": "google_sql_database_instance",
        "cache": "google_memorystore_redis_instance",
        "storage": "google_storage_bucket",
        "queue": "google_pubsub_topic",
        "serverless": "google_cloud_run_service",
        "no_sql": "google_bigtable_instance",
        "network": "google_compute_network / google_compute_subnetwork / google_compute_firewall",
        "k8s": "google_container_cluster",
    },
    "azure": {
        "compute": "azurerm_virtual_machine / azurerm_linux_virtual_machine_scale_set",
        "load_balancer": "azurerm_lb / azurerm_lb_rule",
        "database": "azurerm_mysql_flexible_server / azurerm_postgresql_flexible_server",
        "cache": "azurerm_redis_cache",
        "storage": "azurerm_storage_account",
        "queue": "azurerm_servicebus_queue",
        "serverless": "azurerm_function_app / azurerm_api_management",
        "no_sql": "azurerm_cosmosdb_account",
        "network": "azurerm_virtual_network / azurerm_subnet / azurerm_network_security_group",
        "k8s": "azurerm_kubernetes_cluster",
    },
}

def _detect_components(description):
    desc = description.lower()
    components = []
    if any(w in desc for w in ["web app", "3-tier", "three-tier", "frontend", "backend", "api", "microservice"]):
        components += ["network", "compute", "load_balancer"]
    if any(w in desc for w in ["postgres", "rds", "cloud sql", "mysql", "mariadb", "database", "db"]):
        components.append("database")
    if any(w in desc for w in ["redis", "memcache", "elasticache", "memorystore", "cache"]):
        components.append("cache")
    if any(w in desc for w in ["s3", "gcs", "blob", "storage", "bucket", "object store"]):
        components.append("storage")
    if any(w in desc for w in ["dynamodb", "dynamo", "bigtable", "cosmosdb", "no-sql", "nosql"]):
        components.append("no_sql")
    if any(w in desc for w in ["lambda", "cloud function", "function app", "serverless", "cloud run"]):
        components.append("serverless")
    if any(w in desc for w in ["k8s", "kubernetes", "eks", "gke", "aks", "container"]):
        components.append("k8s")
    if any(w in desc for w in ["queue", "sqs", "pubsub", "service bus", "sns"]):
        components.append("queue")
    if any(w in desc for w in ["high availability", "ha", "multi-az", "multi-zone", "multi-region", "redundant"]):
        components.append("ha")
    if not components:
        components = ["network", "compute"]
    return components

def _estimate_cost(components, target, regions=1):
    base_costs = {
        "aws": {"network": 10, "compute": 98, "load_balancer": 16, "database": 150, "cache": 80,
                "storage": 5, "no_sql": 25, "serverless": 10, "queue": 2, "k8s": 350, "ha": 200},
        "gcp": {"network": 10, "compute": 90, "load_balancer": 16, "database": 140, "cache": 75,
                "storage": 5, "no_sql": 30, "serverless": 10, "queue": 2, "k8s": 330, "ha": 190},
        "azure": {"network": 10, "compute": 100, "load_balancer": 16, "database": 160, "cache": 85,
                  "storage": 5, "no_sql": 35, "serverless": 10, "queue": 2, "k8s": 360, "ha": 210},
    }
    costs = base_costs.get(target, base_costs["aws"])
    total = sum(costs.get(c, 0) for c in components) * regions
    if "ha" in components:
        total = int(total * 1.4)
    return total

def cmd_generate(args):
    llm = LLM()
    description = args.description
    provider = args.provider.lower()
    target = args.target.lower()
    print(f"{'='*60}")
    print(f"INFRA PLANNER — {provider.upper()} / {target.upper()}")
    print(f"{'='*60}\\n")
    print(f"Description: {description}\\n")
    components = _detect_components(description)
    print(f"Detected components: {', '.join(components)}")
    est = _estimate_cost(components, target)
    print(f"Estimated monthly cost: ~${est}\\n")
    if provider == "terraform":
        tf_prompt = f"""Generate production-grade Terraform HCL for {target}.

Requirements: {description}

Detected components: {json.dumps(components)}

Rules:
- Use local variables for region, environment, naming prefix
- Include a variables.tf section (inline as # variables.tf section)
- Include proper tags (managed-by: terraform, project: auto-generated)
- Include lifecycle rules for S3/GCS buckets (versioning, public access block)
- For compute: include launch templates with proper SG, IMDSv2, monitoring
- For database: multi-AZ if HA, backup retention 7 days, encryption at rest
- For load balancer: health checks, idle timeout 60s
- Use data sources where appropriate (e.g. aws_caller_identity)
- Output key resources (endpoints, IDs)
- Do NOT include provider blocks (assumed configured)
- Use HCL2 syntax, no interpolation in strings where not needed
- Keep it under 300 lines
Respond ONLY with the Terraform code, no markdown fences, no explanation."""
    elif provider == "cloudformation":
        tf_prompt = f"""Generate a CloudFormation template (YAML) for {target}.

Requirements: {description}

Detected components: {json.dumps(components)}

Rules:
- Include Parameters, Mappings, Resources, Outputs sections
- Use Fn::If for environment-based sizing
- Include CloudWatch alarms for critical resources
- Include proper DependsOn ordering
- Tags: managed-by: cloudformation, project: auto-generated
- Keep it under 400 lines
Respond ONLY with the YAML template, no markdown fences."""
    else:
        tf_prompt = f"""Generate an Azure Resource Manager (ARM) template (JSON) for this requirement.

Requirements: {description}

Detected components: {json.dumps(components)}

Rules:
- Include $schema, parameters, variables, resources, outputs
- Use Microsoft.Network/virtualNetworks, Microsoft.Compute/virtualMachines, etc.
- Include proper dependencies
- Keep it under 350 lines
Respond ONLY with the JSON template, no markdown fences."""
    print("Generating infrastructure code...")
    code = llm.generate(tf_prompt)
    code = re.sub(r"^```(?:hcl|yaml|json|python)?\s*", "", code.strip())
    code = re.sub(r"\s*```$", "", code.strip())
    ext = "tf" if provider == "terraform" else ("yml" if provider == "cloudformation" else "json")
    filename = args.output or f"main.{ext}"
    with open(filename, "w") as f:
        f.write(code + "\\n")
    print(f"\\n✓ Generated {filename} ({len(code)} chars)")
    print(f"\\n{'='*60}")
    print(f"GENERATED INFRASTRUCTURE ({ext})")
    print(f"{'='*60}\\n")
    print(code[:3000] + ("\\n... (truncated)" if len(code) > 3000 else ""))
    print(f"\\n{'='*60}")
    print(f"ESTIMATED MONTHLY COST: ~${est}")
    print(f"Components: {', '.join(components)}")
    if "ha" in components:
        print("High availability: enabled (multi-AZ/region)")
    print(f"{'='*60}")
    notes = llm.generate(f"Review this {provider} code for {target}:\\n{code[:4000]}\\n\\nIdentify: 1) any missing security controls, 2) any missing cost controls (budgets, lifecycle policies), 3) any missing observability (logs, metrics, alarms), 4) any idempotency issues. Be specific — reference the resource names.")
    print(f"\\nAI REVIEW NOTES:")
    print(notes)

def cmd_validate(args):
    llm = LLM()
    print(f"Validating {args.file}...\\n")
    with open(args.file) as f:
        code = f.read()
    provider = "terraform" if args.file.endswith(".tf") else ("cloudformation" if args.file.endswith((".yml", ".yaml")) else "arm")
    print(f"Detected provider: {provider}")
    print(f"Size: {len(code)} chars, {len(code.splitlines())} lines\\n")
    prompt = f"""Validate this {provider} template for {args.target}:

{code}

Check for:
1. Syntax errors or missing required fields
2. Missing security controls (encryption, IAM, network isolation)
3. Missing cost controls (lifecycle policies, budget alarms)
4. Missing observability (logs, metrics, CloudWatch/Azure Monitor)
5. Resource dependency ordering issues
6. Hardcoded values that should be parameters
7. Missing tags or naming conventions
8. Potential drift causes

Respond as JSON:
{{
  "valid": true/false,
  "errors": ["..."],
  "warnings": ["..."],
  "missing_controls": ["..."],
  "missing_observability": ["..."],
  "recommendations": ["..."],
  "score": 0-100
}}"""
    result = llm.classify(code[:6000], categories=["valid", "invalid", "warnings_only"], instructions=prompt)
    print(f"\\n{'='*60}")
    print(f"VALIDATION REPORT")
    print(f"{'='*60}\\n")
    if "error" not in result:
        print(f"Valid: {result.get('valid', 'unknown')}")
        print(f"Score: {result.get('score', 'N/A')}/100")
        for e in result.get("errors", []):
            print(f"  🔴 ERROR: {e}")
        for w in result.get("warnings", []):
            print(f"  🟡 WARN: {w}")
        for mc in result.get("missing_controls", []):
            print(f"  📋 Missing: {mc}")
    else:
        print(f"  Raw: {result}")
    if args.output:
        with open(args.output, "w") as f:
            json.dump(result, f, indent=2)
        print(f"\\nSaved to {args.output}")

def cmd_estimate(args):
    llm = LLM()
    with open(args.file) as f:
        code = f.read()
    target = args.target.lower()
    prompt = f"""Estimate the monthly cost of this {target} infrastructure:

{code[:5000]}

For each resource type, estimate:
- Resource type
- Instance size
- Estimated monthly cost (USD)
- Region assumption

Total the costs. Include a range (low/high) for variability.
Respond as JSON:
{{
  "resources": [{{"type": "...", "size": "...", "est_monthly_usd": 0.0}}],
  "total_low_usd": 0.0,
  "total_high_usd": 0.0,
  "assumptions": ["..."]
}}"""
    result = llm.classify(code[:5000], categories=["estimated"], instructions=prompt)
    print(f"\\n{'='*60}")
    print(f"COST ESTIMATE — {target.upper()}")
    print(f"{'='*60}\\n")
    if "error" not in result:
        for r in result.get("resources", []):
            print(f"  {r.get('type', 'unknown'):<30} {r.get('size', 'n/a'):<15} ${r.get('est_monthly_usd', 0):>8.2f}/mo")
        print(f"\\n  Estimated monthly cost: ${result.get('total_low_usd', 0):.2f} – ${result.get('total_high_usd', 0):.2f}")
        for a in result.get("assumptions", []):
            print(f"  Note: {a}")
    else:
        print(f"  Raw: {result}")

def cmd_module(args):
    llm = LLM()
    name = args.name
    target = args.target.lower()
    description = args.description
    print(f"Generating Terraform module: {name} for {target}\\n")
    prompt = f"""Generate a reusable Terraform module named '{name}' for {target}.

Purpose: {description}

Rules:
- Module structure: variables.tf, main.tf, outputs.tf, versions.tf
- All inputs via variables with sensible defaults and descriptions
- All outputs documented
- Include a README.md with usage example
- Use local name prefix for all resource names
- Include null_resource or data sources for lookups where needed
- Keep it production-ready
Respond with ALL files, separated by lines starting with '## FILE: <path>'."""
    code = llm.generate(prompt)
    base = os.path.join(os.getcwd(), "modules", name)
    os.makedirs(base, exist_ok=True)
    files = re.split(r"##\s*FILE:\s*", code)
    written = []
    for chunk in files[1:]:
        lines = chunk.strip().split("\\n", 1)
        if len(lines) == 2:
            path = lines[0].strip()
            content = lines[1].strip()
            full = os.path.join(base, path)
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "w") as f:
                f.write(content + "\\n")
            written.append(full)
    if not written:
        full = os.path.join(base, "main.tf")
        with open(full, "w") as f:
            f.write(code + "\\n")
        written.append(full)
    print(f"\\n✓ Module written to {base}/")
    for w in written:
        print(f"  {w}")

def main():
    import argparse
    p = argparse.ArgumentParser(prog="cloud-infra-planner", description="Natural language to cloud infrastructure code")
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("generate", help="Generate IaC from natural language")
    g.add_argument("--description", required=True); g.add_argument("--provider", default="terraform", choices=["terraform", "cloudformation", "arm"])
    g.add_argument("--target", default="aws", choices=["aws", "gcp", "azure"]); g.add_argument("--output", default=None)
    g.set_defaults(fn=cmd_generate)

    v = sub.add_parser("validate", help="Validate generated IaC")
    v.add_argument("--file", required=True); v.add_argument("--target", default="aws"); v.add_argument("--output", default=None)
    v.set_defaults(fn=cmd_validate)

    e = sub.add_parser("estimate", help="Estimate cost of generated IaC")
    e.add_argument("--file", required=True); e.add_argument("--target", default="aws")
    e.set_defaults(fn=cmd_estimate)

    m = sub.add_parser("module", help="Generate a reusable Terraform module")
    m.add_argument("--name", required=True); m.add_argument("--description", required=True)
    m.add_argument("--target", default="aws")
    m.set_defaults(fn=cmd_module)

    args = p.parse_args()
    args.fn(args)

if __name__ == '__main__':
    main()
