provider "aws" {
  region = var.region
}

locals {
  tags = {
    project      = var.project
    map-migrated = var.map_migrated_value
  }
}

data "aws_availability_zones" "azs" {
  state = "available"
}

########################
# VPC + Networking
########################

resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags                 = merge(local.tags, { Name = "${var.project}-vpc" })
}

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.main.id
  tags   = merge(local.tags, { Name = "${var.project}-igw" })
}

# Subnets
resource "aws_subnet" "public_a" {
  vpc_id                  = aws_vpc.main.id
  availability_zone       = data.aws_availability_zones.azs.names[0]
  cidr_block              = "10.0.0.0/24"
  map_public_ip_on_launch = true
  tags                    = merge(local.tags, { Name = "${var.project}-public-a" })
}

resource "aws_subnet" "public_b" {
  vpc_id                  = aws_vpc.main.id
  availability_zone       = data.aws_availability_zones.azs.names[1]
  cidr_block              = "10.0.1.0/24"
  map_public_ip_on_launch = true
  tags                    = merge(local.tags, { Name = "${var.project}-public-b" })
}

resource "aws_subnet" "private_a" {
  vpc_id            = aws_vpc.main.id
  availability_zone = data.aws_availability_zones.azs.names[0]
  cidr_block        = "10.0.10.0/24"
  tags              = merge(local.tags, { Name = "${var.project}-private-a" })
}

resource "aws_subnet" "private_b" {
  vpc_id            = aws_vpc.main.id
  availability_zone = data.aws_availability_zones.azs.names[1]
  cidr_block        = "10.0.11.0/24"
  tags              = merge(local.tags, { Name = "${var.project}-private-b" })
}

# Public route table -> IGW
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  tags   = merge(local.tags, { Name = "${var.project}-public-rt" })
}

resource "aws_route" "public_default" {
  route_table_id         = aws_route_table.public.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.igw.id
}

resource "aws_route_table_association" "public_a" {
  subnet_id      = aws_subnet.public_a.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "public_b" {
  subnet_id      = aws_subnet.public_b.id
  route_table_id = aws_route_table.public.id
}

# NAT for private subnets (needed for SSM + apt/docker pulls)
resource "aws_eip" "nat" {
  domain = "vpc"
  tags   = merge(local.tags, { Name = "${var.project}-nat-eip" })
}

resource "aws_nat_gateway" "nat" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public_a.id
  tags          = merge(local.tags, { Name = "${var.project}-nat" })
  depends_on    = [aws_internet_gateway.igw]
}

# Private route table -> NAT
resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id
  tags   = merge(local.tags, { Name = "${var.project}-private-rt" })
}

resource "aws_route" "private_default" {
  route_table_id         = aws_route_table.private.id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = aws_nat_gateway.nat.id
}

resource "aws_route_table_association" "private_a" {
  subnet_id      = aws_subnet.private_a.id
  route_table_id = aws_route_table.private.id
}

resource "aws_route_table_association" "private_b" {
  subnet_id      = aws_subnet.private_b.id
  route_table_id = aws_route_table.private.id
}

########################
# Security Groups
########################

# ALB SG: allow inbound HTTP from internet (no HTTPS yet)
resource "aws_security_group" "alb" {
  name   = "${var.project}-alb-sg"
  vpc_id = aws_vpc.main.id

  ingress {
    description = "HTTP from internet"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.tags, { Name = "${var.project}-alb-sg" })
}

# EC2 SG: ONLY allow app port 8000 from ALB SG
resource "aws_security_group" "ec2" {
  name   = "${var.project}-ec2-sg"
  vpc_id = aws_vpc.main.id

  ingress {
    description     = "App from ALB only"
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.tags, { Name = "${var.project}-ec2-sg" })
}

# RDS SG: ONLY allow Postgres from EC2 SG
resource "aws_security_group" "rds" {
  name   = "${var.project}-rds-sg"
  vpc_id = aws_vpc.main.id

  ingress {
    description     = "Postgres from EC2 only"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ec2.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.tags, { Name = "${var.project}-rds-sg" })
}

########################
# IAM for SSM (EC2 only)
########################

resource "aws_iam_role" "ec2_ssm" {
  name = "${var.project}-ec2-ssm-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Principal = { Service = "ec2.amazonaws.com" },
      Action = "sts:AssumeRole"
    }]
  })

  tags = local.tags
}

resource "aws_iam_role_policy_attachment" "ssm_core" {
  role       = aws_iam_role.ec2_ssm.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "ec2_profile" {
  name = "${var.project}-ec2-profile"
  role = aws_iam_role.ec2_ssm.name
  tags = local.tags
}

########################
# EC2 (private, SSM only)
########################

data "aws_ami" "ubuntu_2204" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_instance" "app" {
  ami                         = data.aws_ami.ubuntu_2204.id
  instance_type               = var.instance_type
  subnet_id                   = aws_subnet.private_a.id
  vpc_security_group_ids      = [aws_security_group.ec2.id]
  iam_instance_profile        = aws_iam_instance_profile.ec2_profile.name
  associate_public_ip_address = false

  tags = merge(local.tags, { Name = "${var.project}-app" })
}

########################
# ALB (public) -> EC2 (private:8000)
########################

resource "aws_lb" "app" {
  name               = "${var.project}-alb"
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = [aws_subnet.public_a.id, aws_subnet.public_b.id]
  tags               = merge(local.tags, { Name = "${var.project}-alb" })
}

resource "aws_lb_target_group" "app" {
  name        = "${var.project}-tg"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "instance"

  health_check {
    path                = "/"
    protocol            = "HTTP"
    matcher             = "200-399"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }

  tags = merge(local.tags, { Name = "${var.project}-tg" })
}

resource "aws_lb_target_group_attachment" "app" {
  target_group_arn = aws_lb_target_group.app.arn
  target_id        = aws_instance.app.id
  port             = 8000
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.app.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }
}

########################
# RDS Postgres (private)
########################

resource "aws_db_subnet_group" "db" {
  name       = "${var.project}-db-subnets"
  subnet_ids = [aws_subnet.private_a.id, aws_subnet.private_b.id]
  tags       = merge(local.tags, { Name = "${var.project}-db-subnets" })
}

resource "aws_db_instance" "postgres" {
  identifier             = "${var.project}-postgres"
  engine                 = "postgres"

  instance_class         = "db.t3.micro"
  allocated_storage      = 20
  storage_type           = "gp3"

  db_name                = var.db_name
  username               = var.db_username
  password               = var.db_password

  vpc_security_group_ids = [aws_security_group.rds.id]
  db_subnet_group_name   = aws_db_subnet_group.db.name
  publicly_accessible    = false

  skip_final_snapshot    = true
  deletion_protection    = false

  tags = merge(local.tags, { Name = "${var.project}-postgres" })
}
