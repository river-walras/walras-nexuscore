# Vendored libsecp256k1

Upstream: https://github.com/bitcoin-core/secp256k1
Version: **v0.7.1**
Commit: `1a53f4961f337b4d166c25fce72ef0dc88806618`
License: MIT (see `LICENSE`)

Built into `nexuscore.common.secp256k1` (see `nexuscore/common/secp256k1.pyx` and
the `SECP256K1_EXTENSION` branch in `setup.py`), which exposes one operation:
recoverable ECDSA signing over secp256k1.

Vendored rather than depended upon because every Python binding that offers a
recoverable signature (coincurve, secp256k1, pysecp256k1, electrum-ecc) stopped
shipping wheels at cp313, and coincurve's sdist build additionally fails on
Python 3.14 — its build hook looks for `LICENSE` directly inside cffi's
`.dist-info`, but cffi >=2 (the first cffi with cp314 support) moved it to
`.dist-info/licenses/` per PEP 639 (ofek/coincurve#219, #223). Compiling the C
library here decouples us from that release cadence.

## What was kept

Only what a recovery-module build compiles:

- `include/` — `secp256k1.h`, `secp256k1_preallocated.h`, `secp256k1_recovery.h`
- `src/` — all `*_impl.h` headers, `selftest.h`, and the three translation units:
  `secp256k1.c`, `precomputed_ecmult.c`, `precomputed_ecmult_gen.c`
- `src/modules/recovery/main_impl.h`

Removed: tests, benchmarks, `wycheproof/`, the `precompute_ecmult*.c` table
*generators* (the generated tables ship as source upstream, so no codegen step is
needed), the `asm/` directory, and the `ecdh`/`ellswift`/`extrakeys`/`musig`/
`schnorrsig` modules. Only `ENABLE_MODULE_RECOVERY` is defined, so those modules
are never `#include`d by `secp256k1.c`.

## Updating

Re-copy from a new upstream tag keeping the same filter, then run `uv run pytest tests/unit_tests/test_secp256k1.py`.
Those tests pin signatures to the published RFC6979 known-answer vector, so a
misconfigured or miscompiled build fails loudly rather than producing subtly wrong
signatures.

Note that `ECMULT_WINDOW_SIZE` and `COMB_BLOCKS`/`COMB_TEETH` are deliberately
left at upstream's in-header defaults: the vendored precomputed tables were
generated for exactly those values, so overriding them would silently disagree
with the shipped tables.
