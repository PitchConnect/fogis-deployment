# FOGIS Infrastructure as Code Templates

This directory contains Infrastructure as Code (IaC) templates for deploying FOGIS across different platforms and environments.

## Available Templates

### 🏗️ Terraform (AWS)
- **Location**: `terraform/`
- **Purpose**: Provision AWS infrastructure for FOGIS deployment
- **Includes**: VPC, EC2, Security Groups, Load Balancers
- **Target**: Cloud infrastructure provisioning

### 🔧 Ansible
- **Location**: `ansible/`
- **Purpose**: Configure servers and deploy FOGIS services
- **Includes**: Playbooks, inventory, configuration templates
- **Target**: Configuration management and deployment

### ☸️ Kubernetes
- **Location**: `kubernetes/`
- **Purpose**: Container orchestration for FOGIS services
- **Includes**: Deployments, Services, ConfigMaps, Secrets
- **Target**: Container orchestration platforms

## Quick Start

### Generate Templates
```bash
# Generate all templates
./manage_fogis_system.sh iac-generate all

# Generate specific platform
./manage_fogis_system.sh iac-generate terraform
./manage_fogis_system.sh iac-generate ansible
./manage_fogis_system.sh iac-generate kubernetes
```

### Terraform Deployment
```bash
cd templates/iac/terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values
terraform init
terraform plan
terraform apply
```

### Ansible Deployment
```bash
cd templates/iac/ansible
# Edit inventory.yml with your server details
# Edit group_vars/all.yml with your configuration
ansible-playbook -i inventory.yml playbook.yml
```

### Kubernetes Deployment
```bash
cd templates/iac/kubernetes
kubectl apply -f namespace.yaml
kubectl apply -f configmap.yaml
kubectl apply -f secrets.yaml
kubectl apply -f deployments.yaml
kubectl apply -f services.yaml
kubectl apply -f ingress.yaml
```

## Template Customization

All templates are generated from your `fogis-config.yaml` configuration file. To customize:

1. Update your `fogis-config.yaml`
2. Regenerate templates: `./manage_fogis_system.sh iac-generate all`
3. Review and deploy updated templates

## Platform-Specific Documentation

- [Terraform README](terraform/README.md)
- [Ansible README](ansible/README.md)
- [Kubernetes README](kubernetes/README.md)

## Support

For issues or questions:
- GitHub Issues: https://github.com/PitchConnect/fogis-deployment/issues
- Documentation: docs/INFRASTRUCTURE.md
