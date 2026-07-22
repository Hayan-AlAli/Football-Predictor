---
name: ui-ux-pro-max-skill
description: Use when creating, modifying, or reviewing UI components, styles, or user experience in the Football Predictor frontend. Provides guidelines for consistent, accessible, and polished UI/UX.
---

# UI/UX Pro Max Skill

Use when building or reviewing React components in `frontend/src/`. This project uses React 19 + Vite with a glassmorphism design system.

## Design System

- **Theme**: Dark glassmorphism with translucent cards (`glass-card` class)
- **Colors**: Use CSS custom properties defined in `index.css` and `App.css`
- **Spacing**: Follow consistent spacing scale (4px, 8px, 16px, 24px, 32px)
- **Typography**: Use system font stack, maintain clear hierarchy (h1 > h2 > h3)

## Component Guidelines

- **Naming**: PascalCase for components, co-locate CSS files
- **Structure**: One component per file, export default at bottom
- **Props**: Destructure in function signature, provide defaults where appropriate
- **State**: Lift state up only when needed, keep components focused

## CSS Conventions

- Use BEM-inspired naming: `.block__element--modifier`
- Leverage existing utility classes: `fade-in`, `glass-card`, `btn`, `btn-primary`, `btn-ghost`
- Prefer CSS custom properties for theming
- Avoid inline styles except for dynamic values

## Accessibility

- Use semantic HTML elements (`<main>`, `<header>`, `<footer>`, `<nav>`)
- Add `aria-label` to icon-only buttons
- Ensure color contrast meets WCAG AA standards
- Support keyboard navigation for all interactive elements
- Add `alt` text to images, `aria-live` for dynamic content updates

## Loading & Error States

- Always show loading indicators during async operations (use `Loader` component)
- Provide meaningful error messages with recovery actions
- Use `fade-in` class for smooth state transitions
- Empty states should guide users toward next actions

## Responsive Design

- Mobile-first approach
- Use CSS Grid and Flexbox for layouts
- Test breakpoints: 480px (mobile), 768px (tablet), 1024px (desktop)
- Ensure touch targets are at least 44x44px on mobile

## Interaction Patterns

- Debounce rapid user inputs (date pickers, search)
- Provide visual feedback on button clicks (hover, active states)
- Disable buttons during async operations to prevent double-submits
- Use optimistic UI updates where appropriate

## Performance

- Lazy load components below the fold
- Memoize expensive computations with `useMemo`
- Avoid unnecessary re-reactions with `React.memo` for pure components
- Keep bundle size minimal - avoid large unused dependencies

## File Structure

```
frontend/src/
├── components/        # Reusable UI components
│   ├── ComponentName.jsx
│   └── ComponentName.css (if needed)
├── api/              # API client functions
├── assets/           # Static assets (images, icons)
├── App.jsx           # Root component
├── App.css           # Global styles
└── index.css         # CSS reset and variables
```
