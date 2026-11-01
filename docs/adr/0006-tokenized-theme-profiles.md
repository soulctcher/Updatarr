# ADR 0006: Tokenized theme profiles

- **Status:** accepted
- **Date:** 2026-10-23

Keep Ultraviolet as Updatarr's stable brand while exposing a tokenized theme
layer for neutral surfaces, typography, focus and semantic states. Ship System,
Light, Dark, AMOLED, Solarized light/dark, GitHub light/dark, Norse, Nord,
Gruvbox light/dark, Dracula, Catppuccin Latte/Mocha, Sepia, Midnight and High
contrast profiles.

`system` is the default. Explicit choices use stable IDs and fall back to
`system` if unknown. Production preferences will be presentation-only account
settings; the throwaway prototype uses a URL parameter and does not persist
state.

This separation prevents a theme from redefining update safety, provider
health or the brand identity. It also lets every profile share one responsive
layout and one accessibility test contract instead of accumulating independent
stylesheets.
