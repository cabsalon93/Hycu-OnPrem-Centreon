#!/usr/bin/env python3
######################################
## HYCU script to check backup status using HYCU REST API
## Version 2.1 - Complete monitoring suite with 16 check types
## Original author: christophe.Absalon@hycu.com
## Policy compliance check: jeremie.hugo@ansam.ch
## Major improvements and new features: 2025-2026
##
## Compatible with: Centreon, Nagios, Icinga, and other monitoring tools
## Tested with: Python 3.7+ on HYCU 4.9+, 5.x
##
## Version 2.1 Changes:
## - Added: license check (expiration monitoring)
## - Added: version check (informational)
## - Added: backup-validation check (validation jobs monitoring)
## - Added: shares check (NAS/file shares monitoring)
## - Added: buckets check (object storage monitoring)
## - Added: port check (TCP connectivity)
## - Added: unassigned check (objects without policy)
## - Total: 16 check types available
##
## Usage examples:
##   python3 check_hycu_vm_backup_v2.1.py -a "TOKEN" -l 192.168.1.100 -n VM-NAME -t vm
##   python3 check_hycu_vm_backup_v2.1.py -a "TOKEN" -l 192.168.1.100 -n TARGET-NAME -t target
##   python3 check_hycu_vm_backup_v2.1.py -a "TOKEN" -l 192.168.1.100 -n POLICY-NAME -t policy-advanced -w 5 -c 10
##   python3 check_hycu_vm_backup_v2.1.py -a "TOKEN" -l 192.168.1.100 -t jobs -w 5 -c 10 -p 24
##   python3 check_hycu_vm_backup_v2.1.py -a "TOKEN" -l 192.168.1.100 -t license -w 30 -c 7
##   python3 check_hycu_vm_backup_v2.1.py -a "TOKEN" -l 192.168.1.100 -t version
##   python3 check_hycu_vm_backup_v2.1.py -a "TOKEN" -l 192.168.1.100 -t shares -w 3 -c 5
##   python3 check_hycu_vm_backup_v2.1.py -l 192.168.1.100 -t port -n 8443
##   python3 check_hycu_vm_backup_v2.1.py -a "TOKEN" -l 192.168.1.100 -t unassigned -w 5 -c 10
####################################

import requests
import json
import urllib3
import optparse
import sys
import socket
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional

# Remove SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Exit codes for monitoring tools
EXIT_OK = 0
EXIT_WARNING = 1
EXIT_CRITICAL = 2
EXIT_UNKNOWN = 3

# API field constants for consistency
FIELD_PROTECTION_GROUP_NAME = 'protectionGroupName'
FIELD_VM_NAME = 'vmName'
FIELD_SHARE_NAME = 'shareName'
FIELD_APP_NAME = 'name'
FIELD_VG_NAME = 'name'
FIELD_PROTOCOL_LIST = 'protocolTypeList'
FIELD_COMPLIANCY_STATUS = 'compliancyStatus'

# Check type categories
CHECK_TYPES = {
    'objects': ['vm', 'vmid', 'target', 'archive'],
    'policies': ['policy', 'policy-advanced'],
    'global': ['manager', 'jobs', 'license', 'version'],
    'storage': ['shares', 'buckets'],
    'validation': ['backup-validation', 'unassigned'],
    'network': ['port']
}

# Flatten for validation
ALL_CHECK_TYPES = [t for types in CHECK_TYPES.values() for t in types]


class HycuAPIError(Exception):
    """Custom exception for HYCU API errors"""
    pass


def parse_arguments():
    """Parse command line arguments"""
    parser = optparse.OptionParser(
        usage='%prog -a <api_token> -l <hycu_host> -n <object_name> -t <type>',
        description='Monitor HYCU backup status via REST API'
    )
    parser.add_option('-a', dest='apitoken', help='HYCU API token (required for most types)')
    parser.add_option('-l', dest='host', help='HYCU host IP or FQDN (required)')
    parser.add_option('-n', dest='vmtarget', help='Object name to check (required for some types)')
    parser.add_option('-t', dest='scantype', 
                     help='Check type (required). Available types: '
                          'OBJECTS: vm, vmid, target, archive | '
                          'POLICIES: policy, policy-advanced | '
                          'GLOBAL: manager, jobs, license, version | '
                          'STORAGE: shares, buckets | '
                          'VALIDATION: backup-validation, unassigned | '
                          'NETWORK: port')
    parser.add_option('-T', dest='timeout', type='int', default=100,
                     help='API request timeout in seconds (default: 100)')
    parser.add_option('-v', dest='verbose', action='store_true', default=False,
                     help='Verbose mode for debugging')
    
    # Thresholds options (used by: jobs, policy-advanced, license, backup-validation, shares, buckets)
    parser.add_option('-w', '--warning', dest='warning_threshold', type='int', default=5,
                     help='Warning threshold (default: 5). For license: days before expiration. For others: failed count')
    parser.add_option('-c', '--critical', dest='critical_threshold', type='int', default=10,
                     help='Critical threshold (default: 10). For license: days before expiration. For others: failed count')
    parser.add_option('-p', '--period', dest='period_hours', type='int', default=24,
                     help='Time period in hours for jobs and backup-validation checks (default: 24, max: 168)')
    
    (options, args) = parser.parse_args()
    
    # Validate required arguments (some types don't need -n parameter or API token)
    types_without_vmtarget = ['jobs', 'license', 'version', 'backup-validation', 'shares', 'buckets', 'unassigned']
    types_without_token = ['port']
    
    if options.scantype in types_without_vmtarget:
        # For these types, only host is required (and token except for port)
        if options.scantype in types_without_token:
            if not all([options.host, options.scantype]):
                parser.print_help()
                sys.exit(EXIT_UNKNOWN)
        else:
            if not all([options.apitoken, options.host, options.scantype]):
                parser.print_help()
                sys.exit(EXIT_UNKNOWN)
        # Set a dummy value for vmtarget if not provided
        if not options.vmtarget:
            options.vmtarget = options.scantype
    else:
        # For other types, all parameters are required
        if not all([options.apitoken, options.host, options.vmtarget, options.scantype]):
            parser.print_help()
            sys.exit(EXIT_UNKNOWN)
    
    # Validate scantype
    if options.scantype not in ALL_CHECK_TYPES:
        print(f"ERROR: Invalid type '{options.scantype}'.")
        print(f"\nAvailable check types by category:")
        for category, types in CHECK_TYPES.items():
            print(f"  {category.upper()}: {', '.join(types)}")
        sys.exit(EXIT_UNKNOWN)
    
    # Validate jobs-specific options
    if options.scantype == 'jobs':
        validate_thresholds(options.warning_threshold, options.critical_threshold)
        if options.period_hours < 1 or options.period_hours > 168:
            parser.error("Period must be between 1 and 168 hours")
    
    # Validate policy-advanced options
    if options.scantype == 'policy-advanced':
        validate_thresholds(options.warning_threshold, options.critical_threshold)
    
    # Validate license options (inverted: critical < warning for days before expiration)
    if options.scantype == 'license':
        validate_thresholds(options.warning_threshold, options.critical_threshold, inverted=True)
    
    # Validate backup-validation, shares, buckets, unassigned options
    if options.scantype in ['backup-validation', 'shares', 'buckets', 'unassigned']:
        validate_thresholds(options.warning_threshold, options.critical_threshold)
        if options.scantype == 'backup-validation':
            if options.period_hours < 1 or options.period_hours > 168:
                parser.error("Period must be between 1 and 168 hours")
    
    # Validate port options (port number via -n)
    if options.scantype == 'port':
        if options.vmtarget and options.vmtarget != 'port':
            try:
                port_num = int(options.vmtarget)
                if port_num < 1 or port_num > 65535:
                    parser.error("Port number must be between 1 and 65535")
            except ValueError:
                parser.error(f"Port number must be an integer, got '{options.vmtarget}'")
    
    return options


