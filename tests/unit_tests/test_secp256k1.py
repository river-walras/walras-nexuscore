"""Known-answer tests for the vendored libsecp256k1 binding.

This package owns the C build, so a misconfigured one is a real risk: wrong
``ECMULT_WINDOW_SIZE``/``COMB_*`` defines against the shipped precomputed tables,
or a careless vendor refresh, could produce signatures that are structurally valid
but wrong. Downstream that surfaces as an exchange silently rejecting orders, which
is miserable to debug against a live venue.

So these pin exact bytes rather than only checking shape. The primary vector is the
widely published RFC6979-over-secp256k1 one (key=1, "Satoshi Nakamoto"), which is
independently verifiable rather than self-generated. Output was additionally
cross-validated byte-for-byte against coincurve 21.0.0 over random keys and digests
when this binding was written.
"""

import hashlib

import pytest

from nexuscore.common.secp256k1 import SigningKey


# Published RFC6979 / secp256k1 deterministic-ECDSA vector.
KEY = (1).to_bytes(32, "big")
DIGEST = hashlib.sha256(b"Satoshi Nakamoto").digest()
EXPECTED_R = "934b1ea10a4b3c1757e2b0c017d0b6143ce3c9a7e6a4a49860d7a6ab210ee3d8"
EXPECTED_S = "2442ce9d2b916064108014783e923ec36b49743e2ffa1c4496f01a512aafd9e5"
EXPECTED_RECID = 1


def test_matches_published_rfc6979_vector():
    """The load-bearing test: proves the C build computes the real curve."""
    sig = SigningKey(KEY).sign_recoverable(DIGEST)

    assert len(sig) == 65
    assert sig[:32].hex() == EXPECTED_R
    assert sig[32:64].hex() == EXPECTED_S
    assert sig[64] == EXPECTED_RECID


def test_signing_is_deterministic():
    """RFC6979 nonces make output a pure function of (key, digest).

    A caller replaying a signed action would see it change run to run if the nonce
    were random, so this is a behavioural guarantee, not an implementation detail.
    """
    key = SigningKey(KEY)
    first = key.sign_recoverable(DIGEST)

    assert all(key.sign_recoverable(DIGEST) == first for _ in range(5))
    assert SigningKey(KEY).sign_recoverable(DIGEST) == first


def test_distinct_inputs_give_distinct_signatures():
    other_digest = hashlib.sha256(b"not Satoshi").digest()
    other_key = (2).to_bytes(32, "big")
    baseline = SigningKey(KEY).sign_recoverable(DIGEST)

    assert SigningKey(KEY).sign_recoverable(other_digest) != baseline
    assert SigningKey(other_key).sign_recoverable(DIGEST) != baseline


def test_recid_is_a_recovery_id():
    """recid is the raw 0/1; adding 27 for an Ethereum v is the caller's job."""
    assert SigningKey(KEY).sign_recoverable(DIGEST)[64] in (0, 1)


@pytest.mark.parametrize(
    ("key", "message"),
    [
        (b"\x00" * 32, "invalid secp256k1 secret key"),  # zero is out of range
        (b"\xff" * 32, "invalid secp256k1 secret key"),  # >= curve order n
        (b"short", "must be 32 bytes"),
        (b"\x01" * 33, "must be 32 bytes"),
        (b"", "must be 32 bytes"),
    ],
)
def test_rejects_invalid_keys(key, message):
    with pytest.raises(ValueError, match=message):
        SigningKey(key)


@pytest.mark.parametrize("digest", [b"", b"\x01" * 31, b"\x01" * 33])
def test_rejects_wrong_digest_length(digest):
    """The input is already a hash and is never hashed here, so length is exact."""
    with pytest.raises(ValueError, match="must be 32 bytes"):
        SigningKey(KEY).sign_recoverable(digest)


def test_many_keys_and_digests_round_trip():
    """Broad smoke pass: every valid key/digest pair must sign to 65 bytes."""
    for i in range(1, 64):
        sig = SigningKey(i.to_bytes(32, "big")).sign_recoverable(
            hashlib.sha256(str(i).encode()).digest()
        )

        assert len(sig) == 65
        assert sig[64] in (0, 1)
        assert sig[:32] != b"\x00" * 32
