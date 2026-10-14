# backend/app/services/generator.py
"""NL -> IaC template generation.

Deterministic offline core renders Terraform / CloudFormation / ARM templates
from keyword-detected infrastructure components.  An optional LLM pass can
augment the component list when a non-offline LLM adapter is configured; on
any error it falls back to deterministic keyword detection so the template is
always structurally valid and never fabricated from an LLM response.
"""
from __future__ import annotations

import json
from typing import List, Optional, Dict, Any, Tuple

from ..core.config import settings
from ..services.llm import get_llm_adapter
from ..models.generation import Provider, Target

# --------------------------------------------------------------------------- #
# Component detection (deterministic keyword scan)
# --------------------------------------------------------------------------- #
_COMPONENT_KEYWORDS: List[Tuple[str, List[str]]] = [
    ("compute", ["web app", "3-tier", "three-tier", "frontend", "backend",
                 "api", "microservice", "instance", "vm"]),
    ("load_balancer", ["load balancer", "alb", "nlb", "lb", "load balancing"]),
    ("database", ["postgres", "rds", "cloud sql", "mysql", "mariadb",
                  "database", "db"]),
    ("cache", ["redis", "memcache", "elasticache", "memorystore", "cache"]),
    ("storage", ["s3", "gcs", "blob", "storage", "bucket", "object store"]),
    ("no_sql", ["dynamodb", "dynamo", "bigtable", "cosmosdb", "no-sql", "nosql"]),
    ("serverless", ["lambda", "cloud function", "function app",
                    "serverless", "cloud run"]),
    ("k8s", ["k8s", "kubernetes", "eks", "gke", "aks", "container"]),
    ("queue", ["queue", "sqs", "pubsub", "service bus", "sns"]),
    ("ha", ["high availability", "ha", "multi-az", "multi-zone",
            "multi-region", "redundant"]),
]

_AVAILABLE_COMPONENTS = [c for c, _ in _COMPONENT_KEYWORDS]
_DEFAULT_COMPONENTS = ["network", "compute"]


def detect_components(description: str) -> List[str]:
    """Map a natural-language description to a deterministic component list."""
    desc = description.lower()
    found: List[str] = []
    seen: set = set()
    for component, keywords in _COMPONENT_KEYWORDS:
        if any(kw in desc for kw in keywords) and component not in seen:
            found.append(component)
            seen.add(component)
    # A compute tier implies networking; keep the default useful.
    if "compute" in found and "network" not in found:
        found.insert(0, "network")
    if not found:
        return list(_DEFAULT_COMPONENTS)
    return found