def validate_thresholds(warning: int, critical: int, inverted: bool = False) -> bool:
    """
    Validate warning and critical thresholds
    
    Args:
        warning: Warning threshold
        critical: Critical threshold
        inverted: If True, critical must be <= warning (for license expiration)
        
    Returns:
        True if valid
        
    Raises:
        SystemExit: If validation fails
    """
    if warning < 0 or critical < 0:
        print("ERROR: Thresholds must be positive integers")
        sys.exit(EXIT_UNKNOWN)
    
    if inverted:
        if critical > warning:
            print("ERROR: For license checks, critical threshold must be <= warning threshold")
            sys.exit(EXIT_UNKNOWN)
    else:
        if critical < warning:
            print("ERROR: Critical threshold must be >= warning threshold")
            sys.exit(EXIT_UNKNOWN)
    
    return True


def api_request(url: str, headers: dict, timeout: int, verbose: bool = False) -> dict:
    """
    Make an API request with error handling
    
    Args:
        url: API endpoint URL
        headers: Request headers
        timeout: Request timeout in seconds
        verbose: Enable verbose output
        
    Returns:
        JSON response as dictionary
        
    Raises:
        HycuAPIError: If the API request fails
    """
    try:
        if verbose:
            print(f"DEBUG: Calling API: {url}")
        
        response = requests.get(url, headers=headers, timeout=timeout, verify=False)
        
        if verbose:
            print(f"DEBUG: Status code: {response.status_code}")
        
        # Check HTTP status
        if response.status_code == 401:
            raise HycuAPIError("Authentication failed. Check your API token.")
        elif response.status_code == 403:
            raise HycuAPIError("Access forbidden. Check API token permissions.")
        elif response.status_code == 404:
            raise HycuAPIError("Resource not found.")
        elif response.status_code >= 500:
            raise HycuAPIError(f"HYCU server error: {response.status_code}")
        elif response.status_code != 200:
            raise HycuAPIError(f"HTTP {response.status_code}: {response.text}")
        
        return response.json()
    
    except requests.exceptions.Timeout:
        raise HycuAPIError(f"Request timeout after {timeout} seconds")
    except requests.exceptions.ConnectionError:
        raise HycuAPIError(f"Connection error. Check host address and network.")
    except requests.exceptions.RequestException as e:
        raise HycuAPIError(f"Request failed: {str(e)}")
    except json.JSONDecodeError:
        raise HycuAPIError("Invalid JSON response from API")


def get_entity_uuid(host: str, headers: dict, timeout: int, endpoint: str, 
                   name: str, name_field: str, verbose: bool = False) -> Optional[str]:
    """
    Generic function to get UUID from entity name
    Supports case-insensitive search if exact match fails
    
    Args:
        host: HYCU host
        headers: Request headers
        timeout: Request timeout
        endpoint: API endpoint (e.g., 'vms', 'targets', 'policies')
        name: Entity name to search
        name_field: JSON field name for entity name
        verbose: Enable verbose output
        
    Returns:
        UUID string or None if not found
    """
    url = f'https://{host}:8443/rest/v1.0/{endpoint}?pageSize=1000&pageNumber=1'
    data = api_request(url, headers, timeout, verbose)
    
    # Build dictionary of name -> uuid
    entity_dict = {
        entity[name_field]: entity['uuid'] 
        for entity in data.get('entities', [])
    }
    
    if verbose:
        print(f"DEBUG: Found {len(entity_dict)} {endpoint}")
    
    # Try exact match first
    uuid = entity_dict.get(name)
    if uuid:
        if verbose:
            print(f"DEBUG: Exact match found for '{name}'")
        return uuid
    
    # Try case-insensitive match
    if verbose:
        print(f"DEBUG: No exact match for '{name}', trying case-insensitive search...")
    
    name_lower = name.lower()
    for entity_name, entity_uuid in entity_dict.items():
        if entity_name.lower() == name_lower:
            if verbose:
                print(f"DEBUG: Case-insensitive match found: '{entity_name}'")
            return entity_uuid
    
    # No match found
    if verbose:
        print(f"DEBUG: No match found for '{name}'")
        print(f"DEBUG: Available names: {list(entity_dict.keys())[:5]}...")
    
    return None


def check_vm_backup(host: str, headers: dict, timeout: int, uuid: str, 
                   vm_name: str, verbose: bool = False) -> Tuple[int, str]:
    """
    Check backup status for a VM
    
    Returns:
        Tuple of (exit_code, output_message)
    """
    url = f'https://{host}:8443/rest/v1.0/vms/{uuid}/backups?pageSize=10&pageNumber=1'
    data = api_request(url, headers, timeout, verbose)
    
    # Check if backups exist
    backup_count = data.get('metadata', {}).get('grandTotalEntityCount', 0)
    if backup_count == 0:
        return EXIT_CRITICAL, f"{vm_name} has no backups |backup_status=0;;;"
    
    # Get latest backup (first in list)
    latest_backup = data['entities'][0]
    backup_status = latest_backup['status']
    backup_type = latest_backup['type']
    vm_name_from_api = latest_backup.get('vmName', vm_name)
    
    # Determine exit code and numeric status
    status_map = {
        'OK': (EXIT_OK, 2),
        'WARNING': (EXIT_WARNING, 1),
        'FATAL': (EXIT_CRITICAL, 0)
    }
    
    exit_code, numeric_status = status_map.get(backup_status, (EXIT_UNKNOWN, 1))
    
    output = f"{vm_name_from_api} is {backup_status} for last {backup_type} |backup_status={numeric_status};;;"
    return exit_code, output


def check_target_health(host: str, headers: dict, timeout: int, uuid: str, 
                       target_name: str, verbose: bool = False) -> Tuple[int, str]:
    """
    Check health status of a target
    Handles both API response structures (direct object or entities array)
    
    Returns:
        Tuple of (exit_code, output_message)
    """
    url = f'https://{host}:8443/rest/v1.0/targets/{uuid}'
    data = api_request(url, headers, timeout, verbose)
    
    # HYCU API can return either:
    # 1. Direct object: {'name': '...', 'health': '...'}
    # 2. Entities array: {'entities': [{'name': '...', 'health': '...'}]}
    
    if verbose:
        print(f"DEBUG: API response keys: {list(data.keys())}")
    
    # Check if response has 'entities' array (older API format)
    if 'entities' in data and len(data['entities']) > 0:
        if verbose:
            print("DEBUG: Response has 'entities' array, using entities[0]")
        target_data = data['entities'][0]
    else:
        # Direct object response (newer API format)
        if verbose:
            print("DEBUG: Response is direct object")
        target_data = data
    
    # Extract target information
    target_name_from_api = target_data.get('name', target_name)
    target_health = target_data.get('health', 'UNKNOWN')
    
    if verbose:
        print(f"DEBUG: Target name: {target_name_from_api}")
        print(f"DEBUG: Target health: {target_health}")
    
    # Determine exit code
    health_map = {
        'GREEN': (EXIT_OK, 2),
        'GREY': (EXIT_WARNING, 1),
        'RED': (EXIT_CRITICAL, 0),
        'GRAY': (EXIT_WARNING, 1),  # Alternative spelling
    }
    
    exit_code, numeric_status = health_map.get(target_health, (EXIT_UNKNOWN, 1))
    
    output = f"{target_name_from_api} is {target_health} |target_health={numeric_status};;;"
    return exit_code, output


