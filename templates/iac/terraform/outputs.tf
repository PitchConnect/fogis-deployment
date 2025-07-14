# FOGIS Deployment - Terraform Outputs

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
