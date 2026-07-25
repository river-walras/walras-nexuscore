# nexuscore-lib

Core runtime components extracted from `nautilus_trader` for use in Walras.
Pure Cython + Python standard library — no Rust or other native dependencies.

## Features
- Message bus and clock: `MessageBus`, `LiveClock`, `Clock`, `TimeEvent`
- Identifiers: `TraderId`, `ComponentId`, `Identifier`, `UUID4`
- Cryptography: `hmac_signature` (HMAC-SHA256), `HmacSigner`

## Import cost

`import nexuscore` costs ~5.6 MB resident. The only runtime dependency is
`python-dateutil`, imported lazily by `nexuscore.core.datetime` and only for
datetime strings that are not valid ISO 8601 — processes that never pass one
never load it.

`pandas.Timestamp` inputs are still handled at full nanosecond precision. They
are recognised by duck-typing (`Timestamp` subclasses `datetime` and exposes
`.value`), so interop costs nothing when the caller already has pandas and
imports nothing when it does not.

## Usage
```python
from nexuscore import (
    MessageBus,
    LiveClock,
    Clock,
    TimeEvent,
    TraderId,
    ComponentId,
    UUID4,
    hmac_signature,
    HmacSigner,
)
```