def check_archive_status(host: str, headers: dict, timeout: int, uuid: str, 
                        vm_name: str, verbose: bool = False) -> Tuple[int, str]:
    """
    Check archive status for a VM
    
    Returns:
        Tuple of (exit_code, output_message)
    """
    url = f'https://{host}:8443/rest/v1.0/vms/{uuid}/backups?pageSize=10&pageNumber=1'
    data = api_request(url, headers, timeout, verbose)
    
    # Check if backups exist
    backup_count = data.get('metadata', {}).get('grandTotalEntityCount', 0)
    if backup_count == 0:
        return EXIT_CRITICAL, f"{vm_name} has no backups |archive_status=0;;;"
    
    # Get latest backup
    latest_backup = data['entities'][0]
    vm_name_from_api = latest_backup.get('vmName', vm_name)
    backup_type = latest_backup['type']
    archives_ok = latest_backup.get('numberOfArchives', 0)
    archives_failed = latest_backup.get('numberOfFailedArchives', 0)
    
    # Determine archive status - FIXED LOGIC
    if archives_failed >= 1:
        archive_status = 'FAILED'
        exit_code = EXIT_CRITICAL
        numeric_status = 0
    elif archives_ok >= 1:
        archive_status = 'OK'
        exit_code = EXIT_OK
        numeric_status = 2
    else:
        archive_status = 'MISSING'
        exit_code = EXIT_WARNING
        numeric_status = 1
    
    output = (f"{vm_name_from_api} archive is {archive_status} for last {backup_type} "
             f"|archive_status={numeric_status};;; archives_ok={archives_ok};;; "
             f"archives_failed={archives_failed};;;")
    
    return exit_code, output


def check_policy_compliance(host: str, headers: dict, timeout: int, uuid: str, 
                           policy_name: str, verbose: bool = False) -> Tuple[int, str]:
    """
    Check compliance status of a policy
    
    Returns:
        Tuple of (exit_code, output_message)
    """
    url = f'https://{host}:8443/rest/v1.0/policies/{uuid}'
    data = api_request(url, headers, timeout, verbose)
    
    # Get policy information
    policy = data['entities'][0]
    policy_name_from_api = policy.get('name', policy_name)
    policy_status = policy.get('compliancyStatus', 'UNKNOWN')
    compliant_vms = policy.get('compliantVmsCount', 0)
    
    # Determine exit code
    status_map = {
        'GREEN': (EXIT_OK, 2),
        'WARNING': (EXIT_WARNING, 1),
        'RED': (EXIT_CRITICAL, 0)
    }
    
    exit_code, numeric_status = status_map.get(policy_status, (EXIT_UNKNOWN, 1))
    
    output = (f"{policy_name_from_api} is {policy_status} including {compliant_vms} VMs "
             f"|policy_status={numeric_status};;; compliant_vms={compliant_vms};;;")
    
    return exit_code, output


def check_policy_advanced(host: str, headers: dict, timeout: int, policy_name: str,
                         warning_threshold: int, critical_threshold: int,
                         verbose: bool = False) -> Tuple[int, str]:
    """
    Check policy compliance with detailed object counting
    
    Args:
        host: HYCU host
        headers: Request headers
        timeout: Request timeout
        policy_name: Policy name to check
        warning_threshold: Warning threshold for non-compliant objects
        critical_threshold: Critical threshold for non-compliant objects
        verbose: Enable verbose output
        
    Returns:
        Tuple of (exit_code, output_message)
    """
    if verbose:
        print(f"DEBUG: Searching for policy '{policy_name}'")
    
    # Step 1: Get policy UUID
    url = f'https://{host}:8443/rest/v1.0/policies?pageSize=1000&pageNumber=1'
    data = api_request(url, headers, timeout, verbose)
    
    # Find policy by name (case-insensitive)
    policy_uuid = None
    policy_name_lower = policy_name.lower()
    
    for policy in data.get('entities', []):
        if policy['name'].lower() == policy_name_lower:
            policy_uuid = policy['uuid']
            if verbose:
                print(f"DEBUG: Policy found: {policy['name']}")
                print(f"DEBUG: UUID: {policy_uuid}")
            break
    
    if not policy_uuid:
        # Show available policies
        url = f'https://{host}:8443/rest/v1.0/policies?pageSize=1000&pageNumber=1'
        try:
            data = api_request(url, headers, timeout, verbose)
            available_names = [p['name'] for p in data.get('entities', [])]
            if available_names:
                print(f"CRITICAL: Policy '{policy_name}' does not exist")
                print(f"Available policies: {', '.join(available_names[:5])}")
                if len(available_names) > 5:
                    print(f"... and {len(available_names) - 5} more")
            else:
                print(f"CRITICAL: Policy '{policy_name}' does not exist (no policies found)")
        except:
            print(f"CRITICAL: Policy '{policy_name}' does not exist")
        sys.exit(EXIT_CRITICAL)
    
    # Step 2: Get detailed policy info
    url = f'https://{host}:8443/rest/v1.0/policies/{policy_uuid}'
    data = api_request(url, headers, timeout, verbose)
    
    policy = data['entities'][0]
    
    if verbose:
        print(f"DEBUG: Policy compliance status: {policy.get('compliancyStatus')}")
    
    # Extract statistics
    stats = {
        'name': policy.get('name'),
        'status': policy.get('compliancyStatus', 'UNKNOWN'),
        
        # VMs
        'vms_total': policy.get('vmsCount', 0),
        'vms_compliant': policy.get('compliantVmsCount', 0),
        'vms_uncompliant': policy.get('uncompliantVmsCount', 0),
        
        # Shares
        'shares_total': policy.get('sharesCount', 0),
        'shares_compliant': policy.get('compliantSharesCount', 0),
        'shares_uncompliant': policy.get('uncompliantSharesCount', 0),
        
        # Apps
        'apps_total': policy.get('appsCount', 0),
        'apps_compliant': policy.get('compliantAppsCount', 0),
        'apps_uncompliant': policy.get('uncompliantAppsCount', 0),
        
        # Buckets
        'buckets_total': policy.get('bucketsCount', 0),
        'buckets_compliant': policy.get('compliantBucketsCount', 0),
        'buckets_uncompliant': policy.get('uncompliantBucketsCount', 0),
        
        # Volume Groups
        'vgs_total': policy.get('vgsCount', 0),
        'vgs_compliant': policy.get('compliantVgsCount', 0),
        'vgs_uncompliant': policy.get('uncompliantVgsCount', 0),
    }
    
    # Calculate totals
    stats['total_objects'] = (stats['vms_total'] + stats['shares_total'] + 
                             stats['apps_total'] + stats['buckets_total'] + 
                             stats['vgs_total'])
    
    stats['total_compliant'] = (stats['vms_compliant'] + stats['shares_compliant'] + 
                               stats['apps_compliant'] + stats['buckets_compliant'] + 
                               stats['vgs_compliant'])
    
    stats['total_uncompliant'] = (stats['vms_uncompliant'] + stats['shares_uncompliant'] + 
                                 stats['apps_uncompliant'] + stats['buckets_uncompliant'] + 
                                 stats['vgs_uncompliant'])
    
    # Calculate compliance rate
    if stats['total_objects'] > 0:
        stats['compliance_rate'] = (stats['total_compliant'] / stats['total_objects']) * 100
    else:
        stats['compliance_rate'] = 100.0
    
    if verbose:
        print(f"\nDEBUG: Statistics:")
        print(f"  Total objects: {stats['total_objects']}")
        print(f"  Compliant: {stats['total_compliant']}")
        print(f"  Non-compliant: {stats['total_uncompliant']}")
        print(f"  Compliance rate: {stats['compliance_rate']:.1f}%")
        print(f"\nDEBUG: Breakdown:")
        print(f"  VMs: {stats['vms_compliant']}/{stats['vms_total']}")
        print(f"  Shares: {stats['shares_compliant']}/{stats['shares_total']}")
        print(f"  Apps: {stats['apps_compliant']}/{stats['apps_total']}")
        print(f"  Buckets: {stats['buckets_compliant']}/{stats['buckets_total']}")
        print(f"  VGs: {stats['vgs_compliant']}/{stats['vgs_total']}")
    
    # Determine status based on thresholds
    uncompliant_count = stats['total_uncompliant']
    
    if uncompliant_count >= critical_threshold:
        exit_code = EXIT_CRITICAL
        status_label = "CRITICAL"
    elif uncompliant_count >= warning_threshold:
        exit_code = EXIT_WARNING
        status_label = "WARNING"
    else:
        exit_code = EXIT_OK
        status_label = "OK"
    
    # Format output
    message = (f"{status_label}: Policy '{stats['name']}' - "
              f"{stats['total_compliant']}/{stats['total_objects']} objects compliant "
              f"({stats['vms_compliant']}/{stats['vms_total']} VMs, "
              f"{stats['shares_compliant']}/{stats['shares_total']} shares, "
              f"{stats['apps_compliant']}/{stats['apps_total']} apps, "
              f"{stats['buckets_compliant']}/{stats['buckets_total']} buckets, "
              f"{stats['vgs_compliant']}/{stats['vgs_total']} VGs)")
    
    # Performance data for Centreon graphing
    perfdata = (
        f"|"
        f"total_objects={stats['total_objects']};;;0; "
        f"compliant={stats['total_compliant']};;;0; "
        f"uncompliant={stats['total_uncompliant']};{warning_threshold};{critical_threshold};0; "
        f"vms_compliant={stats['vms_compliant']};;;0;{stats['vms_total']} "
        f"vms_uncompliant={stats['vms_uncompliant']};;;0;{stats['vms_total']} "
        f"shares_compliant={stats['shares_compliant']};;;0;{stats['shares_total']} "
        f"shares_uncompliant={stats['shares_uncompliant']};;;0;{stats['shares_total']} "
        f"apps_compliant={stats['apps_compliant']};;;0;{stats['apps_total']} "
        f"apps_uncompliant={stats['apps_uncompliant']};;;0;{stats['apps_total']} "
        f"compliance_rate={stats['compliance_rate']:.2f}%;;;0;100"
    )
    
    output = message + " " + perfdata
    
    # Add verbose details if requested
    if verbose:
        output += "\n\nDetailed Breakdown:"
        output += f"\n  VMs: {stats['vms_compliant']}/{stats['vms_total']} compliant"
        output += f"\n  Shares: {stats['shares_compliant']}/{stats['shares_total']} compliant"
        output += f"\n  Applications: {stats['apps_compliant']}/{stats['apps_total']} compliant"
        output += f"\n  Buckets: {stats['buckets_compliant']}/{stats['buckets_total']} compliant"
        if stats['vgs_total'] > 0:
            output += f"\n  Volume Groups: {stats['vgs_compliant']}/{stats['vgs_total']} compliant"
        output += f"\n  Compliance Rate: {stats['compliance_rate']:.1f}%"
    
    return exit_code, output


