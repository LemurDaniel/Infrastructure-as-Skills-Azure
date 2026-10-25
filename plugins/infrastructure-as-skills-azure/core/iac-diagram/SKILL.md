---
name: iac-diagram
description: Draws an infra-spec.yaml as an editable draw.io diagram, exported as infra-diagram.drawio.png — what gets built, how it connects, what stays open. Read after a spec is written, or when asked for an architecture picture of one.
---

# Drawing the spec

The spec is written for reviewers and backends. The person who asked for the
infrastructure usually reads neither YAML nor HCL, and still has to say whether this is
what they meant. This skill gives them a picture of the same decisions.

```
infra-spec.yaml  ──new_diagram──>  infra-diagram.drawio  ──export_diagram──>  infra-diagram.drawio.png
```

It draws **from the spec, never from rendered code**. That is what lets the diagram come
before rendering — iac-authoring draws it as soon as the spec is written, without asking,
and loops on it with the customer until it fits; the render starts only after that
sign-off, while changing a decision is still one line in the spec, not a regenerated
module. It also keeps the diagram identical
for Terraform and Bicep, as the spec is.

**A diagram is never the last message.** Whoever exports one - first draw, redraw after a
change, a diagram-only request - ends the turn with the sign-off question of
[iac-authoring](../iac-authoring/SKILL.md) (Phase 5, "The code question"): does this fit - yes /
change something / not yet. The wording follows `context.language` (German: *Passt das
so? Ja, passt / Etwas ändern / Noch nicht*; English: *Does this fit your requirements?
Yes, build it / Change something / Not yet*). The yes option is what starts the code
render; without the question it never starts.

## Run it

```sh
python3 <plugin>/core/iac-diagram/scripts/new_diagram.py    ./infra-spec.yaml
python3 <plugin>/core/iac-diagram/scripts/verify_diagram.py  ./infra-spec.yaml ./infra-diagram.drawio
python3 <plugin>/core/iac-diagram/scripts/export_diagram.py ./infra-diagram.drawio
```

Verify first: the export deletes the `.drawio`, and `verify_diagram.py` also reads the PNG,
so it can be run afterwards too.

The language is the spec's `context.language`, `de` or `en`; `--language` overrides it for a
check. It covers the fixed labels and the decisions panel; Azure names, types, ranges and role names stay as Azure spells them,
since those are what the customer will find in the portal.

**Generate first, never write the draw.io XML from scratch.** The layout is computed: every
icon has a fixed slot, containers are sized from their contents, each edge type has its own
track, and the script fails if any two shapes or labels overlap. A hand-placed diagram gets
every one of those wrong in a way that only shows in the picture — labels that wrap after
every word because they inherit the 48px icon width, a label running into the icon below, two
role names stacked on the same line. The script does the bulk of the work, and does it
without spending tokens on coordinates.

**Then finish it by hand.** The script's job ends with the first draft: a cheap, correct
starting point with every shape in a slot. What the customer signs off on is finished by
hand on that file, against the review's findings (iac-authoring Phase 5, Loop 1) - a line
through an icon, two edges on one track, a label on a line, a lane that sits tight, a
colour that reads too close to its neighbour. In this order:

1. Generate, verify, look at the picture (or take the review agent's list), and list what
   is off.
2. Keep the `.drawio` (`export_diagram.py --keep`, or `drawio_png.py extract`), edit only
   the affected cells by id with Edit — `geometry`, `value`, a style attribute, a
   waypoint, an `exitX`/`entryX` anchor — never rewrite the file, and never change the
   ids, which `verify_diagram.py` and the `extract` diff rely on. Move a shape where the
   picture needs it; the computed slot was a starting point, not a rule.
3. `verify_diagram.py`, then `export_diagram.py`, then look at the picture again. Each
   hand edit must pass the same checks as a generated one.
4. **Do not touch `new_diagram.py` in the loop.** A fault the script would repeat on the
   next spec (a routing that merges edges, a slot too narrow for its label) is written
   into the hand-over as a plugin todo, with the cell ids it hit, and fixed in a session of
   its own - never while a customer waits for the picture.

Hand edits are **lost on regeneration**: if the spec changes after them ("etwas ändern"),
regenerate and redo the edits, so note them in the hand-over. Never hand-edit to silence
`overlaps` or `does not fit` from the script - those are the script failing on its own
draft and are reported as such.

**The review is not optional.** Every generation or hand edit of the diagram ends in Loop 1
of [iac-rendering/references/agents.md](../iac-rendering/references/agents.md), with the
checklist and the ceiling of [iac-authoring](../iac-authoring/SKILL.md) Phase 5 - also when
the spec was only extended or changed, and also when this skill was loaded on its own. Nobody
sees the picture before it has been reviewed. If the working mode (Subagents or Same session)
has not been answered in this session, ask it through `AskUserQuestion` before drawing, as
Phase 5 says; never review silently "by looking once" and call it done.

### The review checklist

The reviewer works through this list, in this order, and reports every hit with the cell ids.
A hit in 1-3 is an `error` with cause `render`, always: a customer cannot read a line that
runs through something, whatever the spec says.

1. **Trace every edge from its source to its target**, segment by segment, and for each
   segment ask what it crosses. A segment that passes through the icon, the label or the
   container title of any shape other than its own two ends is an error. Count the edges
   in the picture against `wiring.access` and the generated per-pair edges; a missing one
   is an error, and so is one that ends on the wrong shape.
2. **Two edges that share a stretch** - collinear, or closer than about 8 px for more than a
   short run - are one error: nobody can tell which line goes where. A right-angle crossing
   is not an error.
3. **A label on top of a shape, an icon, another label or another edge's line**, or one that
   sits on a container border so that the border reads as part of the text. A label on its
   own edge's line with a white background is normal.
4. **Text**: wrapped after single words, cut off, in the wrong language, a name that
   disagrees with the spec (`Avm Quellen` for `AVM-Quellen`).
5. **Spec fidelity**: every resource, number and range in the picture is in the spec and the
   other way round; the legend's colours match the edges.
6. **Arrow direction** matches the call (who initiates), not the data flow.

Everything the checklist does not name and that only looks worse than it could is `polish`.

**A layout error is not handed over.** A line through an icon means the row is wrong, not
that the line needs a better waypoint: re-slot the shapes (a column instead of a row, an
icon moved, a container grown and everything below it shifted) until 1-3 are empty. Moving
shapes is allowed here, as above; the pass ceiling limits the reviewer's findings, not what
the diagram agent may change. Only when the same layout error survives a re-slot does the
customer see the picture with it, and then it is named in the sign-off message as an open
`error`, never as "known" or "polish".

**One file is delivered: `infra-diagram.drawio.png`.** A PNG with the diagram embedded — it
opens in a document, a chat or an email like any image, and opens in draw.io as the
editable diagram. `new_diagram.py` writes `infra-diagram.drawio` only as the input of the
export, and `export_diagram.py` deletes it once the PNG carries it (`--keep` leaves it).
The ids come from the spec keys, so two generations diff readably after `extract`.

Exit codes, all scripts: `0` ok, `1` failed, `2` could not run.

- `new_diagram.py` exit 1 with `overlaps` or `does not fit` is a layout bug in the script, not
  something to patch in the output.
- `export_diagram.py` exit 2 means draw.io desktop is not installed. Say so. A substitute
  renderer is acceptable only when the result is the same deliverable: the `.drawio` XML
  embedded into the PNG afterwards (`drawio_png.py embed`) and `drawio_png.py check`
  passing - a cloud session has done it through draw.io's viewer script in headless
  Chromium. A PNG without the embedded diagram is a picture the customer cannot correct;
  where no renderer at all is available, deliver the `.drawio` file (the one case where
  it is the deliverable).
- `export_diagram.py` repairs and checks the PNG after an embedded export. The draw.io
  desktop CLI writes a bad zTXt CRC and no IEND chunk with `--embed-diagram`, every time:
  browsers still show it, strict decoders (and Claude's image reader) reject it. Never
  call the draw.io CLI directly, and never hand over a PNG `drawio_png.py check` calls BAD.
  `--scale` (default 2) and `--border` (default 20) are options.

**Regeneration overwrites the PNG.** Manual edits, the customer's and the fine-tuning above,
are lost on the next run. A change the customer makes in the picture is a change to a
decision, and it goes back into the spec.

To see what the customer changed, take the XML out of their PNG and diff it against a fresh
generation. The ids are stable, so the diff shows the cells they moved, renamed or added:

```sh
python3 <plugin>/core/iac-diagram/scripts/drawio_png.py extract ./theirs.drawio.png <scratch>/theirs.drawio
python3 <plugin>/core/iac-diagram/scripts/new_diagram.py ./infra-spec.yaml --out <scratch>/fresh.drawio
diff <scratch>/fresh.drawio <scratch>/theirs.drawio
```

Each difference is a question for the spec ("you renamed the subnet - is the range still
right?"), not a patch for the diagram.

## Audience

Decide it before drawing. The default is the **customer**: the person who asked for the
infrastructure and has to say whether this is what they meant. Their picture has no repo
names, file paths, variable names, module versions or Terraform internals, and no process
commentary. It is phrased for their tenant, not for how it is built.

An **engineer** reviewing the render also wants the AVM module and version behind each
resource and the spec keys. That is a different picture from a different question; say so
and offer it, rather than putting module versions on the customer's.

## What it shows

One page, the decisions a customer can judge. Not forty attributes.

```
 external zone │ resource group > [ virtual network: subnets with their compute │ Azure PaaS ] │ monitoring, name resolution │ decisions
```

The picture answers one question: **who can reach what.** It is drawn in zones, and the
lines are access, not plumbing.

| Spec | Drawn as |
|---|---|
| `context` | The resource group as the outermost container, region and environment in its label; no subscription frame (it changes per environment and adds only a layer); title and one-line subtitle (exposure, keyless; a resource left public in a private deployment is named, never covered by "no public access") above |
| `virtual-network` subnets, `deployment.address_space` | A virtual network zone with its subnets and ranges. A subnet that hosts compute carries its delegation (`delegated to Microsoft.Web/serverFarms`) |
| Compute (`app-service`, `function-app`, `container-app`, `virtual-machine`, …) | An icon inside the subnet named by its `networking.integration_subnet` decision, else the first integration-like subnet |
| Other `resources:` (storage, vault, database, bus, registry, …) | An icon in the *Azure PaaS* zone below the network, titled *public access disabled* when every one is. A PaaS service is not in the VNet; its endpoint is |
| `user-assigned-identity`, `network-security-group` | Not services that are called: a zone of their own below the PaaS zone (*Identities and network baseline*), so that no line to a service runs through them |
| A second resource of one kind (`app-service__web`, `app-service__mcp`) | Read as the set before the `__` for icon, title and question set; labelled with its `wiring.purposes` entry, else the instance name |
| `deployment.resource_group_split` (+ `resource_group_mode_<role>`, `placement.resource_group`) | **A frame per group** where resources stand together, in the group's colour: solid when the group is created, dashed when it exists. The *Azure PaaS* zone holds one frame per group (stacked in the hub layout, side by side in the compact one, up to eight services), the *Identities and network baseline* zone one per group, the virtual network is the network group's frame, the *Monitoring* title names its group. The outer frame is titled *Deployment*, no group's name, and carries no resource group icon - it is not one. A resource inside a frame carries no tag; compute, which sits in the network's subnets and belongs to another group, carries Azure's resource group icon and `<role> (created\|existing)`. The legend lists the groups, the decisions panel gives their modes. A private endpoint carries none - it lives with the resource it serves |
| Private endpoints | **One** bundled icon in the endpoint subnet (`9× app-service, function-app +7`), not one per resource |
| `subnet_policy.subnet_delegations` | The delegation printed on each subnet; the kind's usual delegation only where the spec says none |
| `wiring.access` | The lines: `{ from, to, label }`. `from` and `to` are resource keys or actors - `internet`, `users`, `external:<name>` - which sit in the *Internet and external services* zone. A line to a PaaS service runs on a shared track and splits on a bus lane, like a tree |
| `wiring.role_assignments` | `← principal: role` in purple on the target's label, **no line of its own** (lines without waypoints ran through icons and titles); an actor as the principal, who has no label to carry it, still gets one. A pair that `wiring.access` draws keeps its line |
| `deployment.network_exposure: public` | An *Internet* actor with an orange line to each compute resource (or PaaS service if there is no compute) |
| Blue and orange lines | Blue: private path, no public route. Orange: from or over the internet, or to a target whose public access is not disabled |
| `wiring.purposes` | What a resource is for, under its type (`Storage Account · Product images`); without one, the spec key |
| `wiring.optional` | The listed resources marked *optional* and faded; the legend says so |
| A resource type with no icon | A box with the type's name, marked as having no question set; the script warns |
| Diagnostics | **Not** a line per resource: a *Monitoring* zone with the workspace and the note *Diagnostic settings of all resources* |
| Private DNS zones | One bundled icon in a *Name resolution* zone (`8× privatelink.*`) |
| Referenced things (`network_ownership: reference`, a central workspace, platform DNS) | Grey and dashed, outside the resource group, labelled as existing and not created |
| `open:` entries, `assumed` values | The affected resource in red; the panel counts them by owner and points at `infra-decisions.md`, which carries every question |

**Layout and how the lines run.** With four or more PaaS services the picture is a **hub**, as in
a hand-drawn architecture: the compute subnets on the left, the endpoint subnet as a tall column
beside them with the bundled *Private Endpoints* in its middle, the services as a column outside
the network. **Each caller has one line into the endpoints** - the farther a caller sits from the
endpoints' height, the further right its track, so a vertical never crosses another caller's run
- and **one line leaves the endpoints for each service**, all on a single trunk. Eleven
connections become four plus seven, and who calls what is text at the service
(`← App Service · web, Function App`), not a line. With fewer services the zone sits below the
network instead and each caller runs on a track beside the subnets and a lane under them to its
services. A line to Application Insights goes out along the row, down the corridor right of the
network, along the gutter above the monitoring zone's row and in at the icon's left - the zone
sits under the network or the services, never beside them; lines to and from an
actor (users, Entra ID) run in the gap between the external zone and the group, never on the
group's border. **With three or more callers the lines into the endpoints are told apart by
colour**, one per caller, and the legend names them; the lines out of the endpoints stay blue,
and orange stays what leaves or crosses the internet. A picture where the lines still read badly
is a layout bug in the script, not something to move by hand.

AI Foundry and Container Apps have no icon of their own in draw.io's library; the nearest are
used (Cognitive Services, Container Instances) and the label carries the real type. Lines run
from compute to PaaS and from actors; a PaaS-to-PaaS line (a search service reading a storage
account) is not routed, so say it in `wiring.purposes` instead.

A legend at the bottom lists only what the picture uses.

Plus a **decisions panel** under the group, beside the legend when the width allows and in
columns below it otherwise: exposure, network, mandates, DNS and diagnostics ownership, and the count
of open and assumed entries by owner, pointing at `infra-decisions.md`. Nothing in it is prose:
the forced chains (`key_protection: hsm → forces key-vault.sku = premium`), the questions and
the reasons are in the decision document, which the customer reads beside the picture (a drawing
is not where prose is read).

What it leaves out: SKUs nobody asked about, TLS floors, soft-delete days, every `default`
from the guardrail baseline. They are in the spec and in the Phase 4 report; on the
picture they are noise that hides the topology.

**Existing is not created.** Drawing a referenced VNet in the same style as a new one tells
the customer this run builds it. The grey styling is the boundary this run stops at.

## Check before handing it over

1. `verify_diagram.py` checks the file against the spec: every resource in `resources:`
   drawn exactly once, nothing drawn that the spec does not contain, every `open:` entry in
   the picture, every `wiring.optional` resource faded. In German it also fails
   on transliterated umlauts (`ueber`, `oeffentlich`) in any label. The network and the
   workspace are drawn even when the spec only references them, and application insights
   next to the workspace; those are not extras.
2. Export a preview and look at it — the overlap check covers geometry, not taste:

```powershell
python3 <plugin>/core/iac-diagram/scripts/export_diagram.py ./infra-diagram.drawio --out <scratch>/preview.png --no-embed
```

3. A `[warn] no icon` from `new_diagram.py` means a resource was drawn as a plain box —
   say so.
4. `drawio_png.py check ./infra-diagram.drawio.png` is `OK`, not `BAD`.

`drawio_png.py labels <file>` lists every label of a `.drawio` or a `.drawio.png` as text,
to read or grep without opening draw.io.

## Icons

`ICONS` in [new_diagram.py](scripts/new_diagram.py) maps each resource key to a path in
draw.io's built-in `azure2` library. Every resource with a question set needs a row there.

Find a path with `drawio_png.py icons <word> [<word>]` (e.g. `icons azure2 key`), never from
memory. A wrong path does not fail, it exports as a broken-image placeholder.
`run_png_tests.py` checks every path in `ICONS` against draw.io's bundled library, and
`drawio_png.py check` warns about unknown paths in a PNG. `azure2` has no subnet shape,
which is why subnets are containers.

## Tests

```sh
python3 <plugin>/core/iac-diagram/tests/run_diagram_tests.py   # fixture specs in, assertions on the drawing out
python3 <plugin>/core/iac-diagram/tests/run_png_tests.py       # PNG repair, extract/embed, verify_diagram, icon table
```

Run both after changing anything under `scripts/`.
