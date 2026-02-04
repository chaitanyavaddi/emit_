output "alb_dns_name" {
  value = aws_lb.app.dns_name
}

output "ec2_instance_id" {
  value = aws_instance.app.id
}

output "rds_endpoint" {
  value = aws_db_instance.postgres.address
}

# Connect to RDS Database
# aws ssm start-session \ 
#   --target i-0a5611e7f75b9c216 \
#   --document-name AWS-StartPortForwardingSessionToRemoteHost \
#   --parameters '{"host":["emit-postgres.c6li6uc2gfzs.us-east-1.rds.amazonaws.com"],"portNumber":["5432"],"localPortNumber":["15432"]}' \
#   --region us-east-1

# Manual Deployment - Connect via SSM
# aws ssm start-session --target i-0a5611e7f75b9c216 --region us-east-1