def check_manager_protected(host: str, headers: dict, timeout: int, 
                           verbose: bool = False) -> Tuple[int, str]:
    """
    Check how many VMs are protected
    
    Returns:
        Tuple of (exit_code, output_message)
    """
    url = f'https://{host}:8443/rest/v1.0/mom/dashboards/vms'
    data = api_request(url, headers, timeout, verbose)
    
    dashboard = data['entities'][0]
    total_count = dashboard.get('totalCount', 0)
    protected_count = dashboard.get('protectedCount', 0)
    unprotected_count = dashboard.get('unprotectedCount', 0)
    
    # Critical if any VM is unprotected
    exit_code = EXIT_OK if unprotected_count == 0 else EXIT_CRITICAL
    
    output = (f"{unprotected_count} VMs not protected out of {total_count} total "
             f"|vms_unprotected={unprotected_count};;; vms_protected={protected_count};;; "
             f"vms_total={total_count};;;")
    
    return exit_code, output


def check_manager_compliance(host: str, headers: dict, timeout: int, 
                            verbose: bool = False) -> Tuple[int, str]:
    """
    Check VM backup compliance status
    
    Returns:
        Tuple of (exit_code, output_message)
    """
    url = f'https://{host}:8443/rest/v1.0/mom/dashboards/vms'
    data = api_request(url, headers, timeout, verbose)
    
    dashboard = data['entities'][0]
    compliance_green = dashboard.get('compliancyGreenCount', 0)
    compliance_red = dashboard.get('compliancyRedCount', 0)
    compliance_grey = dashboard.get('compliancyGreyCount', 0)
    
    # Critical if any VM has red compliance
    exit_code = EXIT_OK if compliance_red == 0 else EXIT_CRITICAL
    
    output = (f"{compliance_red} VMs with non-compliant backups "
             f"|vms_noncompliant={compliance_red};;; vms_compliant={compliance_green};;; "
             f"vms_unknown={compliance_grey};;;")
    
    return exit_code, output


def check_jobs(host: str, headers: dict, timeout: int, period_hours: int,
              warning_threshold: int, critical_threshold: int,
              verbose: bool = False) -> Tuple[int, str]:
    """
    Check HYCU jobs statistics over a time period
    
    Args:
        host: HYCU host
        headers: Request headers
        timeout: Request timeout
        period_hours: Time period in hours to check
        warning_threshold: Warning threshold for failed jobs
        critical_threshold: Critical threshold for failed jobs
        verbose: Enable verbose output
        
    Returns:
        Tuple of (exit_code, output_message)
    """
    # Calculate time range
    now = datetime.now()
    start = now - timedelta(hours=period_hours)
    
    # Convert to milliseconds (HYCU API format)
    end_time = int(now.timestamp() * 1000)
    start_time = int(start.timestamp() * 1000)
    
    if verbose:
        print(f"DEBUG: Time range:")
        print(f"  From: {start.strftime('%Y-%m-%d %H:%M:%S')} ({start_time})")
        print(f"  To:   {now.strftime('%Y-%m-%d %H:%M:%S')} ({end_time})")
    
    # Build API URL with time filters
    url = (f'https://{host}:8443/rest/v1.0/jobs'
           f'?pageSize=10000&pageNumber=1'
           f'&startTime={start_time}&endTime={end_time}')
    
    data = api_request(url, headers, timeout, verbose)
    
    # Initialize counters
    stats = {
        'total': 0,
        'ok': 0,
        'warning': 0,
        'error': 0,
        'running': 0,
        'other': 0,
        'failed_jobs': []
    }
    
    # Get total from metadata
    if 'metadata' in data:
        stats['total'] = data['metadata'].get('grandTotalEntityCount', 0)
        if verbose:
            print(f"DEBUG: Total jobs in period: {stats['total']}")
    
    # Count jobs by status
    if 'entities' in data:
        for job in data['entities']:
            status = job.get('status', 'UNKNOWN').upper()
            job_type = job.get('type', 'UNKNOWN')
            task_name = job.get('taskName', 'Unknown task')
            
            # Count by status
            if status == 'OK':
                stats['ok'] += 1
            elif status == 'WARNING':
                stats['warning'] += 1
                stats['failed_jobs'].append({
                    'name': task_name,
                    'status': status,
                    'type': job_type
                })
            elif status == 'ERROR':
                stats['error'] += 1
                stats['failed_jobs'].append({
                    'name': task_name,
                    'status': status,
                    'type': job_type
                })
            elif status in ['RUNNING', 'QUEUED', 'PENDING']:
                stats['running'] += 1
            else:
                stats['other'] += 1
        
        if verbose:
            print(f"DEBUG: Jobs processed: {len(data['entities'])}")
            print(f"DEBUG: Status breakdown:")
            print(f"  OK: {stats['ok']}")
            print(f"  WARNING: {stats['warning']}")
            print(f"  ERROR: {stats['error']}")
            print(f"  RUNNING: {stats['running']}")
    
    # Calculate failed jobs (WARNING + ERROR)
    stats['failed'] = stats['warning'] + stats['error']
    
    # Calculate success rate
    completed_jobs = stats['ok'] + stats['warning'] + stats['error']
    if completed_jobs > 0:
        stats['success_rate'] = (stats['ok'] / completed_jobs) * 100
    else:
        stats['success_rate'] = 100.0
    
    # Determine status
    if stats['failed'] >= critical_threshold:
        exit_code = EXIT_CRITICAL
        status_label = "CRITICAL"
    elif stats['failed'] >= warning_threshold:
        exit_code = EXIT_WARNING
        status_label = "WARNING"
    else:
        exit_code = EXIT_OK
        status_label = "OK"
    
    # Format output
    message = (f"{status_label}: HYCU jobs over {period_hours}h - "
              f"{stats['failed']} failed ({stats['error']} errors, {stats['warning']} warnings), "
              f"{stats['ok']} successful, {stats['running']} running")
    
    # Performance data for Centreon graphing
    perfdata = (
        f"|"
        f"jobs_ok={stats['ok']};;;0; "
        f"jobs_warning={stats['warning']};;;0; "
        f"jobs_error={stats['error']};;;0; "
        f"jobs_failed={stats['failed']};{warning_threshold};{critical_threshold};0; "
        f"jobs_running={stats['running']};;;0; "
        f"success_rate={stats['success_rate']:.2f}%;;;0;100"
    )
    
    output = message + " " + perfdata
    
    # Add verbose details if requested
    if verbose and stats['failed'] > 0:
        output += "\n\nFailed Jobs Details:"
        for job in stats['failed_jobs'][:10]:
            output += f"\n  - [{job['status']}] {job['name']} (Type: {job['type']})"
        
        if len(stats['failed_jobs']) > 10:
            output += f"\n  ... and {len(stats['failed_jobs']) - 10} more failed jobs"
    
    return exit_code, output


