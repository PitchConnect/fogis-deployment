# FOGIS Deployment - Terraform Configuration
# Generated from fogis-config.yaml

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
  }
}

# Configure AWS Provider
provider "aws" {
  region = var.aws_region
}

# Configure Docker Provider
provider "docker" {}

# VPC Configuration
resource "aws_vpc" "fogis_vpc" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name        = "fogis-vpc"
    Environment = var.environment
    Project     = "FOGIS"
  }
}

# Internet Gateway
resource "aws_internet_gateway" "fogis_igw" {
  vpc_id = aws_vpc.fogis_vpc.id

  tags = {
    Name = "fogis-igw"
  }
}

# Public Subnet
resource "aws_subnet" "fogis_public_subnet" {
  vpc_id                  = aws_vpc.fogis_vpc.id
  cidr_block              = var.public_subnet_cidr
  availability_zone       = var.availability_zone
  map_public_ip_on_launch = true

  tags = {
    Name = "fogis-public-subnet"
  }
}

# Route Table
resource "aws_route_table" "fogis_public_rt" {
  vpc_id = aws_vpc.fogis_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.fogis_igw.id
  }

  tags = {
    Name = "fogis-public-rt"
  }
}

# Route Table Association
resource "aws_route_table_association" "fogis_public_rta" {
  subnet_id      = aws_subnet.fogis_public_subnet.id
  route_table_id = aws_route_table.fogis_public_rt.id
}

# Security Group
resource "aws_security_group" "fogis_sg" {
  name_prefix = "fogis-sg"
  vpc_id      = aws_vpc.fogis_vpc.id

  # SSH access
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.allowed_cidr]
  }

  # HTTP access
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # HTTPS access
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # FOGIS service ports
  ingress {
    from_port   = 9083
    to_port     = 9083
    protocol    = "tcp"
    cidr_blocks = [var.allowed_cidr]
  }

  ingress {
    from_port   = 9085
    to_port     = 9085
    protocol    = "tcp"
    cidr_blocks = [var.allowed_cidr]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "fogis-security-group"
  }
}

# EC2 Instance
resource "aws_instance" "fogis_server" {
  ami                    = var.ami_id
  instance_type          = var.instance_type
  key_name              = var.key_pair_name
  vpc_security_group_ids = [aws_security_group.fogis_sg.id]
  subnet_id             = aws_subnet.fogis_public_subnet.id

  user_data = base64encode(templatefile("${path.module}/user_data.sh", {
    docker_compose_version = var.docker_compose_version
  }))

  tags = {
    Name        = "fogis-server"
    Environment = var.environment
    Project     = "FOGIS"
  }
}

# Elastic IP
resource "aws_eip" "fogis_eip" {
  instance = aws_instance.fogis_server.id
  domain   = "vpc"

  tags = {
    Name = "fogis-eip"
  }
}
