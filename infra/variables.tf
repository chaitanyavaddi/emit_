variable "region" {
  type    = string
  default = "us-east-1"
}

variable "project" {
  type    = string
  default = "emit"
}

variable "map_migrated_value" {
  type    = string
  default = "migAQWO5XH8V0"
}

variable "vpc_cidr" {
  type    = string
  default = "10.0.0.0/16"
}

# EC2: 2 vCPU, 4 GiB
variable "instance_type" {
  type    = string
  default = "t3.medium"
}

variable "db_name" {
  type    = string
  default = "emitdb"
}

variable "db_username" {
  type    = string
  default = "emituser"
}

# Set via env var TF_VAR_db_password (don’t commit)
variable "db_password" {
  type      = string
  sensitive = true
}
