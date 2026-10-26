# .gitignore after a render

A render produces files that must never be committed (state, plans, local credentials) next
to files that must be (the per-stage `*.tfvars` / `*.bicepparam`, the lock file). The
repository's `.gitignore` is the customer's: **add what is missing, never rewrite it, never
remove a line.**

## Procedure

1. Read the `.gitignore` at the repository root (none → create it).
2. For the rendered target, take the entries below. A line counts as present when an
   existing pattern already covers it (`*.tfstate*` covers `*.tfstate`; a `.terraform/`
   anywhere in the file covers `.terraform/`).
3. Append the missing lines in one block under the header `# infrastructure-as-skills-azure`.
   No block, no change, when nothing is missing.
4. If an existing pattern **ignores a file the render needs committed** (`*.tfvars`,
   `*.bicepparam`, `.terraform.lock.hcl`, `infra-spec.yaml`), do not edit it: name the line
   in the hand-over and ask, since the customer may have put it there on purpose.
5. Say in the hand-over which lines were added.

## Terraform

```gitignore
.terraform/
*.tfstate
*.tfstate.*
crash.log
crash.*.log
tfplan
*.tfplan
override.tf
override.tf.json
*_override.tf
*_override.tf.json
.terraformrc
terraform.rc
```

## Bicep

```gitignore
# compiled ARM, what-if output and local parameter overrides
*.compiled.json
whatif.json
*.local.bicepparam
```

## Both

```gitignore
# local secrets and scratch
.env
.env.*
*.pem
*.pfx
*.key
*.local.*
```

## Stays committed

`*.tfvars` and `*.bicepparam` of the stages (the spec forbids secrets in them),
`.terraform.lock.hcl` (pins the provider versions), `infra-spec.yaml`,
`infra-diagram.drawio.png`, `tests/`. `*.tfvars.example` is committed too.
