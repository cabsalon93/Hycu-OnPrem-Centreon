# 🚀 HYCU Monitoring Plugin - Déploiement Rapide avec CLAPI

Guide de déploiement automatisé pour Centreon en utilisant CLAPI (Centreon Command Line API).

## 📋 Table des Matières

1. [Introduction à CLAPI](#introduction-à-clapi)
2. [Prérequis](#prérequis)
3. [Installation du Plugin](#installation-du-plugin)
4. [Configuration du Token API](#configuration-du-token-api)
5. [Script de Déploiement Complet](#script-de-déploiement-complet)
6. [Déploiement Pas-à-Pas](#déploiement-pas-à-pas)
7. [Vérification](#vérification)
8. [Personnalisation](#personnalisation)
9. [Troubleshooting](#troubleshooting)

---

## Introduction à CLAPI

CLAPI (Centreon Command Line API) permet de configurer Centreon en ligne de commande, idéal pour :
- ✅ Déploiement rapide et reproductible
- ✅ Automatisation complète
- ✅ Configuration as Code
- ✅ Déploiement multi-sites

**Temps de déploiement :** ~5 minutes (vs 2h manuellement)

---

## Prérequis

### Accès et Permissions

```bash
# SSH vers le serveur Centreon Central
ssh admin@centreon-central

# Vérifier CLAPI
centreon -u admin -p 'password' -o HOST -a show

# Attendu: Liste des hosts (ou vide si aucun)
```

### Variables d'Environnement

```bash
# Définir les credentials Centreon
export CENTREON_USER="admin"
export CENTREON_PASS="your_centreon_password"

# Définir les informations HYCU
export HYCU_HOST="hycu.company.com"
export HYCU_TOKEN="cjd0NnEybGR93270yagalakXBkN3ZlZA=="

# Poller (central ou nom du poller distant)
export POLLER="Central"
```

---

## Installation du Plugin

### Étape 1 : Copier le Plugin

```bash
# SSH vers Centreon Central (ou poller si distant)
sudo su -

# Télécharger le plugin
cd /usr/lib/nagios/plugins/
wget https://raw.githubusercontent.com/YOUR_USERNAME/hycu-monitoring-plugin/main/check_hycu_vm_backup_v2.1.py

# Permissions
chmod 755 check_hycu_vm_backup_v2.1.py
chown centreon-engine:centreon-engine check_hycu_vm_backup_v2.1.py

# Vérifier
ls -l check_hycu_vm_backup_v2.1.py
# Attendu: -rwxr-xr-x 1 centreon-engine centreon-engine
```

### Étape 2 : Tester le Plugin

```bash
# Test basique
su - centreon-engine -s /bin/bash
/usr/lib/nagios/plugins/check_hycu_vm_backup_v2.1.py -h

# Test avec HYCU
/usr/lib/nagios/plugins/check_hycu_vm_backup_v2.1.py \
  -l $HYCU_HOST \
  -a "$HYCU_TOKEN" \
  -t version

# Attendu: OK: HYCU Controller 'xxx' - Version x.x.x ...
```

---

## Configuration du Token API

### Méthode : Resource Macro (Recommandée)

```bash
# Ajouter le token comme resource $USER10$
centreon -u $CENTREON_USER -p $CENTREON_PASS \
  -o RESOURCECFG -a setparam \
  -v "1;$USER10$;$HYCU_TOKEN;HYCU API Token"

# Exporter la configuration
centreon -u $CENTREON_USER -p $CENTREON_PASS \
  -o POLLERRESOURCES -a export
```

---

## Script de Déploiement Complet

### Script Automatisé : `deploy_hycu_monitoring.sh`

Créer le fichier :

```bash
cat > /tmp/deploy_hycu_monitoring.sh << 'EOFSCRIPT'
#!/bin/bash
################################################################################
# HYCU Monitoring - Déploiement Automatique Centreon via CLAPI
# Version: 2.1
# Description: Déploie tous les checks HYCU en une seule commande
################################################################################

set -e  # Exit on error

# ============================================================================
# CONFIGURATION - À ADAPTER
# ============================================================================

# Centreon credentials
CENTREON_USER="${CENTREON_USER:-admin}"
CENTREON_PASS="${CENTREON_PASS:-centreon}"

# HYCU Configuration
HYCU_HOST="${HYCU_HOST:-hycu.company.com}"
HYCU_ALIAS="${HYCU_ALIAS:-HYCU Production Controller}"
HYCU_IP="${HYCU_IP:-$HYCU_HOST}"
HYCU_TOKEN="${HYCU_TOKEN}"

# Centreon configuration
POLLER="${POLLER:-Central}"
HOSTGROUP="HYCU-Controllers"
CONTACTGROUP="admins"

# Couleurs pour output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================================================
# FONCTIONS
# ============================================================================

print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

clapi() {
    centreon -u "$CENTREON_USER" -p "$CENTREON_PASS" "$@" 2>&1
}

# ============================================================================
# VALIDATION
# ============================================================================

print_header "Validation des prérequis"

if [ -z "$HYCU_TOKEN" ]; then
    print_error "HYCU_TOKEN non défini. Utiliser: export HYCU_TOKEN='votre_token'"
    exit 1
fi

if ! command -v centreon &> /dev/null; then
    print_error "CLAPI non disponible. Êtes-vous sur le serveur Centreon ?"
    exit 1
fi

# Test de connexion Centreon
if ! clapi -o HOST -a show | grep -q "HOST;"; then
    print_error "Impossible de se connecter à CLAPI. Vérifier credentials."
    exit 1
fi

print_success "Prérequis validés"

# ============================================================================
# ÉTAPE 1: CRÉATION DES COMMANDES
# ============================================================================

print_header "Création des commandes de check"

# Commande 1: check_hycu_version
clapi -o CMD -a add \
  -v "check_hycu_version;check;\$USER1\$/check_hycu_vm_backup_v2.1.py -l \$HOSTADDRESS\$ -a \$USER10\$ -t version -T \$ARG1\$" \
  || print_warning "Commande check_hycu_version existe déjà"
print_success "check_hycu_version"

# Commande 2: check_hycu_license
clapi -o CMD -a add \
  -v "check_hycu_license;check;\$USER1\$/check_hycu_vm_backup_v2.1.py -l \$HOSTADDRESS\$ -a \$USER10\$ -t license -w \$ARG1\$ -c \$ARG2\$ -T \$ARG3\$" \
  || print_warning "Commande check_hycu_license existe déjà"
print_success "check_hycu_license"

# Commande 3: check_hycu_jobs
clapi -o CMD -a add \
  -v "check_hycu_jobs;check;\$USER1\$/check_hycu_vm_backup_v2.1.py -l \$HOSTADDRESS\$ -a \$USER10\$ -t jobs -w \$ARG1\$ -c \$ARG2\$ -p \$ARG3\$ -T \$ARG4\$" \
  || print_warning "Commande check_hycu_jobs existe déjà"
print_success "check_hycu_jobs"

# Commande 4: check_hycu_unassigned
clapi -o CMD -a add \
  -v "check_hycu_unassigned;check;\$USER1\$/check_hycu_vm_backup_v2.1.py -l \$HOSTADDRESS\$ -a \$USER10\$ -t unassigned -w \$ARG1\$ -c \$ARG2\$ -T \$ARG3\$" \
  || print_warning "Commande check_hycu_unassigned existe déjà"
print_success "check_hycu_unassigned"

# Commande 5: check_hycu_shares
clapi -o CMD -a add \
  -v "check_hycu_shares;check;\$USER1\$/check_hycu_vm_backup_v2.1.py -l \$HOSTADDRESS\$ -a \$USER10\$ -t shares -w \$ARG1\$ -c \$ARG2\$ -T \$ARG3\$" \
  || print_warning "Commande check_hycu_shares existe déjà"
print_success "check_hycu_shares"

# Commande 6: check_hycu_buckets
clapi -o CMD -a add \
  -v "check_hycu_buckets;check;\$USER1\$/check_hycu_vm_backup_v2.1.py -l \$HOSTADDRESS\$ -a \$USER10\$ -t buckets -w \$ARG1\$ -c \$ARG2\$ -T \$ARG3\$" \
  || print_warning "Commande check_hycu_buckets existe déjà"
print_success "check_hycu_buckets"

# Commande 7: check_hycu_backup_validation
clapi -o CMD -a add \
  -v "check_hycu_backup_validation;check;\$USER1\$/check_hycu_vm_backup_v2.1.py -l \$HOSTADDRESS\$ -a \$USER10\$ -t backup-validation -w \$ARG1\$ -c \$ARG2\$ -p \$ARG3\$ -T \$ARG4\$" \
  || print_warning "Commande check_hycu_backup_validation existe déjà"
print_success "check_hycu_backup_validation"

# Commande 8: check_hycu_port
clapi -o CMD -a add \
  -v "check_hycu_port;check;\$USER1\$/check_hycu_vm_backup_v2.1.py -l \$HOSTADDRESS\$ -t port -n \$ARG1\$ -T \$ARG2\$" \
  || print_warning "Commande check_hycu_port existe déjà"
print_success "check_hycu_port"

# Commande 9: check_hycu_vm
clapi -o CMD -a add \
  -v "check_hycu_vm;check;\$USER1\$/check_hycu_vm_backup_v2.1.py -l \$HOSTADDRESS\$ -a \$USER10\$ -n \"\$ARG1\$\" -t vm -T \$ARG2\$" \
  || print_warning "Commande check_hycu_vm existe déjà"
print_success "check_hycu_vm"

# Commande 10: check_hycu_policy_advanced
clapi -o CMD -a add \
  -v "check_hycu_policy_advanced;check;\$USER1\$/check_hycu_vm_backup_v2.1.py -l \$HOSTADDRESS\$ -a \$USER10\$ -n \"\$ARG1\$\" -t policy-advanced -w \$ARG2\$ -c \$ARG3\$ -T \$ARG4\$" \
  || print_warning "Commande check_hycu_policy_advanced existe déjà"
print_success "check_hycu_policy_advanced"

# Commande 11: check_hycu_target
clapi -o CMD -a add \
  -v "check_hycu_target;check;\$USER1\$/check_hycu_vm_backup_v2.1.py -l \$HOSTADDRESS\$ -a \$USER10\$ -n \"\$ARG1\$\" -t target -T \$ARG2\$" \
  || print_warning "Commande check_hycu_target existe déjà"
print_success "check_hycu_target"

# Commande 12: check_hycu_manager
clapi -o CMD -a add \
  -v "check_hycu_manager;check;\$USER1\$/check_hycu_vm_backup_v2.1.py -l \$HOSTADDRESS\$ -a \$USER10\$ -n \"\$ARG1\$\" -t manager -T \$ARG2\$" \
  || print_warning "Commande check_hycu_manager existe déjà"
print_success "check_hycu_manager"

# ============================================================================
# ÉTAPE 2: CRÉATION DU HOST GROUP
# ============================================================================

print_header "Création du Host Group"

clapi -o HG -a add -v "$HOSTGROUP;HYCU Backup Controllers" \
  || print_warning "Host group existe déjà"
print_success "Host group: $HOSTGROUP"

# ============================================================================
# ÉTAPE 3: CRÉATION DE L'HÔTE HYCU
# ============================================================================

print_header "Création de l'hôte HYCU"

# Supprimer si existe déjà (optionnel - commenter si vous voulez conserver)
# clapi -o HOST -a del -v "$HYCU_HOST" 2>/dev/null || true

# Créer l'hôte
clapi -o HOST -a add \
  -v "$HYCU_HOST;$HYCU_ALIAS;$HYCU_IP;generic-host;$POLLER;$HOSTGROUP" \
  || print_warning "Hôte existe déjà"

# Configuration de l'hôte
clapi -o HOST -a setparam -v "$HYCU_HOST;check_command;check_hycu_port"
clapi -o HOST -a setparam -v "$HYCU_HOST;check_command_arguments;!8443!30"
clapi -o HOST -a setparam -v "$HYCU_HOST;check_interval;5"
clapi -o HOST -a setparam -v "$HYCU_HOST;retry_check_interval;1"
clapi -o HOST -a setparam -v "$HYCU_HOST;max_check_attempts;3"
clapi -o HOST -a setparam -v "$HYCU_HOST;active_checks_enabled;1"
clapi -o HOST -a setparam -v "$HYCU_HOST;passive_checks_enabled;0"

# Ajouter contact group
clapi -o HOST -a addcontactgroup -v "$HYCU_HOST;$CONTACTGROUP" 2>/dev/null || true

print_success "Hôte créé: $HYCU_HOST"

# ============================================================================
# ÉTAPE 4: CRÉATION DES SERVICES
# ============================================================================

print_header "Création des services de monitoring"

# Service 1: Version (informational)
clapi -o SERVICE -a add \
  -v "$HYCU_HOST;HYCU-Version;check_hycu_version" || true
clapi -o SERVICE -a setparam \
  -v "$HYCU_HOST;HYCU-Version;check_command_arguments;!100"
clapi -o SERVICE -a setparam \
  -v "$HYCU_HOST;HYCU-Version;check_interval;1440"
clapi -o SERVICE -a setparam \
  -v "$HYCU_HOST;HYCU-Version;retry_check_interval;60"
clapi -o SERVICE -a setparam \
  -v "$HYCU_HOST;HYCU-Version;max_check_attempts;1"
print_success "Service: HYCU-Version"

# Service 2: License Expiration
clapi -o SERVICE -a add \
  -v "$HYCU_HOST;HYCU-License-Expiration;check_hycu_license" || true
clapi -o SERVICE -a setparam \
  -v "$HYCU_HOST;HYCU-License-Expiration;check_command_arguments;!30!7!100"
clapi -o SERVICE -a setparam \
  -v "$HYCU_HOST;HYCU-License-Expiration;check_interval;1440"
clapi -o SERVICE -a setparam \
  -v "$HYCU_HOST;HYCU-License-Expiration;retry_check_interval;60"
clapi -o SERVICE -a setparam \
  -v "$HYCU_HOST;HYCU-License-Expiration;max_check_attempts;3"
clapi -o SERVICE -a setparam \
  -v "$HYCU_HOST;HYCU-License-Expiration;notifications_enabled;1"
print_success "Service: HYCU-License-Expiration"

# Service 3: Jobs Statistics (24h)
clapi -o SERVICE -a add \
  -v "$HYCU_HOST;HYCU-Jobs-24h;check_hycu_jobs" || true
clapi -o SERVICE -a setparam \
  -v "$HYCU_HOST;HYCU-Jobs-24h;check_command_arguments;!10!20!24!100"
clapi -o SERVICE -a setparam \
  -v "$HYCU_HOST;HYCU-Jobs-24h;check_interval;15"
clapi -o SERVICE -a setparam \
  -v "$HYCU_HOST;HYCU-Jobs-24h;retry_check_interval;5"
clapi -o SERVICE -a setparam \
  -v "$HYCU_HOST;HYCU-Jobs-24h;max_check_attempts;3"
clapi -o SERVICE -a setparam \
  -v "$HYCU_HOST;HYCU-Jobs-24h;notifications_enabled;1"
print_success "Service: HYCU-Jobs-24h"

# Service 4: Unassigned Objects
clapi -o SERVICE -a add \
  -v "$HYCU_HOST;HYCU-Unassigned-Objects;check_hycu_unassigned" || true
clapi -o SERVICE -a setparam \
  -v "$HYCU_HOST;HYCU-Unassigned-Objects;check_command_arguments;!5!10!100"
clapi -o SERVICE -a setparam \
  -v "$HYCU_HOST;HYCU-Unassigned-Objects;check_interval;60"
clapi -o SERVICE -a setparam \
  -v "$HYCU_HOST;HYCU-Unassigned-Objects;retry_check_interval;15"
clapi -o SERVICE -a setparam \
  -v "$HYCU_HOST;HYCU-Unassigned-Objects;max_check_attempts;3"
clapi -o SERVICE -a setparam \
  -v "$HYCU_HOST;HYCU-Unassigned-Objects;notifications_enabled;1"
print_success "Service: HYCU-Unassigned-Objects"

# Service 5: Shares Monitoring
clapi -o SERVICE -a add \
  -v "$HYCU_HOST;HYCU-Shares-NFS-SMB;check_hycu_shares" || true
clapi -o SERVICE -a setparam \
  -v "$HYCU_HOST;HYCU-Shares-NFS-SMB;check_command_arguments;!3!5!100"
clapi -o SERVICE -a setparam \
  -v "$HYCU_HOST;HYCU-Shares-NFS-SMB;check_interval;30"
clapi -o SERVICE -a setparam \
  -v "$HYCU_HOST;HYCU-Shares-NFS-SMB;retry_check_interval;10"
clapi -o SERVICE -a setparam \
  -v "$HYCU_HOST;HYCU-Shares-NFS-SMB;max_check_attempts;3"
print_success "Service: HYCU-Shares-NFS-SMB"

# Service 6: Buckets Monitoring
clapi -o SERVICE -a add \
  -v "$HYCU_HOST;HYCU-Buckets-S3;check_hycu_buckets" || true
clapi -o SERVICE -a setparam \
  -v "$HYCU_HOST;HYCU-Buckets-S3;check_command_arguments;!2!5!100"
clapi -o SERVICE -a setparam \
  -v "$HYCU_HOST;HYCU-Buckets-S3;check_interval;30"
clapi -o SERVICE -a setparam \
  -v "$HYCU_HOST;HYCU-Buckets-S3;retry_check_interval;10"
clapi -o SERVICE -a setparam \
  -v "$HYCU_HOST;HYCU-Buckets-S3;max_check_attempts;3"
print_success "Service: HYCU-Buckets-S3"

# Service 7: Backup Validation
clapi -o SERVICE -a add \
  -v "$HYCU_HOST;HYCU-Backup-Validation-24h;check_hycu_backup_validation" || true
clapi -o SERVICE -a setparam \
  -v "$HYCU_HOST;HYCU-Backup-Validation-24h;check_command_arguments;!5!10!24!100"
clapi -o SERVICE -a setparam \
  -v "$HYCU_HOST;HYCU-Backup-Validation-24h;check_interval;60"
clapi -o SERVICE -a setparam \
  -v "$HYCU_HOST;HYCU-Backup-Validation-24h;retry_check_interval;15"
clapi -o SERVICE -a setparam \
  -v "$HYCU_HOST;HYCU-Backup-Validation-24h;max_check_attempts;3"
print_success "Service: HYCU-Backup-Validation-24h"

# Service 8: Port Connectivity
clapi -o SERVICE -a add \
  -v "$HYCU_HOST;HYCU-Port-8443;check_hycu_port" || true
clapi -o SERVICE -a setparam \
  -v "$HYCU_HOST;HYCU-Port-8443;check_command_arguments;!8443!30"
clapi -o SERVICE -a setparam \
  -v "$HYCU_HOST;HYCU-Port-8443;check_interval;5"
clapi -o SERVICE -a setparam \
  -v "$HYCU_HOST;HYCU-Port-8443;retry_check_interval;1"
clapi -o SERVICE -a setparam \
  -v "$HYCU_HOST;HYCU-Port-8443;max_check_attempts;3"
clapi -o SERVICE -a setparam \
  -v "$HYCU_HOST;HYCU-Port-8443;notifications_enabled;1"
print_success "Service: HYCU-Port-8443"

# Service 9: Manager Protected
clapi -o SERVICE -a add \
  -v "$HYCU_HOST;HYCU-Manager-Protected;check_hycu_manager" || true
clapi -o SERVICE -a setparam \
  -v "$HYCU_HOST;HYCU-Manager-Protected;check_command_arguments;!protected!100"
clapi -o SERVICE -a setparam \
  -v "$HYCU_HOST;HYCU-Manager-Protected;check_interval;30"
clapi -o SERVICE -a setparam \
  -v "$HYCU_HOST;HYCU-Manager-Protected;retry_check_interval;10"
clapi -o SERVICE -a setparam \
  -v "$HYCU_HOST;HYCU-Manager-Protected;max_check_attempts;3"
print_success "Service: HYCU-Manager-Protected"

# ============================================================================
# ÉTAPE 5: APPLICATION DE LA CONFIGURATION
# ============================================================================

print_header "Application de la configuration"

# Appliquer la configuration
clapi -a applycfg -v "$POLLER"

print_success "Configuration appliquée au poller: $POLLER"

# ============================================================================
# RÉSUMÉ
# ============================================================================

print_header "Déploiement terminé avec succès !"

echo ""
echo -e "${GREEN}✓ 12 commandes créées${NC}"
echo -e "${GREEN}✓ 1 host group créé${NC}"
echo -e "${GREEN}✓ 1 hôte créé: $HYCU_HOST${NC}"
echo -e "${GREEN}✓ 9 services créés${NC}"
echo -e "${GREEN}✓ Configuration appliquée${NC}"
echo ""
echo -e "${BLUE}Prochaines étapes:${NC}"
echo "1. Vérifier dans Centreon Web UI: Monitoring > Status Details > Hosts"
echo "2. Forcer un check: cliquer sur l'hôte > Re-schedule check"
echo "3. Vérifier les services: Monitoring > Status Details > Services"
echo "4. Ajouter des services VM si nécessaire (voir section suivante)"
echo ""
echo -e "${YELLOW}Pour ajouter un service VM:${NC}"
echo "centreon -u $CENTREON_USER -p PASSWORD -o SERVICE -a add -v \"$HYCU_HOST;HYCU-VM-NOM_VM;check_hycu_vm\""
echo "centreon -u $CENTREON_USER -p PASSWORD -o SERVICE -a setparam -v \"$HYCU_HOST;HYCU-VM-NOM_VM;check_command_arguments;!NOM_VM!100\""
echo ""

EOFSCRIPT

chmod +x /tmp/deploy_hycu_monitoring.sh
```

---

## Déploiement Pas-à-Pas

### Étape 1 : Préparer les Variables

```bash
# Se connecter au serveur Centreon
ssh admin@centreon-central

# Définir les variables d'environnement
export CENTREON_USER="admin"
export CENTREON_PASS="votre_password_centreon"
export HYCU_HOST="hycu.company.com"
export HYCU_TOKEN="cjd0NnEybGR93270yagalakXBkN3ZlZA=="
export POLLER="Central"
```

### Étape 2 : Ajouter le Token comme Resource

```bash
# Ajouter $USER10$ pour le token HYCU
centreon -u $CENTREON_USER -p $CENTREON_PASS \
  -o RESOURCECFG -a setparam \
  -v "1;\$USER10\$;$HYCU_TOKEN;HYCU API Token"

# Vérifier
centreon -u $CENTREON_USER -p $CENTREON_PASS \
  -o RESOURCECFG -a show | grep USER10
```

### Étape 3 : Exécuter le Script

```bash
# Télécharger le script (depuis ce guide)
# OU le créer manuellement comme montré ci-dessus

# Exécuter
bash /tmp/deploy_hycu_monitoring.sh

# Sortie attendue:
# ========================================
# Création des commandes de check
# ========================================
# ✓ check_hycu_version
# ✓ check_hycu_license
# ...
# ========================================
# Déploiement terminé avec succès !
# ========================================
```

### Étape 4 : Vérifier dans l'Interface

1. **Ouvrir Centreon Web UI**
2. **Aller à** `Monitoring` > `Status Details` > `Hosts`
3. **Trouver l'hôte** `hycu.company.com`
4. **Cliquer dessus** pour voir les services
5. **Forcer un check** sur chaque service

---

## Vérification

### Vérifier les Commandes

```bash
centreon -u $CENTREON_USER -p $CENTREON_PASS \
  -o CMD -a show | grep check_hycu

# Attendu: Liste de 12 commandes check_hycu_*
```

### Vérifier l'Hôte

```bash
centreon -u $CENTREON_USER -p $CENTREON_PASS \
  -o HOST -a show | grep hycu

# Attendu: hycu.company.com avec détails
```

### Vérifier les Services

```bash
centreon -u $CENTREON_USER -p $CENTREON_PASS \
  -o SERVICE -a show -v "$HYCU_HOST"

# Attendu: 9 services HYCU-*
```

### Test Manuel d'un Service

```bash
# Test depuis le poller
su - centreon-engine -s /bin/bash
/usr/lib/nagios/plugins/check_hycu_vm_backup_v2.1.py \
  -l $HYCU_HOST \
  -a "$HYCU_TOKEN" \
  -t version

# Attendu: OK: HYCU Controller ...
```

---

## Personnalisation

### Ajouter des Services VM Supplémentaires

```bash
# Liste de VMs à monitorer
VMS=("PROD-DB-01" "PROD-WEB-01" "PROD-APP-01")

for VM in "${VMS[@]}"; do
  echo "Ajout service pour VM: $VM"
  
  # Créer le service
  centreon -u $CENTREON_USER -p $CENTREON_PASS \
    -o SERVICE -a add \
    -v "$HYCU_HOST;HYCU-VM-$VM;check_hycu_vm"
  
  # Configurer les arguments
  centreon -u $CENTREON_USER -p $CENTREON_PASS \
    -o SERVICE -a setparam \
    -v "$HYCU_HOST;HYCU-VM-$VM;check_command_arguments;!$VM!100"
  
  # Intervalle de check
  centreon -u $CENTREON_USER -p $CENTREON_PASS \
    -o SERVICE -a setparam \
    -v "$HYCU_HOST;HYCU-VM-$VM;check_interval;15"
  
  # Retry
  centreon -u $CENTREON_USER -p $CENTREON_PASS \
    -o SERVICE -a setparam \
    -v "$HYCU_HOST;HYCU-VM-$VM;retry_check_interval;5"
done

# Appliquer la configuration
centreon -u $CENTREON_USER -p $CENTREON_PASS \
  -a applycfg -v "$POLLER"
```

### Modifier les Seuils Globalement

```bash
# Exemple: Modifier les seuils du service Jobs
centreon -u $CENTREON_USER -p $CENTREON_PASS \
  -o SERVICE -a setparam \
  -v "$HYCU_HOST;HYCU-Jobs-24h;check_command_arguments;!20!50!24!100"
# Nouveau: warning=20, critical=50

# Appliquer
centreon -u $CENTREON_USER -p $CENTREON_PASS \
  -a applycfg -v "$POLLER"
```

### Créer un Template de Service Réutilisable

```bash
# Créer un template pour les VMs
centreon -u $CENTREON_USER -p $CENTREON_PASS \
  -o STPL -a add \
  -v "HYCU-VM-Template;HYCU VM Backup Status;check_hycu_vm"

# Configurer le template
centreon -u $CENTREON_USER -p $CENTREON_PASS \
  -o STPL -a setparam \
  -v "HYCU-VM-Template;check_interval;15"

centreon -u $CENTREON_USER -p $CENTREON_PASS \
  -o STPL -a setparam \
  -v "HYCU-VM-Template;max_check_attempts;3"

# Utiliser le template pour créer un service
centreon -u $CENTREON_USER -p $CENTREON_PASS \
  -o SERVICE -a add \
  -v "$HYCU_HOST;HYCU-VM-TEST;HYCU-VM-Template"

# Définir la macro VMNAME
centreon -u $CENTREON_USER -p $CENTREON_PASS \
  -o SERVICE -a setmacro \
  -v "$HYCU_HOST;HYCU-VM-TEST;VMNAME;TEST-VM-NAME"
```

### Ajouter une Policy à Monitorer

```bash
POLICY_NAME="Production"

centreon -u $CENTREON_USER -p $CENTREON_PASS \
  -o SERVICE -a add \
  -v "$HYCU_HOST;HYCU-Policy-$POLICY_NAME;check_hycu_policy_advanced"

centreon -u $CENTREON_USER -p $CENTREON_PASS \
  -o SERVICE -a setparam \
  -v "$HYCU_HOST;HYCU-Policy-$POLICY_NAME;check_command_arguments;!$POLICY_NAME!3!5!100"

# Appliquer
centreon -u $CENTREON_USER -p $CENTREON_PASS \
  -a applycfg -v "$POLLER"
```

---

## Troubleshooting

### Erreur : "Return code end of file"

**Problème :** CLAPI ne peut pas se connecter

**Solution :**
```bash
# Vérifier les credentials
centreon -u $CENTREON_USER -p $CENTREON_PASS -o HOST -a show

# Si erreur, réinitialiser le password
mysql -u root centreon
UPDATE contact SET contact_passwd = MD5('nouveau_password') WHERE contact_alias = 'admin';
exit
```

### Erreur : "Object already exists"

**Problème :** Commande ou service existe déjà

**Solution :**
```bash
# Option 1: Supprimer et recréer
centreon -u $CENTREON_USER -p $CENTREON_PASS \
  -o CMD -a del -v "check_hycu_version"

# Option 2: Modifier l'existant
centreon -u $CENTREON_USER -p $CENTREON_PASS \
  -o CMD -a setparam \
  -v "check_hycu_version;command_line;\$USER1\$/check_hycu_vm_backup_v2.1.py ..."
```

### Services Restent en PENDING

**Problème :** Configuration non appliquée

**Solution :**
```bash
# Forcer l'export de configuration
centreon -u $CENTREON_USER -p $CENTREON_PASS \
  -a applycfg -v "$POLLER"

# Vérifier sur le poller
systemctl status centengine
tail -f /var/log/centreon-engine/centengine.log

# Forcer un check manuel
centreon -u $CENTREON_USER -p $CENTREON_PASS \
  -o HOST -a setparam \
  -v "$HYCU_HOST;check_command;check_hycu_port"
```

### Token Non Reconnu

**Problème :** $USER10$ non défini ou mal exporté

**Solution :**
```bash
# Vérifier la resource
centreon -u $CENTREON_USER -p $CENTREON_PASS \
  -o RESOURCECFG -a show

# Si absent, ajouter
centreon -u $CENTREON_USER -p $CENTREON_PASS \
  -o RESOURCECFG -a setparam \
  -v "1;\$USER10\$;$HYCU_TOKEN;HYCU Token"

# Exporter la resource
centreon -u $CENTREON_USER -p $CENTREON_PASS \
  -o POLLERRESOURCES -a export

# Recharger Centreon Engine
systemctl reload centengine
```

---

## Script Complet d'Import CSV

### Importer des VMs depuis CSV

Créer un fichier `vms.csv` :

```csv
VM_NAME,CHECK_INTERVAL,MAX_ATTEMPTS
PROD-DB-01,15,3
PROD-WEB-01,15,3
PROD-APP-01,30,3
DEV-TEST-01,60,2
```

Script d'import :

```bash
#!/bin/bash

CENTREON_USER="admin"
CENTREON_PASS="password"
HYCU_HOST="hycu.company.com"
POLLER="Central"

# Lire le CSV (skip header)
tail -n +2 vms.csv | while IFS=',' read -r VM_NAME CHECK_INTERVAL MAX_ATTEMPTS; do
  echo "Création service pour VM: $VM_NAME"
  
  # Créer le service
  centreon -u $CENTREON_USER -p $CENTREON_PASS \
    -o SERVICE -a add \
    -v "$HYCU_HOST;HYCU-VM-$VM_NAME;check_hycu_vm" 2>/dev/null
  
  # Configurer
  centreon -u $CENTREON_USER -p $CENTREON_PASS \
    -o SERVICE -a setparam \
    -v "$HYCU_HOST;HYCU-VM-$VM_NAME;check_command_arguments;!$VM_NAME!100"
  
  centreon -u $CENTREON_USER -p $CENTREON_PASS \
    -o SERVICE -a setparam \
    -v "$HYCU_HOST;HYCU-VM-$VM_NAME;check_interval;$CHECK_INTERVAL"
  
  centreon -u $CENTREON_USER -p $CENTREON_PASS \
    -o SERVICE -a setparam \
    -v "$HYCU_HOST;HYCU-VM-$VM_NAME;max_check_attempts;$MAX_ATTEMPTS"
done

# Appliquer la configuration
centreon -u $CENTREON_USER -p $CENTREON_PASS \
  -a applycfg -v "$POLLER"

echo "Import terminé !"
```

---

## Commandes CLAPI Utiles

### Lister les Objets

```bash
# Lister toutes les commandes
centreon -u admin -p password -o CMD -a show

# Lister tous les hosts
centreon -u admin -p password -o HOST -a show

# Lister tous les services d'un host
centreon -u admin -p password -o SERVICE -a show -v "hycu.company.com"

# Lister les resources
centreon -u admin -p password -o RESOURCECFG -a show

# Lister les host groups
centreon -u admin -p password -o HG -a show
```

### Modifier des Objets

```bash
# Modifier une commande
centreon -u admin -p password -o CMD -a setparam \
  -v "check_hycu_license;command_line;NOUVELLE_LIGNE"

# Modifier un paramètre de service
centreon -u admin -p password -o SERVICE -a setparam \
  -v "HYCU-HOST;SERVICE-NAME;check_interval;30"

# Activer/Désactiver un service
centreon -u admin -p password -o SERVICE -a setparam \
  -v "HYCU-HOST;SERVICE-NAME;activate;1"  # 1=actif, 0=inactif
```

### Supprimer des Objets

```bash
# Supprimer un service
centreon -u admin -p password -o SERVICE -a del \
  -v "HYCU-HOST;SERVICE-NAME"

# Supprimer un host
centreon -u admin -p password -o HOST -a del \
  -v "HYCU-HOST"

# Supprimer une commande
centreon -u admin -p password -o CMD -a del \
  -v "COMMAND-NAME"
```

---

## Conclusion

Avec CLAPI, vous pouvez :

✅ **Déployer en 5 minutes** au lieu de 2 heures  
✅ **Reproduire facilement** sur d'autres environnements  
✅ **Automatiser complètement** le déploiement  
✅ **Gérer plusieurs HYCU** avec un seul script  
✅ **Version contrôle** votre configuration (Git)  

**Le script fourni crée :**
- 12 commandes
- 1 host group
- 1 hôte HYCU
- 9 services globaux
- Configuration exportée et appliquée

**Temps total : ~5 minutes ! 🚀**

---

**Documentation officielle CLAPI :**
https://docs.centreon.com/docs/api/clapi/

**Pour toute question :**
- GitHub Issues
- Centreon Community Forums
