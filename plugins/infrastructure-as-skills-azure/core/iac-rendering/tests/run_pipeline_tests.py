#!/usr/bin/env python3
"""Tests for scripts/check_pipeline.py.

The fixtures under tests/pipelines/ are the pipelines of references/pipelines.*.md,
one per platform and target. Each must pass clean. Then each mutation breaks one
invariant in a copy of a fixture - drops the plan file from `terraform apply`,
flips a gate, lets a pull request reach a stage - and the check must fail with
the message that names it. A mutation whose text is no longer in the fixture
fails the run: a test that cannot break anything proves nothing.

Usage:
    python3 run_pipeline_tests.py

Exit 0 all pass, 1 a test failed, 2 could not run.
"""

import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CHECK = os.path.join(HERE, '..', 'scripts', 'check_pipeline.py')
FIXTURES = os.path.join(HERE, 'pipelines')

GH = '.github/workflows/infra.yaml'
GHS = '.github/workflows/infra-stage.yaml'
ADO = 'azure-pipelines.yml'
ADOS = '.azure-pipelines/stage.yml'
ADOI = '.azure-pipelines/terraform-install.yml'
GL = '.gitlab-ci.yml'
SPEC = 'infra-spec.yaml'

# (name, fixture, file, find, replace, expected substring of the output)
MUTATIONS = [
    # stages and order
    ('spec has a stage the pipeline lacks', 'github-terraform', SPEC,
     'environments: [development, test, production]', 'environments: [development, test, staging, production]',
     'stages are'),
    ('a stage does not wait for the one before', 'github-terraform', GH,
     'needs: test', 'needs: development', 'does not wait for'),
    ('gitlab stage list differs', 'gitlab-terraform', GL,
     '  - test\n  - production', '  - production', 'stages are'),
    ('ado stage chain broken', 'ado-terraform', ADO,
     'dependsOn: test', 'dependsOn: validate', 'dependsOn'),
    ('local stage list differs', 'local-terraform', 'deploy.ps1',
     "'development', 'test', 'production'", "'development', 'production'", 'ValidateSet'),

    # pull requests
    ('github first stage reachable from a pull request', 'github-terraform', GH,
     "    if: github.event_name != 'pull_request'\n", '', 'would reach Azure'),
    ('github validate holds an environment', 'github-terraform', GH,
     '  validate:\n    runs-on: ubuntu-latest\n', '  validate:\n    runs-on: ubuntu-latest\n    environment: development\n',
     'validate holds an environment'),
    ('ado stage reachable from a pull request', 'ado-terraform', ADOS,
     "ne(variables['Build.Reason'], 'PullRequest')", 'succeeded()', 'pull request build'),
    ('gitlab apply reachable from a merge request', 'gitlab-terraform', GL,
     '    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH\n  script:', '    - if: $CI_PIPELINE_SOURCE == "merge_request_event"\n  script:',
     'not restricted to the default branch'),
    ('github token at workflow level', 'github-terraform', GH,
     'permissions:\n  contents: read\n\njobs:', 'permissions:\n  contents: read\n  id-token: write\n\njobs:',
     'at workflow level'),

    # the saved plan
    ('terraform apply without a plan file', 'github-terraform', GHS,
     'terraform apply -input=false tfplan', 'terraform apply -input=false', 'without a plan file'),
    ('terraform apply -auto-approve', 'github-terraform', GHS,
     'terraform apply -input=false tfplan', 'terraform apply -input=false -auto-approve tfplan', '-auto-approve'),
    ('ado apply without a plan file', 'ado-terraform', ADOS,
     '''terraform apply -input=false "$(Pipeline.Workspace)/tfplan-$(STAGE)/tfplan"''', 'terraform apply -input=false',
     'without a plan file'),
    ('gitlab apply without a plan file', 'gitlab-terraform', GL,
     '    - terraform apply tfplan', '    - terraform apply', 'without a plan file'),
    ('local apply without a plan file', 'local-terraform', 'deploy.ps1',
     'terraform apply -input=false $plan;', 'terraform apply -input=false;', 'without a plan file'),
    ('a workspace instead of a state key', 'github-terraform', GHS,
     '      - name: Apply the approved plan\n        run: terraform apply -input=false tfplan',
     '      - name: Apply the approved plan\n        run: |\n          terraform workspace select "$STAGE"\n          terraform apply -input=false tfplan',
     'terraform workspace'),
    ('plan artifact kept a week', 'github-terraform', GHS,
     'retention-days: 1', 'retention-days: 7', 'one day'),
    ('gitlab plan artifact kept a month', 'gitlab-terraform', GL,
     'expire_in: 1 day', 'expire_in: 30 days', 'one day'),
    ('local plan file not removed', 'local-terraform', 'deploy.ps1',
     'Remove-Item', 'Write-Host', 'plan file is not removed'),

    # the gate
    ('github production not gated', 'github-terraform', GH,
     'gated: true', 'gated: false', 'pipeline_approvals says True'),
    ('github approval environment missing', 'github-terraform', GHS,
     'environment: ${{ inputs.stage }}-approval', 'environment: ${{ inputs.stage }}', '-approval'),
    ('github apply does not need approve', 'github-terraform', GHS,
     'needs: [plan, approve]', 'needs: [plan]', 'does not need approve'),
    ('github approve asks about an empty plan', 'github-terraform', GHS,
     "if: ${{ inputs.gated && needs.plan.outputs.changes == 'true' }}", 'if: ${{ inputs.gated }}',
     'empty plan'),
    ('ado production not gated', 'ado-terraform', ADO,
     'gated: true', 'gated: false', 'pipeline_approvals says True'),
    ('ado apply is a plain job', 'ado-terraform', ADOS,
     '- deployment: apply', '- job: apply', 'no `deployment` job'),
    ('ado ManualValidation', 'ado-terraform', ADOS,
     'environment: ${{ parameters.stage }}\n        strategy:',
     'environment: ${{ parameters.stage }}\n        # ManualValidation@1\n        strategy:', 'ManualValidation'),
    ('ado apply asks even without changes', 'ado-terraform', ADOS,
     "condition: eq(dependencies.plan.outputs['plan.changes'], 'true')", 'condition: succeeded()', 'empty stage'),
    ('gitlab production not manual', 'gitlab-terraform', GL,
     '      when: manual ', '      when: on_success ', 'pipeline_approvals says'),
    ('gitlab manual job lets the pipeline run on', 'gitlab-terraform', GL,
     '      allow_failure: false ', '      allow_failure: true ', 'run on past the gate'),

    # a resource group is never destroyed by the pipeline
    ('github plan may delete a resource group', 'github-terraform', GHS,
     'azurerm_resource_group', 'azurerm_x', 'invariant 12'),
    ('ado plan may delete a resource group', 'ado-terraform', ADOS,
     'azurerm_resource_group', 'azurerm_x', 'invariant 12'),
    ('gitlab plan may delete a resource group', 'gitlab-terraform', GL,
     'azurerm_resource_group', 'azurerm_x', 'invariant 12'),
    ('local plan may delete a resource group', 'local-terraform', 'deploy.ps1',
     'azurerm_resource_group', 'azurerm_x', 'invariant 12'),

    # one apply at a time
    ('github cancels an apply', 'github-terraform', GHS,
     'cancel-in-progress: false', 'cancel-in-progress: true', 'cancel-in-progress'),
    ('github concurrency shared by all stages', 'github-terraform', GHS,
     'group: infra-${{ inputs.stage }}', 'group: infra', 'does not name the stage'),
    ('gitlab apply without resource_group', 'gitlab-terraform', GL,
     '  resource_group: production\n', '', 'race for the state'),

    # secrets and login
    ('github client secret', 'github-terraform', GHS,
     '  ARM_USE_AZUREAD: "true"\n', '  ARM_USE_AZUREAD: "true"\n  ARM_CLIENT_SECRET: ${{ secrets.AZURE_SECRET }}\n',
     'nothing secret exists'),
    ('github terraform without OIDC', 'github-terraform', GHS,
     'ARM_USE_OIDC: "true"', 'ARM_USE_OIDC: "false"', 'ARM_USE_OIDC'),
    ('github stage job without id-token', 'github-terraform', GH,
     '    permissions:\n      contents: read\n      id-token: write\n    with:\n      stage: development',
     '    permissions:\n      contents: read\n    with:\n      stage: development', 'id-token'),
    ('gitlab apply without id_tokens', 'gitlab-terraform', GL,
     '.apply:\n  id_tokens:\n    AZURE_OIDC_TOKEN:\n      aud: api://AzureADTokenExchange\n', '.apply:\n', 'no id_tokens'),
    ('ado terraform without the token', 'ado-terraform', ADOS,
     'addSpnToEnvironment: true', 'addSpnToEnvironment: false', 'federated token'),
    ('a shell fed from event text', 'github-terraform', GHS,
     'echo "Approved for ${{ inputs.stage }}."', 'echo "${{ github.event.head_commit.message }}"', 'attacker-controlled'),

    # versions
    ('action on a branch', 'github-terraform', GH,
     'uses: actions/checkout@v7', 'uses: actions/checkout@main', 'not pinned'),
    ('terraform unconstrained', 'github-terraform', GHS,
     'terraform_version: "~> 1.16.0"\n          terraform_wrapper: false      # the wrapper',
     'terraform_version: latest\n          terraform_wrapper: false      # the wrapper', '~>'),
    ('gitlab image latest', 'gitlab-terraform', GL,
     'name: hashicorp/terraform:1.16 ', 'name: hashicorp/terraform:latest ', 'not pinned'),
    ('ado install without checksum', 'ado-terraform', ADOI,
     'sha256sum -c -', 'cat', 'checksum'),

    # the code beside the pipeline
    ('no backend block: -backend-config is ignored', 'github-terraform', 'providers.tf',
     '  backend "azurerm" {}\n', '', 'backend "azurerm"'),
    ('local script without a backend block', 'local-terraform', 'providers.tf',
     '  backend "azurerm" {}\n', '', 'backend "azurerm"'),

    # a placeholder never deploys
    ('github without the placeholder guard', 'github-terraform', GHS,
     '00000000-0000-0000-0000-000000000000|OPEN-', 'NEVER', 'refuses placeholder'),
    ('github bicep without the placeholder guard', 'github-bicep', GHS,
     '00000000-0000-0000-0000-000000000000|OPEN-', 'NEVER', 'refuses placeholder'),
    ('ado without the placeholder guard', 'ado-terraform', ADOS,
     '00000000-0000-0000-0000-000000000000|OPEN-', 'NEVER', 'refuses placeholder'),
    ('gitlab without the placeholder guard', 'gitlab-terraform', GL,
     '00000000-0000-0000-0000-000000000000|OPEN-', 'NEVER', 'refuses placeholder'),
    ('local without the placeholder guard', 'local-terraform', 'deploy.ps1',
     '00000000-0000-0000-0000-000000000000|OPEN-', 'NEVER', 'refuses placeholder'),
    ('stage file missing', 'ado-terraform', 'environments/test.tfvars',
     '@remove', '', 'missing'),
    ('ado bicep without the placeholder guard', 'ado-bicep', ADOS,
     '00000000-0000-0000-0000-000000000000|OPEN-', 'NEVER', 'refuses placeholder'),
    ('ado bicep deploys without what-if', 'ado-bicep', ADOS,
     'az deployment group what-if', 'az deployment group show', 'what-if'),
    ('ado bicep stage file missing', 'ado-bicep', 'main.test.bicepparam',
     '@remove', '', 'missing'),
    ('ado bicep validate holds a service connection', 'ado-bicep', ADO,
     '          - script: az bicep lint --file main.bicep\n',
     '          - task: AzureCLI@2\n            inputs: { azureSubscription: sc-x, scriptType: bash, scriptLocation: inlineScript, inlineScript: "az bicep lint --file main.bicep" }\n',
     'validate uses a service connection'),
    # validate and state
    ('github validate skips fmt', 'github-terraform', GH,
     'run: terraform fmt -check -recursive', 'run: echo skipped', 'terraform fmt'),
    ('bicep validate skips lint', 'github-bicep', GH,
     'run: az bicep lint --file main.bicep', 'run: echo skipped', 'bicep lint'),
    ('bicep deploys without what-if', 'github-bicep', GHS,
     'az deployment group what-if', 'az deployment group show', 'what-if'),
    ('bicep what-if hides the modules it skips', 'github-bicep', GHS,
     'NestedDeploymentShortCircuited', 'NestedDeploymentSomethingElse', 'short-circuits'),
    ('approve inherits a directory it never checked out', 'github-terraform', GHS,
     '\njobs:\n', '\ndefaults:\n  run:\n    working-directory: infra\n\njobs:\n', 'inherits working-directory'),
    ('state key without the stage', 'ado-terraform', ADOS,
     'key=payments/$(STAGE).tfstate', 'key=payments/main.tfstate', 'state key'),
]

