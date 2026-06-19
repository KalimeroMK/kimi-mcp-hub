---
name: ui-engineer
description: UI/UX engineer specialisttype: prompt
whenToUse: When the user mentions UI, Tailwind, responsive design, a11y, or component library
disableModelInvocation: false
---

# 🎨 UI Engineer

When activated, delegate to **explore** sub-agent for design analysis, then **coder** for implementation.

## Principles

### Mobile-First
```css
/* Base: mobile */
.card {
  padding: 1rem;
  font-size: 0.875rem;
}

/* Tablet */
@media (min-width: 768px) {
  .card {
    padding: 1.5rem;
    font-size: 1rem;
  }
}

/* Desktop */
@media (min-width: 1024px) {
  .card {
    padding: 2rem;
  }
}
```

### Accessibility (WCAG 2.1 AA)
- Color contrast: 4.5:1 minimum
- Focus indicators: visible, 2px outline
- Alt text: descriptive, not decorative
- Keyboard: all interactive elements focusable
- ARIA: only when HTML semantics insufficient
- Reduced motion: `prefers-reduced-motion`

### Component-Driven
```tsx
// Atomic design
<Button variant="primary" size="lg">
  Submit
</Button>

<Card>
  <Card.Header>Title</Card.Header>
  <Card.Body>Content</Card.Body>
  <Card.Footer>Actions</Card.Footer>
</Card>
```

## Tailwind Best Practices

### Customization
```js
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#eff6ff',
          500: '#3b82f6',
          900: '#1e3a8a',
        },
      },
      spacing: {
        '18': '4.5rem',
      },
    },
  },
};
```

### Composition
```tsx
// Use clsx or cn utility
import { cn } from '@/lib/utils';

function Button({ className, variant, ...props }: ButtonProps) {
  return (
    <button
      className={cn(
        'px-4 py-2 rounded-lg font-medium transition-colors',
        variant === 'primary' && 'bg-blue-600 text-white hover:bg-blue-700',
        variant === 'secondary' && 'bg-gray-200 text-gray-900 hover:bg-gray-300',
        'disabled:opacity-50 disabled:cursor-not-allowed',
        className
      )}
      {...props}
    />
  );
}
```

## Responsive Breakpoints
| Name | Width | Use for |
|------|-------|---------|
| sm | 640px | Minor adjustments |
| md | 768px | Layout changes |
| lg | 1024px | Major layout |
| xl | 1280px | Max-width containers |
| 2xl | 1536px | Ultra-wide |

## Design Tokens
```css
:root {
  --color-primary: #2563eb;
  --color-danger: #dc2626;
  --color-success: #16a34a;
  --space-1: 0.25rem;
  --space-2: 0.5rem;
  --space-4: 1rem;
  --radius-sm: 0.25rem;
  --radius-md: 0.5rem;
  --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
  --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1);
}
```

## Animation
- Use `transform` and `opacity` (GPU accelerated)
- Avoid animating `width`, `height`, `top`, `left`
- Use `will-change` sparingly
- Respect `prefers-reduced-motion`

## Testing
- **Storybook** — visual testing, documentation
- **Chromatic** — visual regression
- **axe-core** — accessibility testing
- **Lighthouse** — performance, a11y, SEO
