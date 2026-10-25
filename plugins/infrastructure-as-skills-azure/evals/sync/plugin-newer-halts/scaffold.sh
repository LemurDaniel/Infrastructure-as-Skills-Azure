#!/bin/sh
set -e
mkdir -p infra
cat > infra/infra-spec.yaml <<'EOF_SCAFFOLD'
schema_version: 1

spec:
  id: testdata-dev
  target: terraform
  generated_by: infrastructure-as-skills-azure
  plugin_version: 99.0.0
  at: 2026-10-20T09:00:00Z

context:
  language: de
  environments: [development]
  location: westeurope
  workload: testdata
  subscription_id:
    development: 11111111-2222-3333-4444-555555555555
  resource_group_name:
    development: rg-testdata-dev-we

deployment:
  landing_zone: { value: standalone, source: stated }
  network_exposure: { value: public, source: stated }
  network_ownership: { value: none, source: stated }
  observability_ownership: { value: none, source: default }
  local_auth: { value: disabled, source: default }
  resource_group_mode_main: { value: existing, source: stated }

wiring:
  access:
    value: []
    source: stated
  purposes:
    value: { storage-account: Testdaten }
    source: stated

resources:
  storage-account:
    networking:
      public_network_access: { value: enabled, source: stated }
EOF_SCAFFOLD