# --------------------------------------------------------------------------- #
# Resource specs (data-driven).  Each entry: (resource_type, name, attrs)
# attrs values are str/int/float/bool/list[str]/dict[str, scalar] (dict -> block)
# --------------------------------------------------------------------------- #
_TF_RESOURCES: Dict[str, Dict[str, List[Tuple[str, str, Dict[str, Any]]]]] = {
    "aws": {
        "network": [
            ("aws_vpc", "main", {"cidr_block": "10.0.0.0/16", "enable_dns_hostnames": True,
                                 "tags": {"Name": "main-vpc"}}),
            ("aws_internet_gateway", "igw", {"vpc_id": "aws_vpc.main.id",
                                             "tags": {"Name": "main-igw"}}),
            ("aws_subnet", "public_a", {"vpc_id": "aws_vpc.main.id",
                                        "cidr_block": "10.0.1.0/24",
                                        "availability_zone": "us-east-1a",
                                        "map_public_ip_on_launch": True,
                                        "tags": {"Name": "public-a"}}),
        ],
        "compute": [
            ("aws_instance", "web", {"ami": "ami-0c02fb55956c7d316",
                                     "instance_type": "t3.medium",
                                     "vpc_security_group_ids": ["aws_security_group.web.id"],
                                     "tags": {"Name": "web"}}),
        ],
        "load_balancer": [
            ("aws_lb", "app", {"name": "app-lb", "internal": False,
                               "load_balancer_type": "application",
                               "subnets": ["aws_subnet.public_a.id"],
                               "tags": {"Name": "app-lb"}}),
            ("aws_lb_target_group", "app", {"name": "app-tg", "port": 80,
                                            "protocol": "HTTP", "vpc_id": "aws_vpc.main.id"}),
            ("aws_lb_listener", "http", {"load_balancer_arn": "aws_lb.app.arn",
                                         "port": 80, "protocol": "HTTP",
                                         "default_action": ["forward"]}),
        ],
        "database": [
            ("aws_db_instance", "db", {"engine": "postgres", "engine_version": "15",
                                       "instance_class": "db.t4g.medium",
                                       "allocated_storage": 20, "username": "dbadmin",
                                       "db_subnet_group_name": "aws_db_subnet_group.db.name",
                                       "vpc_security_group_ids": ["aws_security_group.db.id"],
                                       "backup_retention_period": 7, "deletion_protection": True}),
        ],
        "cache": [
            ("aws_elasticache_replication_group", "cache",
             {"replication_group_description": "redis cache", "node_type": "cache.t4g.micro",
              "engine": "redis", "num_cache_clusters": 2,
              "security_group_ids": ["aws_security_group.cache.id"]}),
        ],
        "storage": [
            ("aws_s3_bucket", "assets", {"bucket": "infra-assets",
                                         "force_destroy": False, "tags": {"Name": "assets"}}),
            ("aws_s3_bucket_versioning", "assets",
             {"bucket": "aws_s3_bucket.assets.id", "versioning_configuration": {"status": "Enabled"}}),
            ("aws_s3_bucket_public_access_block", "assets",
             {"bucket": "aws_s3_bucket.assets.id", "block_public_acls": True,
              "block_public_policy": True, "restrict_public_buckets": True}),
        ],
        "no_sql": [
            ("aws_dynamodb_table", "items", {"name": "items", "billing_mode": "PAY_PER_REQUEST",
                                             "hash_key": "id",
                                             "attribute": [{"name": "id", "type": "S"}],
                                             "tags": {"Name": "items"}}),
        ],
        "serverless": [
            ("aws_iam_role", "lambda_exec",
             {"name": "lambda-exec", "assume_role_policy": {"Version": "2012-10-17",
               "Statement": [{"Effect": "Allow", "Principal": {"Service": "lambda.amazonaws.com"},
                              "Action": "sts:AssumeRole"}]}}),
            ("aws_lambda_function", "app", {"function_name": "app", "runtime": "python3.12",
                                            "handler": "handler.main", "role": "aws_iam_role.lambda_exec.arn",
                                            "filename": "lambda.zip",
                                            "source_code_hash": "base64sha256(file(\"lambda.zip\"))"}),
            ("aws_api_gateway_rest_api", "app", {"name": "app-api", "tags": {"Name": "app-api"}}),
        ],
        "k8s": [
            ("aws_eks_cluster", "main", {"name": "main-cluster", "role_arn": "aws_iam_role.eks.arn",
                                         "vpc_config": {"subnet_ids": ["aws_subnet.public_a.id"]}}),
        ],
        "queue": [
            ("aws_sqs_queue", "events", {"name": "events", "visibility_timeout_seconds": 30,
                                         "tags": {"Name": "events"}}),
            ("aws_sns_topic", "events_topic", {"name": "events-topic", "tags": {"Name": "events-topic"}}),
        ],
    },
    "gcp": {
        "network": [
            ("google_compute_network", "main", {"name": "main-net", "auto_create_subnetworks": False}),
            ("google_compute_subnetwork", "public_a", {"name": "public-a", "ip_cidr_range": "10.0.1.0/24",
                                                        "region": "us-central1"}),
        ],
        "compute": [
            ("google_compute_instance", "web", {"name": "web", "machine_type": "e2-medium",
                                                "zone": "us-central1-a"}),
        ],
        "load_balancer": [
            ("google_compute_global_address", "lb", {"name": "lb-ip", "description": "LB address"}),
            ("google_compute_forwarding_rule", "http", {"name": "http-fr",
                                                        "target": "google_compute_target_http_proxy.http.id",
                                                        "port_range": "80"}),
        ],
        "database": [
            ("google_sql_database_instance", "db", {"name": "db", "database_version": "POSTGRES_15",
                                                     "settings": {"tier": "db-f1-micro", "activation_policy": "ALWAYS"}}),
        ],
        "cache": [
            ("google_redis_instance", "cache", {"name": "cache", "memory_size_gb": 1,
                                                 "redis_version": "REDIS_6_X", "zone": "us-central1-a"}),
        ],
        "storage": [
            ("google_storage_bucket", "assets", {"name": "infra-assets", "location": "US",
                                                 "versioning": {"enabled": True}}),
        ],
        "no_sql": [
            ("google_bigtable_instance", "items", {"name": "items", "cluster": {"cluster_id": "items-1",
                                    "zone": "us-central1-a", "serve_nodes": 1}}),
        ],
        "serverless": [
            ("google_cloud_run_service", "app", {"name": "app", "location": "us-central1"}),
            ("google_cloudfunctions_function", "fn", {"name": "fn", "runtime": "python311", "entry_point": "main"}),
        ],
        "k8s": [
            ("google_container_cluster", "main", {"name": "main-cluster", "initial_node_count": 1}),
        ],
        "queue": [
            ("google_pubsub_topic", "events", {"name": "events"}),
        ],
    },
    "azure": {
        "network": [
            ("azurerm_virtual_network", "main", {"name": "main-vnet",
                                                 "address_space": {"address_prefixes": ["10.0.0.0/16"]},
                                                 "location": "eastus"}),
            ("azurerm_subnet", "public_a", {"name": "public-a", "virtual_network_name": "azurerm_virtual_network.main.name",
                                            "address_prefix": "10.0.1.0/24"}),
        ],
        "compute": [
            ("azurerm_linux_virtual_machine_scale_set", "web", {"name": "web-vmss", "location": "eastus",
                                                               "sku": "Standard_B2s", "instances": 2}),
        ],
        "load_balancer": [
            ("azurerm_lb", "app", {"name": "app-lb", "location": "eastus", "sku": "Standard"}),
            ("azurerm_lb_backend_address_pool", "app", {"name": "app-pool", "loadbalancer_id": "azurerm_lb.app.id"}),
        ],
        "database": [
            ("azurerm_postgresql_flexible_server", "db", {"name": "db", "location": "eastus",
                                                         "version": "15", "sku_name": "B burstable"}),
        ],
        "cache": [
            ("azurerm_redis_cache", "cache", {"name": "cache", "location": "eastus", "sku_name": "Basic", "capacity": 1}),
        ],
        "storage": [
            ("azurerm_storage_account", "assets", {"name": "infrastoreassets", "account_tier": "Standard",
                                                   "account_replication_type": "LRS"}),
        ],
        "no_sql": [
            ("azurerm_cosmosdb_account", "items", {"name": "items", "location": "eastus",
                                                   "offer_type": "Standard", "kind": "GlobalDocumentDB"}),
        ],
        "serverless": [
            ("azurerm_function_app", "app", {"name": "app-fn", "location": "eastus",
                                             "os_type": "linux", "version": "~4"}),
        ],
        "k8s": [
            ("azurerm_kubernetes_cluster", "main", {"name": "main-aks", "location": "eastus", "dns_prefix": "mainaks"}),
        ],
        "queue": [
            ("azurerm_servicebus_queue", "events", {"name": "events", "namespace_id": "azurerm_servicebus_namespace.events.id"}),
        ],
    },
}