def check_license(host: str, headers: dict, timeout: int,
                 warning_days: int, critical_days: int,
                 verbose: bool = False) -> Tuple[int, str]:
    """
    Check HYCU license status and expiration
    
    Args:
        host: HYCU host
        headers: Request headers
        timeout: Request timeout
        warning_days: Warning threshold (days before expiration)
        critical_days: Critical threshold (days before expiration)
        verbose: Enable verbose output
        
    Returns:
        Tuple of (exit_code, output_message)
    """
    url = f'https://{host}:8443/rest/v1.0/administration/license?pageSize=100&pageNumber=1'
    data = api_request(url, headers, timeout, verbose)
    
    if not data.get('entities'):
        return EXIT_CRITICAL, "CRITICAL: No license information found"
    
    lic = data['entities'][0]
    
    # Extract license info
    company = lic.get('companyName', 'N/A')
    lic_type = lic.get('type', 'N/A')
    status = lic.get('status', 'UNKNOWN')
    days_left = lic.get('daysLeft', 0)
    expiration_date = lic.get('expirationDate')
    version_type = lic.get('versionType', 'N/A')
    
    # License capacities
    licensed_vms = lic.get('licensedVms', 0)
    protected_vms = lic.get('protectedVms', 0)
    licensed_sockets = lic.get('licensedSockets', 0)
    actual_sockets = lic.get('actualSockets', 0)
    
    if verbose:
        print(f"DEBUG: License status: {status}")
        print(f"DEBUG: Days left: {days_left}")
        print(f"DEBUG: VMs: {protected_vms}/{licensed_vms}")
        print(f"DEBUG: Sockets: {actual_sockets}/{licensed_sockets}")
    
    # Convert expiration timestamp
    if expiration_date:
        try:
            exp_date_str = datetime.fromtimestamp(expiration_date / 1000).strftime('%Y-%m-%d')
        except:
            exp_date_str = 'N/A'
    else:
        exp_date_str = 'N/A'
    
    # Determine status based on days left
    if days_left <= critical_days:
        exit_code = EXIT_CRITICAL
        status_label = "CRITICAL"
    elif days_left <= warning_days:
        exit_code = EXIT_WARNING
        status_label = "WARNING"
    else:
        exit_code = EXIT_OK
        status_label = "OK"
    
    # Format output
    message = (f"{status_label}: License '{company}' - {days_left} days left (expires {exp_date_str}), "
              f"Status: {status}, VMs: {protected_vms}/{licensed_vms}, "
              f"Sockets: {actual_sockets}/{licensed_sockets}")
    
    # Performance data
    perfdata = (
        f"|"
        f"days_left={days_left};{warning_days};{critical_days};0; "
        f"vms_protected={protected_vms};;;0;{licensed_vms} "
        f"vms_licensed={licensed_vms};;;0; "
        f"sockets_actual={actual_sockets};;;0;{licensed_sockets} "
        f"sockets_licensed={licensed_sockets};;;0;"
    )
    
    output = message + " " + perfdata
    
    return exit_code, output


def check_version(host: str, headers: dict, timeout: int,
                 verbose: bool = False) -> Tuple[int, str]:
    """
    Get HYCU version and controller information (informational only, always OK)
    
    Args:
        host: HYCU host
        headers: Request headers
        timeout: Request timeout
        verbose: Enable verbose output
        
    Returns:
        Tuple of (exit_code, output_message)
    """
    url = f'https://{host}:8443/rest/v1.0/administration/controller?pageSize=1&pageNumber=1'
    data = api_request(url, headers, timeout, verbose)
    
    if not data.get('entities'):
        return EXIT_WARNING, "WARNING: Controller information not available"
    
    ctrl = data['entities'][0]
    
    # Extract controller info
    controller_name = ctrl.get('controllerVmName', 'N/A')
    software_version = ctrl.get('softwareVersion', 'N/A')
    build_version = ctrl.get('buildVersion', 'N/A')
    hypervisor_type = ctrl.get('externalHypervisorType', 'N/A')
    
    if verbose:
        print(f"DEBUG: Controller: {controller_name}")
        print(f"DEBUG: Version: {software_version}")
        print(f"DEBUG: Build: {build_version}")
        print(f"DEBUG: Hypervisor: {hypervisor_type}")
    
    # Format output (always OK for informational check)
    message = (f"OK: HYCU Controller '{controller_name}' - "
              f"Version {software_version} (Build {build_version}), "
              f"Hypervisor: {hypervisor_type}")
    
    # No performance data needed for version check
    output = message
    
    return EXIT_OK, output


def check_backup_validation(host: str, headers: dict, timeout: int, period_hours: int,
                           warning_threshold: int, critical_threshold: int,
                           verbose: bool = False) -> Tuple[int, str]:
    """
    Check backup validation failures over a time period
    
    Args:
        host: HYCU host
        headers: Request headers
        timeout: Request timeout
        period_hours: Time period in hours to check
        warning_threshold: Warning threshold for failed validations
        critical_threshold: Critical threshold for failed validations
        verbose: Enable verbose output
        
    Returns:
        Tuple of (exit_code, output_message)
    """
    # Calculate time range
    now = datetime.now()
    start = now - timedelta(hours=period_hours)
    
    end_time = int(now.timestamp() * 1000)
    start_time = int(start.timestamp() * 1000)
    
    if verbose:
        print(f"DEBUG: Checking backup validations from {start} to {now}")
    
    # Get backup validation jobs
    url = (f'https://{host}:8443/rest/v1.0/jobs'
           f'?pageSize=10000&pageNumber=1'
           f'&startTime={start_time}&endTime={end_time}')
    
    data = api_request(url, headers, timeout, verbose)
    
    # Count validation jobs
    stats = {
        'total': 0,
        'ok': 0,
        'warning': 0,
        'error': 0,
        'failed': 0
    }
    
    if 'entities' in data:
        for job in data['entities']:
            job_type = job.get('type', '')
            # Filter only validation-related jobs
            if 'VALIDATION' in job_type or 'RESTORE_VALIDATE' in job_type:
                stats['total'] += 1
                status = job.get('status', 'UNKNOWN').upper()
                
                if status == 'OK':
                    stats['ok'] += 1
                elif status == 'WARNING':
                    stats['warning'] += 1
                elif status == 'ERROR':
                    stats['error'] += 1
    
    stats['failed'] = stats['warning'] + stats['error']
    
    if verbose:
        print(f"DEBUG: Total validations: {stats['total']}")
        print(f"DEBUG: OK: {stats['ok']}, Failed: {stats['failed']}")
    
    # Determine status
    if stats['failed'] >= critical_threshold:
        exit_code = EXIT_CRITICAL
        status_label = "CRITICAL"
    elif stats['failed'] >= warning_threshold:
        exit_code = EXIT_WARNING
        status_label = "WARNING"
    else:
        exit_code = EXIT_OK
        status_label = "OK"
    
    # Format output
    message = (f"{status_label}: Backup validations over {period_hours}h - "
              f"{stats['failed']} failed ({stats['error']} errors, {stats['warning']} warnings), "
              f"{stats['ok']} successful")
    
    perfdata = (
        f"|"
        f"validations_total={stats['total']};;;0; "
        f"validations_ok={stats['ok']};;;0; "
        f"validations_failed={stats['failed']};{warning_threshold};{critical_threshold};0;"
    )
    
    output = message + " " + perfdata
    
    return exit_code, output


