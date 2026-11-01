# ADR 0003: Separate remote intent from local execution confirmation

- **Status:** accepted
- **Date:** 2026-10-23

## Context

The browser may be used from another trusted device, but a web login alone must
not execute package scripts or mutate installed software on the managed host.
Unprivileged work can still access user data, while privileged work additionally
needs host authorization. Treating remote intent as either form of consent
would silently broaden the attack surface.

## Decision

Allow authenticated remote users to inspect state, manage application policy
and prepare/approve an immutable transaction plan. Every executable software
mutation requires explicit confirmation through the managed host's local
approval surface and enters `awaiting-local-confirmation`; root-required work
then crosses the fixed-operation helper and approved Polkit flow in
`awaiting-authorization`.

## Consequences

- Remote observation and preparation work immediately; unattended remote
  software execution does not, whether or not the provider needs root.
- The KDE host needs an active suitable authorization agent for interactive
  execution.
- Browser and task state must tolerate delayed or rejected authorization.
- A future remote-authorization mechanism requires a new threat model, ADR and
  explicit user approval.

## Alternatives rejected

- **Pass a desktop password through the browser/service:** creates credential
  handling and logging risks.
- **Passwordless blanket helper:** turns web compromise into unrestricted host
  mutation.
- **Pretend the remote action succeeded:** violates truthful status reporting.
