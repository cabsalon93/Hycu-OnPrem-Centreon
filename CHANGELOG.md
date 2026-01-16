# Changelog

All notable changes to the HYCU Monitoring Plugin will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.1.0] - 2026-01-16

### Added
- **New Check Types:**
  - `license` - Monitor license expiration with configurable thresholds
  - `version` - Get HYCU version information (informational check)
  - `backup-validation` - Monitor backup validation jobs over time periods
  - `shares` - Monitor NFS/SMB file shares compliance
  - `buckets` - Monitor S3 object storage buckets compliance
  - `port` - TCP connectivity testing (no API token required)
  - `unassigned` - Audit objects without policy assignment

### Changed
- Updated total check types from 8 to **16**
- Improved validation of thresholds with centralized function
- Enhanced error messages with categorized check types display
- Optimized help text with grouped check types by category
- Port check now uses `-n` parameter instead of `-p` for clarity
- Harmonized code structure with API field constants
- Improved documentation and examples

### Fixed
- Corrected `shares` and `buckets` filtering by protocol type (NFS/SMB vs S3)
- Fixed `unassigned` check to use `protectionGroupName` field correctly
- Fixed field names for applications (`name`) and volume groups (`name`)
- Removed duplicate and repetitive validation code (reduced by 30 lines)

### Technical Improvements
- Added `validate_thresholds()` function for consistent validation
- Added API field constants (FIELD_PROTECTION_GROUP_NAME, etc.)
- Added CHECK_TYPES dictionary for organized type categorization
- Inverted threshold logic for license checks (critical < warning)
- Better separation of concerns in validation logic

## [2.0.0] - 2025-XX-XX

### Added
- `policy-advanced` check with detailed object counting and thresholds
- `jobs` check for monitoring jobs statistics over time periods
- `manager` check for global dashboard (protected/compliance)
- Configurable thresholds (`-w` and `-c` parameters)
- Period-based monitoring (`-p` parameter)
- Verbose debugging mode (`-v`)

### Changed
- Major code refactoring for better maintainability
- Improved error handling with custom HycuAPIError exception
- Better API response parsing
- Case-insensitive policy name search

### Fixed
- Target health check (incorrect API structure handling)
- Archive logic (fixed if/elif conditions)
- HTTP error handling (better status code management)
- Windows compatibility issues

## [1.x] - Previous Versions

### Initial Features
- `vm` - VM backup status check
- `vmid` - VM backup status by UUID
- `target` - Target health monitoring
- `archive` - Archive status check
- `policy` - Simple policy compliance
- Basic REST API integration
- Centreon/Nagios compatibility
- Performance data output

---

## Version Comparison

| Version | Check Types | Key Features |
|---------|-------------|--------------|
| 1.x | 5 | Basic monitoring (vm, target, archive, policy) |
| 2.0 | 8 | Added policy-advanced, jobs, manager with thresholds |
| 2.1 | **16** | Added license, version, validation, storage, network, audit |

---

## Upgrade Notes

### From 2.0 to 2.1

**Breaking Changes:** None - 100% backward compatible

**New Features Available:**
1. License expiration monitoring
2. Version tracking
3. Backup validation monitoring
4. Shares and buckets monitoring
5. TCP port connectivity testing
6. Unassigned objects audit

**Migration Steps:**
1. Replace script file with v2.1
2. Test existing checks (should work identically)
3. Add new check types as needed
4. Update Centreon service templates
5. Create new graphs for new metrics

### From 1.x to 2.0+

**Breaking Changes:**
- Command-line syntax unchanged but more options available
- Output format unchanged (still Nagios-compatible)

**Major Improvements:**
- Configurable thresholds for alerting
- Time-based monitoring (jobs over periods)
- Better error messages
- Verbose debugging mode

---

## Planned Features (Future Versions)

### v2.2 (Planned)
- [ ] Capacity monitoring for targets (usage tracking)
- [ ] Performance metrics (throughput, job duration)
- [ ] Restore jobs monitoring
- [ ] Copy jobs monitoring
- [ ] Batch mode for multiple checks in one call
- [ ] JSON/XML export format option
- [ ] Response caching for performance
- [ ] Multi-threading support for faster checks

### v3.0 (Roadmap)
- [ ] Full SSL certificate validation support
- [ ] HYCU Cloud integration
- [ ] Webhook notifications
- [ ] Email alerting built-in
- [ ] Configuration file support (YAML/JSON)
- [ ] Plugin manager for easy updates
- [ ] Web dashboard for monitoring

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to contribute to this project.

---

## Support

- **Issues:** https://github.com/YOUR_USERNAME/hycu-monitoring-plugin/issues
- **Documentation:** https://github.com/YOUR_USERNAME/hycu-monitoring-plugin/wiki
- **Discussions:** https://github.com/YOUR_USERNAME/hycu-monitoring-plugin/discussions
