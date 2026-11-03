# Updatarr Local Test Checklist

**Test address:** `http://127.0.0.1:8788`
**Build:** signed M7 RC3 local pilot (`updatarr 0.6.0-2`)

**Safety boundary:** read-only inventory only; do not expect Updatarr to install
or remove software

Use the password chosen in the local setup dialog. Please record the page,
action, expected result and actual result for anything that does not work. A
screenshot is especially helpful for layout or theme problems.

## 1. Sign In and Basic Navigation

- [X] Open the test address and confirm the Updatarr sign-in page appears.
- [X] Enter the chosen password and confirm the Overview opens.
- [X] Refresh the browser and confirm the session remains signed in.
- [X] Open Overview, Software, Updates, History and Settings from the side
      navigation.
- [X] Confirm the current page is visually clear in the navigation.
- [X] Sign out, then sign in again.

Expected: no page exposes a password, internal file path or technical error.

## 2. Overview and Read-Only Check

- [X] Confirm the page says **Read-only**, not **Safe preview**.
- [X] Confirm the latest check shows about 1,828 recorded software items, four
      system-package updates and six AUR updates. Counts may change if the host
      changes after this checklist was written.
- [X] Run **Check software** once.
- [X] Confirm progress appears and finishes without creating a duplicate task.
- [X] Confirm System packages and AUR packages do not become **Not supported**.
- [X] Confirm Flatpak, firmware and tool sources clearly say what was checked
      and what was not checked.
- [X] Confirm npm software under the system package area remains **Blocked** and
      uv remains **Not supported** rather than appearing ready.

Expected: the check reads current state only. It must not install, remove or
update software, change Flatpak remotes or start another notifier. Most update
sources can remain **Not Checked** in this pilot: Updatarr recorded their
installed software but did not ask those sources for newer versions.

## 3. Software Page

- [X] Search for a known installed application such as Firefox.
- [X] Clear the search and move through at least two pages of the software list.
- [X] Filter or sort the list and confirm the total count remains believable.
- [X] Open source-documentation links for one system package, one AUR item and
      one Flatpak item where available.
- [X] Confirm long names and descriptions stay inside their rows.

Expected: system, AUR, Flatpak, firmware and tool ownership remain distinct.

## 4. Updates and Safety Information

- [X] Open Updates and confirm system-package updates that belong together are
      presented as one group.
- [X] Select and clear updates without attempting to install them.
- [X] Use **Check Whether Selection Is Safe** and confirm the explanation is in
      plain language.
- [X] Review **Postpone for 24 Hours**, **Skip This Version** and **Pause Until
      Resumed** help without saving a choice unless you intend to test that
      setting.
- [X] Confirm any saved choice offers **Remove Saved Choice** to return to the
      source-reported state.
- [X] Confirm there is no working live install or update action in this pilot.

Expected: Updatarr may prepare or review information, but live execution stays
disabled.

## 5. Safety Checklist

- [X] Confirm results that need attention appear before passed results.
- [ ] Confirm **Passed** is a result count and not a button or link. It is
      valid for this read-only host check to show **0 passed**.
- [ ] Confirm **Needs Attention** links only when Updatarr has a real page where
      the action can be taken. A non-linked result must say when no action is
      available in Updatarr.
- [X] Confirm **Not Checked** and **Not Supported** are visually different and
      do not imply success.
- [ ] Open **View Details** on **Developer Tools** and confirm the recorded
      update sources are listed while the result and next step remain visible.

## 6. Help Pop-Ups

- [X] Hover over several raised circled information icons on every page.
- [X] Confirm each panel opens without a click and appears to the right of the
      pointer when space permits.
- [X] Move the pointer into a help panel and confirm it stays still and remains
      open.
- [X] Test a long panel, including the one near **Review Updates**, and confirm
      its full text and scrollbar can be reached.
- [X] Confirm help panels remain above tables, navigation and dialogs.
- [X] Use the keyboard to focus an information icon and confirm the same help
      is available.

## 7. Themes and Responsive Layout

- [X] Open **Settings → Appearance** and try System, Light, Dark, AMOLED,
      Solarized, GitHub, Norse and several other included themes.
- [X] Refresh after choosing a theme and confirm the selection remains.
- [X] Confirm status meanings do not change with the theme.
- [X] Resize the browser from a wide desktop window to a narrow phone-like
      width.
- [X] Confirm navigation remains usable and no page develops horizontal
      overflow.
- [X] Test browser zoom at 200% and, if practical, 400%.

## 8. System Tray

- [X] Confirm exactly one Updatarr icon appears in the Plasma system tray.
- [ ] After a recorded check with updates, confirm the loop icon appears over a
      muted red circle. After a recorded check with no updates, confirm it uses
      a muted green circle. Before any result is recorded, neutral gray is
      expected instead of a misleading green result.
- [X] Hover over it and confirm the tooltip says how many updates are ready to
      review. At pilot start it reported 10.
- [ ] Left-click the icon and confirm it opens the local Updatarr page at
      `http://127.0.0.1:8788`. This address works only on this computer.
- [ ] Right-click and confirm the menu contains the current status, **Open
      Updatarr**, **Settings…** and **Quit Tray**.
- [ ] Open **Settings…**, change the tray status refresh and notification
      choices, including the optional reminder frequency; save them, close and
      reopen the dialog, and confirm the saved choices remain. These settings
      must not start a software check.
- [X] Close every Updatarr browser tab, then left-click the tray icon and
      confirm the page opens again.
- [X] Confirm the existing Octopi notifier is still present; there should be
      one Updatarr tray and one Octopi notifier, not duplicate Updatarr trays.

If **Quit Tray** is tested, the core remains running. The tray is not enabled at
login, so restart it for this session with:

```bash
systemctl --user start updatarr-tray.service
```

## 9. Expected Temporary Behavior

- [X] Closing the browser does not stop the read-only core.
- [X] Quitting the tray does not stop the core.
- [X] Neither Updatarr unit is enabled at login.
- [X] After a logout or reboot, this temporary pilot is not expected to start
      automatically.

Do not enable `updatarr.service`. RC2's normal packaged core unit has a known
live-provider defect. The current test core is a non-enabled transient pilot
unit.

## 10. About Information

- [ ] Open browser **Settings**, scroll to the final **About Updatarr** section
      and confirm it shows Version 0.6.0, Build M7 and
      `© 2026 ✦ ERIK WINBLAD ✦`.
- [ ] Confirm the email opens a new message addressed to
      `soulctcher@soulctcher.net`.
- [ ] Confirm the `AGPL-3.0-or-later` link opens the official GNU license page.

## Stop Testing

To stop only the tray:

```bash
systemctl --user stop updatarr-tray.service
```

To stop the temporary read-only core:

```bash
systemctl --user stop updatarr-pilot.service
```

Neither command uninstalls Updatarr or removes its database, configuration or
backup.
