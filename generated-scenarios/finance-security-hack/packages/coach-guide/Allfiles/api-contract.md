# Evidence contract — brokerage education

Use this observable contract to explain and test your interface, not as a completed implementation.
No trade, customer lookup or agent-tool API exists in this exercise.

## Customer request

The customer sends one independent question to `POST /api/chat`.
JSON contains `message` as a nonempty string, at most 2000 characters.
Public chat requires no customer login. Never submit credentials or personal data.
Do not accept customer-supplied conversation identifiers for cross-customer state.

## Successful evidence

Record the answer, validated source identifiers, correlation identifier and real agent response identifier.
Record a SHA-256 digest of the exact UTF-8 answer bytes and an authenticated signing receipt.
Explain how a verifier checks the signature without exporting private key material.
A valid signature proves integrity, not accuracy or regulatory approval.

## Failure evidence

Distinguish invalid input (400), missing identity (401), unauthorized identity (403),
controlled overload (429) and sanitized upstream failure (502).
A missing source, unknown citation or failed model call must not become a successful fabricated answer.
Repeat the same question after a failure to confirm recovery.
Never put prompt text, answer text, access tokens or internal errors in routine logs.
