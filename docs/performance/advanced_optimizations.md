# Optional advanced optimizations

When profiling highlights bottlenecks that our Python-first architecture cannot
resolve, we have a handful of opt-in strategies that preserve deterministic
outputs while reducing latency. These techniques are intentionally scoped to the
hottest workloads and should only follow demonstrated wins from the profiling
playbooks documented elsewhere in the performance directory.

## Native extensions for compute hotspots

* After capturing cProfile or Pyinstrument traces that repeatedly flag the same
  tight loop, consider moving just that loop into a Python C-extension or a Rust
  microkernel. Prefer Rust via [`maturin`](https://github.com/PyO3/maturin) so we
  can share ownership across the broader team and still publish binary wheels.
* Keep the extension API narrow and feed it typed, contiguous buffers (e.g.
  NumPy arrays) to avoid per-call overhead. Unit tests must lock in the expected
  outputs so that native speedups never change chart interpretations.

## Memory-mapped caches for large ephemerides

* Extremely large ephemeris arrays or precomputed harmonics can be exposed as
  `numpy.memmap` views stored under `data/` to avoid per-worker duplication.
* Map these arrays read-only so that multiple worker processes can share the
  same OS page cache without risking mutation. Document the provenance of every
  file and update scripts in `rulesets/` or `datasets/` when regenerating them.

## Sharded Redis deployments

* For globally popular bodies/dates or heavy synastry lookups that benefit from
  cross-process reuse, shard Redis deployments across availability zones and use
  consistent hashing for key placement.
* Continue emitting cache provenance headers (`X-Cache-Status`, `ETag`) so that
  downstream services can trace a response back to the data source, even when it
  crosses Redis shards.

Each of these optimizations remains optional; the default deployment path stays
pure-Python for portability. Optimizations are only merged after benchmarks in
`tests/perf/` and load tests in `scripts/perf/` confirm the gains and document
hardware/software baselines for reproducibility.
