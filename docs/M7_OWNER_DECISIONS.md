# M7 Owner Decisions

**Prepared:** 2026-11-01  
**Status:** license, Git authority, release proof and AUR boundary selected;
copyright-holder text still required  
**Effect:** selecting options authorizes documentation and project-local
implementation only; retained M7 host and publication gates still apply

This is a plain-language decision sheet, not legal advice. Supporting facts and
primary sources are in the
[M7 release-foundations research](research/m7-release-foundations-research.md).

## Decision 1: Redistribution License

Choose one:

### A. AGPL-3.0-or-later — Recommended for Network Source Sharing

People may use, change and redistribute Updatarr under strong source-sharing
terms. A person who operates a modified Updatarr for users over a network must
also offer those users the corresponding source. This most directly matches a
browser-managed application when the priority is keeping hosted modifications
available.

### B. GPL-3.0-or-later — Strong Distribution Copyleft

People may use, change and redistribute Updatarr under strong source-sharing
terms when copies are distributed. Merely operating a modified version over a
network does not, by itself, trigger GPLv3 distribution requirements. This is
appropriate when distribution copyleft is desired without the AGPL network
condition.

### C. MIT — Permissive

People may use, change, redistribute, sublicense and sell copies while
retaining the copyright and license notice. Modified versions can be kept
closed. This is appropriate when broad reuse matters more than requiring
downstream source sharing.

Record the selected SPDX expression and the copyright-holder name exactly.

## Decision 2: Git and Release Authority

Choose one:

### A. Initialize This Workspace, Then Attach an Owner-Controlled Remote — Recommended

Create a local repository from the reviewed tree, record the accepted M6 state
and M7 documentation as the import baseline, and add a remote only after the
owner supplies or creates its location. Ignored development state, virtual
environments, built browser output and database files remain outside Git.

### B. Wait for an Empty Owner-Created Repository

Do not initialize this workspace yet. The owner creates the destination and
provides its local clone or approved remote before provenance work continues.

No option authorizes pushing, changing a remote account or publishing a
repository without a separate instruction.

## Decision 3: How People Verify an Official Release

Choose one:

### A. Use One Release Key for Git and Downloaded Files — Recommended

Create or select one owner-controlled release key. Use it to prove both the
official release label in Git and the source/package files people download.
This gives people one public identity to check in both places. The technical
format is OpenPGP. Updatarr may prepare the commands and verification tests,
but using the private key must happen through a local password prompt under the
owner's control.

### B. Use an SSH Key for Git and Choose File Verification Later

Use an owner-controlled SSH key to prove the official release label in Git.
Before anything is published, choose a separate way to prove the downloaded
source/package files. This may reuse an existing Git signing setup, but users
would have two verification methods to understand.

### C. Do Not Sign Yet

Create clearly labeled internal test versions without a cryptographic proof of
who approved them. Public release remains blocked, and M7 cannot pass its final
release-candidate gate until a signing method is selected.

## Decision 4: Initial AUR Boundary

Choose one:

### A. First Candidate Keeps Live AUR Execution Disabled — Recommended

Ship read-only AUR discovery, metadata and review while build/install controls
remain visibly unavailable with no override. Continue isolation work without
holding the rest of the release candidate behind arbitrary build-script risk.

### B. Do Not Produce a Candidate Until AUR Isolation Passes

Continue the isolation prototype and hostile testing first. The release
candidate waits until independent review accepts the boundary. This delays the
candidate and still does not authorize a live AUR build.

## Decision 5: Managed-Computer Pilot

No decision is needed yet. The M7 team will first complete disposable
install/start/backup/restore/upgrade/uninstall evidence. It will then present an
exact host pilot plan for a separate approval. The recommended current choice
is to keep the managed-computer pilot unauthorized.

## Decision Record

- [x] License option **1A: AGPL-3.0-or-later** selected. Exact
      copyright-holder text remains pending.
- [x] Git option **2A: initialize this workspace, then attach an
      owner-controlled remote later** selected. This does not authorize a push.
- [x] Release proof option **3A: one owner-controlled OpenPGP key for signed
      Git release labels and downloaded files** selected. This does not
      authorize private-key use yet.
- [x] AUR option **4B: do not produce a release candidate until AUR isolation
      passes** selected. This does not authorize a live AUR build.
- [x] Managed-computer pilot remains unauthorized until its exact plan is
      reviewed separately.