# Cloudformation is AWS-native; ARM is Azure-native.
_CFN_RESOURCES: Dict[str, List[Tuple[str, str, Dict[str, Any]]]] = {
    "network": [("AWS::EC2::VPC", "VPC", {"CidrBlock": "10.0.0.0/16", "EnableDnsHostnames": True,
                                          "Tags": [{"Key": "Name", "Value": "main-vpc"}]}),
                ("AWS::EC2::InternetGateway", "IGW", {"Tags": [{"Key": "Name", "Value": "main-igw"}]})],
    "compute": [("AWS::EC2::Instance", "Web", {"ImageId": "ami-0c02fb55956c7d316", "InstanceType": "t3.medium"})],
    "load_balancer": [("AWS::ElasticLoadBalancingV2::LoadBalancer", "AppLB", {"Type": "application", "Subnets": ["subnet-0abc"]}),
                      ("AWS::ElasticLoadBalancingV2::TargetGroup", "AppTG", {"Port": 80, "Protocol": "HTTP", "VpcId": {"Ref": "VPC"}}),
                      ("AWS::ElasticLoadBalancingV2::Listener", "HTTPListener", {"LoadBalancerArn": {"Ref": "AppLB"}, "Port": 80, "Protocol": "HTTP"})],
    "database": [("AWS::RDS::DBInstance", "DB", {"Engine": "postgres", "DBInstanceClass": "db.t4g.medium",
                                                 "AllocatedStorage": 20, "BackupRetentionPeriod": 7, "DeletionPolicy": "Snapshot"})],
    "cache": [("AWS::ElastiCache::ReplicationGroup", "Cache", {"Engine": "redis", "CacheNodeType": "cache.t4g.micro", "NumCacheClusters": 2})],
    "storage": [("AWS::S3::Bucket", "Assets", {"BucketName": "infra-assets", "VersioningConfiguration": {"Status": "Enabled"},
                 "PublicAccessBlock": {"BlockPublicAcls": True, "BlockPublicPolicy": True}})],
    "no_sql": [("AWS::DynamoDB::Table", "Items", {"BillingMode": "PAY_PER_REQUEST",
               "AttributeDefinitions": [{"AttributeName": "id", "AttributeType": "S"}],
               "KeySchema": [{"AttributeName": "id", "KeyType": "HASH"}]})],
    "serverless": [("AWS::Lambda::Function", "App", {"Runtime": "python3.12", "Handler": "handler.main", "Code": {"ZipFile": ""}}),
                   ("AWS::ApiGateway::RestApi", "AppAPI", {"Name": "app-api"})],
    "k8s": [("AWS::EKS::Cluster", "Cluster", {"Name": "main-cluster", "RoleArn": {"Ref": "EKSPolicy"}})],
    "queue": [("AWS::SQS::Queue", "Events", {}), ("AWS::SNS::Topic", "EventsTopic", {})],
}

