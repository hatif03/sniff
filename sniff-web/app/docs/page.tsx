import fs from 'fs';
import path from 'path';
import Link from 'next/link';
import { Metadata } from 'next';
import MarkdownContent from '@/components/MarkdownContent';
import { Button } from '@/components/ui/button';
import { Container } from '@/components/ui/container';
import { Display2, Heading3 } from '@/components/ui/typography';

export const metadata: Metadata = {
  title: "Documentation - Sniff",
  description: "Reference docs for Sniff, including the sniff-cli developer tool for persona-driven signup testing.",
};

// Read the markdown file at build time
function getDocumentation() {
  const docsPath = path.join(process.cwd(), 'docs', 'cli-readme.md');
  const content = fs.readFileSync(docsPath, 'utf8');

  // Extract sections for table of contents, excluding "Table of Contents" itself
  const sections = content.split('\n## ').slice(1);
  const tableOfContents = sections
    .map(section => {
      const title = section.split('\n')[0];
      const id = title.toLowerCase().replace(/[^a-z0-9]+/g, '-');
      return { title, id };
    })
    .filter(item => item.title !== 'Table of Contents'); // Exclude "Table of Contents"

  // Remove the "Table of Contents" section from the content
  const contentWithoutTOC = content.replace(/\n## Table of Contents[\s\S]*?(?=\n## |$)/, '');

  return { content: contentWithoutTOC, tableOfContents };
}

export default function DocsPage() {
  const { content, tableOfContents } = getDocumentation();

  const tocNav = (
    <nav className="space-y-2">
      {tableOfContents.map((item) => (
        <a
          key={item.id}
          href={`#${item.id}`}
          className="block text-sm text-muted-foreground hover:text-primary transition-colors py-1"
        >
          {item.title}
        </a>
      ))}
    </nav>
  );

  return (
    <main className="min-h-screen bg-background">
      {/* Header */}
      <header className="bg-surface border-b border-foreground/10 sticky top-0 z-50 backdrop-blur-sm bg-surface/95">
        <Container className="py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link href="/" className="text-2xl font-display font-bold text-foreground hover:text-primary transition-colors">
                Sniff
              </Link>
              <span className="text-muted-foreground">/</span>
              <span className="text-lg font-medium text-muted-foreground">Documentation</span>
            </div>
            <Link
              href="/"
              className="px-4 py-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
            >
              ← Back to Home
            </Link>
          </div>
        </Container>
      </header>

      <Container className="py-12">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-12">
          {/* Sidebar Table of Contents */}
          <aside className="lg:col-span-1">
            {/* Mobile: collapsible so it doesn't push all article content below a full TOC dump */}
            <details className="lg:hidden mb-8 rounded-lg border border-foreground/10 bg-surface p-4">
              <summary className="cursor-pointer text-sm font-bold text-foreground uppercase tracking-wide">
                On This Page
              </summary>
              <div className="mt-4">{tocNav}</div>
            </details>

            {/* Desktop: sticky sidebar, always expanded */}
            <div className="hidden lg:block sticky top-24">
              <h2 className="text-sm font-bold text-foreground uppercase tracking-wide mb-4">
                On This Page
              </h2>
              {tocNav}
            </div>
          </aside>

          {/* Main Content */}
          <article className="lg:col-span-3">
            <div className="mb-8">
              <Display2 as="h1" className="text-foreground mb-4">
                Documentation
              </Display2>
              <p className="text-lg text-muted-foreground">
                Most people run Sniff straight from the{" "}
                <Link href="/dashboard/new-run" className="text-primary hover:underline">
                  web dashboard
                </Link>
                . For developers who want scriptable, CI-friendly runs, <code>sniff-cli</code> is
                also available — reference docs below.
              </p>
            </div>

            {/* Render markdown content with client component */}
            <MarkdownContent content={content} />

            {/* Footer CTA */}
            <div className="mt-16 p-8 bg-gradient-to-br from-primary/10 to-soft-accent/10 rounded-2xl border border-primary/20">
              <Heading3 as="h3" className="text-foreground mb-3">
                Ready to Get Started?
              </Heading3>
              <p className="text-muted-foreground mb-6">
                Run your first persona-driven audit from the dashboard in under 60 seconds — no
                install required. Prefer the command line? <code>sniff-cli</code> covers CI and
                scripted runs, see the reference below.
              </p>
              <div className="flex flex-wrap gap-3">
                <Button asChild size="lg">
                  <Link href="/dashboard/new-run">Run an Audit</Link>
                </Button>
                <Button asChild variant="outline" size="lg">
                  <Link href="/">Back to Home</Link>
                </Button>
              </div>
            </div>
          </article>
        </div>
      </Container>
    </main>
  );
}
