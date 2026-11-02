# Updatarr Local Test Checklist

**Test address:** `http://127.0.0.1:8788`  
**Build:** signed M7 RC2 local pilot  
**Safety boundary:** read-only inventory only; do not expect Updatarr to install
or remove software

Use the password chosen in the local setup dialog. Please record the page,
action, expected result and actual result for anything that does not work. A
screenshot is especially helpful for layout or theme problems.

## 1. Sign In and Basic Navigation

- [ ] Open the test address and confirm the Updatarr sign-in page appears.
- [ ] Enter the chosen password and confirm the Overview opens.
- [ ] Refresh the browser and confirm the session remains signed in.
- [ ] Open Overview, Software, Updates, History and Settings from the side
      navigation.
- [ ] Confirm the current page is visually clear in the navigation.
- [ ] Sign out, then sign in again.

Expected: no page exposes a password, internal file path or technical error.

## 2. Overview and Read-Only Check

- [ ] Confirm the page says **Read-only**, not **Safe preview**.
- [ ] Confirm the latest check shows about 1,828 recorded software items, four
      system-package updates and six AUR updates. Counts may change if the host
      changes after this checklist was written.
- [ ] Run **Check for Updates** once.
- [ ] Confirm progress appears and finishes without creating a duplicate task.
- [ ] Confirm System packages and AUR packages do not become **Not supported**.
- [ ] Confirm Flatpak, firmware and tool sources clearly say what was checked
      and what was not checked.
- [ ] Confirm npm software under the system package area remains **Blocked** and
      uv remains **Not supported** rather than appearing ready.

Expected: the check reads current state only. It must not install, remove or
update software, change Flatpak remotes or start another notifier.

## 3. Software Page

- [ ] Search for a known installed application such as Firefox.
- [ ] Clear the search and move through at least two pages of the software list.
- [ ] Filter or sort the list and confirm the total count remains believable.
- [ ] Open source-documentation links for one system package, one AUR item and
      one Flatpak item where available.
- [ ] Confirm long names and descriptions stay inside their rows.

Expected: system, AUR, Flatpak, firmware and tool ownership remain distinct.

## 4. Updates and Safety Information

- [ ] Open Updates and confirm system-package updates that belong together are
      presented as one group.
- [ ] Select and clear updates without attempting to install them.
- [ ] Use **Check Whether Selection Is Safe** and confirm the explanation is in
      plain language.
- [ ] Review **Postpone for 24 Hours**, **Skip This Version** and **Pause Until
      Resumed** help without saving a choice unless you intend to test that
      setting.
- [ ] Confirm any saved choice offers **Remove Saved Choice** to return to the
      source-reported state.
- [ ] Confirm there is no working live install or update action in this pilot.

Expected: Updatarr may prepare or review information, but live execution stays
disabled.

## 5. Safety Checklist

- [ ] Confirm results that need attention appear before passed results.
- [ ] Confirm **Passed** is not a link.
- [ ] Confirm **Needs Attention** links only when Updatarr has a real page where
      the action can be taken.
- [ ] Confirm **Not Checked** and **Not Supported** are visually different and
      do not imply success.
- [ ] Expand details and confirm the result, consequence and next step remain
      understandable.

## 6. Help Pop-Ups

- [ ] Hover over several raised circled information icons on every page.
- [ ] Confirm each panel opens without a click and appears to the right of the
      pointer when space permits.
- [ ] Move the pointer into a help panel and confirm it stays still and remains
      open.
- [ ] Test a long panel, including the one near **Review Updates**, and confirm
      its full text and scrollbar can be reached.
- [ ] Confirm help panels remain above tables, navigation and dialogs.
- [ ] Use the keyboard to focus an information icon and confirm the same help
      is available.

## 7. Themes and Responsive Layout

- [ ] Open **Settings → Appearance** and try System, Light, Dark, AMOLED,
      Solarized, GitHub, Norse and several other included themes.
- [ ] Refresh after choosing a theme and confirm the selection remains.
- [ ] Confirm status meanings do not change with the theme.
- [ ] Resize the browser from a wide desktop window to a narrow phone-like
      width.
- [ ] Confirm navigation remains usable and no page develops horizontal
      overflow.
- [ ] Test browser zoom at 200% and, if practical, 400%.

## 8. System Tray

- [ ] Confirm exactly one Updatarr icon appears in the Plasma system tray.
- [ ] Hover over it and confirm the tooltip says how many updates are ready to
      review. At pilot start it reported 10.
- [ ] Left-click the icon and confirm it opens the loopback Updatarr page.
- [ ] Right-click and confirm the menu contains the current status, **Open
      Updatarr** and **Quit Tray**.
- [ ] Close every Updatarr browser tab, then left-click the tray icon and
      confirm the page opens again.
- [ ] Confirm the existing Octopi notifier is still present; there should be
      one Updatarr tray and one Octopi notifier, not duplicate Updatarr trays.

If **Quit Tray** is tested, the core remains running. The tray is not enabled at
login, so restart it for this session with:

```bash
systemctl --user start updatarr-tray.service
```

## 9. Expected Temporary Behavior

- [ ] Closing the browser does not stop the read-only core.
- [ ] Quitting the tray does not stop the core.
- [ ] Neither Updatarr unit is enabled at login.
- [ ] After a logout or reboot, this temporary pilot is not expected to start
      automatically.

Do not enable `updatarr.service`. RC2's normal packaged core unit has a known
live-provider defect. The current test core is a non-enabled transient pilot
unit.

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
