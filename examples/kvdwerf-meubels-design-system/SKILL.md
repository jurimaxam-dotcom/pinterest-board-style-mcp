---
name: kvdwerf-meubels-design
description: Use this skill to generate well-branded interfaces and assets in the "Meubels (kvdwerf)" style (derived from a Pinterest moodboard). Contains color tokens, radius and visual/content guidelines as a foundations design system.
user-invocable: true
---

Read the `readme.md` in this skill and explore the token files under `tokens/`.

When creating visual artifacts (mocks, prototypes, slides) or production code, use the CSS custom properties from `styles.css` (`--color-*`, `--radius-base`) and follow the Do/Don't directives in the readme. Pull colours from these tokens instead of inventing new ones.

This is a **foundations** design system (colours + radius + style guidance) distilled from a moodboard: it ships **no** prebuilt components and **no** font files. Treat typography as *guidance* (classification only), never as bundled fonts.

If invoked without further guidance, ask what the user wants to build, then act as an expert designer working in this palette and vibe.
