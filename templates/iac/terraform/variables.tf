# FOGIS Deployment - Terraform Variables

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