_ARM_RESOURCES: Dict[str, List[Tuple[str, str, Dict[str, Any]]]] = {
    "network": [("Microsoft.Network/virtualNetworks", "main-vnet", {"addressSpace": {"addressPrefixes": ["10.0.0.0/16"]}, "location": "eastus"}),
                ("Microsoft.Network/subnets", "public-a", {"properties": {"addressPrefix": "10.0.1.0/24"}})],
    "compute": [("Microsoft.Compute/virtualMachines", "web-vmss", {"location": "eastus", "properties": {"virtualMachineProfile": {}}})],
    "load_balancer": [("Microsoft.Network/loadBalancers", "app-lb", {"location": "eastus", "sku": {"name": "Standard"}}),
                      ("Microsoft.Network/networkInterfaces", "app-nic", {"location": "eastus"})],
    "database": [("Microsoft.DBforPostgreSQL/servers", "db", {"location": "eastus", "properties": {"version": "15"}})],
    "cache": [("Microsoft.Cache/Redis", "cache", {"location": "eastus", "properties": {"sku": {"name": "Basic"}}})],
    "storage": [("Microsoft.Storage/storageAccounts", "infrastoreassets", {"location": "eastus", "sku": {"name": "Standard_LRS"}, "kind": "StorageV2"})],
    "no_sql": [("Microsoft.DocumentDB/databaseAccounts", "items", {"location": "eastus", "properties": {"databaseAccountOfferType": "Standard"}})],
    "serverless": [("Microsoft.Web/serverfarms", "app-plan", {"location": "eastus", "sku": {"name": "Y1"}}),
                   ("Microsoft.Web/functions", "app-fn", {"location": "eastus"})],
    "k8s": [("Microsoft.ContainerService/managedClusters", "main-aks", {"location": "eastus"})],
    "queue": [("Microsoft.ServiceBus/namespaces", "events-ns", {"location": "eastus", "sku": {"name": "Standard"}})],
}