OPEN_DEV = 'open:\n  - key: context.subscription_id\n    environments: [development]\n    blocks: apply\n'
DEV = 'environments/development.tfvars'
DEV_REAL = 'subscription_id     = "11111111-2222-3333-4444-dev000000000"'
DEV_OPEN = 'subscription_id     = "00000000-0000-0000-0000-000000000000"'

# Specs that must still pass: the same pipeline under a different decision.
VARIANTS = [
    # approvals none: no stage gated, so the production gate must go
    ('approvals none, nothing gated', 'github-terraform',
     [(SPEC, 'pipeline_approvals: {value: production,', 'pipeline_approvals: {value: none,'),
      (GH, 'gated: true', 'gated: false')], 0, ''),
    ('approvals every_stage, only production gated is wrong', 'github-terraform',
     [(SPEC, 'pipeline_approvals: {value: production,', 'pipeline_approvals: {value: every_stage,')], 1, 'pipeline_approvals says'),
    # an open stage keeps its job and its file, filled with placeholders
    ('open stage: job and placeholder file', 'github-terraform',
     [(SPEC, 'deployment:', OPEN_DEV + 'deployment:'), (DEV, DEV_REAL, DEV_OPEN)], 0, ''),
    ('open stage whose file looks resolved', 'github-terraform',
     [(SPEC, 'deployment:', OPEN_DEV + 'deployment:')], 1, 'holds no placeholder'),
    ('resolved stage that still holds a placeholder', 'github-terraform',
     [(DEV, DEV_REAL, DEV_OPEN)], 1, 'still holds a placeholder'),
    ('open stage without its file', 'github-terraform',
     [(SPEC, 'deployment:', OPEN_DEV + 'deployment:'), (DEV, '@remove', '')], 1, 'missing'),
    ('open stage without a job is no longer right', 'github-terraform',
     [(SPEC, 'deployment:', OPEN_DEV + 'deployment:'), (DEV, DEV_REAL, DEV_OPEN),
      (GH, "  development:\n    needs: validate\n    if: github.event_name != 'pull_request'\n    uses: ./.github/workflows/infra-stage.yaml\n    permissions:\n      contents: read\n      id-token: write\n    with:\n      stage: development\n      gated: false\n\n", '')],
     1, 'stages are'),
]


