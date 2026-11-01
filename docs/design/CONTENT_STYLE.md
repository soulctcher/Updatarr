# Updatarr interface language

**Status:** accepted product rule  
**Canonical terms:** [GLOSSARY.md](../../GLOSSARY.md)

Every label should make sense to a person familiar with ordinary desktop
software updates. Technical detail remains available, but it does not replace a
clear heading, status or action.

## Rules

1. Use the glossary term in visible text and accessible names. Internal state,
   database and adapter names do not appear as labels.
2. Name actions with a verb and object: **Check for updates**, **Review system
   updates**, **Postpone until…**, **Save this plan for later**.
3. Name status by what it means now: **Ready to review**, **Blocked**, **Needs
   refresh**, **Source unavailable**, **Not supported**, **Turned off**.
4. State cause, effect and next step in errors. Example: “Flatpak could not
   connect to Flathub. Its results may be out of date. Check the connection and
   try again.”
5. Use the real source name—pacman, AUR, Flatpak or fwupd—when it helps. Use
   **update source** for the general concept.
6. Expand uncommon abbreviations on first use. Product names and familiar units
   such as AUR, KDE, MiB and URL may remain abbreviated where space is limited.
7. Put implementation detail, command output and internal state IDs in an
   optional technical-details area. Keep the primary explanation plain.
8. Use the same term in headings, buttons, notifications, tray text, API error
   messages and help. Synonyms are not variety; they are ambiguity.
9. Keep the working screen focused on decisions and results. Put short
   explanations behind a small, raised circled information button beside the
   relevant heading. Use a wider, scrollable hover panel when the explanation
   contains several choices or steps.
10. Help is optional context, never a hiding place for a blocker, consequence,
    required action or status. The visible heading and action must still make
    sense without opening help.
11. Use title case for visible page, section, card, dialog and table-column
    titles. Keep buttons, status labels, instructions and body copy in sentence
    case. Preserve official casing such as **AUR**, **KDE**, **AMOLED**,
    **GitHub**, **Node.js**, **npm**, **fnm**, **fwupd** and **uv**.

## Help pattern

- Use a slightly raised, compact circled **i**, like a superscript reference.
- Every help panel appears on pointer hover and keyboard focus. It must not
  require a click. Keep it visible while the pointer is over the panel.
- Place pointer-opened panels to the right of the pointer. Render every panel
  in a viewport-level top layer so sticky headers, tables and dialogs cannot
  overlap it. Keep the panel within the visible viewport when space is tight.
- Fix the panel's position when it opens. Moving from the information button
  into the panel must not move the panel, close it or make its scrollbar
  unreachable. Show the full explanation whenever the viewport has room.
- Use a compact panel for one short explanation and a wider, scrollable panel
  for page-level guidance, several related choices or multi-step help.
- On touch screens, focusing the control reveals the same panel. Escape removes
  keyboard focus and hides it.
- Give every help button a specific accessible name, such as “Information:
  About update sources.” Never use “More information” without naming the
  subject.
- Avoid permanent “What this page does” panels. They compete with the work and
  make repeat visits noisy.

## Checklist status pattern

- Keep Passed as a non-interactive badge: a successful check has no action.
- Keep Not Checked and Not Supported as non-interactive badges unless Updatarr
  has a real screen or control where that condition can be acted on.
- Make Needs Attention a link only when it can navigate to a specific Updatarr
  control where the user can take the action. Do not link it to explanatory
  copy or to the row's Next Step sentence.
- Keep the next step readable in place. The status control is a shortcut, not
  the only way to discover what to do.

## Plain-language gate

Before a changed flow is ready for review, read every rendered page, help
panel, empty state, error, status, server-provided explanation and
accessible name as a first-time user would. Replace internal or specialist
terms with familiar words. When a product name or exact technical term is
necessary, pair it with a plain explanation. Automated forbidden-word checks
support this review but do not replace it.

## Review checklist

- Can a label be understood without a tooltip?
- Does every count say what is counted?
- Does “up to date” come only from a current successful check?
- Are blocked, error, turned off, unavailable and needs-refresh states distinct?
- Does every destructive or privileged action name what will change?
- Do visible text and accessible names use the same plain language?
- Are update groups explained as “must update together” rather than with terms
  such as “atomic,” “native group” or “consistency set”?
- Is instructional material behind the correct compact or wide hover panel?
- Are blockers, consequences and next steps still visible without opening
  help?
- Has every page, including opened help and server-provided text, received a
  plain-language reading pass?

Prototype tests reject known internal jargon in both rendered text and explicit
accessible names. Production component tests must extend that check to dialogs,
notifications, settings, tray menus and server-provided errors.
