# Terraform + Larrot example (ROADMAP 3.2)
#
# Point the community huaweicloud provider at Larrot instead of the real cloud.
# The provider supports per-service endpoint overrides via the `endpoints`
# block. If this deploys unmodified against Larrot, the simulator is
# Terraform-compatible: existing IaC works with zero changes.
#
# Run:
#   terraform init && terraform apply
#
# Requirements: Larrot running on http://127.0.0.1:8200

terraform {
  required_providers {
    huaweicloud = {
      source = "huaweicloud/huaweicloud"
    }
  }
}

provider "huaweicloud" {
  region     = "ap-southeast-1"
  access_key = "HWYSIMAK00000001"
  secret_key = "HWYSIMSK00000001"

  endpoints {
    ecs = "http://127.0.0.1:8200"
    evs = "http://127.0.0.1:8200"
    vpc = "http://127.0.0.1:8200"
    iam = "http://127.0.0.1:8200"
  }
}

# A VPC through Larrot
resource "huaweicloud_vpc" "demo" {
  name = "tf-demo-vpc"
  cidr = "192.168.0.0/16"
}

# An ECS through Larrot
resource "huaweicloud_compute_instance" "demo" {
  name              = "tf-demo-vm"
  image_id          = "1ce5800a-e487-4c1b-b264-3353a39e2b4b"
  flavor_id         = "s6.large.2"
  availability_zone = "ap-southeast-1a"
  system_disk_type  = "SAS"
  system_disk_size  = 40

  depends_on = [huaweicloud_vpc.demo]
}

output "vpc_id" {
  value = huaweicloud_vpc.demo.id
}
