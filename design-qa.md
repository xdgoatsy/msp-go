# Personal Home Design QA

## Comparison Target

- Source visual truth: `E:/code/msp-go/.tmp/personal-home-concept-1.png` (1487 x 1058).
- User-reported desktop crop: `C:/Users/Administrator/AppData/Local/Temp/codex-clipboard-a0d57afe-a195-4e30-aac1-80c952fd0c4e.png`.
- Student desktop implementation: `C:/Users/Administrator/.codex/visualizations/2026/07/21/019f86ea-94de-7ac3-a546-0601a2ff12bd/personal-home-student-final.png`.
- Teacher desktop implementation: `C:/Users/Administrator/.codex/visualizations/2026/07/21/019f86ea-94de-7ac3-a546-0601a2ff12bd/personal-home-teacher-final.png`.
- Student dark implementation: `C:/Users/Administrator/.codex/visualizations/2026/07/21/019f86ea-94de-7ac3-a546-0601a2ff12bd/personal-home-student-dark-final.png`.
- Student mobile implementation: `C:/Users/Administrator/.codex/visualizations/2026/07/21/019f86ea-94de-7ac3-a546-0601a2ff12bd/personal-home-student-mobile-final.png`.
- Mobile navigation state: `C:/Users/Administrator/.codex/visualizations/2026/07/21/019f86ea-94de-7ac3-a546-0601a2ff12bd/personal-home-mobile-menu-final.png`.
- Crop-fix wide desktop: `C:/Users/Administrator/.codex/visualizations/2026/07/21/019f86ea-94de-7ac3-a546-0601a2ff12bd/personal-home-hero-crop-fixed-wide.png`.
- Crop-fix 1440 desktop: `C:/Users/Administrator/.codex/visualizations/2026/07/21/019f86ea-94de-7ac3-a546-0601a2ff12bd/personal-home-hero-crop-fixed-1440.png`.
- Crop-fix dark desktop: `C:/Users/Administrator/.codex/visualizations/2026/07/21/019f86ea-94de-7ac3-a546-0601a2ff12bd/personal-home-hero-crop-fixed-dark-1440.png`.
- Implementation URL: `http://127.0.0.1:5173/home` after student or teacher login.
- Desktop state: authenticated student and teacher fixtures, light theme, 1440 x 1024 browser viewport. The Browser viewport could not reproduce the source's exact 1487 x 1058 inner viewport, so the 1432 x 1018 screenshot was proportionally normalized for comparison.
- Mobile state: authenticated student fixture, light theme, 390 x 844 browser viewport.

## Full-View Comparison Evidence

- Combined comparison: `C:/Users/Administrator/.codex/visualizations/2026/07/21/019f86ea-94de-7ac3-a546-0601a2ff12bd/personal-home-comparison-final.png`.
- The source and implementation were placed in one normalized side-by-side image before judgment; the comparison was also inspected with `view_image` alongside the source and latest screenshot.
- First-viewport balance is preserved: greeting and CTA on the left, calculus surface and notebook visual on the right, four-metric strip below, and a two-column continuation area.
- The implementation keeps the existing product header, role badge, navigation density, theme control, and icon family instead of introducing a second app shell.
- Student and teacher pages share one visual system while the data, copy, CTA, actions, recent activity, and affiliation adapt to role.

## Focused Region Comparison Evidence

- Hero and metrics: `C:/Users/Administrator/.codex/visualizations/2026/07/21/019f86ea-94de-7ac3-a546-0601a2ff12bd/personal-home-comparison-hero-final.png`.
- Content sections: `C:/Users/Administrator/.codex/visualizations/2026/07/21/019f86ea-94de-7ac3-a546-0601a2ff12bd/personal-home-comparison-sections-final.png`.
- The focused hero pass verified the H1, supporting sentence, CTA label/icon, continuation copy, image crop, metric labels, metric icons, and vertical spacing.
- The focused content pass verified headings, list density, progress treatment, timestamps, card radii, borders, icon alignment, and affiliation action placement.

## Required Fidelity Surfaces

- Fonts and typography: the project sans-serif stack is retained; the H1, section headings, metrics, labels, metadata, and controls have explicit sizes and weights with zero letter spacing. Long usernames and API-derived hero context use `overflow-wrap:anywhere`.
- Spacing and layout rhythm: the max-width, hero split, four-column metric strip, two-column content grid, 8 px radii, single-level cards, and restrained shadows preserve the source hierarchy without nested cards.
- Colors and visual tokens: the source's white, blue, violet, emerald, and coral balance maps to existing project tokens. The primary CTA now uses `primary-700` so white text passes AA in both themes.
- Image quality and asset fidelity: dedicated 69 KB light and 81 KB dark WebP assets preserve the calculus surface, notebook, pen, subject scale, and background integration. Both loaded at their natural dimensions with no placeholder, CSS drawing, inline SVG illustration, or broken crop.
- Copy and content: the source H1, student supporting sentence, CTA, and continuation context match. `累计学习` intentionally replaces the source's `本周学习` because the real overview API returns cumulative study time.
- Icons: all interface icons use the existing Lucide family with consistent outline weight, optical size, color, and alignment.
- States and interactions: student, teacher, light, dark, loading, partial failure, empty data, retry, theme toggle, mobile navigation open/close, and role-specific destinations are implemented.
- Accessibility: semantic headings and regions, labelled navigation, focus rings, status live region, reduced-motion handling, sufficient text contrast, mobile menu `aria-expanded`, and Escape dismissal are present.

