# Key Vault key - what the question set cannot express

## This set or the vault's

The vault's `customer_managed_keys` (with its `key_type`, `key_size`, `key_rotation_days`,
`key_expiry_days`) decides the keys of `deployment.key_management: customer_managed` - one rule for
all of them, rendered through the vault module's `keys` input. This set exists for a key that
answers differently:

| The key is... | Decided in |
|---|---|
| A customer-managed key for a service, same type, size and rotation as its siblings | `key-vault` (`customer_managed_keys`) |
| A customer-managed key that needs its own rotation, size or protection | This set - and its name is not in the vault's list |
| A signing key, or a key an application encrypts with | This set |
| A key a person imports (BYOK) | Not covered |

A name is in exactly one of the two. This set's defaults (`3072`, `P90D` rotation, `P365D` expiry)
equal the vault's, so moving a key from one to the other changes nothing but where it is written.

## Fixed at creation

- **The name and the key type.** A key is not renamed; the type (RSA/EC) and the HSM/software
  protection cannot change in place. A software key cannot become an HSM key.
- **The size and the curve.** A version has one; a larger key is a new key, or a rotation to a
  version created under a new definition.
- **Operations and attributes belong to a version.** Changing `key_operations` updates the
  current version; a version created by rotation carries the policy's attributes.

## Ordering

The vault, the key writer's role on the vault (a data-plane write needs it, see
`key-vault/notes.md`), the key, then the key's role assignments, then the consumer. A customer-managed
key's consumer takes a **user-assigned** identity whose role on the key is granted before the
consumer exists - system-assigned would make the consumer depend on itself.

## Pitfalls

**A consumer pinned to a version breaks on rotation.** Services that follow the key's latest version
(storage with a versionless key URI, SQL, disks with auto-rotation) pick up a new version; a
consumer that stored a version id keeps the old one until it expires. Render the versionless id
(`resource_versionless_id` / the key URI without the version) wherever the consumer allows.

**Module defaults diverge.** The vault module's `keys` default `key_opts` to `["sign", "verify"]`,
the key submodule to none, the Bicep key module to none (and its `kty` to **EC**). Written always.

**The near-expiry notification goes to Event Grid and no further.** The rotation policy's notify
action raises a key-near-expiry event on the vault's Event Grid topic; no mail is sent. Without a
subscription on that event the warning is a log entry nobody reads - an `open:` entry owned by
the platform team.

**An expired customer-managed key makes data unreadable.** A service that cannot use its key
(expired, disabled, deleted, role removed) stops reading the data it protects, usually with an
error that does not name the key. This is why expiry is much longer than rotation and a warning
exists. Purge protection on the vault (inherited) keeps a deleted key recoverable.

**A signing key and its verifiers.** Rotation creates a new version that signs from then on; a
verifier must trust every version whose signatures are still in circulation, which means the old
public key stays published until the last token or document signed with it has expired.

**Secure key release** (`release_policy`) replaces the key when added, changed or removed on an
existing key, because the provider marks it force-new: key material is destroyed. It is not
covered here for that reason.

## Not covered here, and why

Imported keys (BYOK), secure key release, Managed HSM keys, key backup and restore, and the Event Grid
subscription behind the near-expiry warning each carry decisions of their own and have no question
set yet; a request for one is said out loud, not improvised.
