#!/usr/bin/env python3
"""
Infrastructure as Code Generator for FOGIS Deployment
Generate Terraform, Ansible, and Kubernetes templates

This module generates Infrastructure as Code templates for:
- Terraform: Cloud infrastructure provisioning
- Ansible: Configuration management and deployment
- Kubernetes: Container orchestration manifests
"""

import logging
from pathlib import Path
from typing import Any, Dict, List

import yaml

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IaCGeneratorError(Exception):
    """Exception raised for IaC generation errors"""


class IaCGenerator:
    """
    Infrastructure as Code generator for FOGIS deployment

    Generates deployment templates for multiple platforms:
    - Terraform: AWS, GCP, Azure infrastructure
    - Ansible: Server configuration and deployment
    - Kubernetes: Container orchestration
    """

    def __init__(self, config_file: str = "fogis-config.yaml"):
        """
        Initialize IaC generator

        Args:
            config_file: Path to FOGIS configuration file
        """
        self.config_file = config_file
        self.config = self._load_config()
        self.templates_dir = Path("templates/iac")
        self.templates_dir.mkdir(parents=True, exist_ok=True)

    def _load_config(self) -> Dict[str, Any]:
        """Load FOGIS configuration"""
        try:
            with open(self.config_file, "r") as f:
                return yaml.safe_load(f)
        except Exception as e:
            raise IaCGeneratorError(f"Failed to load config: {e}")

    def generate_all_templates(self) -> Dict[str, List[str]]:
        """
        Generate all IaC templates

        Returns:
            Dictionary mapping platform to list of generated files
        """
        logger.info("Generating all Infrastructure as Code templates...")

        results = {
            "terraform": self.generate_terraform_templates(),
            "ansible": self.generate_ansible_templates(),
            "kubernetes": self.generate_kubernetes_templates(),
        }

        logger.info("All IaC templates generated successfully")
        return results

    def generate_terraform_templates(self) -> List[str]:
        """
        Generate Terraform templates

        Returns:
            List of generated Terraform files
        """
        logger.info("Generating Terraform templates...")

        terraform_dir = self.templates_dir / "terraform"
        terraform_dir.mkdir(exist_ok=True)

        generated_files = []

        # Generate main.tf
        main_tf = self._generate_terraform_main()
        main_tf_path = terraform_dir / "main.tf"
        with open(main_tf_path, "w") as f:
            f.write(main_tf)
        generated_files.append(str(main_tf_path))

        # Generate variables.tf
        variables_tf = self._generate_terraform_variables()
        variables_tf_path = terraform_dir / "variables.tf"
        with open(variables_tf_path, "w") as f:
            f.write(variables_tf)
        generated_files.append(str(variables_tf_path))

        # Generate outputs.tf
        outputs_tf = self._generate_terraform_outputs()
        outputs_tf_path = terraform_dir / "outputs.tf"
        with open(outputs_tf_path, "w") as f:
            f.write(outputs_tf)
        generated_files.append(str(outputs_tf_path))

        # Generate terraform.tfvars.example
        tfvars = self._generate_terraform_tfvars()
        tfvars_path = terraform_dir / "terraform.tfvars.example"
        with open(tfvars_path, "w") as f:
            f.write(tfvars)
        generated_files.append(str(tfvars_path))

        logger.info(f"Generated {len(generated_files)} Terraform files")
        return generated_files

    def _generate_terraform_main(self) -> str:
        """Generate Terraform main configuration"""
        services = self.config.get("services", {})
        ports = services.get("ports", {})

        return f"""# FOGIS Deployment - Terraform Configuration
# Generated from {self.config_file}

terraform {{
  required_version = ">= 1.0"
  required_providers {{
    aws = {{
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }}
    docker = {{
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }}
  }}
}}

# Configure AWS Provider
provider "aws" {{
  region = var.aws_region
}}

# Configure Docker Provider
provider "docker" {{}}

# VPC Configuration
resource "aws_vpc" "fogis_vpc" {{
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {{
    Name        = "fogis-vpc"
    Environment = var.environment
    Project     = "FOGIS"
  }}
}}

# Internet Gateway
resource "aws_internet_gateway" "fogis_igw" {{
  vpc_id = aws_vpc.fogis_vpc.id

  tags = {{
    Name = "fogis-igw"
  }}
}}

# Public Subnet
resource "aws_subnet" "fogis_public_subnet" {{
  vpc_id                  = aws_vpc.fogis_vpc.id
  cidr_block              = var.public_subnet_cidr
  availability_zone       = var.availability_zone
  map_public_ip_on_launch = true

  tags = {{
    Name = "fogis-public-subnet"
  }}
}}

# Route Table
resource "aws_route_table" "fogis_public_rt" {{
  vpc_id = aws_vpc.fogis_vpc.id

  route {{
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.fogis_igw.id
  }}

  tags = {{
    Name = "fogis-public-rt"
  }}
}}

# Route Table Association
resource "aws_route_table_association" "fogis_public_rta" {{
  subnet_id      = aws_subnet.fogis_public_subnet.id
  route_table_id = aws_route_table.fogis_public_rt.id
}}

# Security Group
resource "aws_security_group" "fogis_sg" {{
  name_prefix = "fogis-sg"
  vpc_id      = aws_vpc.fogis_vpc.id

  # SSH access
  ingress {{
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.allowed_cidr]
  }}

  # HTTP access
  ingress {{
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }}

  # HTTPS access
  ingress {{
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }}

  # FOGIS service ports
  ingress {{
    from_port   = {ports.get("calendar_sync", 8080)}
    to_port     = {ports.get("calendar_sync", 8080)}
    protocol    = "tcp"
    cidr_blocks = [var.allowed_cidr]
  }}

  ingress {{
    from_port   = {ports.get("google_drive", 8081)}
    to_port     = {ports.get("google_drive", 8081)}
    protocol    = "tcp"
    cidr_blocks = [var.allowed_cidr]
  }}

  egress {{
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }}

  tags = {{
    Name = "fogis-security-group"
  }}
}}

# EC2 Instance
resource "aws_instance" "fogis_server" {{
  ami                    = var.ami_id
  instance_type          = var.instance_type
  key_name              = var.key_pair_name
  vpc_security_group_ids = [aws_security_group.fogis_sg.id]
  subnet_id             = aws_subnet.fogis_public_subnet.id

  user_data = base64encode(templatefile("${{path.module}}/user_data.sh", {{
    docker_compose_version = var.docker_compose_version
  }}))

  tags = {{
    Name        = "fogis-server"
    Environment = var.environment
    Project     = "FOGIS"
  }}
}}

# Elastic IP
resource "aws_eip" "fogis_eip" {{
  instance = aws_instance.fogis_server.id
  domain   = "vpc"

  tags = {{
    Name = "fogis-eip"
  }}
}}
"""

    def _generate_terraform_variables(self) -> str:
        """Generate Terraform variables configuration"""
        return """# FOGIS Deployment - Terraform Variables

variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-west-2"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "prod"
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidr" {
  description = "CIDR block for public subnet"
  type        = string
  default     = "10.0.1.0/24"
}

variable "availability_zone" {
  description = "Availability zone for resources"
  type        = string
  default     = "us-west-2a"
}

variable "allowed_cidr" {
  description = "CIDR block allowed to access FOGIS services"
  type        = string
  default     = "0.0.0.0/0"
}

variable "ami_id" {
  description = "AMI ID for EC2 instance (Ubuntu 22.04 LTS)"
  type        = string
  default     = "ami-0c02fb55956c7d316"  # Ubuntu 22.04 LTS in us-west-2
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.medium"
}

variable "key_pair_name" {
  description = "Name of AWS key pair for SSH access"
  type        = string
}

variable "docker_compose_version" {
  description = "Docker Compose version to install"
  type        = string
  default     = "2.21.0"
}
"""

    def _generate_terraform_outputs(self) -> str:
        """Generate Terraform outputs configuration"""
        return """# FOGIS Deployment - Terraform Outputs

output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.fogis_vpc.id
}

output "public_subnet_id" {
  description = "ID of the public subnet"
  value       = aws_subnet.fogis_public_subnet.id
}

output "security_group_id" {
  description = "ID of the security group"
  value       = aws_security_group.fogis_sg.id
}

output "instance_id" {
  description = "ID of the EC2 instance"
  value       = aws_instance.fogis_server.id
}

output "instance_public_ip" {
  description = "Public IP address of the instance"
  value       = aws_eip.fogis_eip.public_ip
}

output "instance_private_ip" {
  description = "Private IP address of the instance"
  value       = aws_instance.fogis_server.private_ip
}

output "ssh_connection_command" {
  description = "SSH command to connect to the instance"
  value       = "ssh -i ~/.ssh/${var.key_pair_name}.pem ubuntu@${aws_eip.fogis_eip.public_ip}"
}

output "fogis_urls" {
  description = "URLs for FOGIS services"
  value = {
    calendar_sync = "http://${aws_eip.fogis_eip.public_ip}:8080"
    google_drive  = "http://${aws_eip.fogis_eip.public_ip}:8081"
  }
}
"""

    def _generate_terraform_tfvars(self) -> str:
        """Generate Terraform tfvars example"""
        return """# FOGIS Deployment - Terraform Variables Example
# Copy this file to terraform.tfvars and customize values

# AWS Configuration
aws_region = "us-west-2"
environment = "prod"

# Network Configuration
vpc_cidr = "10.0.0.0/16"
public_subnet_cidr = "10.0.1.0/24"
availability_zone = "us-west-2a"

# Security Configuration
allowed_cidr = "0.0.0.0/0"  # Restrict this to your IP range for security

# Instance Configuration
ami_id = "ami-0c02fb55956c7d316"  # Ubuntu 22.04 LTS
instance_type = "t3.medium"
key_pair_name = "your-key-pair-name"  # Replace with your AWS key pair

# Software Versions
docker_compose_version = "2.21.0"
"""

    def generate_ansible_templates(self) -> List[str]:
        """
        Generate Ansible templates

        Returns:
            List of generated Ansible files
        """
        logger.info("Generating Ansible templates...")

        ansible_dir = self.templates_dir / "ansible"
        ansible_dir.mkdir(exist_ok=True)

        generated_files = []

        # Generate playbook.yml
        playbook = self._generate_ansible_playbook()
        playbook_path = ansible_dir / "playbook.yml"
        with open(playbook_path, "w") as f:
            f.write(playbook)
        generated_files.append(str(playbook_path))

        # Generate inventory.yml
        inventory = self._generate_ansible_inventory()
        inventory_path = ansible_dir / "inventory.yml"
        with open(inventory_path, "w") as f:
            f.write(inventory)
        generated_files.append(str(inventory_path))

        # Generate group_vars
        group_vars_dir = ansible_dir / "group_vars"
        group_vars_dir.mkdir(exist_ok=True)

        group_vars = self._generate_ansible_group_vars()
        group_vars_path = group_vars_dir / "all.yml"
        with open(group_vars_path, "w") as f:
            f.write(group_vars)
        generated_files.append(str(group_vars_path))

        logger.info(f"Generated {len(generated_files)} Ansible files")
        return generated_files

    def _generate_ansible_playbook(self) -> str:
        """Generate Ansible playbook"""
        services = self.config.get("services", {})

        return f"""---
# FOGIS Deployment - Ansible Playbook
# Generated from {self.config_file}

- name: Deploy FOGIS System
  hosts: fogis_servers
  become: yes
  vars:
    fogis_user: "{{{{ ansible_user }}}}"
    fogis_home: "/home/{{{{ fogis_user }}}}/fogis-deployment"
    docker_compose_version: "2.21.0"

  tasks:
    - name: Update system packages
      apt:
        update_cache: yes
        upgrade: dist
        cache_valid_time: 3600

    - name: Install required packages
      apt:
        name:
          - apt-transport-https
          - ca-certificates
          - curl
          - gnupg
          - lsb-release
          - git
          - python3
          - python3-pip
          - python3-venv
        state: present

    - name: Add Docker GPG key
      apt_key:
        url: https://download.docker.com/linux/ubuntu/gpg
        state: present

    - name: Add Docker repository
      apt_repository:
        repo: "deb [arch=amd64] https://download.docker.com/linux/ubuntu {{{{ ansible_distribution_release }}}} stable"
        state: present

    - name: Install Docker
      apt:
        name:
          - docker-ce
          - docker-ce-cli
          - containerd.io
          - docker-buildx-plugin
          - docker-compose-plugin
        state: present

    - name: Add user to docker group
      user:
        name: "{{{{ fogis_user }}}}"
        groups: docker
        append: yes

    - name: Start and enable Docker service
      systemd:
        name: docker
        state: started
        enabled: yes

    - name: Create FOGIS directory
      file:
        path: "{{{{ fogis_home }}}}"
        state: directory
        owner: "{{{{ fogis_user }}}}"
        group: "{{{{ fogis_user }}}}"
        mode: '0755'

    - name: Clone FOGIS repository
      git:
        repo: "{{{{ fogis_repo_url }}}}"
        dest: "{{{{ fogis_home }}}}"
        version: "{{{{ fogis_repo_branch | default('main') }}}}"
        force: yes
      become_user: "{{{{ fogis_user }}}}"

    - name: Copy FOGIS configuration
      template:
        src: fogis-config.yaml.j2
        dest: "{{{{ fogis_home }}}}/fogis-config.yaml"
        owner: "{{{{ fogis_user }}}}"
        group: "{{{{ fogis_user }}}}"
        mode: '0644'
      become_user: "{{{{ fogis_user }}}}"

    - name: Copy OAuth credentials
      copy:
        src: "{{{{ oauth_credentials_file }}}}"
        dest: "{{{{ fogis_home }}}}/credentials.json"
        owner: "{{{{ fogis_user }}}}"
        group: "{{{{ fogis_user }}}}"
        mode: '0600'
      become_user: "{{{{ fogis_user }}}}"
      when: oauth_credentials_file is defined

    - name: Generate FOGIS configuration files
      command: ./manage_fogis_system.sh config-generate
      args:
        chdir: "{{{{ fogis_home }}}}"
      become_user: "{{{{ fogis_user }}}}"

    - name: Start FOGIS services
      command: docker compose up -d
      args:
        chdir: "{{{{ fogis_home }}}}"
      become_user: "{{{{ fogis_user }}}}"

    - name: Wait for services to be ready
      wait_for:
        port: "{{{{ item }}}}"
        host: localhost
        delay: 10
        timeout: 300
      loop:
        - {services.get("ports", {}).get("calendar_sync", 8080)}
        - {services.get("ports", {}).get("google_drive", 8081)}

    - name: Create systemd service for FOGIS
      template:
        src: fogis.service.j2
        dest: /etc/systemd/system/fogis.service
        mode: '0644'
      notify: reload systemd

    - name: Enable FOGIS service
      systemd:
        name: fogis
        enabled: yes
        daemon_reload: yes

  handlers:
    - name: reload systemd
      systemd:
        daemon_reload: yes
"""

    def _generate_ansible_inventory(self) -> str:
        """Generate Ansible inventory"""
        return """# FOGIS Deployment - Ansible Inventory
# Generated inventory file

all:
  children:
    fogis_servers:
      hosts:
        fogis-server-1:
          ansible_host: 192.168.1.100  # Replace with your server IP
          ansible_user: ubuntu
          ansible_ssh_private_key_file: ~/.ssh/your-key.pem
        # Add more servers as needed
        # fogis-server-2:
        #   ansible_host: 192.168.1.101
        #   ansible_user: ubuntu
        #   ansible_ssh_private_key_file: ~/.ssh/your-key.pem
      vars:
        # Common variables for all FOGIS servers
        fogis_repo_url: "https://github.com/PitchConnect/fogis-deployment.git"
        fogis_repo_branch: "main"
        # oauth_credentials_file: "/path/to/your/credentials.json"
"""

    def _generate_ansible_group_vars(self) -> str:
        """Generate Ansible group variables"""
        fogis_config = self.config.get("fogis", {})
        services = self.config.get("services", {})

        return f"""---
# FOGIS Deployment - Ansible Group Variables
# Generated from {self.config_file}

# FOGIS Configuration
fogis_username: "{fogis_config.get("username", "")}"
fogis_password: "{fogis_config.get("password", "")}"
user_referee_number: {fogis_config.get("referee_number", 0)}

# Service Configuration
calendar_sync_port: {services.get("ports", {}).get("calendar_sync", 8080)}
google_drive_port: {services.get("ports", {}).get("google_drive", 8081)}

# Docker Configuration
docker_compose_version: "2.21.0"

# System Configuration
timezone: "Europe/Stockholm"
locale: "en_US.UTF-8"

# Security Configuration
firewall_enabled: true
fail2ban_enabled: true

# Monitoring Configuration
monitoring_enabled: true
log_retention_days: 30

# Backup Configuration
backup_enabled: true
backup_schedule: "0 2 * * *"  # Daily at 2 AM
backup_retention_days: 30
"""

    def generate_kubernetes_templates(self) -> List[str]:
        """
        Generate Kubernetes templates

        Returns:
            List of generated Kubernetes files
        """
        logger.info("Generating Kubernetes templates...")

        k8s_dir = self.templates_dir / "kubernetes"
        k8s_dir.mkdir(exist_ok=True)

        generated_files = []

        # Generate namespace
        namespace = self._generate_k8s_namespace()
        namespace_path = k8s_dir / "namespace.yaml"
        with open(namespace_path, "w") as f:
            f.write(namespace)
        generated_files.append(str(namespace_path))

        # Generate configmap
        configmap = self._generate_k8s_configmap()
        configmap_path = k8s_dir / "configmap.yaml"
        with open(configmap_path, "w") as f:
            f.write(configmap)
        generated_files.append(str(configmap_path))

        # Generate secrets
        secrets = self._generate_k8s_secrets()
        secrets_path = k8s_dir / "secrets.yaml"
        with open(secrets_path, "w") as f:
            f.write(secrets)
        generated_files.append(str(secrets_path))

        # Generate deployments
        deployments = self._generate_k8s_deployments()
        deployments_path = k8s_dir / "deployments.yaml"
        with open(deployments_path, "w") as f:
            f.write(deployments)
        generated_files.append(str(deployments_path))

        # Generate services
        services = self._generate_k8s_services()
        services_path = k8s_dir / "services.yaml"
        with open(services_path, "w") as f:
            f.write(services)
        generated_files.append(str(services_path))

        logger.info(f"Generated {len(generated_files)} Kubernetes files")
        return generated_files

    def _generate_k8s_namespace(self) -> str:
        """Generate Kubernetes namespace"""
        return """# FOGIS Deployment - Kubernetes Namespace
apiVersion: v1
kind: Namespace
metadata:
  name: fogis
  labels:
    name: fogis
    app: fogis-deployment
"""

    def _generate_k8s_configmap(self) -> str:
        """Generate Kubernetes ConfigMap"""
        fogis_config = self.config.get("fogis", {})
        services = self.config.get("services", {})

        return f"""# FOGIS Deployment - Kubernetes ConfigMap
apiVersion: v1
kind: ConfigMap
metadata:
  name: fogis-config
  namespace: fogis
  labels:
    app: fogis-deployment
data:
  # FOGIS Configuration
  FOGIS_USERNAME: "{fogis_config.get("username", "")}"
  USER_REFEREE_NUMBER: "{fogis_config.get("referee_number", 0)}"

  # Service Ports
  CALENDAR_SYNC_PORT: "{services.get("ports", {}).get("calendar_sync", 8080)}"
  GOOGLE_DRIVE_PORT: "{services.get("ports", {}).get("google_drive", 8081)}"

  # Application Configuration
  LOG_LEVEL: "INFO"
  TIMEZONE: "Europe/Stockholm"

  # Google Configuration
  GOOGLE_CALENDAR_ID: "primary"
  GOOGLE_DRIVE_FOLDER: "WhatsApp_Group_Assets"
"""

    def _generate_k8s_secrets(self) -> str:
        """Generate Kubernetes Secrets"""
        return """# FOGIS Deployment - Kubernetes Secrets
# Note: Replace base64 encoded values with your actual credentials
apiVersion: v1
kind: Secret
metadata:
  name: fogis-secrets
  namespace: fogis
  labels:
    app: fogis-deployment
type: Opaque
data:
  # Base64 encoded FOGIS password
  FOGIS_PASSWORD: ""  # echo -n "your-password" | base64

  # Base64 encoded Google OAuth credentials
  GOOGLE_CREDENTIALS: ""  # base64 < credentials.json
---
apiVersion: v1
kind: Secret
metadata:
  name: fogis-oauth-tokens
  namespace: fogis
  labels:
    app: fogis-deployment
type: Opaque
data:
  # Base64 encoded OAuth tokens (will be populated by init containers)
  CALENDAR_TOKEN: ""
  DRIVE_TOKEN: ""
  CONTACTS_TOKEN: ""
"""

    def _generate_k8s_deployments(self) -> str:
        """Generate Kubernetes Deployments"""
        services = self.config.get("services", {})
        ports = services.get("ports", {})

        return f"""# FOGIS Deployment - Kubernetes Deployments
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fogis-calendar-sync
  namespace: fogis
  labels:
    app: fogis-calendar-sync
spec:
  replicas: 1
  selector:
    matchLabels:
      app: fogis-calendar-sync
  template:
    metadata:
      labels:
        app: fogis-calendar-sync
    spec:
      containers:
      - name: calendar-sync
        image: ghcr.io/pitchconnect/fogis-calendar-phonebook-sync:latest
        ports:
        - containerPort: {ports.get("calendar_sync", 8080)}
        env:
        - name: FOGIS_USERNAME
          valueFrom:
            configMapKeyRef:
              name: fogis-config
              key: FOGIS_USERNAME
        - name: FOGIS_PASSWORD
          valueFrom:
            secretKeyRef:
              name: fogis-secrets
              key: FOGIS_PASSWORD
        - name: USER_REFEREE_NUMBER
          valueFrom:
            configMapKeyRef:
              name: fogis-config
              key: USER_REFEREE_NUMBER
        volumeMounts:
        - name: oauth-credentials
          mountPath: /app/credentials.json
          subPath: credentials.json
          readOnly: true
        - name: oauth-tokens
          mountPath: /app/token.json
          subPath: calendar-token.json
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
      volumes:
      - name: oauth-credentials
        secret:
          secretName: fogis-secrets
          items:
          - key: GOOGLE_CREDENTIALS
            path: credentials.json
      - name: oauth-tokens
        secret:
          secretName: fogis-oauth-tokens
          items:
          - key: CALENDAR_TOKEN
            path: calendar-token.json
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fogis-google-drive
  namespace: fogis
  labels:
    app: fogis-google-drive
spec:
  replicas: 1
  selector:
    matchLabels:
      app: fogis-google-drive
  template:
    metadata:
      labels:
        app: fogis-google-drive
    spec:
      containers:
      - name: google-drive
        image: ghcr.io/pitchconnect/google-drive-service:latest
        ports:
        - containerPort: {ports.get("google_drive", 8081)}
        env:
        - name: GOOGLE_DRIVE_FOLDER
          valueFrom:
            configMapKeyRef:
              name: fogis-config
              key: GOOGLE_DRIVE_FOLDER
        volumeMounts:
        - name: oauth-credentials
          mountPath: /app/credentials.json
          subPath: credentials.json
          readOnly: true
        - name: oauth-tokens
          mountPath: /app/token.json
          subPath: drive-token.json
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
      volumes:
      - name: oauth-credentials
        secret:
          secretName: fogis-secrets
          items:
          - key: GOOGLE_CREDENTIALS
            path: credentials.json
      - name: oauth-tokens
        secret:
          secretName: fogis-oauth-tokens
          items:
          - key: DRIVE_TOKEN
            path: drive-token.json
"""

    def _generate_k8s_services(self) -> str:
        """Generate Kubernetes Services"""
        services = self.config.get("services", {})
        ports = services.get("ports", {})

        return f"""# FOGIS Deployment - Kubernetes Services
apiVersion: v1
kind: Service
metadata:
  name: fogis-calendar-sync-service
  namespace: fogis
  labels:
    app: fogis-calendar-sync
spec:
  selector:
    app: fogis-calendar-sync
  ports:
  - name: http
    port: 80
    targetPort: {ports.get("calendar_sync", 8080)}
    protocol: TCP
  type: ClusterIP
---
apiVersion: v1
kind: Service
metadata:
  name: fogis-google-drive-service
  namespace: fogis
  labels:
    app: fogis-google-drive
spec:
  selector:
    app: fogis-google-drive
  ports:
  - name: http
    port: 80
    targetPort: {ports.get("google_drive", 8081)}
    protocol: TCP
  type: ClusterIP
---
# LoadBalancer service for external access (optional)
apiVersion: v1
kind: Service
metadata:
  name: fogis-external-service
  namespace: fogis
  labels:
    app: fogis-deployment
spec:
  selector:
    app: fogis-calendar-sync  # Primary service
  ports:
  - name: calendar-sync
    port: {ports.get("calendar_sync", 8080)}
    targetPort: {ports.get("calendar_sync", 8080)}
    protocol: TCP
  type: LoadBalancer
"""


def main():
    """
    Main function for IaC generator CLI
    """
    import sys

    if len(sys.argv) < 2:
        print("Usage: python iac_generator.py <command> [args]")
        print("Commands: all, terraform, ansible, kubernetes")
        sys.exit(1)

    command = sys.argv[1]
    config_file = sys.argv[2] if len(sys.argv) > 2 else "fogis-config.yaml"

    try:
        generator = IaCGenerator(config_file)

        if command == "all":
            results = generator.generate_all_templates()
            print("Generated Infrastructure as Code templates:")
            for platform, files in results.items():
                print(f"  {platform.title()}:")
                for file in files:
                    print(f"    - {file}")

        elif command == "terraform":
            files = generator.generate_terraform_templates()
            print(f"Generated {len(files)} Terraform files:")
            for file in files:
                print(f"  - {file}")

        elif command == "ansible":
            files = generator.generate_ansible_templates()
            print(f"Generated {len(files)} Ansible files:")
            for file in files:
                print(f"  - {file}")

        elif command == "kubernetes":
            files = generator.generate_kubernetes_templates()
            print(f"Generated {len(files)} Kubernetes files:")
            for file in files:
                print(f"  - {file}")

        else:
            print(f"Unknown command: {command}")
            sys.exit(1)

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