# --------------------------------------------------------------------------- #
# Rendering helpers
# --------------------------------------------------------------------------- #
def _normalize(target: str) -> str:
    return target.lower()


def _resolve_components(description: str, components: Optional[List[str]], target: str) -> List[str]:
    if components:
        return list(components)
    return detect_components(description)


def _tf_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return "[" + ", ".join(_tf_scalar(v) for v in value) + "]"
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


def _tf_resource(rtype: str, name: str, attrs: Dict[str, Any]) -> str:
    lines = [f'resource "{rtype}" "{name}" {{']
    for key, value in attrs.items():
        if isinstance(value, dict):
            lines.append(f"  {key} {{")
            for k2, v2 in value.items():
                lines.append(f"    {k2} = {_tf_scalar(v2)}")
            lines.append("  }")
        else:
            lines.append(f"  {key} = {_tf_scalar(value)}")
    lines.append("}")
    return "\n".join(lines)


def _tf_provider_source(provider_name: str) -> str:
    return {
        "aws": '"hashicorp/aws"',
        "google": '"hashicorp/google"',
        "azurerm": '"hashicorp/azurerm"',
    }.get(provider_name, '"hashicorp/aws"')


def _tf_default_region(target: str) -> str:
    return {"aws": '"us-east-1"', "gcp": '"us-central1"', "azure": '"eastus"'}[target]


def _apply_ha(target: str, attrs: Dict[str, Any]) -> None:
    """Mutate attrs in place to reflect high-availability settings."""
    if target == "aws":
        if "multi_az" not in attrs:
            attrs["multi_az"] = True
        if "backup_retention_period" not in attrs:
            attrs["backup_retention_period"] = 7
    elif target == "gcp":
        settings_block = attrs.setdefault("settings", {})
        if isinstance(settings_block, dict):
            settings_block.setdefault("availability_type", "REGIONAL")


def _render_terraform(target: str, components: List[str], description: str) -> str:
    table = _TF_RESOURCES.get(_normalize(target), _TF_RESOURCES["aws"])
    ha = "ha" in components
    provider_name = {"aws": "aws", "gcp": "google", "azure": "azurerm"}[_normalize(target)]
    lines: List[str] = []
    lines.append("# Generated by cloud-infra-planner (deterministic offline core)")
    lines.append(f"# Requirement: {description}")
    lines.append(f"# Target: {target}  |  Components: {', '.join(components)}")
    lines.append("")
    lines.append("terraform {")
    lines.append('  required_version = ">= 1.0"')
    lines.append("  required_providers {")
    lines.append(f"    {provider_name} = {{")
    lines.append(f"      source  = {_tf_provider_source(provider_name)}")
    lines.append("    }")
    lines.append("  }")
    lines.append("}")
    lines.append("")
    lines.append(f'provider "{provider_name}" {{ region = var.region }}')
    lines.append("")
    lines.append('variable "region" {')
    lines.append("  type    = string")
    lines.append(f"  default = {_tf_default_region(target)}")
    lines.append("}")
    lines.append("")

    for component in components:
        if component == "ha":
            continue
        for (rtype, rname, attrs) in table.get(component, []):
            if ha and component in ("compute", "database", "cache"):
                _apply_ha(target, attrs)
            lines.append(_tf_resource(rtype, rname, attrs))
            lines.append("")

    lines.append('output "template_source" {')
    lines.append('  value = "cloud-infra-planner"')
    lines.append("}")
    return "\n".join(lines)


