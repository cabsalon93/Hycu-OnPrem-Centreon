# 🎨 HYCU Monitoring Plugin - Centreon Integration Guide

Complete guide for integrating HYCU Monitoring Plugin into Centreon monitoring platform.

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Plugin Installation](#plugin-installation)
3. [Secure Token Storage](#secure-token-storage)
4. [Commands Configuration](#commands-configuration)
5. [Service Templates](#service-templates)
6. [Host Configuration](#host-configuration)
7. [Services Configuration](#services-configuration)
8. [Graph Configuration](#graph-configuration)
9. [Notification Setup](#notification-setup)
10. [Best Practices](#best-practices)
11. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements

- **Centreon Version:** 20.04 or higher (tested on 20.x, 21.x, 22.x, 23.x, 24.x)
- **Python:** 3.7+ installed on poller
- **Network:** Poller can reach HYCU on port 8443
- **Permissions:** SSH access to Centreon Central/Poller

### HYCU Requirements

- **HYCU Version:** 4.9+ or 5.x
- **API Token:** Generated from HYCU UI
- **User:** Read-only access sufficient

### Verify Prerequisites

```bash
# SSH to Centreon poller
ssh centreon@poller-server

# Check Python version
python3 --version
# Expected: Python 3.7.x or higher

# Check network connectivity
telnet hycu-host.company.com 8443
# Expected: Connected

# Check plugin directory
ls -l /usr/lib/nagios/plugins/
# Expected: Directory exists and writable
```

---

## Plugin Installation

### Method 1: Direct Download (Recommended)

```bash
# SSH to Centreon Central or Poller
ssh centreon@centreon-server

# Switch to root
sudo su -

# Download plugin
cd /usr/lib/nagios/plugins/
wget https://raw.githubusercontent.com/YOUR_USERNAME/hycu-monitoring-plugin/main/check_hycu_vm_backup_v2.1.py

# Set permissions
chmod 755 check_hycu_vm_backup_v2.1.py
chown centreon-engine:centreon-engine check_hycu_vm_backup_v2.1.py

# Verify
ls -l check_hycu_vm_backup_v2.1.py
# Expected: -rwxr-xr-x centreon-engine centreon-engine
```

### Method 2: Manual Copy

```bash
# From your workstation, copy to Centreon server
scp check_hycu_vm_backup_v2.1.py centreon@centreon-server:/tmp/

# SSH to Centreon server
ssh centreon@centreon-server
sudo su -

# Move to plugin directory
mv /tmp/check_hycu_vm_backup_v2.1.py /usr/lib/nagios/plugins/
chmod 755 /usr/lib/nagios/plugins/check_hycu_vm_backup_v2.1.py
chown centreon-engine:centreon-engine /usr/lib/nagios/plugins/check_hycu_vm_backup_v2.1.py
```

### Test Installation

```bash
# Test plugin execution
su - centreon-engine -s /bin/bash
/usr/lib/nagios/plugins/check_hycu_vm_backup_v2.1.py -h

# Expected output: Plugin help text
```

---

## Secure Token Storage

### Method 1: Resource Macro (Recommended for Production)

**Advantages:**
- ✅ Centralized token management
- ✅ Easy to update
- ✅ Hidden from logs
- ✅ Used across all HYCU hosts

**Steps:**

1. **Login to Centreon Web UI** as admin

2. **Navigate to:** `Configuration` > `Pollers` > `Resources`

3. **Add New Resource:**
   - **Macro name:** `$USER10$`
   - **Macro value:** `YOUR_HYCU_API_TOKEN_HERE`
   - **Comment:** `HYCU API Token - Do not share`
   - **Linked Instances:** Select your poller(s)

4. **Save** and **Export Configuration**

5. **Reload Poller:**
   ```bash
   systemctl reload centengine
   ```

**Usage in commands:**
```bash
$USER1$/check_hycu_vm_backup_v2.1.py -l $HOSTADDRESS$ -a $USER10$ -t version
```

### Method 2: Host Custom Macro

**Advantages:**
- ✅ Different tokens per HYCU controller
- ✅ Flexibility for multi-tenant

**Steps:**

1. **Navigate to:** `Configuration` > `Hosts` > `Hosts`

2. **Select HYCU Host**

3. **Go to:** `Macros` tab

4. **Add Custom Macro:**
   - **Macro name:** `HYCUTOKEN`
   - **Macro value:** `YOUR_TOKEN`
   - **Password:** ☑ (checked - hides value)
   - **Description:** `HYCU API Token`

5. **Save**

**Usage in commands:**
```bash
$USER1$/check_hycu_vm_backup_v2.1.py -l $HOSTADDRESS$ -a $_HOSTHYCUTOKEN$ -t version
```

### Method 3: Service Custom Macro (Least Recommended)

Only use if you need different tokens per service.

---

## Commands Configuration

### Access Commands

`Configuration` > `Commands` > `Checks`

### 1. Global Version Check

**Purpose:** Get HYCU version (always OK, informational)

```
Name: check_hycu_version
Type: Check
Command Line:
$USER1$/check_hycu_vm_backup_v2.1.py -l $HOSTADDRESS$ -a $USER10$ -t version -T $ARG1$

Argument Example:
ARG1: 100 (timeout in seconds)
```

**Enable shell:** No  
**Graph template:** None (informational only)

### 2. License Expiration

**Purpose:** Monitor license expiration with inverted thresholds

```
Name: check_hycu_license
Type: Check
Command Line:
$USER1$/check_hycu_vm_backup_v2.1.py -l $HOSTADDRESS$ -a $USER10$ -t license -w $ARG1$ -c $ARG2$ -T $ARG3$

Argument Example:
ARG1: 30 (warning: 30 days before expiration)
ARG2: 7  (critical: 7 days before expiration)
ARG3: 100 (timeout)
```

**Note:** Thresholds are inverted (critical < warning)

### 3. Jobs Monitoring

**Purpose:** Monitor backup jobs over time period

```
Name: check_hycu_jobs
Type: Check
Command Line:
$USER1$/check_hycu_vm_backup_v2.1.py -l $HOSTADDRESS$ -a $USER10$ -t jobs -w $ARG1$ -c $ARG2$ -p $ARG3$ -T $ARG4$

Argument Example:
ARG1: 10 (warning: 10 failed jobs)
ARG2: 20 (critical: 20 failed jobs)
ARG3: 24 (period: 24 hours)
ARG4: 100 (timeout)
```

### 4. Unassigned Objects Audit

**Purpose:** Monitor objects without policy

```
Name: check_hycu_unassigned
Type: Check
Command Line:
$USER1$/check_hycu_vm_backup_v2.1.py -l $HOSTADDRESS$ -a $USER10$ -t unassigned -w $ARG1$ -c $ARG2$ -T $ARG3$

Argument Example:
ARG1: 5  (warning: 5 unassigned objects)
ARG2: 10 (critical: 10 unassigned objects)
ARG3: 100 (timeout)
```

### 5. VM Backup Status

**Purpose:** Check individual VM backup status

```
Name: check_hycu_vm
Type: Check
Command Line:
$USER1$/check_hycu_vm_backup_v2.1.py -l $HOSTADDRESS$ -a $USER10$ -n "$ARG1$" -t vm -T $ARG2$

Argument Example:
ARG1: VM-PROD-01 (VM name)
ARG2: 100 (timeout)
```

**Note:** Use quotes around $ARG1$ for VM names with spaces

### 6. Policy Compliance Advanced

**Purpose:** Monitor policy with detailed breakdown

```
Name: check_hycu_policy_advanced
Type: Check
Command Line:
$USER1$/check_hycu_vm_backup_v2.1.py -l $HOSTADDRESS$ -a $USER10$ -n "$ARG1$" -t policy-advanced -w $ARG2$ -c $ARG3$ -T $ARG4$

Argument Example:
ARG1: Production (policy name)
ARG2: 3  (warning: 3 non-compliant)
ARG3: 5  (critical: 5 non-compliant)
ARG4: 100 (timeout)
```

### 7. Shares Monitoring

**Purpose:** Monitor NFS/SMB file shares

```
Name: check_hycu_shares
Type: Check
Command Line:
$USER1$/check_hycu_vm_backup_v2.1.py -l $HOSTADDRESS$ -a $USER10$ -t shares -w $ARG1$ -c $ARG2$ -T $ARG3$

Argument Example:
ARG1: 3  (warning: 3 non-compliant shares)
ARG2: 5  (critical: 5 non-compliant shares)
ARG3: 100 (timeout)
```

### 8. Buckets Monitoring

**Purpose:** Monitor S3 buckets

```
Name: check_hycu_buckets
Type: Check
Command Line:
$USER1$/check_hycu_vm_backup_v2.1.py -l $HOSTADDRESS$ -a $USER10$ -t buckets -w $ARG1$ -c $ARG2$ -T $ARG3$

Argument Example:
ARG1: 2  (warning: 2 non-compliant buckets)
ARG2: 5  (critical: 5 non-compliant buckets)
ARG3: 100 (timeout)
```

### 9. Backup Validation

**Purpose:** Monitor validation jobs

```
Name: check_hycu_backup_validation
Type: Check
Command Line:
$USER1$/check_hycu_vm_backup_v2.1.py -l $HOSTADDRESS$ -a $USER10$ -t backup-validation -w $ARG1$ -c $ARG2$ -p $ARG3$ -T $ARG4$

Argument Example:
ARG1: 5  (warning: 5 failed validations)
ARG2: 10 (critical: 10 failed validations)
ARG3: 24 (period: 24 hours)
ARG4: 100 (timeout)
```

### 10. Port Connectivity

**Purpose:** Test TCP port connectivity (no token needed)

```
Name: check_hycu_port
Type: Check
Command Line:
$USER1$/check_hycu_vm_backup_v2.1.py -l $HOSTADDRESS$ -t port -n $ARG1$ -T $ARG2$

Argument Example:
ARG1: 8443 (port number)
ARG2: 30 (timeout - max 30s for port checks)
```

**Note:** No API token required for this check

### 11. Target Health

**Purpose:** Monitor backup target health

```
Name: check_hycu_target
Type: Check
Command Line:
$USER1$/check_hycu_vm_backup_v2.1.py -l $HOSTADDRESS$ -a $USER10$ -n "$ARG1$" -t target -T $ARG2$

Argument Example:
ARG1: NFS-TARGET-01 (target name)
ARG2: 100 (timeout)
```

### 12. Manager Dashboard

**Purpose:** Global protected/compliance overview

```
Name: check_hycu_manager
Type: Check
Command Line:
$USER1$/check_hycu_vm_backup_v2.1.py -l $HOSTADDRESS$ -a $USER10$ -n "$ARG1$" -t manager -T $ARG2$

Argument Example:
ARG1: protected (or "compliance")
ARG2: 100 (timeout)
```

---

## Service Templates

### Template 1: HYCU-Global-License

**Purpose:** Monitor license expiration (critical service)

```
Configuration > Services > Templates

Template Settings:
- Name: HYCU-Global-License
- Alias: HYCU License Expiration Monitoring
- Template: generic-service
- Check Command: check_hycu_license
- Args: !30!7!100
- Check Period: 24x7
- Max Check Attempts: 3
- Normal Check Interval: 1440 (once per day)
- Retry Check Interval: 60
- Active Checks: Enabled
- Passive Checks: Disabled
```

**Notification Settings:**
- Notifications Enabled: Yes
- Notification Period: 24x7
- Notification Interval: 1440 (once per day)
- Notify on: Warning, Critical, Recovery

**Macros:**
- WARNINGDAYS: 30
- CRITICALDAYS: 7

### Template 2: HYCU-Global-Jobs-24h

**Purpose:** Monitor all backup jobs over 24h

```
Template Settings:
- Name: HYCU-Global-Jobs-24h
- Alias: HYCU Jobs Statistics (24 hours)
- Check Command: check_hycu_jobs
- Args: !10!20!24!100
- Check Period: 24x7
- Max Check Attempts: 3
- Normal Check Interval: 15
- Retry Check Interval: 5
```

**Performance Data:** Yes (for graphs)

**Macros:**
- WARNING: 10
- CRITICAL: 20
- PERIOD: 24

### Template 3: HYCU-Global-Unassigned

**Purpose:** Audit unassigned objects

```
Template Settings:
- Name: HYCU-Global-Unassigned
- Alias: HYCU Unassigned Objects Audit
- Check Command: check_hycu_unassigned
- Args: !5!10!100
- Check Period: 24x7
- Max Check Attempts: 3
- Normal Check Interval: 60 (hourly)
- Retry Check Interval: 15
```

### Template 4: HYCU-Object-VM

**Purpose:** Individual VM backup monitoring

```
Template Settings:
- Name: HYCU-Object-VM
- Alias: HYCU VM Backup Status
- Check Command: check_hycu_vm
- Args: !$_SERVICEVMNAME$!100
- Check Period: 24x7
- Max Check Attempts: 3
- Normal Check Interval: 15
- Retry Check Interval: 5
```

**Custom Macros:**
- VMNAME: (to be filled per service)

### Template 5: HYCU-Storage-Shares

**Purpose:** NFS/SMB shares compliance

```
Template Settings:
- Name: HYCU-Storage-Shares
- Alias: HYCU Shares Monitoring
- Check Command: check_hycu_shares
- Args: !3!5!100
- Check Period: 24x7
- Max Check Attempts: 3
- Normal Check Interval: 30
- Retry Check Interval: 10
```

### Template 6: HYCU-Network-Port

**Purpose:** HYCU API connectivity test

```
Template Settings:
- Name: HYCU-Network-Port
- Alias: HYCU Port Connectivity
- Check Command: check_hycu_port
- Args: !8443!30
- Check Period: 24x7
- Max Check Attempts: 3
- Normal Check Interval: 5
- Retry Check Interval: 1
```

**Note:** Fast check interval for quick detection

---

## Host Configuration

### Create HYCU Host

`Configuration` > `Hosts` > `Hosts` > `Add`

**General Information:**
```
Name: HYCU-PROD
Alias: HYCU Production Controller
IP Address/DNS: hycu.company.com
Snmp Community & Version: (leave empty)
Monitored from: Central (or your poller)
Timezone: Europe/Paris (adjust to your timezone)
Templates: generic-host
Host Groups: HYCU-Controllers (create if needed)
```

**Check Options:**
```
Check Command: check_hycu_port (or check-host-alive)
Args: !8443!30
Max Check Attempts: 3
Normal Check Interval: 5
Retry Check Interval: 1
```

**Notification:**
```
Notification Enabled: Yes
Contact addons: admin (or your notification groups)
Notification Period: 24x7
Notification Options: Down, Unreachable, Recovery
```

**Custom Macros:**
```
Macro Name: HYCUTOKEN
Macro Value: YOUR_API_TOKEN (if using host-level token)
Password: ☑ (checked)
Description: HYCU API Token
```

**Save and Export Configuration**

---

## Services Configuration

### Add Services to HYCU Host

`Configuration` > `Services` > `Services by host`

Select Host: **HYCU-PROD**

#### Service 1: License Monitoring

```
Service Settings:
- Description: HYCU-License-Expiration
- Template: HYCU-Global-License (or create from command)
- Check Command: check_hycu_license
- Args: !30!7!100
- Normal Check Interval: 1440 (daily)
- Graphical Template: (create custom - see Graph section)
```

#### Service 2: Jobs Statistics

```
Service Settings:
- Description: HYCU-Jobs-24h
- Template: HYCU-Global-Jobs-24h
- Check Command: check_hycu_jobs
- Args: !10!20!24!100
- Normal Check Interval: 15 (every 15 min)
- Graphical Template: HYCU-Jobs
```

#### Service 3: Unassigned Objects

```
Service Settings:
- Description: HYCU-Unassigned-Objects
- Template: HYCU-Global-Unassigned
- Check Command: check_hycu_unassigned
- Args: !5!10!100
- Normal Check Interval: 60 (hourly)
```

#### Service 4: Port Connectivity

```
Service Settings:
- Description: HYCU-Port-8443
- Template: HYCU-Network-Port
- Check Command: check_hycu_port
- Args: !8443!30
- Normal Check Interval: 5 (every 5 min)
```

#### Service 5: Version Information

```
Service Settings:
- Description: HYCU-Version
- Check Command: check_hycu_version
- Args: !100
- Normal Check Interval: 1440 (daily)
```

#### Service 6: Shares Monitoring

```
Service Settings:
- Description: HYCU-Shares-NFS-SMB
- Template: HYCU-Storage-Shares
- Check Command: check_hycu_shares
- Args: !3!5!100
- Normal Check Interval: 30
```

#### Service 7: Buckets Monitoring

```
Service Settings:
- Description: HYCU-Buckets-S3
- Check Command: check_hycu_buckets
- Args: !2!5!100
- Normal Check Interval: 30
```

### For Individual VMs (Dynamic Services)

Create services per VM using the HYCU-Object-VM template:

```
Service Settings:
- Description: HYCU-VM-PROD-DB-01
- Template: HYCU-Object-VM
- Custom Macro VMNAME: PROD-DB-01
```

**Tip:** Use Centreon Host Discovery or create via CSV import for bulk VM services.

---

## Graph Configuration

### Access Graph Templates

`Configuration` > `Services` > `Graph templates`

### Graph 1: License Days Left

```
Graph Settings:
- Name: HYCU-License-Days-Left
- Vertical Label: Days
- Width: 500
- Height: 200
- Lower Limit: 0
- Upper Limit: (auto)
```

**Curves:**
```
Curve 1:
- Metric: days_left
- Name: Days Before Expiration
- Color: #FF6600 (orange)
- Filled: No
- Line Type: Line
- Thickness: 2
```

**Thresholds:**
```
- Warning: 30 (horizontal line, yellow)
- Critical: 7 (horizontal line, red)
```

### Graph 2: Jobs Statistics

```
Graph Settings:
- Name: HYCU-Jobs-Statistics
- Vertical Label: Jobs Count
- Stacked: No
```

**Curves:**
```
Curve 1:
- Metric: jobs_ok
- Name: Successful Jobs
- Color: #00CC00 (green)

Curve 2:
- Metric: jobs_failed
- Name: Failed Jobs
- Color: #CC0000 (red)

Curve 3:
- Metric: jobs_running
- Name: Running Jobs
- Color: #0066CC (blue)
```

### Graph 3: Success Rate

```
Graph Settings:
- Name: HYCU-Success-Rate
- Vertical Label: Percentage (%)
- Lower Limit: 0
- Upper Limit: 100
```

**Curves:**
```
Curve 1:
- Metric: success_rate
- Name: Success Rate
- Color: #00AA00 (green)
- Filled: Yes
- Area: Yes
```

**Thresholds:**
```
- Warning: 95% (below = warning)
- Critical: 90% (below = critical)
```

### Graph 4: Unassigned Objects

```
Graph Settings:
- Name: HYCU-Unassigned-Objects
- Vertical Label: Count
- Stacked: Yes
```

**Curves:**
```
Curve 1:
- Metric: unassigned_vms
- Name: VMs
- Color: #FF0000

Curve 2:
- Metric: unassigned_shares
- Name: Shares
- Color: #FF6600

Curve 3:
- Metric: unassigned_buckets
- Name: Buckets
- Color: #FFCC00

Curve 4:
- Metric: unassigned_apps
- Name: Applications
- Color: #00CC00

Curve 5:
- Metric: unassigned_vgs
- Name: Volume Groups
- Color: #0066CC
```

### Graph 5: Shares Compliance

```
Graph Settings:
- Name: HYCU-Shares-Compliance
- Vertical Label: Count
- Stacked: No
```

**Curves:**
```
Curve 1:
- Metric: shares_compliant
- Name: Compliant
- Color: #00CC00 (green)

Curve 2:
- Metric: shares_non_compliant
- Name: Non-Compliant
- Color: #FF0000 (red)

Curve 3:
- Metric: shares_unprotected
- Name: Unprotected
- Color: #FF6600 (orange)
```

### Assign Graphs to Services

```
Configuration > Services > Services by host
Select service > Graphical Template > Choose template
Save
Export Configuration
```

---

## Notification Setup

### Create Contact Group for HYCU

`Configuration` > `Users` > `Contact Groups`

```
Contact Group Settings:
- Name: HYCU-Admins
- Alias: HYCU Administrators
- Contacts: admin, backup-team, on-call
- Linked to: Host Group: HYCU-Controllers
```

### Configure Service Notifications

For critical services (License, Jobs, Unassigned):

```
Service Configuration:
- Notification Enabled: Yes
- Contacts: HYCU-Admins
- Notification Period: 24x7
- Notification Options: Warning, Critical, Recovery, Flapping
- First Notification Delay: 0 (immediate)
- Notification Interval: 0 (send only once, then on recovery)
```

### Email Notification

Ensure Centreon email is configured:

`Administration` > `Parameters` > `Centreon UI` > `Notification`

### Escalation (Optional)

Create escalation for critical services:

`Configuration` > `Notifications` > `Escalations`

```
Escalation Settings:
- Name: HYCU-Critical-Escalation
- Alias: HYCU Critical Services Escalation
- First Notification: 1
- Last Notification: 5
- Notification Interval: 30
- Escalation Period: 24x7
- Contacts: On-Call-Manager, CTO
- Services: HYCU-License-Expiration, HYCU-Jobs-24h
```

---

## Best Practices

### Check Intervals

Recommended intervals by service type:

| Service Type | Normal Interval | Retry Interval | Rationale |
|--------------|-----------------|----------------|-----------|
| Port | 5 min | 1 min | Quick detection of outages |
| Jobs | 15 min | 5 min | Regular job monitoring |
| License | 1440 min (daily) | 60 min | Slow-changing data |
| Version | 1440 min (daily) | - | Informational only |
| Unassigned | 60 min | 15 min | Audit/compliance |
| VM Status | 15 min | 5 min | Critical VMs |
| Shares/Buckets | 30 min | 10 min | Storage compliance |

### Thresholds by Environment

#### Production
```bash
# Jobs
-w 5 -c 10    # Low tolerance

# Unassigned
-w 1 -c 5     # Very low tolerance

# License
-w 30 -c 7    # 1 month warning, 1 week critical
```

#### Development/Test
```bash
# Jobs
-w 20 -c 50   # Higher tolerance

# Unassigned
-w 10 -c 20   # Relaxed

# License
-w 15 -c 3    # Shorter notice
```

### Service Groups

Create service groups for better organization:

```
Service Group: HYCU-Global
- HYCU-License-Expiration
- HYCU-Jobs-24h
- HYCU-Version
- HYCU-Port-8443

Service Group: HYCU-Storage
- HYCU-Shares-NFS-SMB
- HYCU-Buckets-S3

Service Group: HYCU-Compliance
- HYCU-Unassigned-Objects
- HYCU-Backup-Validation

Service Group: HYCU-VMs
- HYCU-VM-PROD-DB-01
- HYCU-VM-PROD-WEB-01
- ...
```

### Performance Optimization

1. **Distribute checks** across time to avoid spikes
2. **Use check_period** to limit checks during maintenance windows
3. **Adjust timeout** (`-T`) based on HYCU API response time
4. **Cache results** using passive checks for non-critical data

### Security Best Practices

1. **Token Storage:**
   - Use `$USER10$` resource macro (not visible in UI)
   - Never hardcode tokens in command definitions
   - Rotate tokens every 90 days

2. **Permissions:**
   - Plugin owned by centreon-engine:centreon-engine
   - Read-only API token in HYCU
   - Limit Centreon user access to HYCU configurations

3. **Network:**
   - Firewall rules: Poller → HYCU:8443
   - No direct internet access from HYCU
   - Use VPN/private network if possible

---

## Troubleshooting

### Issue 1: Plugin Not Found

**Symptom:** `(No output returned from plugin)`

**Solutions:**
```bash
# Check file exists
ls -l /usr/lib/nagios/plugins/check_hycu_vm_backup_v2.1.py

# Check permissions
chmod 755 /usr/lib/nagios/plugins/check_hycu_vm_backup_v2.1.py

# Check ownership
chown centreon-engine:centreon-engine /usr/lib/nagios/plugins/check_hycu_vm_backup_v2.1.py

# Test as centreon-engine user
su - centreon-engine -s /bin/bash
/usr/lib/nagios/plugins/check_hycu_vm_backup_v2.1.py -h
```

### Issue 2: Authentication Failed

**Symptom:** `CRITICAL: API Error - Authentication failed`

**Solutions:**
```bash
# Verify token in resource macro
Configuration > Pollers > Resources
Check $USER10$ value

# Test manually with token
/usr/lib/nagios/plugins/check_hycu_vm_backup_v2.1.py \
  -l hycu.company.com \
  -a "YOUR_TOKEN" \
  -t version \
  -v

# Regenerate token in HYCU UI if needed
Administration > Users > Generate API Token
```

### Issue 3: Timeout

**Symptom:** `(Service Check Timed Out)`

**Solutions:**
```bash
# Increase timeout in command
-T 300  # 5 minutes

# Test network latency
ping hycu.company.com

# Test API response time
time curl -k -H "Authorization: Bearer TOKEN" \
  https://hycu.company.com:8443/rest/v1.0/administration/controller

# Check poller load
top
# Reduce concurrent checks if overloaded
```

### Issue 4: No Performance Data in Graphs

**Symptom:** Graphs are empty despite OK service

**Solutions:**
```bash
# Check service has "Process Performance Data" enabled
Configuration > Services > Select service
Performance Data: Yes

# Verify performance data in service output
Monitoring > Services > Select service
Check output contains: |metric=value;;;

# Check Centreon Broker
systemctl status cbd
/var/log/centreon-broker/central-broker-master.log

# Rebuild RRD databases
Monitoring > Performances > Data
Select service > Rebuild
```

### Issue 5: Macro Not Expanded

**Symptom:** Command shows `$USER10$` literally in execution

**Solutions:**
```bash
# Check resource is defined
Configuration > Pollers > Resources
Verify $USER10$ exists

# Export configuration
Configuration > Pollers > Pollers
Select poller > Export
Check: "Restart Monitoring Engine"

# Reload centengine
systemctl reload centengine

# Check effective command
cat /etc/centreon-engine/commands.cfg | grep check_hycu
```

### Issue 6: Service Always UNKNOWN

**Symptom:** Service stuck in UNKNOWN state

**Solutions:**
```bash
# Check Python syntax
python3 -m py_compile /usr/lib/nagios/plugins/check_hycu_vm_backup_v2.1.py

# Test command manually
/usr/lib/nagios/plugins/check_hycu_vm_backup_v2.1.py -l HOST -a TOKEN -t TYPE -v

# Check logs
tail -f /var/log/centreon-engine/centengine.log

# Verify command definition syntax
Configuration > Commands > Checks
Check for typos in command line
```

### Debug Mode

Enable verbose output for troubleshooting:

```bash
# Add -v flag to command temporarily
$USER1$/check_hycu_vm_backup_v2.1.py -l $HOSTADDRESS$ -a $USER10$ -t jobs -w 10 -c 20 -p 24 -v

# Check service output in Centreon UI
Monitoring > Services > Select service
View full output
```

### Support Checklist

When asking for help, provide:

1. ✅ Centreon version (`rpm -qa | grep centreon`)
2. ✅ Python version (`python3 --version`)
3. ✅ Plugin version (header of .py file)
4. ✅ Complete command with `-v` flag
5. ✅ Service output from Centreon UI
6. ✅ Relevant logs (`/var/log/centreon-engine/centengine.log`)
7. ✅ Network test results (`telnet HYCU 8443`)

---

## Quick Reference Card

### Common Commands

```bash
# Test version check
/usr/lib/nagios/plugins/check_hycu_vm_backup_v2.1.py -l HOST -a TOKEN -t version

# Test with verbose
/usr/lib/nagios/plugins/check_hycu_vm_backup_v2.1.py -l HOST -a TOKEN -t jobs -w 10 -c 20 -v

# Reload Centreon Engine
systemctl reload centengine

# Export configuration
Configuration > Pollers > Export

# View service output
Monitoring > Services > Select service
```

### Useful Paths

```
Plugin: /usr/lib/nagios/plugins/check_hycu_vm_backup_v2.1.py
Config: /etc/centreon-engine/
Logs: /var/log/centreon-engine/centengine.log
Resources: Configuration > Pollers > Resources
Commands: Configuration > Commands > Checks
Services: Configuration > Services > Services by host
```

---

## Conclusion

You now have a complete Centreon integration for HYCU monitoring!

**Next Steps:**
1. Create your first HYCU host
2. Add global services (license, jobs, port)
3. Configure graphs
4. Test notifications
5. Add VM-specific services as needed

**For more help:**
- [Main README](README.md)
- [Installation Guide](HOWTO.md)
- [GitHub Issues](https://github.com/YOUR_USERNAME/hycu-monitoring-plugin/issues)

---

**Happy Monitoring with Centreon! 🎨📊**
