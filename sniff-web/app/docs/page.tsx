import fs from 'fs';
import path from 'path';
import Link from 'next/link';
import { Metadata } from 'next';
import MarkdownContent from '@/components/MarkdownContent';

export const metadata: Metadata = {
  title: "CLI Documentation - Sherlock Personas",
  description: "Complete guide to using the Sherlock CLI for persona-driven signup testing.",
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

  return (
    <main className="min-h-screen bg-background">
      {/* Header */}
      <header className="bg-surface border-b border-primary/10 sticky top-0 z-50 backdrop-blur-sm bg-surface/95">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link href="/" className="text-2xl font-display font-bold text-primary hover:text-accent transition-colors">
                Sherlock
              </Link>
              <span className="text-muted">/</span>
              <span className="text-lg font-medium text-muted">Documentation</span>
            </div>
            <Link
              href="/"
              className="px-4 py-2 text-sm font-medium text-muted hover:text-primary transition-colors"
            >
              ← Back to Home
            </Link>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-12">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-12">
          {/* Sidebar Table of Contents */}
          <aside className="lg:col-span-1">
            <div className="sticky top-24">
              <h2 className="text-sm font-bold text-primary uppercase tracking-wide mb-4">
                On This Page
              </h2>
              <nav className="space-y-2">
                {tableOfContents.map((item) => (
                  <a
                    key={item.id}
                    href={`#${item.id}`}
                    className="block text-sm text-muted hover:text-accent transition-colors py-1"
                  >
                    {item.title}
                  </a>
                ))}
              </nav>
            </div>
          </aside>

          {/* Main Content */}
          <article className="lg:col-span-3">
            <div className="mb-8">
              <h1 className="text-4xl font-display font-bold text-primary mb-4">
                Sherlock CLI Documentation
              </h1>
              <p className="text-lg text-muted">
                Everything you need to know to run persona-driven signup tests with Sherlock.
              </p>
            </div>

            {/* Render markdown content with client component */}
            <MarkdownContent content={content} />

            {/* Footer CTA */}
            <div className="mt-16 p-8 bg-gradient-to-br from-accent/10 to-soft-accent/10 rounded-2xl border border-accent/20">
              <h3 className="text-2xl font-display font-bold text-primary mb-3">
                Ready to Get Started?
              </h3>
              <p className="text-muted mb-6">
                Install Sherlock CLI and run your first persona-driven test in under 60 seconds.
              </p>
              <div className="bg-primary text-white p-4 rounded-lg font-mono text-sm mb-4">
                $ pip install sherlock-personas<br/>
                $ sherlock run --persona confused_first_time_user
              </div>
              <Link
                href="/"
                className="inline-block px-6 py-3 bg-accent text-white rounded-lg font-medium hover:bg-accent/90 transition-colors"
              >
                Back to Home
              </Link>
            </div>
          </article>
        </div>
      </div>
    </main>
  );
}
