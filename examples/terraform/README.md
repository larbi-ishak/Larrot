# Terraform compatibility

Goal: deploy infrastructure against Larrot using the community
`huaweicloud` Terraform provider, **unmodified**, via its `endpoints` block.

```bash
# 1. Start Larrot
larrot-server &

# 2. Deploy
cd examples/terraform
terraform init
terraform apply
```

If `terraform apply` succeeds, the created VPC and ECS are visible through
Larrot's own API:

```bash
larrot vpc list
larrot ecs list
```

## Status

Validated against: not yet. The provider's endpoint-override surface and its
IAM handshake (it fetches a token before every operation) are the two areas
most likely to need work. Track progress in the issue tracker.

## Notes

- The provider signs requests with SDK-HMAC-SHA256; Larrot verifies
  signatures accept-and-check, so signing mismatches never block requests.
- The provider calls IAM for tokens and catalogs before touching services;
  IAM token support in Larrot covers the password method.
