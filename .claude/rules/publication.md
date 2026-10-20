---
paths:
  - "linkedin_publisher/**"
  - "publication_registry/**"
---

# Publication and registry work

Use [ARCHITECTURE](../../docs/ARCHITECTURE.md) and applicable accepted decisions
for the current run-outcome and persistence contracts. Check publication and
registry failure paths together; successful remote publication and successful
record persistence are separate observations.

Use existing test doubles. Do not publish posts, retry a real post, read runtime
credentials, dispatch workflows or access the private runtime repository as an
offline test. Personal runtime configuration belongs outside this product repo.