def check_shares(host: str, headers: dict, timeout: int,
                warning_threshold: int, critical_threshold: int,
                verbose: bool = False) -> Tuple[int, str]:
    """
    Check shares (NFS/SMB) backup status
    
    Args:
        host: HYCU host
        headers: Request headers
        timeout: Request timeout
        warning_threshold: Warning threshold for failed shares
        critical_threshold: Critical threshold for failed shares
        verbose: Enable verbose output
        
    Returns:
        Tuple of (exit_code, output_message)
    """
    url = f'https://{host}:8443/rest/v1.0/shares?pageSize=1000&pageNumber=1'
    data = api_request(url, headers, timeout, verbose)
    
    stats = {
        'total': 0,
        'protected': 0,
        'compliant': 0,
        'non_compliant': 0,
        'unprotected': 0
    }
    
    if 'entities' in data:
        for share in data['entities']:
            # Filter only NFS/SMB shares (exclude S3 buckets)
            protocols = share.get('protocolTypeList', [])
            if not any(p in ['NFS', 'SMB'] for p in protocols):
                continue  # Skip S3 buckets
            
            status = share.get('status', 'UNKNOWN')
            compliancy_status = share.get('compliancyStatus', 'UNKNOWN')
            
            # Only count shares with defined status (exclude UNDEFINED)
            if status in ['PROTECTED', 'UNPROTECTED']:
                stats['total'] += 1
                
                if status == 'PROTECTED':
                    stats['protected'] += 1
                    
                    if compliancy_status == 'GREEN':
                        stats['compliant'] += 1
                    elif compliancy_status in ['RED', 'YELLOW']:
                        stats['non_compliant'] += 1
                else:
                    stats['unprotected'] += 1
    
    if verbose:
        print(f"DEBUG: Total NFS/SMB shares: {stats['total']}")
        print(f"DEBUG: Protected: {stats['protected']}, Compliant: {stats['compliant']}")
        print(f"DEBUG: Non-compliant: {stats['non_compliant']}")
    
    # Determine status based on non-compliant shares
    if stats['non_compliant'] >= critical_threshold:
        exit_code = EXIT_CRITICAL
        status_label = "CRITICAL"
    elif stats['non_compliant'] >= warning_threshold:
        exit_code = EXIT_WARNING
        status_label = "WARNING"
    else:
        exit_code = EXIT_OK
        status_label = "OK"
    
    # Format output
    message = (f"{status_label}: Shares (NFS/SMB) - "
              f"{stats['compliant']}/{stats['total']} compliant, "
              f"{stats['non_compliant']} non-compliant, "
              f"{stats['unprotected']} unprotected")
    
    perfdata = (
        f"|"
        f"shares_total={stats['total']};;;0; "
        f"shares_compliant={stats['compliant']};;;0; "
        f"shares_non_compliant={stats['non_compliant']};{warning_threshold};{critical_threshold};0; "
        f"shares_unprotected={stats['unprotected']};;;0;"
    )
    
    output = message + " " + perfdata
    
    return exit_code, output


def check_buckets(host: str, headers: dict, timeout: int,
                 warning_threshold: int, critical_threshold: int,
                 verbose: bool = False) -> Tuple[int, str]:
    """
    Check buckets (S3/object storage) backup status
    
    Args:
        host: HYCU host
        headers: Request headers
        timeout: Request timeout
        warning_threshold: Warning threshold for failed buckets
        critical_threshold: Critical threshold for failed buckets
        verbose: Enable verbose output
        
    Returns:
        Tuple of (exit_code, output_message)
    """
    # Note: HYCU uses /shares endpoint for both shares and buckets
    url = f'https://{host}:8443/rest/v1.0/shares?pageSize=1000&pageNumber=1'
    data = api_request(url, headers, timeout, verbose)
    
    stats = {
        'total': 0,
        'protected': 0,
        'compliant': 0,
        'non_compliant': 0,
        'unprotected': 0
    }
    
    if 'entities' in data:
        for bucket in data['entities']:
            # Filter only S3 buckets (exclude NFS/SMB shares)
            protocols = bucket.get('protocolTypeList', [])
            if 'S3' not in protocols:
                continue  # Skip NFS/SMB shares
            
            status = bucket.get('status', 'UNKNOWN')
            compliancy_status = bucket.get('compliancyStatus', 'UNKNOWN')
            
            # Only count buckets with defined status (exclude UNDEFINED)
            if status in ['PROTECTED', 'UNPROTECTED']:
                stats['total'] += 1
                
                if status == 'PROTECTED':
                    stats['protected'] += 1
                    
                    if compliancy_status == 'GREEN':
                        stats['compliant'] += 1
                    elif compliancy_status in ['RED', 'YELLOW']:
                        stats['non_compliant'] += 1
                else:
                    stats['unprotected'] += 1
    
    if verbose:
        print(f"DEBUG: Total S3 buckets: {stats['total']}")
        print(f"DEBUG: Protected: {stats['protected']}, Compliant: {stats['compliant']}")
        print(f"DEBUG: Non-compliant: {stats['non_compliant']}")
    
    # Determine status based on non-compliant buckets
    if stats['non_compliant'] >= critical_threshold:
        exit_code = EXIT_CRITICAL
        status_label = "CRITICAL"
    elif stats['non_compliant'] >= warning_threshold:
        exit_code = EXIT_WARNING
        status_label = "WARNING"
    else:
        exit_code = EXIT_OK
        status_label = "OK"
    
    # Format output
    message = (f"{status_label}: Buckets (S3) - "
              f"{stats['compliant']}/{stats['total']} compliant, "
              f"{stats['non_compliant']} non-compliant, "
              f"{stats['unprotected']} unprotected")
    
    perfdata = (
        f"|"
        f"buckets_total={stats['total']};;;0; "
        f"buckets_compliant={stats['compliant']};;;0; "
        f"buckets_non_compliant={stats['non_compliant']};{warning_threshold};{critical_threshold};0; "
        f"buckets_unprotected={stats['unprotected']};;;0;"
    )
    
    output = message + " " + perfdata
    
    return exit_code, output


def check_port(host: str, port: int, timeout: int = 5,
              verbose: bool = False) -> Tuple[int, str]:
    """
    Check TCP port connectivity
    
    Args:
        host: Target host IP or FQDN
        port: TCP port number to check
        timeout: Connection timeout in seconds (default: 5)
        verbose: Enable verbose output
        
    Returns:
        Tuple of (exit_code, output_message)
    """
    if verbose:
        print(f"DEBUG: Testing TCP connection to {host}:{port}")
        print(f"DEBUG: Timeout: {timeout} seconds")
    
    start_time = datetime.now()
    
    try:
        # Create socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        
        # Attempt connection
        result = sock.connect_ex((host, port))
        
        # Calculate response time
        end_time = datetime.now()
        response_time_ms = int((end_time - start_time).total_seconds() * 1000)
        
        sock.close()
        
        if verbose:
            print(f"DEBUG: Connection result code: {result}")
            print(f"DEBUG: Response time: {response_time_ms}ms")
        
        if result == 0:
            # Port is open
            exit_code = EXIT_OK
            message = f"OK: Port {port} is OPEN on {host} (response time: {response_time_ms}ms)"
            perfdata = f"|response_time={response_time_ms}ms;;;0;"
        else:
            # Port is closed or filtered
            exit_code = EXIT_CRITICAL
            message = f"CRITICAL: Port {port} is CLOSED on {host}"
            perfdata = f"|response_time=0ms;;;0;"
        
        output = message + " " + perfdata
        return exit_code, output
        
    except socket.gaierror as e:
        # DNS resolution failed
        if verbose:
            print(f"DEBUG: DNS resolution failed: {e}")
        return EXIT_CRITICAL, f"CRITICAL: Cannot resolve hostname {host} - DNS error"
    
    except socket.timeout:
        # Connection timeout
        if verbose:
            print(f"DEBUG: Connection timeout after {timeout} seconds")
        return EXIT_CRITICAL, f"CRITICAL: Port {port} on {host} - Connection timeout after {timeout}s"
    
    except Exception as e:
        # Other errors
        if verbose:
            print(f"DEBUG: Unexpected error: {e}")
            import traceback
            traceback.print_exc()
        return EXIT_CRITICAL, f"CRITICAL: Port check failed - {str(e)}"


