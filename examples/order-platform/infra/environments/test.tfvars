# Stage test. One state per stage: terraform init -backend-config="key=orders/test.tfstate"
#
# OPEN entries of infra-spec.yaml, rendered as placeholders (a placeholder never deploys):
#   resources.api-management.service.publisher_name                 - Workload-Verantwortliche -> publisher_name
#   resources.api-management.service.publisher_email                - Workload-Verantwortliche -> publisher_email
#   resources.function-app.hosting.runtime_stack                    - Entwicklung              -> function_runtime_name, function_runtime_version
#   resources.application-gateway.networking.listeners              - Workload-Verantwortliche -> appgw_listener_hostnames
#   resources.virtual-machine.machine.size                          - Workload-Verantwortliche -> vm_size (assumption: Standard_D2ds_v5)
#   resources.virtual-machine.security.ssh_public_key               - Workload-Verantwortliche -> vm_admin_ssh_public_key
# Not in the spec's open list, but needed to deploy: event_function_name (name of the BlobCreated handler).
# The subscription of the stage is open too: all-zero GUID until the stage's subscription is named.

subscription_id = "00000000-0000-0000-0000-000000000000"
environment     = "test"
location        = "germanywestcentral"
workload        = "orders"
tags            = {}

# deployment.address_space
address_space = "10.101.0.0/23"

# deployment.resource_lock / resource_group_lock: production
lock_enabled = false

# OPEN
publisher_name           = "OPEN-publisher-name"
publisher_email          = "OPEN-publisher-email"
function_runtime_name    = "OPEN-runtime-name"
function_runtime_version = "OPEN-runtime-version"
appgw_listener_hostnames = ["OPEN-appgw-listener-hostname"]
vm_size                  = "OPEN-vm-size"
vm_admin_ssh_public_key  = "OPEN-ssh-public-key"
event_function_name      = "OPEN-function-name"
