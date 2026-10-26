# Traffic Manager - what the question set cannot express

## Where it sits

Traffic Manager is a DNS answer. A client asks for `www.example.com`, the public zone's CNAME
points at `<name>.trafficmanager.net`, Traffic Manager answers with the address of one endpoint,
and from then on the client talks to that endpoint directly. Nothing passes through the profile:
no TLS, no firewall, no path routing, no caching. Those are Front Door's (`front-door` set), which
is the right answer for a web application that needs a layer-7 entry; Traffic Manager is the
right answer for steering between regions or providers at the DNS level - non-HTTP protocols, an
endpoint outside Azure, a Front Door per region, a staged migration.

## Fixed at creation

- **The relative DNS name.** `<name>.trafficmanager.net` is global across every tenant and cannot
  be changed; a deleted profile's name is free for anyone after deletion.
- **The routing method** can be changed in place, but the endpoints' meaning changes with it: a
  Weighted profile's weights are ignored by Priority and the reverse. Treat a method change as a
  new profile in review.
- **An endpoint's kind** (azure / external / nested) - a change is a new endpoint.

## Ordering

1. Resource group
2. The endpoints' targets - App Services, public IPs, Front Doors, the child profiles of a nested
   setup - with their health path answering
3. The profile with its endpoints
4. The diagnostic setting, after the workspace
5. The public zone's CNAME (or apex alias) to the profile - last, when the probes show every
   endpoint healthy; before that the name sends users to an endpoint that is still being built

Deletion runs the other way: the zone's record first, or the name resolves to nothing while the
TTL runs.

## Pitfalls

**The modules disagree on everything that has a default.** Terraform requires the routing method,
the DNS config and the monitor config; Bicep defaults to `Performance`, TTL 60 and a probe over
lowercase `http` on port 80 at `/`. A Bicep render that leaves the monitor at its default probes
HTTP on a site that only serves HTTPS and marks every endpoint down. Every decision is written on
both calls.

**Failover time is TTL plus detection.** With the standard probe (30 s, three failures) an endpoint
is marked down after up to 90 seconds, and a client keeps its cached answer for the TTL on top.
60 + 90 seconds is the honest number for `standard`; `fast` halves the detection, not the TTL. A
TTL of 0 is accepted and is a query per request.

**The probe is the users' request, or it is wrong.** HTTPS on 443 at a path that checks the
application's dependencies. A probe that gets a redirect (HTTP to HTTPS, sign-in) counts it as
failure unless `expected_status_codes` includes 3xx; a probe on a management port, or a TCP probe,
reports a dead application as healthy. The probe comes from Traffic Manager's address ranges
(service tag `AzureTrafficManager`), which a firewall in front of the endpoint has to allow.

**Priority needs more than one endpoint, and weights need the method.** A Priority profile with one
endpoint fails over to nothing; a `priority` value on a Weighted profile is ignored silently.
`Geographic` needs every region a user can come from mapped - the `World` region as a catch-all
on one endpoint - or those users get NXDOMAIN.

**An Azure endpoint takes the resource, not its address.** `target_resource_id` is the App Service,
the public IP or the Front Door; Traffic Manager reads the address and the region from it. An
address typed as an external endpoint loses that and needs its region stated for `Performance`.

**Nested profiles are how two methods combine.** Failover between regions and performance within
them is a Performance parent with a Priority child per region; `min_child_endpoints` says how many
healthy children keep the parent endpoint up.

**Traffic View costs.** It is billed per million queries on top of the profile and is the right
tool for one decision - where the next region goes. On for a few weeks, then off.

**A disabled endpoint is the planned failover.** `enabled: false` on an endpoint takes it out of
rotation without deleting it; that is the release-day move and what `role_assignments` is for.

## Not covered here, and why

Front Door, Application Gateway, custom headers per endpoint, `always_serve`, `allowed endpoint
record types`, real-user measurements and the public zone's record each carry decisions of their
own; a request for one is said out loud, not improvised.