def check_unassigned(host: str, headers: dict, timeout: int,
                    warning_threshold: int, critical_threshold: int,
                    verbose: bool = False) -> Tuple[int, str]:
    """
    Check for unassigned objects (VMs, shares, buckets, apps, VGs without policy)
    An object is unassigned if protectionGroupName is null/None
    
    Args:
        host: HYCU host
        headers: Request headers
        timeout: Request timeout
        warning_threshold: Warning threshold for unassigned objects
        critical_threshold: Critical threshold for unassigned objects
        verbose: Enable verbose output
        
    Returns:
        Tuple of (exit_code, output_message)
    """
    unassigned_objects = {
        'vms': [],
        'shares': [],
        'buckets': [],
        'apps': [],
        'vgs': []
    }
    
    stats = {
        'vms': 0,
        'shares': 0,
        'buckets': 0,
        'apps': 0,
        'vgs': 0,
        'total': 0
    }
    
    # Check VMs
    if verbose:
        print("DEBUG: Checking unassigned VMs...")
    
    url = f'https://{host}:8443/rest/v1.0/vms?pageSize=1000&pageNumber=1'
    try:
        data = api_request(url, headers, timeout, verbose=False)
        if 'entities' in data:
            for vm in data['entities']:
                protection_group = vm.get('protectionGroupName')
                # Unassigned = no protectionGroupName (null/None/empty)
                if not protection_group:
                    vm_name = vm.get('vmName', 'Unknown')
                    unassigned_objects['vms'].append(vm_name)
                    stats['vms'] += 1
    except Exception as e:
        if verbose:
            print(f"DEBUG: Error checking VMs: {e}")
    
    # Check Shares (NFS/SMB only)
    if verbose:
        print("DEBUG: Checking unassigned shares...")
    
    url = f'https://{host}:8443/rest/v1.0/shares?pageSize=1000&pageNumber=1'
    try:
        data = api_request(url, headers, timeout, verbose=False)
        if 'entities' in data:
            for share in data['entities']:
                # Filter NFS/SMB shares only
                protocols = share.get('protocolTypeList', [])
                if not any(p in ['NFS', 'SMB'] for p in protocols):
                    continue
                
                protection_group = share.get('protectionGroupName')
                # Unassigned = no protectionGroupName
                if not protection_group:
                    share_name = share.get('shareName', 'Unknown')
                    unassigned_objects['shares'].append(share_name)
                    stats['shares'] += 1
    except Exception as e:
        if verbose:
            print(f"DEBUG: Error checking shares: {e}")
    
    # Check Buckets (S3) - using same data from shares endpoint
    if verbose:
        print("DEBUG: Checking unassigned buckets...")
    
    try:
        if 'entities' in data:
            for bucket in data['entities']:
                # Filter S3 buckets only
                protocols = bucket.get('protocolTypeList', [])
                if 'S3' not in protocols:
                    continue
                
                protection_group = bucket.get('protectionGroupName')
                # Unassigned = no protectionGroupName
                if not protection_group:
                    bucket_name = bucket.get('shareName', 'Unknown')
                    unassigned_objects['buckets'].append(bucket_name)
                    stats['buckets'] += 1
    except Exception as e:
        if verbose:
            print(f"DEBUG: Error checking buckets: {e}")
    
    # Check Applications
    if verbose:
        print("DEBUG: Checking unassigned applications...")
    
    url = f'https://{host}:8443/rest/v1.0/applications?pageSize=1000&pageNumber=1'
    try:
        data = api_request(url, headers, timeout, verbose=False)
        if 'entities' in data:
            for app in data['entities']:
                protection_group = app.get('protectionGroupName')
                # Unassigned = no protectionGroupName
                if not protection_group:
                    # Use 'name' field for applications
                    app_name = app.get('name', 'Unknown')
                    unassigned_objects['apps'].append(app_name)
                    stats['apps'] += 1
    except Exception as e:
        if verbose:
            print(f"DEBUG: Error checking applications: {e}")
    
    # Check Volume Groups
    if verbose:
        print("DEBUG: Checking unassigned volume groups...")
    
    url = f'https://{host}:8443/rest/v1.0/volumegroups?pageSize=1000&pageNumber=1'
    try:
        data = api_request(url, headers, timeout, verbose=False)
        if 'entities' in data:
            for vg in data['entities']:
                protection_group = vg.get('protectionGroupName')
                # Unassigned = no protectionGroupName
                if not protection_group:
                    # Use 'name' field for volume groups
                    vg_name = vg.get('name', 'Unknown')
                    unassigned_objects['vgs'].append(vg_name)
                    stats['vgs'] += 1
    except Exception as e:
        if verbose:
            print(f"DEBUG: Error checking volume groups: {e}")
    
    # Calculate total
    stats['total'] = stats['vms'] + stats['shares'] + stats['buckets'] + stats['apps'] + stats['vgs']
    
    if verbose:
        print(f"\nDEBUG: Unassigned objects summary:")
        print(f"  VMs: {stats['vms']}")
        print(f"  Shares: {stats['shares']}")
        print(f"  Buckets: {stats['buckets']}")
        print(f"  Applications: {stats['apps']}")
        print(f"  Volume Groups: {stats['vgs']}")
        print(f"  TOTAL: {stats['total']}")
    
    # Determine status
    if stats['total'] >= critical_threshold:
        exit_code = EXIT_CRITICAL
        status_label = "CRITICAL"
    elif stats['total'] >= warning_threshold:
        exit_code = EXIT_WARNING
        status_label = "WARNING"
    else:
        exit_code = EXIT_OK
        status_label = "OK"
    
    # Format output
    message = (f"{status_label}: {stats['total']} unassigned objects - "
              f"{stats['vms']} VMs, {stats['shares']} shares, {stats['buckets']} buckets, "
              f"{stats['apps']} apps, {stats['vgs']} VGs")
    
    # Add list of unassigned objects (limited to first 10 per category)
    details = []
    if stats['vms'] > 0:
        vm_list = ', '.join(unassigned_objects['vms'][:10])
        if stats['vms'] > 10:
            vm_list += f" (+{stats['vms']-10} more)"
        details.append(f"VMs: {vm_list}")
    
    if stats['shares'] > 0:
        share_list = ', '.join(unassigned_objects['shares'][:10])
        if stats['shares'] > 10:
            share_list += f" (+{stats['shares']-10} more)"
        details.append(f"Shares: {share_list}")
    
    if stats['buckets'] > 0:
        bucket_list = ', '.join(unassigned_objects['buckets'][:10])
        if stats['buckets'] > 10:
            bucket_list += f" (+{stats['buckets']-10} more)"
        details.append(f"Buckets: {bucket_list}")
    
    if stats['apps'] > 0:
        app_list = ', '.join(unassigned_objects['apps'][:10])
        if stats['apps'] > 10:
            app_list += f" (+{stats['apps']-10} more)"
        details.append(f"Apps: {app_list}")
    
    if stats['vgs'] > 0:
        vg_list = ', '.join(unassigned_objects['vgs'][:10])
        if stats['vgs'] > 10:
            vg_list += f" (+{stats['vgs']-10} more)"
        details.append(f"VGs: {vg_list}")
    
    # Add details if there are unassigned objects
    if details:
        message += " | " + " / ".join(details)
    
    # Performance data
    perfdata = (
        f"|"
        f"unassigned_total={stats['total']};{warning_threshold};{critical_threshold};0; "
        f"unassigned_vms={stats['vms']};;;0; "
        f"unassigned_shares={stats['shares']};;;0; "
        f"unassigned_buckets={stats['buckets']};;;0; "
        f"unassigned_apps={stats['apps']};;;0; "
        f"unassigned_vgs={stats['vgs']};;;0;"
    )
    
    output = message + " " + perfdata
    
    return exit_code, output


