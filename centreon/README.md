# HYCU Monitoring — Centreon Plugin Pack (CLAPI import)

This folder provides a **ready-to-import Centreon configuration** so you don't
have to create commands and service templates by hand (the long manual procedure
in [`../CENTREON_HOWTO.md`](../CENTREON_HOWTO.md)).

It is delivered as a **CLAPI** import file ([`hycu-pluginpack.clapi`](hycu-pluginpack.clapi)),
the native text format of Centreon. It is **not** an official marketplace Plugin
Pack (those are built on the `centreon-plugins` Perl framework); it is the
"level 1" equivalent that gives ~90% of the convenience.

## What it creates

| Object | Names |
|--------|-------|
| **12 check commands** | `check_hycu_version`, `check_hycu_license`, `check_hycu_jobs`, `check_hycu_backup_validation`, `check_hycu_unassigned`, `check_hycu_shares`, `check_hycu_buckets`, `check_hycu_port`, `check_hycu_vm`, `check_hycu_target`, `check_hycu_policy_advanced`, `check_hycu_manager` |
| **1 host template** | `HYCU-Controller` (host check = TCP 8443, password macro `HYCUTOKEN`) |
| **13 service templates** | `HYCU-Version`, `HYCU-License`, `HYCU-Jobs`, `HYCU-Backup-Validation`, `HYCU-Unassigned`, `HYCU-Shares`, `HYCU-Buckets`, `HYCU-Port-8443`, `HYCU-Manager-Protected`, `HYCU-Manager-Compliance`, `HYCU-VM-Backup`, `HYCU-Target-Health`, `HYCU-Policy-Advanced` |

The global service templates (license, jobs, shares, …) are **auto-attached** to
the `HYCU-Controller` host template, so they deploy automatically on any host
using that template. The per-object templates (`HYCU-VM-Backup`,
`HYCU-Target-Health`, `HYCU-Policy-Advanced`) are **not** auto-attached because
they need a specific object name — instantiate them per object (see below).

## Prerequisites

1. Deploy the plugin on each poller:
   ```bash
   cp check_hycu_vm_backup_v2.2.py /usr/lib/nagios/plugins/
   chmod 755 /usr/lib/nagios/plugins/check_hycu_vm_backup_v2.2.py
   pip install requests
   ```
2. `$USER1$` must point to the plugin directory (default `/usr/lib/nagios/plugins`).

## Import

On the **central** Centreon server:

```bash
centreon -u admin -p '<admin_password>' -i /path/to/hycu-pluginpack.clapi
```

> Re-running the import is safe for new objects but will report errors for
> objects that already exist — that is expected; existing objects are left
> untouched.

## Configure a HYCU host

1. `Configuration > Hosts > Add`
2. **Name** = your controller, **IP** = controller FQDN/IP
3. **Templates** = `HYCU-Controller`
4. Open the **Macros** tab → set `HYCUTOKEN` to your real API token
   (the imported default is the placeholder `CHANGE_ME_HYCU_API_TOKEN`)
5. Save → the global HYCU services appear automatically.

### Add per-object services (VM / target / policy)

For object-specific checks, create a service on the host and pick the template,
then set the object name in its check arguments (`Macros / arguments`):

| Template | Arguments (`!` separated) | Example |
|----------|---------------------------|---------|
| `HYCU-VM-Backup` | `!<vm_name>!<timeout>` | `!PROD-DB-01!100` |
| `HYCU-Target-Health` | `!<target_name>!<timeout>` | `!01_NFS_Shared!100` |
| `HYCU-Policy-Advanced` | `!<policy>!<warn>!<crit>!<timeout>` | `!Gold!5!10!100` |

## Default thresholds

| Service template | Warning | Critical | Period |
|------------------|---------|----------|--------|
| HYCU-License (days left) | 30 | 7 | — |
| HYCU-Jobs (failed) | 10 | 20 | 24h |
| HYCU-Backup-Validation (failed) | 5 | 10 | 24h |
| HYCU-Unassigned (objects) | 5 | 10 | — |
| HYCU-Shares (non-compliant) | 3 | 5 | — |
| HYCU-Buckets (non-compliant) | 2 | 5 | — |

Adjust any of these per host/service by overriding the check arguments.

## Notes

- The token is stored as a **password host macro** (`$_HOSTHYCUTOKEN$`), so it is
  per-controller and hidden in the UI. If you prefer a single global token,
  replace `-a $_HOSTHYCUTOKEN$` with `-a $USER10$` in the commands and define the
  `$USER10$` resource macro instead (see `CENTREON_HOWTO.md`, Method 1).
- `check_hycu_manager` requires a token with HYCU MoM dashboard permissions; on a
  standalone controller it may return *Access forbidden*.
- CLAPI object signatures can vary slightly between Centreon major versions. If a
  line is rejected, check that release's CLAPI reference for `CMD`, `HTPL`, `STPL`.
