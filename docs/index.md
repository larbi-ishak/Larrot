# Larrot

**A local Huawei Cloud API simulator: LocalStack, but for Huawei Cloud.
It runs the REST APIs of Huawei Cloud's international site on your
machine - 59 services, 720 documented operations, on ports 8200/8201.

## Quick start

```bash
pip install larrot
larrot-server
# REST on http://127.0.0.1:8200, OBS on http://127.0.0.1:8201
```

Point any `huaweicloudsdk*` SDK at `http://127.0.0.1:8200` and your
existing scripts run unchanged.

## What makes it different from a mock

- **State machines with preconditions** - can't stop a stopped server,
  can't snapshot an in-use volume, can't detach a system disk
- **Async job model** - every mutation returns a `job_id`, completes
  after 1-3s, clients poll - like the real cloud
- **Per-region quirk profiles** - the `hcs` region behaves differently
  from the public region, reproducing observed production behavior
- **Exact error codes** - `Ecs.0005 "device is illegal"`, `APIGW.0301`,
  per-service error envelope shapes (nested ECS, flat VPC, OBS XML)
- **Rate limiting, signature verification, chaos injection** - the
  full gateway behavior

## Measured fidelity

| Dimension | Result |
|---|---|
| Documented operations implemented + tested | 720/720 |
| Unit + integration tests | 523, all green |
| Real-world multi-service scenarios | 50, all green |
| Adversarial fuzz requests | 3,288, zero 5xx |
| Conformance + negative checks | 202, all green |

Full numbers: [Coverage](coverage.md), [Conformance](conformance.md).

## Explore

- [Service catalog](catalog.md) - all 59 services by category
- [Architecture](architecture.md) - how it's built
- [Real-world architectures](architectures.md) - the 50 tested scenarios
- [Examples](examples.md) - SDK code and scenario walkthroughs

## The web console

Open `http://127.0.0.1:8200/console` for a live resource browser with
chaos injection, or `http://127.0.0.1:8200/docs` for the full Swagger
UI grouped by service.

## License

Apache 2.0. Larrot is an independent, community-developed project and
is not affiliated with Huawei Technologies.