def _render_cloudformation(target: str, components: List[str], description: str) -> str:
    import yaml  # local import: only needed for YAML output
    template: Dict[str, Any] = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": f"cloud-infra-planner: {description}",
        "Resources": {},
    }
    for component in components:
        if component == "ha":
            continue
        for (rtype, rname, props) in _CFN_RESOURCES.get(component, []):
            entry: Dict[str, Any] = {"Type": rtype, "Properties": props}
            if "ha" in components and component == "database":
                entry["Properties"] = {**props, "MultiAZ": True}
            template["Resources"][rname] = entry
    return (
        "# Generated by cloud-infra-planner (deterministic offline core)\n"
        + yaml.safe_dump(template, sort_keys=False, default_flow_style=False)
    )


def _render_arm(target: str, components: List[str], description: str) -> str:
    resources: List[Dict[str, Any]] = []
    for component in components:
        if component == "ha":
            continue
        for (rtype, rname, props) in _ARM_RESOURCES.get(component, []):
            resource: Dict[str, Any] = {"type": rtype, "apiVersion": "2021-04-01", "name": rname}
            resource.update(props)
            resources.append(resource)
    template = {
        "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
        "contentVersion": "1.0.0.0",
        "description": f"cloud-infra-planner: {description}",
        "resources": resources,
    }
    return json.dumps(template, indent=2)


# --------------------------------------------------------------------------- #
# LLM advisory augmentation (opt-in, grounded, safe-fallback)
# --------------------------------------------------------------------------- #
async def _llm_augment(description: str, components: List[str]) -> List[str]:
    """Ask a configured, non-offline LLM to extract additional components.

    The LLM output is parsed defensively; any failure leaves the deterministic
    component list untouched.  Only components present in _AVAILABLE_COMPONENTS
    are accepted, so the LLM can never inject arbitrary resources.
    """
    try:
        adapter = get_llm_adapter()
        if not adapter.is_configured() or settings.demo_mode:
            return list(components)
        if settings.llm_provider.lower() == "offline":
            return list(components)
        system = (
            "You are an infrastructure planner. From the user's description of "
            "desired cloud infrastructure, extract the relevant components as a "
            "JSON array of strings. Allowed components: "
            + ", ".join(_AVAILABLE_COMPONENTS)
            + ". Respond with ONLY the JSON array."
        )
        result = await adapter.chat(
            [{"role": "system", "content": system},
             {"role": "user", "content": description}],
            temperature=0.2, max_tokens=256,
        )
        parsed = json.loads(result.content.strip())
        if isinstance(parsed, list):
            merged = list(components)
            for comp in parsed:
                if isinstance(comp, str) and comp in _AVAILABLE_COMPONENTS and comp not in merged:
                    merged.append(comp)
            return merged
    except Exception:
        pass
    return list(components)


class Generator:
    """Deterministic NL -> IaC generator with optional LLM advisory augmentation."""

    def detect_components(self, description: str) -> List[str]:
        return detect_components(description)

    async def generate(
        self,
        description: str,
        provider: Provider,
        target: Target,
        components: Optional[List[str]] = None,
        use_llm: bool = True,
    ) -> str:
        """Render an IaC template.  Always returns a structurally-valid template."""
        prov = provider.value if hasattr(provider, "value") else str(provider).lower()
        tgt = target.value if hasattr(target, "value") else str(target).lower()

        resolved = _resolve_components(description, components, tgt)
        if use_llm:
            resolved = await _llm_augment(description, resolved)

        if prov == "terraform":
            return _render_terraform(tgt, resolved, description)
        elif prov == "cloudformation":
            return _render_cloudformation(tgt, resolved, description)
        elif prov == "arm":
            return _render_arm(tgt, resolved, description)
        else:
            raise ValueError(f"Unsupported provider: {prov}")


generator = Generator()
Generator.__module__ = "backend.app.services.generator"