# Maintenance configuration - what the question set cannot express

## Fixed at creation

- **The scope.** `InGuestPatch` and `Host` are different configurations; changing it is a
  delete and a create, and every assignment to the old one goes with it.
- **The region.** A configuration is assigned only to machines of its own region.
- **Nothing else.** The window, the classifications and the exclusions are edited in place
  and apply from the next run.

## Where the assignment lives

The configuration says *when* and *what*; the assignment
(`Microsoft.Maintenance/configurationAssignments`) says *which machine*. This family renders
the assignment **on the machine**: the `virtual-machine` set references the configuration, and
both AVM machine modules take its id (`maintenance_configuration_resource_ids` in Terraform,
`maintenanceConfigurationResourceId` in Bicep) and create the assignment themselves. One
configuration, many machines; a machine takes one `InGuestPatch` configuration.

A scale set has no such input in either AVM module: its assignment is authored beside the call
(`azurerm_maintenance_assignment_virtual_machine_scale_set`, or the
`configurationAssignments` extension resource scoped to the scale set). Check Azure Update
Manager's support for the scale set's orchestration mode before promising a window.

## What the machine must carry

A machine follows the window only when both hold, and both are the machine's:

| Machine setting | Value | Without it |
|---|---|---|
| `patch_mode` | `AutomaticByPlatform` | `ImageDefault` patches from inside the guest, whatever the window says |
| `bypass_platform_safety_checks_on_user_schedule_enabled` (Bicep `bypassPlatformSafetyChecksOnUserSchedule`) | `true` - the Terraform module defaults to `false`, the Bicep one to `true` | Azure keeps its own platform schedule and the configuration is assigned but not used - no error anywhere |

The second one is the silent failure: the plan shows the assignment, the portal shows the
schedule, and the machine is patched at a time nobody chose.

## Ordering

The configuration before the assignment, the machine before the assignment. A configuration
created in the same deployment as its machines is fine; the machine module takes its id as an
input, which orders it.

## Pitfalls

**`InGuestPatchMode: User` is required for a patch schedule.** It is not a decision and is
written whenever the scope is `InGuestPatch`; without it Azure rejects the configuration or
treats it as a platform one.

**The window's limits are the scope's.** `InGuestPatch` takes a duration of 1:30 to 3:55. Azure
stops starting updates when the remaining time is too short for one more and the restart, so
a window at the minimum patches less than its list.

**The start date is the anchor of the recurrence.** A monthly window counts from it; a weekly
window opens on the next listed day after it. The time is in the window's time zone, which is a
Windows id, not an IANA name.

**Stages in one window patch together.** A broken update then reaches production in the same
hour as development. Stagger `recur_every` per stage so production follows the others.

**`reboot_setting: Never` hides exposure.** The update reports installed; the vulnerable code
runs until the next restart.

**An empty platform block is not "nothing".** The Terraform module fills a missing
`classifications_to_include` with `Critical, Security` - a system not in `operating_systems`
is rendered `null`, never `{}`.

## Not covered here, and why

Dynamic scopes (subscription-wide assignments by tag or resource group), pre- and
post-maintenance events, hotpatching, Arc-enabled servers and the `OSImage`, `Extension`,
`SQLDB` and `SQLManagedInstance` scopes each carry decisions of their own and have no question
set; a request for one is said out loud, not improvised.
