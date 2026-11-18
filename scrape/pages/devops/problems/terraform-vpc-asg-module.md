# Terraform: VPC and autoscaling group module — DevOps interview problem · FAANGrind

Source: https://faangrind.vercel.app/devops/problems/terraform-vpc-asg-module

[DevOps problems](/devops#problems)

CODEImplement it#39Medium

# Terraform: VPC and autoscaling group module

terraformawsvpcautoscalingalbmodulesReported at Infosys, Capgemini, Accenture

## Problem statement

Write a reusable Terraform module that creates a 3-availability-zone VPC and a web tier on EC2: public and private subnets computed from one CIDR, an internet gateway, NAT gateways, route tables, and an Auto Scaling group behind an Application Load Balancer with a launch template, target group, listeners, least-privilege security groups and a target tracking policy. The module must be usable for both dev (one NAT gateway, 1 instance, HTTP only) and prod (one NAT per zone, 3 to 12 instances, HTTPS) through typed, validated variables. No AMI ids or account ids may be hard-coded.

## Requirements

### Functional

* `variables.tf` with types, descriptions and `validation` blocks; `main.tf` with locals, `for_each` over availability zones and `cidrsubnet` arithmetic; `outputs.tf` exposing ids the next modules (RDS, EKS, DNS) need.
* Subnets carry `kubernetes.io/role/elb`, `kubernetes.io/role/internal-elb` and `karpenter.sh/discovery` tags when an EKS cluster name is given.
* The launch template requires IMDSv2, uses an SSM public parameter for the AMI, encrypted gp3 root volume and user data from a template file.
* The ALB listens on 80 and, when a certificate ARN is given, on 443 with 80 redirecting; the target group health check hits the app's readiness path.
* The ASG uses ELB health checks, a target tracking policy on `ALBRequestCountPerTarget`, and `instance_refresh` so a launch template change rolls instances automatically.

### Non-functional

* Loss of one AZ keeps 2 of 3 instances and, in prod, outbound traffic from the other 2 zones (one NAT per AZ).
* A rolling AMI update keeps at least 90 percent of desired capacity healthy and rolls back automatically on failed health checks.
* Each /20 subnet has 4,091 usable addresses; the /16 leaves 10 of 16 slots free for future tiers.
* `terraform plan` on an unchanged configuration shows 0 changes, even after the scaling policy moved `desired_capacity`.
* An unhealthy instance leaves the target group within 45 s (3 failed checks at 15 s) and drains for 30 s before termination.
* Dev costs about one third of prod for NAT gateways: 1 instead of 3 hourly charges.

## API

```
# Module interface (modules/web-asg)
Inputs   name, environment, vpc_cidr, az_count, single_nat_gateway, eks_cluster_name,
         instance_type, ami_ssm_parameter, asg_min_size, asg_max_size, app_port,
         health_check_path, requests_per_target, certificate_arn, tags
Outputs  vpc_id, public_subnet_ids, private_subnet_ids, nat_gateway_public_ips,
         alb_dns_name, alb_zone_id, asg_name, app_security_group_id

# Workflow in envs/prod
terraform init                      # downloads hashicorp/aws ~> 6.0, configures the S3 backend
terraform fmt -check -recursive     # formatting is a CI gate
terraform validate                  # types, references, validation block syntax
terraform plan -out=tfplan          # review: expect 45 to add on first run in prod (29 blocks, 8 of them for_each over 3 AZs)
terraform apply tfplan              # apply exactly the reviewed plan
terraform output alb_dns_name       # feed into a Route 53 alias record

# Rolling AMI update: change nothing in git, the SSM parameter moved
terraform plan                      # shows launch template update, ASG picks latest_version
terraform apply                     # instance_refresh starts; watch with:
aws autoscaling describe-instance-refreshes --auto-scaling-group-name <asg_name>

# Files the module expects next to main.tf
user_data.sh.tftpl                  # templatefile input with ${app_port} and ${environment}
```

## Data model

```
aws_vpc (10.40.0.0/16)
 |- aws_internet_gateway
 |- aws_subnet.public[az]   10.40.0.0/20, 10.40.16.0/20, 10.40.32.0/20     tags: role/elb=1
 |     |- aws_route_table.public -> 0.0.0.0/0 via igw
 |     |- aws_nat_gateway[az] + aws_eip[az]      (1 or 3, by single_nat_gateway)
 |- aws_subnet.private[az]  10.40.128.0/20, 10.40.144.0/20, 10.40.160.0/20  tags: role/internal-elb=1
 |     |- aws_route_table.private[az] -> 0.0.0.0/0 via nat[az] (or nat[first az])
 |
 |- aws_security_group.alb   in: 80, 443 from 0.0.0.0/0    out: app_port to sg.app
 |- aws_security_group.app   in: app_port from sg.alb      out: all (through NAT)
 |
 |- aws_lb (public subnets) -> aws_lb_listener 80 (redirect or forward), 443 (forward)
 |     |- aws_lb_target_group (HTTP app_port, health check /readyz, drain 30 s)
 |
 |- aws_launch_template (AMI from data.aws_ssm_parameter, IMDSv2, gp3 encrypted, user data)
 |- aws_iam_role + instance profile (AmazonSSMManagedInstanceCore, no SSH)
 |- aws_autoscaling_group (private subnets, ELB health check, instance_refresh)
 |     |- aws_autoscaling_policy TargetTrackingScaling ALBRequestCountPerTarget
 |        resource_label = "<alb arn_suffix>/<target group arn_suffix>"

for_each keys are AZ names, so adding a 4th AZ adds resources instead of renumbering them.
```

## Approach

1. Variables first: `name` with a regex validation, `environment` limited to three values, `vpc_cidr` validated with `cidrhost`, `az_count` 2 to 4, `asg_max_size >= asg_min_size`. A validation error stops `terraform plan` with a message the caller can act on.
2. Data sources: `aws_availability_zones` filtered to `opt-in-not-required` so Local Zones are never picked; `aws_ssm_parameter` for the Amazon Linux 2023 AMI so the id is never in git.
3. Locals compute the subnet map: `cidrsubnet(var.vpc_cidr, 4, i)` for public and `cidrsubnet(var.vpc_cidr, 4, i + 8)` for private, keyed by AZ name. `nat_azs` is one AZ or all of them.
4. VPC, internet gateway, then `aws_subnet.public` and `aws_subnet.private` with `for_each` over the maps. Tags merge the common tags, the optional EKS discovery tags and the role tag.
5. NAT: one EIP and one NAT gateway per entry in `nat_azs`, with `depends_on` the internet gateway. One private route table per AZ so each can point at its own NAT; with a single NAT every table points at the first AZ's gateway.
6. Security groups as empty shells plus `aws_vpc_security_group_ingress_rule` and `egress_rule` resources, which the provider recommends over inline rules. The ALB may talk only to the app port on the app group; the app group accepts only from the ALB group.
7. IAM role and instance profile with the SSM managed policy: operators use Session Manager, no key pairs exist.
8. Launch template: `http_tokens = "required"`, detailed monitoring, encrypted gp3, `update_default_version`, `user_data` from `templatefile` and `create_before_destroy`.
9. ALB in public subnets, target group with `name_prefix` and `create_before_destroy` (an in-use target group cannot be replaced otherwise), listeners built with `dynamic "default_action"` so one file serves dev and prod.
10. ASG in private subnets, `health_check_type = "ELB"`, `launch_template.version = latest_version`, `instance_refresh` with 90/110 percent bounds, `skip_matching` and `auto_rollback`, and `ignore_changes = [desired_capacity]` so the scaling policy and Terraform do not fight.
11. Target tracking on `ALBRequestCountPerTarget` with `resource_label` built from the two `arn_suffix` attributes.
12. Outputs give the next modules what they need and nothing more: ids, the ALB DNS name and zone id, and the app security group id for the database rule.

## Architecture diagram

Rendering diagram…

## Deep dives

### cidrsubnet arithmetic

`cidrsubnet(prefix, newbits, netnum)` extends the prefix length by `newbits` and picks the `netnum`-th block, counting from 0. With `10.40.0.0/16` and `newbits = 4` the result is a /20, there are 2^4 = 16 slots, and each holds 2^12 = 4,096 addresses (AWS reserves 5, so 4,091 usable). Slot 0 is `10.40.0.0/20`, slot 1 is `10.40.16.0/20`, slot 2 is `10.40.32.0/20`. Private subnets use slots 8, 9 and 10: `10.40.128.0/20`, `10.40.144.0/20`, `10.40.160.0/20`. The gap between 3 and 8 is deliberate: a fourth AZ or a database tier can be added without renumbering, and renumbering a subnet means destroying it. Keying the `for_each` by AZ name has the same purpose: removing the middle AZ removes one subnet instead of shifting the other two to new indexes. Why /20 and not /24: an EKS cluster with the VPC CNI gives every pod an address from the subnet, and a /24 (251 usable) runs out at about 4 nodes of `m5.large`.

### One NAT per AZ or one in total

A NAT gateway has an hourly charge plus a per-GB charge; three of them triple the hourly part (an assumed 0.045 USD per hour gives about 99 USD per month for three versus 33 USD for one). The single NAT also carries a hidden cost: traffic from zone b to the NAT in zone a crosses zones and is billed as inter-AZ data transfer. The real question is availability: if zone a fails with one NAT, instances in b and c are still running but cannot reach package mirrors, Secrets Manager or any external API. For prod the module defaults to one per AZ and one route table per AZ so that each zone's egress stays inside the zone. For dev `single_nat_gateway = true` keeps the same code path, the same tags and the same route tables, so dev is a cheap copy of prod rather than a different design.

### Instance refresh for rolling AMI updates

The SSM parameter resolves to a new AMI id on the next `terraform plan`. The launch template gets a new version, `update_default_version` marks it default, and the ASG references `latest_version`, so the ASG resource shows a diff and `instance_refresh` starts. With `min_healthy_percentage = 90` and `max_healthy_percentage = 110` on 12 instances, at most 1 instance is out of service and at most 13 exist at once; on 3 instances, 90 percent rounds to 3 so AWS launches first and terminates after. `instance_warmup = 120` matches the ASG's `default_instance_warmup`: a new instance must pass the ALB health check and then wait 120 s before the next replacement starts. `skip_matching` keeps instances already on the new version, `auto_rollback` returns to the previous template if new instances fail. The whole 12-instance roll takes roughly 12 x (boot + 120 s), about 30 to 40 minutes, with no manual step.

### Module interface design

A module is an API. Inputs should be few, typed and validated; defaults should be the production-safe choice (`single_nat_gateway = false`, `http_tokens = "required"`), so a caller has to opt into the cheaper or weaker option in writing. Behaviour toggles are booleans or `count` on a resource, never a copied file. Outputs expose ids, not whole objects, so the module can change internals without breaking callers. Version the module with Git tags and pin `source = "git::...?ref=v1.4.0"` in prod. Anything environment-specific (the certificate ARN, the cluster name, the tags map) is an input; anything structural (two tiers, per-AZ route tables) is fixed, because a module that can build any shape is a module nobody can review.

## Evaluation

**Static checks.** `terraform fmt -check`, `terraform validate` and `tflint` with the AWS ruleset run in CI on every pull request. `terraform plan` against an empty account must show exactly the expected count (45 resources for the module at `az_count = 3` with three NAT gateways and a certificate: 29 resource blocks, of which 8 are `for_each` over 3 AZs; dev with one NAT gateway and no certificate plans 39). `checkov` or `trivy config` must pass: IMDSv2 required, EBS encrypted, no `0.0.0.0/0` ingress on the app group, ALB with `drop_invalid_header_fields`.

**Behaviour tests.** Apply in a sandbox account, then: `curl -I` against the ALB DNS name on port 80 returns 301 to HTTPS in prod and 200 in dev; `aws elbv2 describe-target-health` shows 3 healthy targets in 3 different AZs; stop the app on one instance and watch the target go unhealthy within 45 s and the ASG replace it; run a load test at 4 x `requests_per_target` and watch the ASG grow and, 15 minutes after the test, shrink. Change `instance_type` and confirm an instance refresh runs with no 5xx from the ALB. Run `terraform plan` again after the scale-out: 0 changes, which proves `ignore_changes` is right.

**Edge cases.** `az_count = 4` in a region with 3 AZs fails on `slice`, so the validation should check against the data source in a precondition. A `vpc_cidr` of /24 fails the validation with a clear message. `certificate_arn = ""` must produce no 443 listener, no 443 rule, and a forwarding 80 listener. `terraform destroy` on prod is blocked by `enable_deletion_protection` on the ALB.

**What a strong answer adds.** The separate security group rule resources and why; `create_before_destroy` on the target group and launch template; the `resource_label` format; `skip_matching` and `auto_rollback`; per-AZ route tables; a note that Terraform test (`terraform test` with `.tftest.hcl` files) or Terratest can assert the plan.

## Bottlenecks & mitigations

* NAT gateway bandwidth and the per-GB charge: a tier that pulls large images or streams to S3 should use VPC endpoints for S3 and ECR instead of NAT.
* `health_check_grace_period` of 120 s sets the floor on how fast a scale-out adds capacity; baking the app into the AMI cuts it.
* Target tracking reacts on 1-minute ALB metrics, so a spike shorter than 2 to 3 minutes is served by the existing instances only.
* A single ALB per module: a listener rule limit or a WAF association applies to every host on it.
* The Terraform state for VPC and ASG is one file, so a locked state during a long instance refresh blocks unrelated changes.

## Failure modes

* **Plan wants to destroy and recreate every subnet.** The `for_each` keys changed from AZ names to indexes, or the AZ order changed. Mitigation: key by AZ name; use `moved` blocks when a key must change.
* **Instances never become healthy and the ASG keeps replacing them.** The health check path returns non-200 before the app is up, or the app group does not allow the ALB. Mitigation: `health_check_grace_period` above the real boot time; check `aws elbv2 describe-target-health` reason codes.
* **Terraform and the scaling policy fight over desired\_capacity.** Each apply resets the count to min. Mitigation: `ignore_changes = [desired_capacity]`.
* **Cannot delete the target group.** It is still attached to a listener. Mitigation: `name_prefix` plus `create_before_destroy` so the new one is attached first.
* **Instances in private subnets have no internet after a zone failure.** Single NAT in the failed zone. Mitigation: `single_nat_gateway = false` in prod.
* **Credential theft through SSRF.** An app proxying user URLs fetches `169.254.169.254`. Mitigation: `http_tokens = "required"` and `http_put_response_hop_limit = 1` so a containerised app cannot reach it either.
* **Instance refresh rolls back every time.** The new AMI has a user data or package regression. Mitigation: a dev apply first; a checkpoint at 25 percent with `checkpoint_percentages`.
* **The load balancer controller ignores the subnets.** Role tags missing because `eks_cluster_name` was empty. Mitigation: set it, and check with `aws ec2 describe-subnets --filters Name=tag:kubernetes.io/role/elb,Values=1`.

## Reference solution

Terraform (HCL) · parsed and checked

```
# =====================================================================
# modules/web-asg/variables.tf
# =====================================================================

variable "name" {
  description = "Short name used as a prefix for every resource (for example orders-prod)."
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,20}$", var.name))
    error_message = "name must be 2 to 21 chars, lowercase letters, digits and hyphens, starting with a letter."
  }
}

variable "environment" {
  description = "dev, staging or prod. Drives the single-NAT default and tags."
  type        = string

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be dev, staging or prod."
  }
}

variable "vpc_cidr" {
  description = "VPC CIDR. A /16 gives 65,536 addresses, enough for 6 /20 subnets plus spare."
  type        = string
  default     = "10.40.0.0/16"

  validation {
    condition     = can(cidrhost(var.vpc_cidr, 0)) && tonumber(split("/", var.vpc_cidr)[1]) <= 20
    error_message = "vpc_cidr must be a valid IPv4 CIDR no smaller than /20."
  }
}

variable "az_count" {
  description = "Number of availability zones to use. 3 is the production default."
  type        = number
  default     = 3

  validation {
    condition     = var.az_count >= 2 && var.az_count <= 4
    error_message = "az_count must be between 2 and 4."
  }
}

variable "single_nat_gateway" {
  description = "true = one NAT gateway for all private subnets (cheap, dev). false = one per AZ (prod)."
  type        = bool
  default     = false
}

variable "eks_cluster_name" {
  description = "If set, subnets get the tags the AWS Load Balancer Controller and Karpenter use for discovery."
  type        = string
  default     = ""
}

variable "instance_type" {
  description = "EC2 instance type for the web tier."
  type        = string
  default     = "t3.small"
}

variable "ami_ssm_parameter" {
  description = "SSM public parameter that resolves to the AMI id. No AMI ids are hard-coded."
  type        = string
  default     = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-6.1-x86_64"
}

variable "asg_min_size" {
  description = "Minimum instances. 3 in prod so one per AZ survives a zone loss."
  type        = number
  default     = 3
}

variable "asg_max_size" {
  description = "Maximum instances the target tracking policy may reach."
  type        = number
  default     = 12

  validation {
    condition     = var.asg_max_size >= var.asg_min_size
    error_message = "asg_max_size must be at least asg_min_size."
  }
}

variable "app_port" {
  description = "Port the application listens on behind the ALB."
  type        = number
  default     = 8080
}

variable "health_check_path" {
  description = "HTTP path the ALB target group probes. Must return 200 only when ready."
  type        = string
  default     = "/readyz"
}

variable "requests_per_target" {
  description = "Target tracking goal: ALB requests per instance per minute. Measure it from a load test."
  type        = number
  default     = 3000
}

variable "certificate_arn" {
  description = "ACM certificate for the HTTPS listener. Empty = HTTP only (dev)."
  type        = string
  default     = ""
}

variable "tags" {
  description = "Extra tags merged into every resource."
  type        = map(string)
  default     = {}
}

# =====================================================================
# modules/web-asg/main.tf
# =====================================================================

terraform {
  required_version = ">= 1.9.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

# Only real AZs, not Local Zones (those need an opt-in and have no NAT).
data "aws_availability_zones" "available" {
  state = "available"
  filter {
    name   = "opt-in-status"
    values = ["opt-in-not-required"]
  }
}

# The AMI id comes from AWS's public SSM parameter, so every plan picks the
# current Amazon Linux 2023 image and nothing in git goes stale.
data "aws_ssm_parameter" "ami" {
  name = var.ami_ssm_parameter
}

locals {
  azs = slice(data.aws_availability_zones.available.names, 0, var.az_count)

  # Subnet layout with cidrsubnet(prefix, newbits, netnum):
  #   /16 + 4 newbits = /20 (4,096 addresses each), 16 possible slots.
  #   public  subnets take slots 0..az_count-1
  #   private subnets take slots 8..8+az_count-1  (leaves room for a 4th AZ or a db tier)
  public_subnets  = { for i, az in local.azs : az => cidrsubnet(var.vpc_cidr, 4, i) }
  private_subnets = { for i, az in local.azs : az => cidrsubnet(var.vpc_cidr, 4, i + 8) }

  # dev saves ~2 NAT gateways; prod keeps one per AZ so a zone loss does not
  # cut outbound traffic for the other zones.
  nat_azs = var.single_nat_gateway ? [local.azs[0]] : local.azs

  eks_tags = var.eks_cluster_name == "" ? {} : {
    "kubernetes.io/cluster/${var.eks_cluster_name}" = "shared"
    "karpenter.sh/discovery"                        = var.eks_cluster_name
  }

  common_tags = merge(var.tags, {
    Name        = var.name
    Environment = var.environment
    ManagedBy   = "terraform"
  })
}

# ---------- VPC and gateways ----------

resource "aws_vpc" "this" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true # needed for EKS, RDS endpoints and private hosted zones
  tags                 = local.common_tags
}

resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id
  tags   = local.common_tags
}

resource "aws_subnet" "public" {
  for_each = local.public_subnets

  vpc_id                  = aws_vpc.this.id
  cidr_block              = each.value
  availability_zone       = each.key
  map_public_ip_on_launch = false # ALB and NAT get addresses; instances never do

  tags = merge(local.common_tags, local.eks_tags, {
    Name                     = "${var.name}-public-${each.key}"
    Tier                     = "public"
    "kubernetes.io/role/elb" = "1" # AWS Load Balancer Controller: internet-facing LBs go here
  })
}

resource "aws_subnet" "private" {
  for_each = local.private_subnets

  vpc_id            = aws_vpc.this.id
  cidr_block        = each.value
  availability_zone = each.key

  tags = merge(local.common_tags, local.eks_tags, {
    Name                              = "${var.name}-private-${each.key}"
    Tier                              = "private"
    "kubernetes.io/role/internal-elb" = "1" # internal LBs and Karpenter nodes go here
  })
}

resource "aws_eip" "nat" {
  for_each = toset(local.nat_azs)

  domain = "vpc"
  tags   = merge(local.common_tags, { Name = "${var.name}-nat-${each.key}" })
}

resource "aws_nat_gateway" "this" {
  for_each = toset(local.nat_azs)

  allocation_id = aws_eip.nat[each.key].id
  subnet_id     = aws_subnet.public[each.key].id
  tags          = merge(local.common_tags, { Name = "${var.name}-nat-${each.key}" })

  # The provider docs recommend an explicit dependency so the IGW exists first.
  depends_on = [aws_internet_gateway.this]
}

# ---------- Route tables ----------

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.this.id
  tags   = merge(local.common_tags, { Name = "${var.name}-public" })
}

resource "aws_route" "public_internet" {
  route_table_id         = aws_route_table.public.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.this.id
}

resource "aws_route_table_association" "public" {
  for_each = aws_subnet.public

  subnet_id      = each.value.id
  route_table_id = aws_route_table.public.id
}

# One private route table per AZ so each AZ can point at its own NAT.
resource "aws_route_table" "private" {
  for_each = aws_subnet.private

  vpc_id = aws_vpc.this.id
  tags   = merge(local.common_tags, { Name = "${var.name}-private-${each.key}" })
}

resource "aws_route" "private_nat" {
  for_each = aws_subnet.private

  route_table_id         = aws_route_table.private[each.key].id
  destination_cidr_block = "0.0.0.0/0"
  # With a single NAT every AZ routes to the one in the first AZ.
  nat_gateway_id = var.single_nat_gateway ? aws_nat_gateway.this[local.azs[0]].id : aws_nat_gateway.this[each.key].id
}

resource "aws_route_table_association" "private" {
  for_each = aws_subnet.private

  subnet_id      = each.value.id
  route_table_id = aws_route_table.private[each.key].id
}

# ---------- Security groups (least privilege, rules as separate resources) ----------

resource "aws_security_group" "alb" {
  name_prefix = "${var.name}-alb-"
  description = "ALB: 80/443 from the internet"
  vpc_id      = aws_vpc.this.id
  tags        = merge(local.common_tags, { Name = "${var.name}-alb" })

  lifecycle {
    create_before_destroy = true # a renamed SG must exist before the old one is removed from the ALB
  }
}

resource "aws_vpc_security_group_ingress_rule" "alb_http" {
  security_group_id = aws_security_group.alb.id
  description       = "HTTP from anywhere, redirected to HTTPS by the listener"
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "tcp"
  from_port         = 80
  to_port           = 80
}

resource "aws_vpc_security_group_ingress_rule" "alb_https" {
  count = var.certificate_arn == "" ? 0 : 1

  security_group_id = aws_security_group.alb.id
  description       = "HTTPS from anywhere"
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
}

resource "aws_vpc_security_group_egress_rule" "alb_to_app" {
  security_group_id            = aws_security_group.alb.id
  description                  = "Only to the app port on the instances"
  referenced_security_group_id = aws_security_group.app.id
  ip_protocol                  = "tcp"
  from_port                    = var.app_port
  to_port                      = var.app_port
}

resource "aws_security_group" "app" {
  name_prefix = "${var.name}-app-"
  description = "Web instances: app port from the ALB only"
  vpc_id      = aws_vpc.this.id
  tags        = merge(local.common_tags, { Name = "${var.name}-app" })

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_vpc_security_group_ingress_rule" "app_from_alb" {
  security_group_id            = aws_security_group.app.id
  description                  = "App port from the ALB security group, never from a CIDR"
  referenced_security_group_id = aws_security_group.alb.id
  ip_protocol                  = "tcp"
  from_port                    = var.app_port
  to_port                      = var.app_port
}

resource "aws_vpc_security_group_egress_rule" "app_all" {
  security_group_id = aws_security_group.app.id
  description       = "Outbound through NAT for packages, SSM and the database"
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}

# ---------- IAM for SSM Session Manager (no SSH, no key pairs) ----------

data "aws_iam_policy_document" "ec2_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "app" {
  name_prefix        = "${var.name}-app-"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume.json
  tags               = local.common_tags
}

resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.app.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "app" {
  name_prefix = "${var.name}-app-"
  role        = aws_iam_role.app.name
}

# ---------- Launch template ----------

resource "aws_launch_template" "app" {
  name_prefix            = "${var.name}-"
  image_id               = data.aws_ssm_parameter.ami.value
  instance_type          = var.instance_type
  update_default_version = true # each change becomes the default version the ASG follows
  vpc_security_group_ids = [aws_security_group.app.id]

  iam_instance_profile {
    name = aws_iam_instance_profile.app.name
  }

  # IMDSv2 only: a stolen SSRF cannot read instance credentials with a plain GET.
  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
    instance_metadata_tags      = "enabled"
  }

  monitoring {
    enabled = true # 1-minute CloudWatch metrics; needed for scaling that reacts in time
  }

  block_device_mappings {
    device_name = "/dev/xvda"
    ebs {
      volume_size           = 20
      volume_type           = "gp3"
      encrypted             = true
      delete_on_termination = true
    }
  }

  # Minimal user data: install the app from a release artifact and start it.
  # Real projects bake the app into the AMI and keep this to configuration.
  user_data = base64encode(templatefile("${path.module}/user_data.sh.tftpl", {
    app_port    = var.app_port
    environment = var.environment
  }))

  tag_specifications {
    resource_type = "instance"
    tags          = merge(local.common_tags, { Name = "${var.name}-app" })
  }

  lifecycle {
    create_before_destroy = true
  }
}

# ---------- Load balancer ----------

resource "aws_lb" "this" {
  name                       = "${var.name}-alb"
  internal                   = false
  load_balancer_type         = "application"
  security_groups            = [aws_security_group.alb.id]
  subnets                    = [for s in aws_subnet.public : s.id]
  drop_invalid_header_fields = true
  idle_timeout               = 60
  enable_deletion_protection = var.environment == "prod"
  tags                       = local.common_tags
}

resource "aws_lb_target_group" "app" {
  name_prefix          = "app-" # at most 6 characters
  port                 = var.app_port
  protocol             = "HTTP"
  vpc_id               = aws_vpc.this.id
  target_type          = "instance"
  deregistration_delay = 30 # seconds to drain in-flight requests before an instance is removed

  health_check {
    enabled             = true
    path                = var.health_check_path
    port                = "traffic-port"
    protocol            = "HTTP"
    interval            = 15
    timeout             = 5
    healthy_threshold   = 2 # in service after 30 s of passing checks
    unhealthy_threshold = 3 # out after 45 s of failing checks
    matcher             = "200"
  }

  tags = local.common_tags

  # A target group in use by a listener cannot be deleted first; name_prefix
  # plus create_before_destroy lets Terraform swap it without downtime.
  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.this.arn
  port              = 80
  protocol          = "HTTP"

  # With a certificate, 80 only redirects. Without one (dev) it forwards.
  dynamic "default_action" {
    for_each = var.certificate_arn == "" ? [1] : []
    content {
      type             = "forward"
      target_group_arn = aws_lb_target_group.app.arn
    }
  }

  dynamic "default_action" {
    for_each = var.certificate_arn == "" ? [] : [1]
    content {
      type = "redirect"
      redirect {
        port        = "443"
        protocol    = "HTTPS"
        status_code = "HTTP_301"
      }
    }
  }
}

resource "aws_lb_listener" "https" {
  count = var.certificate_arn == "" ? 0 : 1

  load_balancer_arn = aws_lb.this.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = var.certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }
}

# ---------- Auto Scaling group ----------

resource "aws_autoscaling_group" "app" {
  name_prefix               = "${var.name}-"
  min_size                  = var.asg_min_size
  max_size                  = var.asg_max_size
  desired_capacity          = var.asg_min_size
  vpc_zone_identifier       = [for s in aws_subnet.private : s.id] # one subnet per AZ = spread by AWS
  target_group_arns         = [aws_lb_target_group.app.arn]
  health_check_type         = "ELB" # replace an instance the ALB marks unhealthy, not only a dead VM
  health_check_grace_period = 120   # time for user data to install and start the app
  default_instance_warmup   = 120   # new instances do not count in metrics until warm
  termination_policies      = ["OldestLaunchTemplate", "OldestInstance"]
  wait_for_capacity_timeout = "10m"

  launch_template {
    id      = aws_launch_template.app.id
    version = aws_launch_template.app.latest_version
  }

  # Rolling replacement whenever the launch template changes (new AMI, new
  # user data, new instance type). 90 percent healthy means at most ~10 percent
  # of capacity is being replaced at any moment.
  instance_refresh {
    strategy = "Rolling"
    preferences {
      min_healthy_percentage = 90
      max_healthy_percentage = 110
      instance_warmup        = 120
      skip_matching          = true # do not replace instances already on the new version
      auto_rollback          = true # bring back the old template if new instances fail health checks
    }
    triggers = ["tag"]
  }

  dynamic "tag" {
    for_each = merge(local.common_tags, { Name = "${var.name}-app" })
    content {
      key                 = tag.key
      value               = tag.value
      propagate_at_launch = true
    }
  }

  lifecycle {
    create_before_destroy = true
    # The scaling policy moves desired_capacity; Terraform must not reset it on every apply.
    ignore_changes = [desired_capacity]
  }
}

# Target tracking on ALB requests per target keeps each instance at a known load.
resource "aws_autoscaling_policy" "requests" {
  name                      = "${var.name}-requests-per-target"
  autoscaling_group_name    = aws_autoscaling_group.app.name
  policy_type               = "TargetTrackingScaling"
  estimated_instance_warmup = 120

  target_tracking_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ALBRequestCountPerTarget"
      # Format: app/<alb-name>/<id>/targetgroup/<tg-name>/<id>, built from the two ARN suffixes.
      resource_label = "${aws_lb.this.arn_suffix}/${aws_lb_target_group.app.arn_suffix}"
    }
    target_value     = var.requests_per_target
    disable_scale_in = false
  }
}

# =====================================================================
# modules/web-asg/outputs.tf
# =====================================================================

output "vpc_id" {
  description = "VPC id for other modules (RDS, EKS) to attach to."
  value       = aws_vpc.this.id
}

output "public_subnet_ids" {
  description = "Public subnet ids keyed by AZ."
  value       = { for az, s in aws_subnet.public : az => s.id }
}

output "private_subnet_ids" {
  description = "Private subnet ids keyed by AZ."
  value       = { for az, s in aws_subnet.private : az => s.id }
}

output "nat_gateway_public_ips" {
  description = "Egress IPs to allow-list at third parties."
  value       = [for e in aws_eip.nat : e.public_ip]
}

output "alb_dns_name" {
  description = "Point a Route 53 alias record at this."
  value       = aws_lb.this.dns_name
}

output "alb_zone_id" {
  description = "Hosted zone id of the ALB, needed for the alias record."
  value       = aws_lb.this.zone_id
}

output "asg_name" {
  description = "Auto Scaling group name, for CloudWatch dashboards and instance refresh commands."
  value       = aws_autoscaling_group.app.name
}

output "app_security_group_id" {
  description = "Attach this to the database security group as the allowed source."
  value       = aws_security_group.app.id
}

# =====================================================================
# Root module usage: envs/prod/main.tf
# =====================================================================

module "web_prod" {
  source = "../../modules/web-asg"

  name               = "orders-prod"
  environment        = "prod"
  vpc_cidr           = "10.40.0.0/16"
  az_count           = 3
  single_nat_gateway = false
  eks_cluster_name   = "orders-prod"
  instance_type      = "t3.small"
  asg_min_size       = 3
  asg_max_size       = 12
  certificate_arn    = "arn:aws:acm:ap-south-1:111122223333:certificate/REPLACE-ME"

  tags = {
    Team       = "payments"
    CostCenter = "cc-1234"
  }
}

# envs/dev/main.tf differs in: environment = "dev", single_nat_gateway = true,
# asg_min_size = 1, asg_max_size = 2, certificate_arn = "".
```

## Follow-up questions interviewers ask

* Add VPC endpoints for S3, ECR and Secrets Manager. Which are gateway and which are interface endpoints, and what does each cost?
* Convert the ASG to a mixed instances policy with 70 percent Spot. What changes in the launch template and the termination handling?
* Move the state to S3 with locking and split VPC and web tier into two state files. How do the outputs cross the boundary?
* Write a `terraform test` that asserts the plan has exactly one NAT gateway when `single_nat_gateway = true`.
* Replace the web tier with an EKS node group in the same VPC. Which subnets, tags and security group rules are reused?
* The security team wants no `0.0.0.0/0` egress. What does the app group need to reach, and how do you list it?

## Lessons that cover this

* [#11AWS core - IAM, VPC, EC2, S3, RDS, load balancers, autoscalingCloud and IaC](/devops/learn/aws-core-for-devops)
* [#13Terraform - infrastructure as codeCloud and IaC](/devops/learn/terraform-infrastructure-as-code)
* [#14Ansible and configuration managementCloud and IaC](/devops/learn/ansible-configuration-management)

## Further reading

* [Terraform documentationGuidedeveloper.hashicorp.com](https://developer.hashicorp.com/terraform/docs)
* [Amazon VPC documentationGuidedocs.aws.amazon.com](https://docs.aws.amazon.com/vpc/)
* [Amazon EC2 Auto Scaling documentationGuidedocs.aws.amazon.com](https://docs.aws.amazon.com/autoscaling/ec2/userguide/what-is-amazon-ec2-auto-scaling.html)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousKubernetes manifests: Deployment, Service, Ingress and HPA with probes and limits](/devops/problems/kubernetes-manifests-web-app)[NextHelm chart from scratch with values, templates and a test](/devops/problems/helm-chart-from-scratch)

## On this page

1. [Problem](#statement)
2. [Requirements](#requirements)
3. [API](#api)
4. [Data model](#data-model)
5. [Approach](#design)
6. [Diagram](#diagram)
7. [Deep dives](#deep-dives)
8. [Evaluation](#evaluation)
9. [Bottlenecks](#bottlenecks)
10. [Failure modes](#failures)
11. [Reference solution](#code)
12. [Follow-ups](#follow-ups)
13. [Lessons](#lessons)
14. [Further reading](#reading)
15. [My notes](#notes)
