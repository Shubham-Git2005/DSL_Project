---
name: SkillsBridge workspace
description: An evidence-first assessment desk for a local prototype.
colors:
  canvas: "#f6f7f4"
  surface: "#fff"
  ink: "#242e29"
  secondary: "#606c64"
  faint: "#727c75"
  line: "#e1e5df"
  green: "#214b3c"
  green-hover: "#173b2e"
  mint: "#e6eee5"
  soft: "#f0f3ed"
  danger: "#a03636"
typography:
  headline:
    fontFamily: "Geist, ui-sans-serif, system-ui, sans-serif"
    fontSize: "36px"
    fontWeight: 600
    lineHeight: 1.15
    letterSpacing: "-0.035em"
  title:
    fontFamily: "Geist, ui-sans-serif, system-ui, sans-serif"
    fontSize: "18px"
    fontWeight: 600
    lineHeight: "28px"
    letterSpacing: "-0.025em"
  body:
    fontFamily: "Geist, ui-sans-serif, system-ui, sans-serif"
    fontSize: "14px"
    lineHeight: 1.5
  label:
    fontFamily: "Geist, ui-sans-serif, system-ui, sans-serif"
    fontSize: "12px"
    fontWeight: 500
rounded:
  badge: "4px"
  inset: "6px"
  control: "8px"
  surface: "12px"
spacing:
  compact: "8px"
  field: "12px"
  inset: "16px"
  panel: "24px"
  section: "32px"
  workspace: "40px"
components:
  button-primary:
    backgroundColor: "{colors.green}"
    textColor: "{colors.surface}"
    rounded: "{rounded.control}"
    padding: "12px 16px"
  button-primary-hover:
    backgroundColor: "{colors.green-hover}"
  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "12px 16px"
  field:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "12px"
  badge:
    backgroundColor: "{colors.mint}"
    textColor: "{colors.green}"
    rounded: "{rounded.badge}"
    padding: "2px 8px"
  surface:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.surface}"
---

# Design System: SkillsBridge workspace

## Overview

**Creative North Star: "An assessment desk"**

A clear reading surface, compact navigation, evidence arranged as a ledger, and an inline report. This is the shipped Operate-mode prototype: the student's source material carries the visual interest. White working surfaces sit on a quiet near-white canvas, with ink typography and restrained green states.

This document refreshes the existing direction contract against `prototype/static/index.html`, `style.css`, and `app.js`. It describes the implemented interface, not validated model performance or a published service. Durable product truth remains in PRODUCT.md; surface behavior and implementation extensions are recorded in `.impeccable/surfaces/assessment-desk.json`.

**Key Characteristics:**
- Evidence and uncertainty remain readable together.
- Complete quiet borders define flat working surfaces.
- Inline editing and expansion keep source context close.
- Small, functional state changes respect reduced motion.

## Colors

The primary palette pairs deep green and muted green highlights with near-white surfaces and readable ink.

### Primary
- **Desk green:** primary actions, report icon, links, and active navigation text.
- **Deep desk green:** primary button hover.
- **Evidence mint:** supported/default badges and evidence-related accents.

### Neutral
- **Canvas:** workspace background.
- **Working white:** forms, evidence entries, and report surfaces.
- **Ink:** headings and primary copy.
- **Secondary / faint:** supporting text and import separators.
- **Ledger line:** complete panel borders and dividers.
- **Soft surface:** muted badges, hover surfaces, and report notices.

### Status
Warning badges use a warm cream background with brown text; failed badges and error messages use restrained red treatments. Labels supply the meaning alongside color. The guide panel uses a muted green surface; the integration code sample uses a dark green surface.

**The Status Truth Rule.** Green connection status means the workspace connected; evaluator capability and readiness-model status remain separate labelled facts.

## Typography

Geist is self-hosted at `/static/GeistVariable.woff2`, with system sans fallbacks and `font-display: swap`. Headings are balanced; paragraphs use pretty wrapping. The interface uses a fixed scale rather than viewport-sized display type.

- **Headline:** page headings use the frontmatter headline role; at widths up to 1180px they become (30px / 36px).
- **Title:** panel headings use the title role; guide and model headings use (24px / 32px). Mobile panel/report headings use (16px).
- **Body:** base copy uses the body role; detailed evidence, report, and instructional text commonly uses (12px), with (20–22px) reading line heights.
- **Label:** field labels use the label role. Metadata and badges use (10–11px); the uppercase sidebar workspace label adds (0.12em) tracking.
- **Code:** integration examples use `ui-monospace, SFMono-Regular, Consolas, monospace`, normally (11px / 23px), with tabular numerals in the optional metric table.

## Layout

