# Sherlock Personas Website

A high-impact single-page website showcasing Sherlock Personas - AI-powered signup experiments with instant team alerts.

## Features

- ✨ **Animation-First Design**: Smooth, purposeful animations built with Framer Motion
- 📱 **Fully Responsive**: Optimized for mobile, tablet, and desktop
- ⚡ **Performance Optimized**: Fast loading with < 145kB First Load JS
- ♿ **Accessible**: Supports reduced motion preferences
- 🎨 **Clean Design**: Minimal UI with calm, confident aesthetics

## Tech Stack

- **Framework**: Next.js 15 (App Router)
- **Language**: TypeScript (strict mode)
- **Styling**: Tailwind CSS
- **Animation**: Framer Motion + GSAP
- **Smooth Scroll**: Lenis
- **Fonts**: Space Grotesk (display), Inter (body), JetBrains Mono (code)

## Getting Started

### Prerequisites

- Node.js 18+
- Yarn package manager

### Installation

```bash
# Install dependencies
yarn install

# Start development server
yarn dev

# Build for production
yarn build

# Start production server
yarn start
```

Open [http://localhost:3000](http://localhost:3000) to view the site.

## Deployment to Vercel

### Option 1: Deploy via GitHub (Recommended)

1. Push your code to GitHub:
   ```bash
   git remote add origin <your-github-repo-url>
   git push -u origin main
   ```

2. Visit [vercel.com](https://vercel.com)
3. Click "New Project"
4. Import your GitHub repository
5. Vercel will auto-detect Next.js and deploy

### Option 2: Deploy via Vercel CLI

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel

# Deploy to production
vercel --prod
```

## Project Structure

```
sherlock_website/
├── app/
│   ├── globals.css         # Global styles
│   ├── layout.tsx          # Root layout with fonts
│   └── page.tsx            # Main page
├── components/
│   ├── HeroSection.tsx
│   ├── ProblemSection.tsx
│   ├── HowItWorksSection.tsx
│   ├── ReplaySection.tsx
│   ├── DifferentiatorsSection.tsx
│   ├── ArchitectureSection.tsx
│   ├── FooterCTA.tsx
│   └── SmoothScroll.tsx
├── PLAN.md                 # Design & technical spec
└── WORKLOG.md             # Implementation log
```

## Performance

- **First Load JS**: 145 kB
- **Main Route**: 43 kB
- **LCP Target**: < 2.5s
- **Scroll Performance**: 60fps

## Animation Highlights

1. **Hero**: Staggered text reveals with underline sweep effect
2. **Timeline**: Vertical timeline with alternating content cards
3. **Terminal**: Character-by-character typewriter effect
4. **Alert Card**: Rise-in animation with scale + opacity
5. **Smooth Scroll**: Buttery smooth scrolling via Lenis

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## License

Built for the hackathon with ❤️

## Credits

Built with Claude, Bedrock, and modern web technologies.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
