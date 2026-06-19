---
name: ui-ux-pro-max
description: UI/UX design intelligence for visual design and design systems.
type: prompt
whenToUse: When the user asks for UI/UX design direction, design systems, visual hierarchy, color, typography, or design review.
disableModelInvocation: false
---
# 🎨 UI/UX Pro Max

## Design Principles

1. **Mobile-first**: Design for 320px, scale up
2. **Accessibility**: WCAG 2.1 AA minimum
   - Color contrast 4.5:1
   - Focus indicators visible
   - Alt text for images
   - Keyboard navigable
3. **Performance**: < 100KB CSS, < 50KB JS for initial load
4. **Consistency**: Design system tokens (colors, spacing, typography)

## Component Patterns

### Forms
- Label above input (not placeholder as label)
- Error messages inline, below field
- Submit button disabled until valid
- Autofill-friendly names

### Buttons
- Primary: high contrast, one per page
- Secondary: outlined
- Destructive: red, requires confirmation
- Loading state: spinner, disabled

### Navigation
- Max 7 items in main nav
- Breadcrumbs for deep hierarchies
- Search in header for > 50 pages

## Tailwind Best Practices
```html
<!-- Good -->
<button class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700
               focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
               disabled:opacity-50 disabled:cursor-not-allowed">

<!-- Bad -->
<button class="p-2 bg-blue-500 text-white rounded">
```

## Responsive Breakpoints
- `sm`: 640px — minor adjustments
- `md`: 768px — layout changes
- `lg`: 1024px — major layout
- `xl`: 1280px — max-width containers

## Design Tokens Example
```css
:root {
  --color-primary: #2563eb;
  --color-danger: #dc2626;
  --space-1: 0.25rem;
  --space-2: 0.5rem;
  --space-4: 1rem;
  --radius: 0.5rem;
  --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
}
```
