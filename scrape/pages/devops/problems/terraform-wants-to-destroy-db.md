# Terraform plan wants to destroy the production database — DevOps interview problem · FAANGrind

Source: https://faangrind.vercel.app/devops/problems/terraform-wants-to-destroy-db

[DevOps problems](/devops#problems)

OPSTroubleshooting#30Medium

# Terraform plan wants to destroy the production database

terraformawsrdsstatemoved-blockci-cdReported at Infosys, Wipro, Capgemini

## Problem statement

It is 16:50 on a Friday. A pull request titled "refactor: move RDS into the database module" has a green plan and one approval. The plan summary in the PR comment reads `Plan: 1 to add, 0 to change, 1 to destroy.` and the body contains `# aws_db_instance.main will be destroyed` and `# module.database.aws_db_instance.main will be created`. The reviewer is reaching for the apply button. Stop it, explain exactly what Terraform intends and why, fix the PR so the plan shows zero destroys, and make sure a plan like this can never be applied by a tired reviewer again.

## Requirements

### Functional

* Read the plan output and the plan JSON to find whether this is a replacement (one resource, an attribute marked `forces replacement`) or a delete plus a create of two different addresses.
* Name the attribute or address change that causes it and rule out the other common causes with evidence: a changed identifier, engine or subnet group, drift from a console change, a provider upgrade.
* Produce a plan with `0 to destroy` for the same refactor, without touching the live database.
* Add three layers that stop this class of apply: a CI gate on the plan JSON, `prevent_destroy` in the lifecycle, and `deletion_protection` on the instance.
* Write the 3-line note that goes on the PR explaining what was wrong and what changed.

### Non-functional

* Decision within 15 minutes of seeing the plan; no apply until the plan shows 0 destroys for every resource tagged `protected`.
* Blast radius if applied: the production database, 1.2 TB, an estimated 6 hours to restore from the last automated snapshot, with up to 5 minutes of data lost to the snapshot interval.
* The fix is a code change in the same PR, reviewed again, with the new plan attached; no `terraform state` commands run by hand against production unless the moved block cannot express the change.
* The CI gate runs on every plan in under 10 seconds and cannot be skipped by a label.
* Zero changes to the running database during the investigation: the plan is read-only.

## Back-of-the-envelope estimates

**Impact if applied.** Terraform destroys the old address first and creates the new one after, because a plain destroy and create are two unrelated actions. With `skip_final_snapshot = false` and a `final_snapshot_identifier` set, a final snapshot is taken, which for 1.2 TB takes about 20 to 40 minutes; then a new empty instance is created. Restore from that snapshot into a new instance: about 1 hour to provision and warm up, plus application reconfiguration, so a 2 to 6 hour outage. If `skip_final_snapshot = true` the data is gone except for the last automated backup, taken up to 24 hours ago, with point-in-time recovery to within 5 minutes if backups are on. The order service does 300 requests a second; 3 hours of outage is 300 x 3,600 x 3 = 3,240,000 failed requests, against an error budget of 0.1 percent per month, which is about 43 minutes.

## API

```
# 1. Stop the apply. Lock the PR (a comment, a "do-not-merge" label, or a required check set to failing).
gh pr edit 418 --add-label do-not-merge
gh pr comment 418 --body "Plan destroys aws_db_instance.main. Do not apply. Investigating."

# 2. Read the full plan, not the summary. Look for the two headers and for "forces replacement".
terraform plan -no-color -out=tfplan.bin
#   # aws_db_instance.main will be destroyed
#   # (because aws_db_instance.main is not in configuration)
#   - resource "aws_db_instance" "main" { ... }
#   # module.database.aws_db_instance.main will be created
#   + resource "aws_db_instance" "main" { ... }
#   Plan: 1 to add, 0 to change, 1 to destroy.
# Two different addresses, no "-/+" header, no "forces replacement" line: a move, not a replacement.

# 3. The machine-readable version: what the CI gate reads.
terraform show -json tfplan.bin > plan.json
jq -r '.resource_changes[] | select(.change.actions | index("delete"))
       | [.address, (.change.actions|join(",")), (.action_reason // "none"),
          (.change.replace_paths // [] | tostring)] | @tsv' plan.json
#   aws_db_instance.main   delete   delete_because_no_resource_config   []

# 4. Confirm what is in state and what the config now declares.
terraform state list | grep aws_db_instance
#   aws_db_instance.main
grep -rn 'resource "aws_db_instance"' modules/database/ main.tf
#   modules/database/main.tf:12:resource "aws_db_instance" "main" {
git diff origin/main -- main.tf modules/database/main.tf | grep -E '^[-+]' | grep -vE 'moved|^(\+\+\+|---)'
#   -resource "aws_db_instance" "main" {       (removed from root)
#   +module "database" { source = "./modules/database" ... }

# 5. Rule out drift and provider changes before trusting the diagnosis.
terraform plan -refresh-only -no-color | grep -E "has changed|No changes"
#   No changes. Your infrastructure still matches the configuration.
git diff origin/main -- .terraform.lock.hcl
#   (empty: same provider version)

# 6. Does the real instance already have deletion protection?
aws rds describe-db-instances --db-instance-identifier orders-prod \
  --query 'DBInstances[0].[DeletionProtection,DBInstanceClass,Engine,EngineVersion,DBSubnetGroup.DBSubnetGroupName]' --output text
#   False  db.r6g.xlarge  postgres  16.4  orders-prod-subnets
```

## Data model

```
Plan output, human form
  # X will be destroyed           delete; look for the "(because ...)" line under it
  # X must be replaced            -/+  one address, one or more attributes marked "# forces replacement"
  # X will be created             +    new address or new resource
  # X has moved to Y              a moved block was understood; no destroy
  Plan: A to add, C to change, D to destroy.

Plan JSON (terraform show -json tfplan.bin), what the CI gate reads
  .resource_changes[]
     .address                 "aws_db_instance.main"
     .previous_address        present only when a moved block renamed it
     .type, .name, .module_address
     .change.actions          ["delete"] | ["create"] | ["update"] | ["delete","create"] | ["create","delete"] | ["no-op"]
     .change.replace_paths    [["engine"]] the attribute paths that forced a replacement
     .change.before / .after  the values; after is null on delete
     .action_reason           delete_because_no_resource_config | replace_because_cannot_update |
                              replace_by_request | replace_because_tainted | delete_because_no_module ...
  .resource_drift[]           differences found by refresh against the prior state

Attributes of aws_db_instance that force a new instance (provider schema ForceNew)
  engine, username, db_name, availability_zone, storage_encrypted, kms_key_id,
  character_set_name, timezone, snapshot_identifier, restore_to_point_in_time
  (identifier, engine_version, instance_class, storage_type, db_subnet_group_name
   are modified in place, some only after a reboot or in the maintenance window)

Guards
  lifecycle { prevent_destroy = true }     Terraform refuses a plan that destroys this address
                                           (does not help when the block itself is removed)
  deletion_protection = true               the AWS API refuses the delete, whatever Terraform plans
  moved { from = aws_db_instance.main  to = module.database.aws_db_instance.main }
```

## Diagnosis and fix

1. **Stop the apply first.** Add the `do-not-merge` label and a comment (command 1). A 10-minute delay costs nothing; the apply costs the database.
2. **Read the whole plan.** Two headers with two different addresses: `will be destroyed` with the reason `is not in configuration`, and `will be created`; no `-/+` and no `forces replacement` line (command 2). Terraform is not replacing one resource; it has lost track of one and found a new one. The JSON agrees: `action_reason` is `delete_because_no_resource_config` and `replace_paths` is empty (command 3).
3. **Find what moved.** State still holds `aws_db_instance.main` at the root; the diff shows the block was cut from `main.tf` and pasted into `modules/database/main.tf` (command 4). Terraform identifies a resource by its address, not by the AWS object, so the root address is orphaned and the module address is new.
4. **Rule out the other causes.** A refresh-only plan shows no drift, so nobody changed the instance in the console. The lock file is unchanged, so the provider did not change a default. The module declares the same `identifier`, `engine`, `db_subnet_group_name` and `storage_type`; only `engine`, `username`, `db_name` and the encryption settings would force a replacement, and that would show as `-/+` on one address.
5. **Fix in the PR.** Add a `moved` block at the root: `from = aws_db_instance.main`, `to = module.database.aws_db_instance.main`. Re-plan: `# aws_db_instance.main has moved to module.database.aws_db_instance.main` and `0 to destroy`. Keep the block permanently. `terraform state mv` does the same by hand, unreviewed, against production state, so it is the fallback.
6. **Add the guards in the same PR.** In the module: `deletion_protection = true` (an in-place update) and `lifecycle { prevent_destroy = true }`. In CI: after `terraform plan -out`, run `terraform show -json` and fail the job if any resource of a protected type (`aws_db_instance`, `aws_rds_cluster`, `aws_s3_bucket`, `aws_dynamodb_table`) has `delete` in `change.actions`, printing the address and `action_reason`.
7. **Verify.** The new plan: 0 to destroy, 1 to change, and the `has moved to` line. Apply on Monday; `terraform state list` shows only the module address and `describe-db-instances` shows `DeletionProtection: True`.
8. **Prevent, in writing.** The PR note: "The refactor changed the resource address, so Terraform planned to destroy the old one and create a new one. A `moved` block keeps the existing instance. CI now blocks any plan that deletes a protected resource, and the instance has deletion protection." Add "destroy count must be 0 for protected types" to the review checklist.

## Architecture diagram

Rendering diagram…

## Deep dives

### Replacement versus delete and create

Terraform shows two very different things that both end in `1 to destroy`. A replacement is one address whose header reads `must be replaced` with `-/+`, and inside the diff at least one attribute carries `# forces replacement`; in JSON the actions are `["delete","create"]` (or `["create","delete"]` with `create_before_destroy`), `replace_paths` names the attribute, and `action_reason` is `replace_because_cannot_update`. The provider has said it cannot change that attribute in place. For `aws_db_instance` that list is short: `engine`, `username`, `db_name`, `availability_zone`, `storage_encrypted`, `kms_key_id`, the character set and timezone, and restoring from a snapshot or a point in time. Changing `identifier`, `engine_version`, `instance_class`, `storage_type` or `db_subnet_group_name` is an in-place modify, sometimes with a reboot. A delete plus a create is two addresses: one with `will be destroyed` and `delete_because_no_resource_config`, one with `will be created`. That is never a change to the database; it is a change to the map Terraform keeps between addresses and real objects. Telling the two apart from the plan text is the whole diagnosis.

### Why a moved block and not state mv

Both make the state agree with the new address. `terraform state mv` edits the production state file from a laptop, with no review and no record in Git; if two people refactor in parallel the second one finds the address already gone. A `moved` block is code: it is reviewed with the refactor, applied by the same pipeline, and it works for every workspace and every environment that still has the old address, including a developer's stale state next month. Terraform renames the object in state before planning, so the plan shows `has moved to` and no destroy. Keep historical `moved` blocks in the module; deleting one later turns the rename back into a destroy for anyone who has not applied since. Use `state mv` only when a `moved` block cannot express the change, for example moving a resource between two separate root configurations with different state files, and then `terraform state pull` a backup first.

### Three layers that stop the apply

`prevent_destroy = true` makes Terraform error during plan when the plan would destroy that address. It would not have caught this PR, because the guard lives in the resource block that was removed from the root; the orphaned state object has no lifecycle rules. `deletion_protection = true` is enforced by the AWS API: `DeleteDBInstance` fails until someone turns it off, which is a separate, visible change. It catches the orphan case and a wrong `terraform destroy`, at the cost of a two-step process for a real decommission. The CI gate reads the plan JSON and refuses any `delete` action on a protected type; it catches the orphan case, the replacement case and a tainted resource, and it explains why in the PR. The gate uses `terraform show -json` on the saved plan file, never a regex on the text output, because the text format changes between versions. Three layers, because each one has a hole the others cover.

### When the destroy is real

Sometimes the plan is right: the team wants a new engine, a different encryption key, or a move to a different region. Then the answer is not a trick in state but a migration: create the new instance under a new address, replicate data into it (a read replica promoted, or logical replication for a major version change, or an RDS blue-green deployment where supported), cut the application over behind a connection string change, verify, and only then remove the old resource with `deletion_protection` turned off in its own reviewed PR. `create_before_destroy` does not help for a database: the new instance is empty, and the identifier must differ anyway.

## Evaluation

**Did you find it?** The note says: "The refactor moved `aws_db_instance.main` into `module.database`; Terraform tracks resources by address, so the old address shows `delete_because_no_resource_config` and the new one `create`. No attribute forces replacement, there is no drift and the provider version is unchanged."

**Is it fixed?** The re-plan on the same PR shows `aws_db_instance.main has moved to module.database.aws_db_instance.main`, `0 to destroy`, and one in-place update for `deletion_protection`. After apply, `terraform state list` shows only the module address, `describe-db-instances` shows deletion protection on, and the application never noticed.

**Is it prevented?** The CI gate on plan JSON blocks any `delete` action on protected types and prints the reason; `deletion_protection` and `prevent_destroy` are set; the review checklist says a destroy count above 0 on a protected type needs a named migration plan.

**What a strong answer adds.** The difference between `-/+` with `forces replacement` and two addresses with `not in configuration`; the JSON fields `action_reason` and `replace_paths`; which `aws_db_instance` attributes actually force a new instance; why `prevent_destroy` would not have helped here; why the gate parses JSON rather than text; and the blue-green path when the change is intended.

**What a weak answer does.** Approves because the plan is green and "Terraform knows what it is doing", or runs `terraform state mv` on production from a laptop without a backup and without telling the reviewer why.

## Bottlenecks & mitigations

* The PR summary line: `1 to add, 1 to destroy` looks routine next to 40 other changes, and the detail is folded away.
* Terraform tracks by address, not by cloud identity: any rename of a resource, module or `for_each` key is a destroy until a `moved` block says otherwise.
* Friday-evening review: the person approving is the only control, and they are tired.
* The final snapshot: taking it is the only reason the data would survive, and it takes 20 to 40 minutes for 1.2 TB.
* State locks: a half-finished apply that destroyed but failed to create leaves the lock held and the database gone.

## Failure modes

* **Approving on the summary.** `1 to destroy` is read as a tag change. Mitigation: the CI gate on protected types, and the plan detail pasted above the fold in the PR.
* **Refactor without a moved block.** Every rename is a destroy and create. Mitigation: a `moved` block in the same PR, a plan check that any `delete` with `delete_because_no_resource_config` on a stateful type fails.
* **Removing an old moved block.** The rename reverts to a destroy for stale states. Mitigation: keep historical `moved` blocks in the module.
* **Relying on prevent\_destroy alone.** It lives in the block that was removed. Mitigation: `deletion_protection` at the API and the CI gate.
* **Console change creates drift.** A manual parameter change makes the next plan modify or replace. Mitigation: `-refresh-only` plans on a schedule, `ignore_changes` only for accepted drift, otherwise import the change into code.
* **Provider upgrade changes a default.** A new provider version introduces an attribute whose default differs from the live value. Mitigation: provider upgrades in their own PR with an empty plan as the acceptance test.
* **state mv by hand without a backup.** A typo moves the wrong address. Mitigation: `terraform state pull > backup.tfstate` first, and prefer `moved` blocks.
* **skip\_final\_snapshot true in production.** A destroy loses the data outright. Mitigation: `skip_final_snapshot = false` with a dated `final_snapshot_identifier`, and backups with point-in-time recovery enabled.

## Follow-up questions interviewers ask

* The plan shows `-/+` on one address with `engine_version` changed from 15 to 16. Does that force replacement, and how would you do the upgrade safely?
* `prevent_destroy` is set but the plan still destroys. List the ways that can happen.
* Write the CI gate as a 20-line script over `terraform show -json`: which fields does it read and what does it print?
* The same refactor must be applied in dev, staging and prod with separate state files. How do `moved` blocks behave in each?
* A colleague already ran `terraform state mv` in prod and the PR with the `moved` block is applied afterwards. What happens?
* The database must really move to a new KMS key. Design the migration with zero data loss and name the downtime.

## Lessons that cover this

* [#13Terraform - infrastructure as codeCloud and IaC](/devops/learn/terraform-infrastructure-as-code)
* [#28Interview playbook, what is new in 2026, revision sheetShip](/devops/learn/interview-playbook-2026-revision)

## Further reading

* [Terraform documentationGuidedeveloper.hashicorp.com](https://developer.hashicorp.com/terraform/docs)
* [GitHub Actions documentationGuidedocs.github.com](https://docs.github.com/en/actions)
* [How Complex Systems FailPaperhow.complexsystems.fail](https://how.complexsystems.fail/)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousIntermittent DNS resolution failures in the cluster](/devops/problems/intermittent-dns-failures)[NextOOMKilled pods and an HPA that keeps scaling up and down](/devops/problems/oomkilled-hpa-thrashing)

## On this page

1. [Problem](#statement)
2. [Requirements](#requirements)
3. [Estimates](#estimates)
4. [API](#api)
5. [Data model](#data-model)
6. [Diagnosis and fix](#design)
7. [Diagram](#diagram)
8. [Deep dives](#deep-dives)
9. [Evaluation](#evaluation)
10. [Bottlenecks](#bottlenecks)
11. [Failure modes](#failures)
12. [Follow-ups](#follow-ups)
13. [Lessons](#lessons)
14. [Further reading](#reading)
15. [My notes](#notes)
