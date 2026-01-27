# 📘 HYCU Monitoring Plugin - Complete Installation and Configuration Guide

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [HYCU API Token Generation](#hycu-api-token-generation)
4. [Basic Configuration](#basic-configuration)
5. [Testing the Plugin](#testing-the-plugin)
6. [Centreon Integration](#centreon-integration)
7. [Advanced Configuration](#advanced-configuration)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements

- **Operating System:** Linux (RHEL, CentOS, Debian, Ubuntu) or Windows
- **Python:** Version 3.7 or higher
- **Network:** Access to HYCU controller on port 8443 (HTTPS)
- **Permissions:** Ability to execute Python scripts

### Python Packages

The plugin uses only standard Python libraries:
- `requests` (usually pre-installed)
- `json`, `sys`, `socket`, `datetime`, `optparse`, `urllib3`

If `requests` is missing:

```bash
# RHEL/CentOS
sudo yum install python3-requests

# Debian/Ubuntu
sudo apt-get install python3-requests

# pip
pip3 install requests
```

### HYCU Requirements

- **Version:** HYCU 4.9+ or 5.x
- **API Access:** REST API enabled (default)
- **User Permissions:** Read-only access is sufficient

---

## Installation

### Method 1: Direct Download (Recommended)

```bash
# Download the script
wget https://raw.githubusercontent.com/YOUR_USERNAME/hycu-monitoring-plugin/main/check_hycu_vm_backup_v2.1.py

# Make executable
chmod +x check_hycu_vm_backup_v2.1.py

# Move to plugin directory (Centreon/Nagios)
sudo mv check_hycu_vm_backup_v2.1.py /usr/lib/nagios/plugins/
```

### Method 2: Git Clone

```bash
# Clone repository
git clone https://github.com/YOUR_USERNAME/hycu-monitoring-plugin.git

# Navigate to directory
cd hycu-monitoring-plugin

# Make executable
chmod +x check_hycu_vm_backup_v2.1.py

# Copy plugin (Centreon/Nagios)
cp -p $(pwd)/check_hycu_vm_backup_v2.1.py /usr/lib/nagios/plugins/
```

### Method 3: Manual Copy

1. Download `check_hycu_vm_backup_v2.1.py` from GitHub
2. Copy to your monitoring server
3. Place in `/usr/lib/nagios/plugins/` or equivalent
4. Set execute permissions: `chmod +x check_hycu_vm_backup_v2.1.py`

### Verify Installation

```bash
# Check Python version
python3 --version
# Expected: Python 3.7.x or higher

# Test plugin help
python3 /usr/lib/nagios/plugins/check_hycu_vm_backup_v2.1.py -h

# Verify script is executable
ls -l /usr/lib/nagios/plugins/check_hycu_vm_backup_v2.1.py
# Expected: -rwxr-xr-x (executable)
```

---

## HYCU API Token Generation

### Step 1: Access HYCU Web Interface

1. Open browser: `https://your-hycu-host:8443`
2. Log in with administrator credentials

### Step 2: Navigate to User Management

1. Click **Administration** (gear icon)
2. Select **Users** from left menu
3. Find or create a monitoring user

### Step 3: Generate Token

1. Select the user (e.g., `monitoring`)
2. Click **Generate API Token** button
3. Copy the token immediately (it's shown only once)
4. Save securely (e.g., password manager)

**Token Format Example:**
```
cjd0NnEybGRwMDYwdjYyaWZ1bzV0aXBkN3ZlZA==
```

### Step 4: Test Token

```bash
# Test with version check (no specific permissions needed)
python3 check_hycu_vm_backup_v2.1.py \
  -l your-hycu-host.com \
  -a "YOUR_TOKEN_HERE" \
  -t version

# Expected output:
# OK: HYCU Controller 'hycu-prod' - Version 5.2.0 (Build 12345), Hypervisor: KVM
```

### Security Best Practices

✅ **Create dedicated monitoring user** - Don't use admin account  
✅ **Read-only permissions** - Monitoring doesn't need write access  
✅ **Token rotation** - Regenerate tokens every 90 days  
✅ **Secure storage** - Use Centreon resource macros or vault  
✅ **Audit logs** - Review API access regularly  

---

## Basic Configuration

### Configuration File Setup

Create a configuration file for easy testing:

```bash
# Create .env file
cat > ~/.hycu_monitoring.env << 'EOF'
HYCU_HOST=hycu.company.com
HYCU_TOKEN=cjd0NnEybGRwMDYwdjYyaWZ1bzV0aXBkN93270==
EOF

# Secure the file
chmod 600 ~/.hycu_monitoring.env

# Load in shell
source ~/.hycu_monitoring.env
```

### Test All Check Types

```bash
# Source config
source ~/.hycu_monitoring.env

# Test basic checks
echo "Testing version..."
python3 check_hycu_vm_backup_v2.1.py -l $HYCU_HOST -a $HYCU_TOKEN -t version

echo "Testing port..."
python3 check_hycu_vm_backup_v2.1.py -l $HYCU_HOST -t port -n 8443

echo "Testing license..."
python3 check_hycu_vm_backup_v2.1.py -l $HYCU_HOST -a $HYCU_TOKEN -t license -w 30 -c 7

echo "Testing jobs..."
python3 check_hycu_vm_backup_v2.1.py -l $HYCU_HOST -a $HYCU_TOKEN -t jobs -w 5 -c 10

echo "Testing unassigned..."
python3 check_hycu_vm_backup_v2.1.py -l $HYCU_HOST -a $HYCU_TOKEN -t unassigned -w 5 -c 10
```

---

## Testing the Plugin

### Test Script

Create a comprehensive test script:

```bash
#!/bin/bash
# test_all_checks.sh

# Configuration
HYCU_HOST="hycu.company.com"
HYCU_TOKEN="YOUR_TOKEN"
PLUGIN="/usr/lib/nagios/plugins/check_hycu_vm_backup_v2.1.py"

echo "========================================="
echo "HYCU Monitoring Plugin - Test Suite"
echo "========================================="
echo ""

# Test 1: Version (always works)
echo "[1/10] Testing version check..."
python3 $PLUGIN -l $HYCU_HOST -a $HYCU_TOKEN -t version
echo ""

# Test 2: Port connectivity
echo "[2/10] Testing port check..."
python3 $PLUGIN -l $HYCU_HOST -t port -n 8443
echo ""

# Test 3: License status
echo "[3/10] Testing license check..."
python3 $PLUGIN -l $HYCU_HOST -a $HYCU_TOKEN -t license -w 30 -c 7
echo ""

# Test 4: Jobs statistics
echo "[4/10] Testing jobs check..."
python3 $PLUGIN -l $HYCU_HOST -a $HYCU_TOKEN -t jobs -w 5 -c 10 -p 24
echo ""

# Test 5: Unassigned objects
echo "[5/10] Testing unassigned check..."
python3 $PLUGIN -l $HYCU_HOST -a $HYCU_TOKEN -t unassigned -w 5 -c 10
echo ""

# Test 6: Shares monitoring
echo "[6/10] Testing shares check..."
python3 $PLUGIN -l $HYCU_HOST -a $HYCU_TOKEN -t shares -w 3 -c 5
echo ""

# Test 7: Buckets monitoring
echo "[7/10] Testing buckets check..."
python3 $PLUGIN -l $HYCU_HOST -a $HYCU_TOKEN -t buckets -w 2 -c 5
echo ""

# Test 8: Manager dashboard
echo "[8/10] Testing manager check..."
python3 $PLUGIN -l $HYCU_HOST -a $HYCU_TOKEN -n protected -t manager
echo ""

# Test 9: Backup validation
echo "[9/10] Testing backup-validation check..."
python3 $PLUGIN -l $HYCU_HOST -a $HYCU_TOKEN -t backup-validation -w 5 -c 10 -p 24
echo ""

# Test 10: VM check (requires VM name)
echo "[10/10] Testing VM check (enter VM name or press Enter to skip)..."
read -p "VM Name: " VM_NAME
if [ -n "$VM_NAME" ]; then
    python3 $PLUGIN -l $HYCU_HOST -a $HYCU_TOKEN -n "$VM_NAME" -t vm
else
    echo "Skipped"
fi
echo ""

echo "========================================="
echo "Test Suite Complete"
echo "========================================="
```

Save as `test_all_checks.sh`, make executable, and run:

```bash
chmod +x test_all_checks.sh
./test_all_checks.sh
```

---

## Centreon Integration

### Step 1: Add Plugin to Centreon

```bash
# SSH to Centreon server
ssh root@centreon-server

# Copy plugin
scp check_hycu_vm_backup_v2.1.py root@centreon-server:/usr/lib/nagios/plugins/

# Set permissions
chmod +x /usr/lib/nagios/plugins/check_hycu_vm_backup_v2.1.py
chown centreon-engine:centreon-engine /usr/lib/nagios/plugins/check_hycu_vm_backup_v2.1.py
```

### Step 2: Store API Token Securely

**Method A: Resource Macro (Recommended)**

1. In Centreon Web UI: **Configuration** > **Centreon** > **Resources**
2. Add new resource:
   - Name: `$USER10$`
   - Value: `YOUR_HYCU_API_TOKEN`
   - Comment: `HYCU API Token`
3. Click **Save**

**Method B: Custom Macro on Host**

1. Go to **Configuration** > **Hosts**
2. Select HYCU host
3. Go to **Custom Macros** tab
4. Add:
   - Name: `$_HOSTHYCUTOKEN$`
   - Value: `YOUR_TOKEN`
   - Password: ✓ (checked)
5. Click **Save**

### Step 3: Create Commands

Go to **Configuration** > **Commands** > **Checks**

#### Command 1: check_hycu_vm

```
Name: check_hycu_vm
Type: Check
Command Line:
$USER1$/check_hycu_vm_backup_v2.1.py -l $HOSTADDRESS$ -a $USER10$ -n "$ARG1$" -t vm
```

#### Command 2: check_hycu_jobs

```
Name: check_hycu_jobs
Type: Check
Command Line:
$USER1$/check_hycu_vm_backup_v2.1.py -l $HOSTADDRESS$ -a $USER10$ -t jobs -w $ARG1$ -c $ARG2$ -p $ARG3$
```

#### Command 3: check_hycu_license

```
Name: check_hycu_license
Type: Check
Command Line:
$USER1$/check_hycu_vm_backup_v2.1.py -l $HOSTADDRESS$ -a $USER10$ -t license -w $ARG1$ -c $ARG2$
```

#### Command 4: check_hycu_unassigned

```
Name: check_hycu_unassigned
Type: Check
Command Line:
$USER1$/check_hycu_vm_backup_v2.1.py -l $HOSTADDRESS$ -a $USER10$ -t unassigned -w $ARG1$ -c $ARG2$
```

#### Command 5: check_hycu_port

```
Name: check_hycu_port
Type: Check
Command Line:
$USER1$/check_hycu_vm_backup_v2.1.py -l $HOSTADDRESS$ -t port -n $ARG1$
```

### Step 4: Create Service Templates

#### Template: HYCU-License-Expiration

```
Name: HYCU-License-Expiration
Check Command: check_hycu_license
Args: !30!7
Check Period: 24x7
Max Check Attempts: 3
Check Interval: 1440 (once per day)
Retry Interval: 60
```

#### Template: HYCU-Jobs-24h

```
Name: HYCU-Jobs-24h
Check Command: check_hycu_jobs
Args: !10!20!24
Check Period: 24x7
Max Check Attempts: 3
Check Interval: 15
Retry Interval: 5
```

#### Template: HYCU-Unassigned-Objects

```
Name: HYCU-Unassigned-Objects
Check Command: check_hycu_unassigned
Args: !5!10
Check Period: 24x7
Max Check Attempts: 3
Check Interval: 60
Retry Interval: 15
```

### Step 5: Create Host

1. **Configuration** > **Hosts** > **Add**
2. Fill in:
   - Name: `HYCU-PROD`
   - Alias: `HYCU Production Controller`
   - IP Address: `192.168.1.100` (or FQDN)
   - Templates: `generic-host`
   - Host Groups: `HYCU-Controllers`
3. **Save**

### Step 6: Add Services

1. **Configuration** > **Services** > **By host**
2. Select host: `HYCU-PROD`
3. Add services:

| Service | Template | Args |
|---------|----------|------|
| HYCU-License | HYCU-License-Expiration | Default |
| HYCU-Jobs-24h | HYCU-Jobs-24h | Default |
| HYCU-Unassigned | HYCU-Unassigned-Objects | Default |
| HYCU-Port-8443 | HYCU-Port-Check | !8443 |

### Step 7: Deploy Configuration

1. **Configuration** > **Pollers**
2. Select poller
3. Click **Export Configuration**
4. Check all options
5. Click **Export**
6. Verify services appear in **Monitoring** > **Services**

### Step 8: Create Graphs

1. **Monitoring** > **Performances** > **Graphs**
2. For each service, configure:

**License Graph:**
- Metric: `days_left`
- Warning: 30
- Critical: 7

**Jobs Graph:**
- Metrics: `jobs_ok`, `jobs_failed`, `success_rate`
- Stack: No

**Unassigned Graph:**
- Metrics: `unassigned_total`, `unassigned_vms`, `unassigned_shares`
- Stack: Yes

---

## Advanced Configuration

### Custom Thresholds by Environment

```bash
# Production (low tolerance)
python3 check_hycu_vm_backup_v2.1.py -l hycu-prod -a $TOKEN -t jobs -w 5 -c 10

# Development (high tolerance)
python3 check_hycu_vm_backup_v2.1.py -l hycu-dev -a $TOKEN -t jobs -w 20 -c 50

# DR Site (medium tolerance)
python3 check_hycu_vm_backup_v2.1.py -l hycu-dr -a $TOKEN -t jobs -w 10 -c 25
```

### Scheduled Tasks (Cron)

For standalone monitoring without Centreon:

```bash
# Edit crontab
crontab -e

# Add checks
# Check license daily at 8am
0 8 * * * /usr/lib/nagios/plugins/check_hycu_vm_backup_v2.1.py -l hycu.local -a TOKEN -t license -w 30 -c 7 | mail -s "HYCU License" admin@company.com

# Check jobs every hour
0 * * * * /usr/lib/nagios/plugins/check_hycu_vm_backup_v2.1.py -l hycu.local -a TOKEN -t jobs -w 10 -c 20 >> /var/log/hycu-checks.log
```

### Multiple HYCU Controllers

```bash
# Create wrapper script
cat > /usr/local/bin/check_all_hycu.sh << 'EOF'
#!/bin/bash
CONTROLLERS=("hycu-site1.local" "hycu-site2.local" "hycu-dr.local")
TOKEN="YOUR_TOKEN"

for controller in "${CONTROLLERS[@]}"; do
    echo "Checking $controller..."
    /usr/lib/nagios/plugins/check_hycu_vm_backup_v2.1.py \
        -l $controller \
        -a $TOKEN \
        -t version
done
EOF

chmod +x /usr/local/bin/check_all_hycu.sh
```

---

## Troubleshooting

### Common Issues and Solutions

#### Issue 1: Authentication Failed

**Error:** `CRITICAL: API Error - Authentication failed. Check your API token.`

**Solutions:**
1. Verify token is correct (no extra spaces)
2. Check token hasn't expired
3. Regenerate token in HYCU UI
4. Verify user has API access permissions

**Test:**
```bash
# Verbose mode shows HTTP status
python3 check_hycu_vm_backup_v2.1.py -l HOST -a TOKEN -t version -v
```

#### Issue 2: Connection Timeout

**Error:** `CRITICAL: Connection error: ...timeout...`

**Solutions:**
1. Check network connectivity: `ping hycu-host`
2. Verify port 8443 is open: `telnet hycu-host 8443`
3. Check firewall rules
4. Increase timeout: `-T 300`

**Test:**
```bash
# Test port separately
python3 check_hycu_vm_backup_v2.1.py -l HOST -t port -n 8443 -v
```

#### Issue 3: Object Not Found

**Error:** `CRITICAL: VM 'VM-NAME' does not exist or is not discoverable`

**Solutions:**
1. Verify object name (case-sensitive)
2. Check object exists in HYCU UI
3. Use UUID instead: `-t vmid -n "UUID"`
4. Use verbose mode to see available objects

**Test:**
```bash
# List all VMs (use manager check)
python3 check_hycu_vm_backup_v2.1.py -l HOST -a TOKEN -n protected -t manager -v
```

#### Issue 4: SSL Certificate Errors

**Error:** `SSL: CERTIFICATE_VERIFY_FAILED`

**Note:** Plugin disables SSL verification by default. If error persists:

```python
# In script, verify this line exists:
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
```

#### Issue 5: Python Not Found

**Error:** `python3: command not found`

**Solutions:**
```bash
# Find Python
which python3
# or
which python

# Create alias if needed
alias python3=/usr/bin/python3.7

# Or use full path
/usr/bin/python3.7 check_hycu_vm_backup_v2.1.py ...
```

### Debug Checklist

When troubleshooting, run through this checklist:

```bash
# 1. Check Python version
python3 --version

# 2. Check script exists and is executable
ls -l /usr/lib/nagios/plugins/check_hycu_vm_backup_v2.1.py

# 3. Test help (verifies script runs)
python3 check_hycu_vm_backup_v2.1.py -h

# 4. Test port connectivity (no API needed)
python3 check_hycu_vm_backup_v2.1.py -l HOST -t port -n 8443 -v

# 5. Test version (minimal API call)
python3 check_hycu_vm_backup_v2.1.py -l HOST -a TOKEN -t version -v

# 6. Test specific check with verbose
python3 check_hycu_vm_backup_v2.1.py -l HOST -a TOKEN -t TYPE -v
```

### Getting Help

If issues persist:

1. **Run with verbose:** `-v` flag shows detailed debug info
2. **Check logs:** `/var/log/centreon-engine/centengine.log`
3. **Test manually:** Run from command line before adding to Centreon
4. **GitHub Issues:** https://github.com/YOUR_USERNAME/hycu-monitoring-plugin/issues
5. **HYCU Support:** Verify API is functioning in HYCU UI

---

## Next Steps

After successful installation:

1. ✅ Review [README.md](README.md) for all check types
2. ✅ Create Centreon dashboards with graphs
3. ✅ Set up alerting (email, Slack, etc.)
4. ✅ Document your configuration
5. ✅ Train team on new monitoring

---

**Installation Complete! 🎉**

Your HYCU monitoring is now ready for production use.
