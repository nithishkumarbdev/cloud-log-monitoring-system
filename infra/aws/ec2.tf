data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }
}

resource "aws_security_group" "demo_instance" {
  name        = "${var.project_name}-instance-sg"
  description = "SSH from the operator IP only, no inbound HTTP needed since traffic is synthetic"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "SSH from operator"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.ssh_ingress_cidr]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Project = var.project_name }
}

data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

resource "aws_instance" "demo" {
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = "t2.micro"
  subnet_id              = data.aws_subnets.default.ids[0]
  vpc_security_group_ids = [aws_security_group.demo_instance.id]
  iam_instance_profile   = aws_iam_instance_profile.demo_instance.name

  # Cron regenerates synthetic auth/access lines every 2 minutes so the
  # CloudWatch agent has something to ship. Real production traffic never
  # touches this box, see log-generator/README for why.
  user_data = templatefile("${path.module}/user_data.sh.tpl", {
    log_group_name = aws_cloudwatch_log_group.demo_logs.name
    aws_region     = var.aws_region
  })

  tags = {
    Name    = "${var.project_name}-demo-instance"
    Project = var.project_name
  }
}

output "instance_public_ip" {
  value = aws_instance.demo.public_ip
}
