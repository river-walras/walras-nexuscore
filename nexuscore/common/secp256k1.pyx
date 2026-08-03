# cython: language_level=3
"""Recoverable ECDSA signing over secp256k1, bound to vendored libsecp256k1.

Exchanges on EVM-style venues (Hyperliquid, dYdX) want a 65-byte recoverable
signature, and every Python binding that offers one -- coincurve, secp256k1,
pysecp256k1, electrum-ecc -- stopped shipping wheels at cp313. On Python 3.14 they
fall back to an sdist build, and coincurve's fails outright: its build hook looks
for ``LICENSE`` directly inside cffi's ``.dist-info``, but cffi >=2 (the first with
cp314 support) moved it to ``.dist-info/licenses/`` per PEP 639
(ofek/coincurve#219, #223).

The cp314-ready alternatives cannot do the job either: pure-Python ``eth_keys`` is
byte-identical but ~60x slower (~1.25ms vs ~21us per signature), and
``cryptography`` is abi3 but OpenSSL exposes no recovery id, so it cannot produce
the recoverable form at all.

Note this is the one place the package carries a native crypto dependency, which
``common/signing.py`` deliberately avoids for HMAC. That reasoning does not
transfer: HMAC has a stdlib implementation that is fast enough, secp256k1 has
none. Vendoring libsecp256k1 here means wheels track new Python releases on our
own schedule instead of an upstream's. See ``vendor/secp256k1/README.md``.

Signatures are byte-identical to coincurve's ``PrivateKey.sign_recoverable``: the
nonce comes from libsecp256k1's default RFC6979 generator, so output is fully
determined by (key, digest). ``tests/unit_tests/test_secp256k1.py`` pins that
against the published RFC6979 vector.
"""

from cpython.bytes cimport PyBytes_FromStringAndSize

cdef extern from "secp256k1.h":
    ctypedef struct secp256k1_context:
        pass
    int SECP256K1_CONTEXT_NONE
    secp256k1_context *secp256k1_context_create(unsigned int flags)
    void secp256k1_context_destroy(secp256k1_context *ctx)
    int secp256k1_context_randomize(secp256k1_context *ctx,
                                    const unsigned char *seed32)
    int secp256k1_ec_seckey_verify(const secp256k1_context *ctx,
                                   const unsigned char *seckey)

cdef extern from "secp256k1_recovery.h":
    ctypedef struct secp256k1_ecdsa_recoverable_signature:
        pass
    int secp256k1_ecdsa_sign_recoverable(
        const secp256k1_context *ctx,
        secp256k1_ecdsa_recoverable_signature *sig,
        const unsigned char *msghash32,
        const unsigned char *seckey,
        void *noncefp,
        const void *ndata,
    )
    int secp256k1_ecdsa_recoverable_signature_serialize_compact(
        const secp256k1_context *ctx,
        unsigned char *output64,
        int *recid,
        const secp256k1_ecdsa_recoverable_signature *sig,
    )


cdef secp256k1_context *_CTX = NULL


cdef secp256k1_context *_context() except NULL:
    """Create the process-wide signing context on first use.

    Blinded with ``secp256k1_context_randomize`` (as upstream recommends) to
    harden the scalar multiply against side-channel leakage. Randomizing once at
    creation is what makes the context safe to share: signing only reads it, so
    concurrent signs from multiple threads are fine, but randomize itself is not.
    """
    global _CTX
    if _CTX is not NULL:
        return _CTX

    cdef secp256k1_context *ctx = secp256k1_context_create(SECP256K1_CONTEXT_NONE)
    if ctx is NULL:
        raise MemoryError("secp256k1_context_create failed")

    import os

    cdef const unsigned char[::1] seed = os.urandom(32)
    if secp256k1_context_randomize(ctx, &seed[0]) != 1:
        secp256k1_context_destroy(ctx)
        raise RuntimeError("secp256k1_context_randomize failed")

    _CTX = ctx
    return _CTX


cdef class SigningKey:
    """A validated secp256k1 secret key that signs 32-byte digests.

    Holds the key so the validity check and context setup are paid once per key
    rather than per signature.
    """

    cdef unsigned char _seckey[32]

    def __cinit__(self, key: bytes):
        if len(key) != 32:
            raise ValueError(f"secret key must be 32 bytes, got {len(key)}")

        cdef const unsigned char[::1] buf = key
        cdef secp256k1_context *ctx = _context()
        if secp256k1_ec_seckey_verify(ctx, &buf[0]) != 1:
            raise ValueError("invalid secp256k1 secret key")

        cdef Py_ssize_t i
        for i in range(32):
            self._seckey[i] = buf[i]

    def sign_recoverable(self, digest: bytes) -> bytes:
        """Sign a 32-byte ``digest``, returning 65 bytes of ``r || s || recid``.

        ``digest`` is signed as-is — it is already a hash, so nothing is hashed
        here. ``recid`` is the raw 0/1 recovery id; callers that need an Ethereum
        ``v`` add 27.
        """
        if len(digest) != 32:
            raise ValueError(f"digest must be 32 bytes, got {len(digest)}")

        cdef const unsigned char[::1] msg = digest
        cdef secp256k1_context *ctx = _context()
        cdef secp256k1_ecdsa_recoverable_signature sig

        if secp256k1_ecdsa_sign_recoverable(
            ctx, &sig, &msg[0], self._seckey, NULL, NULL
        ) != 1:
            raise RuntimeError("secp256k1_ecdsa_sign_recoverable failed")

        cdef unsigned char out[65]
        cdef int recid = 0
        if secp256k1_ecdsa_recoverable_signature_serialize_compact(
            ctx, out, &recid, &sig
        ) != 1:
            raise RuntimeError("failed to serialize recoverable signature")

        out[64] = <unsigned char> recid
        return PyBytes_FromStringAndSize(<char *> out, 65)
