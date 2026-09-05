# ADR 0008: Separate service-caller authentication from action authorization

## Status

Accepted

## Context

Governed Agent Actions already separate untrusted action proposals, trusted caller context, deterministic authorization, human approval, runtime enforcement, and mutable execution.

Phase 34 made caller identity provenance explicit, but the only implemented source was `trusted_composition`. That accurately described the local lab boundary but did not demonstrate credential verification.

The next identity increment needs to establish caller context from an actual credential check without collapsing authentication into authorization or prematurely introducing remote OAuth/OIDC infrastructure.

## Decision

Introduce a framework-neutral caller-authentication boundary in the application layer.

The application contract exposes:

- `CallerCredential` as opaque credential material using `SecretStr`;
- `CallerAuthenticator` as the authentication port;
- `CallerAuthenticationDecision` with closed `authenticated` and `rejected` outcomes;
- trusted `ActionContext` only on successful authentication;
- no credential field in authentication decisions, authorization requests, or execution evidence.

The first provider-free adapter is `StaticApiKeyCallerAuthenticator`.

It is a controlled service/client authentication fixture, not an end-user identity system. During construction it reduces configured synthetic high-entropy API keys to SHA-256 digests and retains only those digests with caller ids. Presented credentials are reduced to the same fixed-size digest and compared with `hmac.compare_digest()`.

A successful match creates:

```text
ActionContext(
    caller_id=<configured service caller>,
    identity_source="api_key",
)
```

A failed match returns `rejected` with no trusted context.

`api_key` therefore means only that the controlled API-key authentication adapter verified the presented synthetic service credential against configured verification material. It does not mean end-user authentication, federated identity, OAuth authorization, or production IAM assurance.

Authentication and action authorization remain separate decisions:

```text
credential
    |
    v
authentication
    |
    +-- rejected ------> no trusted caller context
    |
    +-- authenticated -> ActionContext
                              |
                              v
                         authorization
                              |
                              v
                       runtime enforcement
```

Phase 35 deliberately established authentication before composing it with `GovernedActionRuntime`. Phase 36 adds that composition in a separate application-owned runtime so tests can distinguish failures at the authentication boundary from failures at the authorization boundary.

## Why API key only as a fixture

A service API key provides a small provider-free mechanism for proving possession of configured credential material and deriving a service caller identity.

It does not require inventing a token format or simulating an enterprise identity provider. The fixture is intentionally limited to synthetic high-entropy service credentials and does not model passwords.

The adapter also avoids transport assumptions: there is no header name, HTTP endpoint, MCP argument, or environment-variable contract in the authentication port.

## Alternatives considered

### Treat `caller_id` as already authenticated

Rejected because that repeats the ambiguity Phase 34 was created to remove. A caller identifier alone is not evidence that a credential was verified.

### Add OAuth/OIDC immediately

Rejected for this increment because remote protocol flow, issuer discovery, JWT/JWK validation, audience/scopes, refresh behavior, transport security, and provider configuration would obscure the basic authentication-versus-authorization boundary.

### Put API-key verification inside MCP or a framework adapter

Rejected because authentication semantics should not depend on LangGraph, CrewAI, LlamaIndex, Agno, or MCP. Those are orchestration/protocol adapters rather than the owner of caller identity policy.

### Pass credentials into `GovernedActionRuntime`

Rejected because the runtime should consume trusted caller context, not secrets. Keeping credentials outside authorization and execution evidence reduces accidental secret propagation.

### Store configured API keys as plaintext in the fixture

Rejected. The controlled adapter reduces configured keys to digests when it is constructed and never intentionally stores them in its runtime records.

## Consequences

### Positive

- authentication is now explicit rather than implied by `caller_id`;
- failed authentication cannot create trusted action context;
- raw credentials stay outside authorization and execution evidence;
- the application contract remains framework- and transport-neutral;
- no new dependency is required;
- future HTTP/OAuth/MCP authentication can implement the same conceptual boundary without changing action policy ownership.

### Trade-offs

- the fixture is process-local and static;
- SHA-256 digest storage assumes synthetic high-entropy API keys and is not password hashing;
- there is no rotation, expiry, revocation, throttling, vault integration, or audit store;
- the current authorization policy does not yet include `identity_source` as a policy dimension;
- the authenticated composition remains local and transport-neutral rather than proving remote identity propagation.

These are explicit boundaries, not production claims.

## Evolution note: Phase 36

Phase 36 introduces `AuthenticatedGovernedActionRuntime` as an application-owned composition boundary.

It accepts `CallerCredential` and `ProposedAction` as separate inputs, authenticates first, and passes only the derived `ActionContext` into `GovernedActionRuntime`. Rejected authentication returns separate authentication evidence with no action execution evidence and does not call authorization, approval, or the mutable executor.

Successful authentication still does not imply authorization. The existing governed runtime evaluates the authenticated caller against the same deterministic least-privilege policy and can still return `deny`.

`AuthenticatedActionExecutionEvidence` keeps authentication and governed execution evidence separate and rejects impossible combinations: rejected authentication cannot carry execution evidence, and authenticated execution must use the exact context established by authentication.

The composed invariant is:

```text
credential verification
    -> trusted ActionContext
    -> authorization
    -> approval when required
    -> mutable execution
```

Raw credential material is intentionally absent from the returned evidence object.

## Security invariants

```text
credential verification != authorization
failed authentication -> no ActionContext
failed authentication -> no authorization/runtime invocation
raw credential not in authorization/runtime evidence
api_key source != end-user identity
authenticated != authorized
```

## Revisit when

Revisit this decision when a real transport requires OAuth/OIDC, mTLS, signed workload identity, or another authentication mechanism; when service credentials require lifecycle management; or when authorization must distinguish the same `caller_id` by identity source.

Any future mechanism must keep raw credential material outside model-controlled action proposals and must derive trusted `ActionContext` before invoking action authorization.

Refs #152, #154
