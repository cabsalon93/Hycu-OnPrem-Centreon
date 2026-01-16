# 🛡️ HYCU Monitoring Plugin for Centreon/Nagios

[![Python Version](https://img.shields.io/badge/python-3.7%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![HYCU Compatible](https://img.shields.io/badge/HYCU-4.9%2B%20%7C%205.x-purple)](https://www.hycu.com/)
[![Version](https://img.shields.io/badge/version-2.1-orange)](CHANGELOG.md)

Professional monitoring plugin for HYCU backup infrastructure. Monitor VMs, policies, jobs, licenses, storage, and more through HYCU REST API.

## 📋 Table of Contents

- [Features](#-features)
- [Quick Start](#-quick-start)
- [Installation](#-installation)
- [Usage](#-usage)
- [Check Types](#-check-types)
- [Examples](#-examples)
- [Centreon Integration](#-centreon-integration)
- [Contributing](#-contributing)
- [License](#-license)

## ✨ Features

### 16 Check Types Available

| Category | Types | Description |
|----------|-------|-------------|
| **OBJECTS** | vm, vmid, target, archive | Individual object monitoring |
| **POLICIES** | policy, policy-advanced | Policy compliance with thresholds |
| **GLOBAL** | manager, jobs, license, version | Global infrastructure monitoring |
| **STORAGE** | shares, buckets | NFS/SMB shares and S3 buckets |
| **VALIDATION** | backup-validation, unassigned | Validation jobs and compliance audits |
| **NETWORK** | port | TCP connectivity tests |

### Key Features

✅ **16 monitoring check types** - Complete HYCU infrastructure coverage  
✅ **Centreon/Nagios compatible** - Standard exit codes and performance data  
✅ **Configurable thresholds** - Warning and critical levels with `-w` and `-c`  
✅ **Time-based monitoring** - Jobs and validation checks over custom periods  
✅ **Detailed performance metrics** - 60+ metrics for Centreon graphing  
✅ **Verbose debugging mode** - `-v` flag for troubleshooting  
✅ **No dependencies** - Pure Python with standard libraries  
✅ **SSL verification disabled** - Works with self-signed certificates  

## 🚀 Quick Start

### Prerequisites

- Python 3.7 or higher
- HYCU 4.9+ or 5.x
- HYCU API token
- Network access to HYCU controller (port 8443)

### Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/hycu-monitoring-plugin.git
cd hycu-monitoring-plugin

# Make the script executable
chmod +x check_hycu_vm_backup_v2.1.py

# Test the connection
python3 check_hycu_vm_backup_v2.1.py -l your-hycu-host.com -a YOUR_TOKEN -t version
```

### Generate API Token

1. Log in to HYCU web interface
2. Go to **Administration** > **Users**
3. Select your user > **Generate API Token**
4. Copy the token (starts with base64 encoded string)

## 📖 Usage

### Basic Syntax

```bash
python3 check_hycu_vm_backup_v2.1.py -l <host> -a <token> -t <type> [options]
```

### Common Options

| Option | Description | Required |
|--------|-------------|----------|
| `-l, --host` | HYCU host IP or FQDN | Yes |
| `-a, --token` | HYCU API token | Most types |
| `-t, --type` | Check type (see below) | Yes |
| `-n, --name` | Object name | Some types |
| `-w, --warning` | Warning threshold | Optional |
| `-c, --critical` | Critical threshold | Optional |
| `-p, --period` | Time period in hours | Optional |
| `-T, --timeout` | API timeout in seconds | Optional |
| `-v, --verbose` | Enable debug output | Optional |

## 🔍 Check Types

### OBJECTS - Individual Object Monitoring

#### 1. VM Backup Status (`vm`)
```bash
python3 check_hycu_vm_backup_v2.1.py -l HOST -a TOKEN -n "VM-NAME" -t vm
```
**Output:** `OK: VM-NAME is OK for last FULL |backup_status=2;;;`

#### 2. VM Backup by UUID (`vmid`)
```bash
python3 check_hycu_vm_backup_v2.1.py -l HOST -a TOKEN -n "VM-UUID" -t vmid
```
**Use case:** When VM name is not unique

#### 3. Target Health (`target`)
```bash
python3 check_hycu_vm_backup_v2.1.py -l HOST -a TOKEN -n "TARGET-NAME" -t target
```
**Output:** `OK: 01_NFS_Shared is GREEN |target_health=2;;;`

#### 4. Archive Status (`archive`)
```bash
python3 check_hycu_vm_backup_v2.1.py -l HOST -a TOKEN -n "VM-NAME" -t archive
```
**Output:** `OK: VM-NAME archive is OK for last FULL |archive_status=2;;; archives_ok=2;;; archives_failed=0;;;`

### POLICIES - Policy Compliance

#### 5. Policy Compliance Simple (`policy`)
```bash
python3 check_hycu_vm_backup_v2.1.py -l HOST -a TOKEN -n "POLICY-NAME" -t policy
```
**Output:** `OK: Bronze is GREEN including 36 VMs |policy_status=2;;; compliant_vms=36;;;`

#### 6. Policy Compliance Advanced (`policy-advanced`)
```bash
python3 check_hycu_vm_backup_v2.1.py -l HOST -a TOKEN -n "POLICY-NAME" -t policy-advanced -w 5 -c 10
```
**Output:** `OK: Policy 'Bronze' - 50/51 objects compliant (36/37 VMs, 6/7 shares, 7/7 apps, 1/1 buckets, 0/0 VGs) |...`
**Features:** Detailed breakdown by object type, configurable thresholds

### GLOBAL - Infrastructure Monitoring

#### 7. Manager Dashboard (`manager`)
```bash
# Check protected VMs
python3 check_hycu_vm_backup_v2.1.py -l HOST -a TOKEN -n "protected" -t manager

# Check compliance
python3 check_hycu_vm_backup_v2.1.py -l HOST -a TOKEN -n "compliance" -t manager
```
**Output:** `OK: 0 VMs not protected out of 150 total |vms_unprotected=0;;; vms_protected=150;;; vms_total=150;;;`

#### 8. Jobs Statistics (`jobs`)
```bash
python3 check_hycu_vm_backup_v2.1.py -l HOST -a TOKEN -t jobs -w 10 -c 20 -p 24
```
**Output:** `OK: HYCU jobs over 24h - 5 failed (4 errors, 1 warnings), 95 successful, 2 running |...`
**Parameters:**
- `-w` : Warning threshold (failed jobs)
- `-c` : Critical threshold (failed jobs)
- `-p` : Period in hours (1-168)

#### 9. License Status (`license`)
```bash
python3 check_hycu_vm_backup_v2.1.py -l HOST -a TOKEN -t license -w 30 -c 7
```
**Output:** `WARNING: License 'Company' - 15 days left (expires 2026-01-31), Status: ACTIVE, VMs: 50/100, Sockets: 4/8 |...`
**Note:** Thresholds are inverted (critical < warning) for days before expiration

#### 10. Version Information (`version`)
```bash
python3 check_hycu_vm_backup_v2.1.py -l HOST -a TOKEN -t version
```
**Output:** `OK: HYCU Controller 'hycu-demo05' - Version 5.2.0 (Build 12345), Hypervisor: KVM`
**Use case:** Inventory, documentation, always returns OK

### STORAGE - Shares and Buckets

#### 11. Shares Monitoring (`shares`)
```bash
python3 check_hycu_vm_backup_v2.1.py -l HOST -a TOKEN -t shares -w 3 -c 5
```
**Output:** `OK: Shares (NFS/SMB) - 6/7 compliant, 1 non-compliant, 0 unprotected |...`
**Monitors:** NFS and SMB file shares

#### 12. Buckets Monitoring (`buckets`)
```bash
python3 check_hycu_vm_backup_v2.1.py -l HOST -a TOKEN -t buckets -w 2 -c 5
```
**Output:** `OK: Buckets (S3) - 1/1 compliant, 0 non-compliant, 0 unprotected |...`
**Monitors:** S3 object storage buckets

### VALIDATION - Compliance and Audits

#### 13. Backup Validation (`backup-validation`)
```bash
python3 check_hycu_vm_backup_v2.1.py -l HOST -a TOKEN -t backup-validation -w 5 -c 10 -p 24
```
**Output:** `CRITICAL: Backup validations over 24h - 12 failed (10 errors, 2 warnings), 45 successful |...`
**Use case:** Verify backup integrity and restorability

#### 14. Unassigned Objects (`unassigned`)
```bash
python3 check_hycu_vm_backup_v2.1.py -l HOST -a TOKEN -t unassigned -w 5 -c 10
```
**Output:** `WARNING: 7 unassigned objects - 3 VMs, 2 shares, 0 buckets, 1 apps, 1 VGs | VMs: VM-TEST-01, VM-TEST-02, VM-DEMO-03 / ...`
**Use case:** Audit objects without policy assignment

### NETWORK - Connectivity Tests

#### 15. Port Connectivity (`port`)
```bash
# Default port (8443)
python3 check_hycu_vm_backup_v2.1.py -l HOST -t port

# Custom port
python3 check_hycu_vm_backup_v2.1.py -l HOST -t port -n 22
```
**Output:** `OK: Port 8443 is OPEN on demo05.hycu.com (response time: 15ms) |response_time=15ms;;;0;`
**Note:** No API token required

## 📚 Examples

### Production Examples

```bash
# Monitor critical production VM
python3 check_hycu_vm_backup_v2.1.py -l hycu.prod.company.com -a "TOKEN" -n "PROD-DB-01" -t vm

# Check production policy with low tolerance
python3 check_hycu_vm_backup_v2.1.py -l hycu.prod.company.com -a "TOKEN" -n "Production" -t policy-advanced -w 1 -c 3

# Monitor jobs with high volume tolerance
python3 check_hycu_vm_backup_v2.1.py -l hycu.prod.company.com -a "TOKEN" -t jobs -w 20 -c 50 -p 24

# Alert 30 days before license expiration
python3 check_hycu_vm_backup_v2.1.py -l hycu.prod.company.com -a "TOKEN" -t license -w 30 -c 7

# Daily audit of unassigned objects
python3 check_hycu_vm_backup_v2.1.py -l hycu.prod.company.com -a "TOKEN" -t unassigned -w 5 -c 10
```

### Debugging

```bash
# Verbose mode for troubleshooting
python3 check_hycu_vm_backup_v2.1.py -l HOST -a TOKEN -n "VM-NAME" -t vm -v

# Test API connectivity
python3 check_hycu_vm_backup_v2.1.py -l HOST -a TOKEN -t version -v

# Test port without credentials
python3 check_hycu_vm_backup_v2.1.py -l HOST -t port -n 8443 -v
```

## 🎨 Centreon Integration

### Service Templates

Create service templates in Centreon for each check type. Example for license monitoring:

**Template Name:** `HYCU-License-Expiration`

**Check Command:**
```
$USER1$/check_hycu_vm_backup_v2.1.py -l $HOSTADDRESS$ -a $USER2$ -t license -w $ARG1$ -c $ARG2$
```

**Macros:**
- `$USER2$` = HYCU API Token (stored securely in resource)
- `$ARG1$` = Warning days (default: 30)
- `$ARG2$` = Critical days (default: 7)

### Example Service Configuration

```ini
[Service: HYCU License]
check_command=check_hycu_license!30!7
check_interval=1440  # Once per day
retry_interval=60
max_check_attempts=3
```

See [CENTREON_HOWTO.md](CENTREON_HOWTO.md) for complete integration guide.

## 📊 Performance Data

All checks return performance data in Nagios format:

```
|metric=value;warning;critical;min;max
```

**Example metrics:**
- `jobs_ok`, `jobs_failed`, `success_rate`
- `days_left`, `vms_protected`, `sockets_actual`
- `shares_compliant`, `buckets_non_compliant`
- `unassigned_total`, `response_time`

Use these metrics to create graphs in Centreon/Nagios for trend analysis.

## 🔒 Security Best Practices

1. **Store API tokens securely** - Use Centreon resource macros or environment variables
2. **Limit token permissions** - Create dedicated monitoring user with read-only access
3. **Network segmentation** - Restrict access to HYCU API port (8443)
4. **Token rotation** - Regularly regenerate API tokens
5. **Audit logs** - Monitor API access in HYCU logs

## 🐛 Troubleshooting

### Common Issues

**Issue:** `Authentication failed`  
**Solution:** Verify API token is correct and not expired

**Issue:** `Connection timeout`  
**Solution:** Check network connectivity and firewall rules (port 8443)

**Issue:** `Object does not exist`  
**Solution:** Verify object name (case-sensitive), use `-v` for debugging

**Issue:** `Invalid type`  
**Solution:** Run with `-h` to see all valid check types

### Debug Mode

Always use `-v` flag when troubleshooting:

```bash
python3 check_hycu_vm_backup_v2.1.py -l HOST -a TOKEN -t TYPE -v
```

This shows:
- API endpoints called
- HTTP status codes
- Response summaries
- Processing steps

## 📈 Roadmap

### Planned Features (v2.2)

- [ ] Capacity monitoring for targets
- [ ] Performance metrics (throughput, duration)
- [ ] Restore jobs monitoring
- [ ] Copy jobs monitoring
- [ ] Batch mode for multiple checks
- [ ] JSON/XML export format
- [ ] API response caching
- [ ] Multi-threading support

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup

```bash
# Clone repo
git clone https://github.com/YOUR_USERNAME/hycu-monitoring-plugin.git
cd hycu-monitoring-plugin

# Create test environment
cp .env.template .env
# Edit .env with your test credentials

# Run tests
python3 test_hycu_checks.py
```

## 📝 Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Credits

- **Original Author:** christophe.Absalon@hycu.com
- **Policy Compliance:** jeremie.hugo@ansam.ch
- **v2.0-2.1 Enhancements:** Major improvements and new features

## 📞 Support

- **Issues:** [GitHub Issues](https://github.com/YOUR_USERNAME/hycu-monitoring-plugin/issues)
- **Documentation:** [Wiki](https://github.com/YOUR_USERNAME/hycu-monitoring-plugin/wiki)
- **HYCU API Docs:** https://docs.hycu.com

---

**Made with ❤️ for the HYCU Community**