## Above-The-Fold Copy Diff

- Matched: `早上好，林同学`, `坚持每天进步一点点，数学思维终将成就你的无限可能。`, `继续学习`, and the last-learning context.
- Intentional product additions: the existing role badge and authenticated user greeting remain in the header.
- Intentional data correction: `累计学习` reflects the backend contract; using `本周学习` would misrepresent cumulative minutes.
- Teacher copy is role-specific because the selected source only depicted the student state.

## Findings

No actionable P0, P1, or P2 findings remain.

## Intentional Deviations

- The source's scheduled times were not implemented because the product has no schedule contract. The same area uses real mastery data and common learning actions, avoiding fabricated times while preserving the two-column hierarchy and three-item rhythm.
- Existing project navigation includes `我的班级` and a role badge that were not shown in the concept. These are required product controls and remain visually consistent.
- The generated hero asset omits the source's freestanding formula annotation but preserves the mathematical surface, notebook, pen, palette, crop, and visual weight.

## Patches Made During QA

- Routed student and teacher login, root, logo, and role fallback paths to `/home`; administrators remain on `/admin/dashboard`.
- Added independent `Promise.allSettled` data regions so request failures do not become false zero or empty states.
- Corrected cumulative study-time labeling and converted student mastery ratios from `0..1` to `0..100` display percentages.
- Corrected teacher class-request failure copy and added an unexpected-payload fallback that exits loading and supports retry.
- Added light/dark calculus assets, role-aware sections, entrance/progress/float motion, and reduced-motion support for Framer Motion and skeleton pulses.
- Replaced the desktop hero image's `object-cover` plus 1.3x zoom with a 340 px media frame and right-aligned `object-contain` at 1.05x, keeping the calculus peaks visible without weakening the notebook and pen composition.
- Raised CTA and small-text contrast, added the partial-failure live region, and protected long dynamic hero text from clipping.
- Added a semantic mobile navigation landmark and a working overflow menu with Escape dismissal.
- Removed temporary preview and temporary test sources before handoff.

## Verification

- Browser/IAB desktop: student light, teacher light, and student dark rendered meaningful content with loaded assets, no horizontal overflow, and no new console warning/error entries after a clean preview reload.
- Browser responsive check: 390 x 844 mobile had no document-level horizontal overflow; the hero, image, metric cards, and text stayed within the viewport. The calculus image intentionally crops inside its overflow-hidden media frame.
- Desktop crop follow-up: the 2180 x 900 and 1440 x 1024 browser checks rendered a 672 x 340 media frame with `object-fit: contain`, `object-position: 100% 50%`, and `scale: 1.05`; every calculus peak remained inside the frame and the light asset loaded at its natural 1694 px width.
- Dark-theme crop follow-up: the dark asset loaded at its natural 1774 px width in the same 672 x 340 frame, with the peaks, notebook, and pen all visible.
- Mobile regression follow-up: the implementation diff is limited to `lg:` classes, so the base `object-cover`, `scale-[1.15]`, and `sm:scale-125` behavior shown in the existing real 390 x 844 mobile screenshot is unchanged. A current 382 px-wide DOM geometry check also reported `object-fit: cover`, `scale: 1.15`, and a 374 px document inside the 382 px viewport. Its browser screenshot output was truncated to 382 x 272 and is intentionally excluded from visual evidence.
- Console follow-up: the two existing data-request warnings were present before the style change and did not increase after reload, viewport changes, or theme interaction; no framework overlay or hero-related warning/error appeared.
- Interaction proof: theme toggled light/dark; mobile navigation changed `aria-expanded` from `false` to `true`, exposed all role links, and returned to `false` on Escape.
- Route protection: unauthenticated `/home` redirected to `/welcome`.
- Temporary contract tests: 2/2 passed for student mastery `0.72 -> 72%`, cumulative labeling, and teacher class-request failure semantics; the temporary test file was deleted.
- Earlier production-data helper verification: 18/18 temporary tests passed with 98.57% statements, 83.72% branches, 100% functions, and 100% lines for `homeData.ts`; those temporary sources were deleted as required.
- `npm.cmd run lint`: passed.
- `npm.cmd run build`: passed; only pre-existing Browserslist age and large-chunk advisory warnings remain.
- `git diff --check`: passed with line-ending notices only.
- Repository scan: no test/spec source, temporary preview entry, preview token, or test-only fixture remains.

## Residual Risk

- Safari and Firefox were not separately exercised.
- Real backend outage transitions were isolated in temporary tests and code review rather than induced against a live production account.
- Source and implementation viewport sizes differ slightly because the in-app browser's inner viewport could not be set to the source's exact dimensions; the comparison uses proportional normalization and an additional exact 390 x 844 responsive check.

final result: passed