Desktop uses a fixed left rail (216px), a top bar (72px), and a flexible main area capped at (1520px). Main padding is (40px). The assessment workspace pairs a flexible primary column with a context column (272px), separated by (24px). Profile fields use two columns; evidence editors expand below their ledger summaries.

At widths of at least (1500px), main padding becomes (48px 56px) and the context column becomes (304px). At up to (1180px), the rail narrows to (192px), main padding becomes (32px 24px), and profile fields stack. At up to (980px), the workspace becomes one column with a two-column context region; model and API layouts stack. At up to (700px), navigation becomes a horizontally scrollable top row, content uses (24px 20px) padding, profile/editor/context grids become single-column, and the supporting how-to panel is hidden. The desktop profile/settings entry is hidden on mobile; API access remains available through the integration view.

History changes from a row with a date to stacked records on mobile. Long code remains horizontally scrollable. Controls and grid children allow shrinking to avoid forcing the page wider.

## Elevation & Depth

Working surfaces are flat: white fills, complete thin borders, and softly tinted insets provide separation. Shadows are reserved for interruption layers: the native dialog uses (0 24px 80px #23362926), and the toast uses (0 8px 24px #18332224). Dialog backdrops dim the workspace with (#152a1e50).

## Shapes

Panel and dialog corners use the surface radius; inputs, buttons, and evidence entries use the control radius. Smaller evidence icons and quotation blocks use the inset radius; badges use the badge radius. Avatars and connection dots are circular. The empty evidence region has a dashed border. Inline stroke icons are typically (16–20px), with (1.6px) strokes; the guide's three bars are a restrained decorative signature.

## Components

### Buttons and fields

Primary buttons are solid green, secondary buttons are white with a complete border, and text actions are unfilled. Standard buttons use (12px 16px) padding; small buttons use (8px 12px). Hover changes the fill or text color; enabled buttons shift down (1px) when pressed. Disabled controls use reduced opacity and a waiting cursor.

Fields have a white fill, a thin (#dce2da) border, and (12px) padding. Textareas resize vertically. Focused fields use a (#64836e) border and translucent outline. Keyboard focus uses an offset (3px) outline in (#6b9479). Validation and connection errors appear as inline alert messages rather than color alone.

### Navigation and status

Navigation items have a minimum height of (44px), muted default text, a soft hover fill, and a green active treatment. The current page has `aria-current="page"`. On mobile an underline replaces the active fill. Badges distinguish normal, muted, warning, and failed states through text and tone; they are status labels rather than filters.

### Evidence ledger and report

Native disclosure elements hold inline evidence editors, optional scores, and report artifacts. Evidence entries expose category, title, source text, optional URL, and removal. Their summaries preserve a compact ledger with category icons and student-supplied labels. Imports accept README text or a keyboard-operable text-file attachment; they do not imply verified ownership or deployed code.

A persistent synthetic-example notice remains visible after edits and appears in the resulting example report. Processing has live text, a pulse dot, skeletons, and a manual status check. The inline report distinguishes offline scanning from semantic assessment, displays readiness unavailability explicitly, and pairs findings with source quotes. Experience tiers, reasons, and optional tier quotes sit within each artifact. Offline results do not claim semantic level assessment. Report completion focuses its heading and announces readiness through a status toast.

The report offers JSON export and an inline human-review request form. A saved request explicitly says no notification was sent. History supports name search, refresh, reopening/status checks, and deletion through a native confirmation dialog. The model lab presents the awaiting-labels state and conditional experimental-model information. The integration view presents endpoints and a copyable Python example. Workspace access uses a native password dialog with a page-memory API key; it is not a multiuser login.

### Motion and feedback

Most state transitions use (180ms) with `cubic-bezier(.22,1,.36,1)`. View changes use a short (220ms) fade and (5px) rise. Disclosure chevrons rotate; processing pulses at (1.5s). Scrolling to processing/report is smooth unless reduced motion is requested. The reduced-motion media query removes animations and transitions. Status toasts remain for (4 seconds).

## Do's and Don'ts

### Do:
- Do keep source quotations, uncertainty, and evidence status close to findings.
- Do preserve visible keyboard focus and native disclosure/dialog behavior.
- Do distinguish synthetic examples, offline scanning, semantic assessment, and model availability.
- Do use flat bordered working surfaces and reserve shadows for dialogs and toasts.

### Don't:
- Don't add fabricated accuracy, readiness percentages, decorative charts, or score rings.
- Don't replace evidence with stock imagery, glass effects, or background gradients.
- Don't imply that a review request sends a notification or that workspace access is a multiuser login.
- Don't claim real labels, a trained replacement model, configured live provider credentials, or published hosting from this UI.