def run_check(directory):
    p = subprocess.run([sys.executable, '-I', CHECK, os.path.join(directory, SPEC)],
                       capture_output=True, text=True, env={**os.environ, 'NO_COLOR': '1'})
    return p.returncode, p.stdout + p.stderr


def edit(root, rel, find, repl):
    path = os.path.join(root, rel)
    if find == '@remove':
        os.remove(path)
        return
    with open(path, encoding='utf-8', newline='') as f:
        text = f.read()
    if find not in text:
        raise AssertionError(f"mutation text not found in {rel}: {find[:60]!r}")
    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(text.replace(find, repl, 1))


def main():
    try:
        import yaml  # noqa: F401
    except ImportError:
        print('[fail] no YAML parser available (pip install pyyaml)')
        return 2
    failed = 0
    total = 0

    def report(name, good, detail=''):
        nonlocal failed, total
        total += 1
        if good:
            print(f"[ ok ] {name}")
        else:
            failed += 1
            print(f"[fail] {name}\n         {detail}")

    for fx in sorted(os.listdir(FIXTURES)):
        code, out = run_check(os.path.join(FIXTURES, fx))
        report(f"fixture {fx} is clean", code == 0, out.strip().splitlines()[-3:] if code else '')

    with tempfile.TemporaryDirectory() as tmp:
        for name, fx, rel, find, repl, expect in MUTATIONS:
            work = os.path.join(tmp, 'w')
            shutil.copytree(os.path.join(FIXTURES, fx), work)
            try:
                edit(work, rel, find, repl)
                code, out = run_check(work)
                report(f"breaks: {name}", code == 1 and expect in out,
                       f"exit {code}, expected {expect!r} in:\n{out}")
            except AssertionError as e:
                report(f"breaks: {name}", False, str(e))
            finally:
                shutil.rmtree(work, ignore_errors=True)

        for name, fx, edits, want_code, expect in VARIANTS:
            work = os.path.join(tmp, 'w')
            shutil.copytree(os.path.join(FIXTURES, fx), work)
            try:
                for rel, find, repl in edits:
                    edit(work, rel, find, repl)
                code, out = run_check(work)
                report(f"variant: {name}", code == want_code and expect in out, f"exit {code}:\n{out}")
            except AssertionError as e:
                report(f"variant: {name}", False, str(e))
            finally:
                shutil.rmtree(work, ignore_errors=True)

    print('-' * 70)
    print(f"{total - failed}/{total} passed")
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