def main():
    """Main execution function"""
    try:
        # Parse arguments
        options = parse_arguments()
        
        # Setup API headers
        headers = {
            "Authorization": f"Bearer {options.apitoken}",
            "Content-Type": "application/json"
        }
        
        # Route to appropriate check based on type
        if options.scantype == 'vm':
            # Get VM UUID from name
            uuid = get_entity_uuid(
                options.host, headers, options.timeout, 
                'vms', options.vmtarget, 'vmName', options.verbose
            )
            if uuid is None:
                print(f"CRITICAL: VM '{options.vmtarget}' does not exist")
                sys.exit(EXIT_CRITICAL)
            
            exit_code, output = check_vm_backup(
                options.host, headers, options.timeout, uuid, 
                options.vmtarget, options.verbose
            )
        
        elif options.scantype == 'vmid':
            # Use provided UUID directly
            exit_code, output = check_vm_backup(
                options.host, headers, options.timeout, 
                options.vmtarget, options.vmtarget, options.verbose
            )
        
        elif options.scantype == 'target':
            # Get target UUID from name
            uuid = get_entity_uuid(
                options.host, headers, options.timeout, 
                'targets', options.vmtarget, 'name', options.verbose
            )
            if uuid is None:
                # Provide helpful error message with available targets
                url = f'https://{options.host}:8443/rest/v1.0/targets?pageSize=1000&pageNumber=1'
                try:
                    data = api_request(url, headers, options.timeout, options.verbose)
                    available_names = [entity['name'] for entity in data.get('entities', [])]
                    if available_names:
                        print(f"CRITICAL: Target '{options.vmtarget}' does not exist")
                        print(f"Available targets: {', '.join(available_names[:5])}")
                        if len(available_names) > 5:
                            print(f"... and {len(available_names) - 5} more")
                    else:
                        print(f"CRITICAL: Target '{options.vmtarget}' does not exist (no targets found)")
                except:
                    print(f"CRITICAL: Target '{options.vmtarget}' does not exist")
                sys.exit(EXIT_CRITICAL)
            
            exit_code, output = check_target_health(
                options.host, headers, options.timeout, uuid, 
                options.vmtarget, options.verbose
            )
        
        elif options.scantype == 'archive':
            # Get VM UUID from name
            uuid = get_entity_uuid(
                options.host, headers, options.timeout, 
                'vms', options.vmtarget, 'vmName', options.verbose
            )
            if uuid is None:
                print(f"CRITICAL: VM '{options.vmtarget}' does not exist")
                sys.exit(EXIT_CRITICAL)
            
            exit_code, output = check_archive_status(
                options.host, headers, options.timeout, uuid, 
                options.vmtarget, options.verbose
            )
        
        elif options.scantype == 'policy':
            # Get policy UUID from name
            uuid = get_entity_uuid(
                options.host, headers, options.timeout, 
                'policies', options.vmtarget, 'name', options.verbose
            )
            if uuid is None:
                print(f"CRITICAL: Policy '{options.vmtarget}' does not exist")
                sys.exit(EXIT_CRITICAL)
            
            exit_code, output = check_policy_compliance(
                options.host, headers, options.timeout, uuid, 
                options.vmtarget, options.verbose
            )
        
        elif options.scantype == 'policy-advanced':
            # Check policy with detailed object counting and thresholds
            exit_code, output = check_policy_advanced(
                options.host, headers, options.timeout,
                options.vmtarget,
                options.warning_threshold,
                options.critical_threshold,
                options.verbose
            )
        
        elif options.scantype == 'manager':
            if options.vmtarget == 'protected':
                exit_code, output = check_manager_protected(
                    options.host, headers, options.timeout, options.verbose
                )
            elif options.vmtarget == 'compliance':
                exit_code, output = check_manager_compliance(
                    options.host, headers, options.timeout, options.verbose
                )
            else:
                print(f"ERROR: For manager type, use -n protected or -n compliance")
                sys.exit(EXIT_UNKNOWN)
        
        elif options.scantype == 'jobs':
            # Check jobs statistics over specified period
            # The -n parameter is ignored for jobs type (could be anything)
            exit_code, output = check_jobs(
                options.host, headers, options.timeout,
                options.period_hours,
                options.warning_threshold,
                options.critical_threshold,
                options.verbose
            )
        
        elif options.scantype == 'license':
            # Check license status and expiration
            # The -n parameter is ignored for license type
            exit_code, output = check_license(
                options.host, headers, options.timeout,
                options.warning_threshold,
                options.critical_threshold,
                options.verbose
            )
        
        elif options.scantype == 'version':
            # Get HYCU version information (always OK)
            # The -n parameter is ignored for version type
            exit_code, output = check_version(
                options.host, headers, options.timeout,
                options.verbose
            )
        
        elif options.scantype == 'backup-validation':
            # Check backup validation jobs over specified period
            # The -n parameter is ignored
            exit_code, output = check_backup_validation(
                options.host, headers, options.timeout,
                options.period_hours,
                options.warning_threshold,
                options.critical_threshold,
                options.verbose
            )
        
        elif options.scantype == 'shares':
            # Check shares backup compliance
            # The -n parameter is ignored
            exit_code, output = check_shares(
                options.host, headers, options.timeout,
                options.warning_threshold,
                options.critical_threshold,
                options.verbose
            )
        
        elif options.scantype == 'buckets':
            # Check buckets backup compliance
            # The -n parameter is ignored
            exit_code, output = check_buckets(
                options.host, headers, options.timeout,
                options.warning_threshold,
                options.critical_threshold,
                options.verbose
            )
        
        elif options.scantype == 'port':
            # Check TCP port connectivity
            # Use -n to specify port number (default: 8443)
            # The -a parameter is ignored (no API token needed)
            try:
                port = int(options.vmtarget) if options.vmtarget and options.vmtarget != 'port' else 8443
            except ValueError:
                print(f"ERROR: Port number must be an integer, got '{options.vmtarget}'")
                sys.exit(EXIT_UNKNOWN)
            
            timeout = min(options.timeout, 30)  # Max 30s for port check
            
            exit_code, output = check_port(
                options.host,
                port,
                timeout,
                options.verbose
            )
        
        elif options.scantype == 'unassigned':
            # Check for unassigned objects (VMs, shares, buckets, apps, VGs without policy)
            # The -n parameter is ignored
            exit_code, output = check_unassigned(
                options.host, headers, options.timeout,
                options.warning_threshold,
                options.critical_threshold,
                options.verbose
            )
        
        else:
            print(f"ERROR: Unknown scan type '{options.scantype}'")
            sys.exit(EXIT_UNKNOWN)
        
        # Output result and exit
        print(output)
        sys.exit(exit_code)
    
    except HycuAPIError as e:
        print(f"CRITICAL: API Error - {str(e)}")
        sys.exit(EXIT_CRITICAL)
    
    except Exception as e:
        print(f"UNKNOWN: Unexpected error - {str(e)}")
        if options.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(EXIT_UNKNOWN)


if __name__ == "__main__":
    main()
