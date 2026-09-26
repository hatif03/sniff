'use client';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface MarkdownContentProps {
  content: string;
}

export default function MarkdownContent({ content }: MarkdownContentProps) {
  return (
    <div className="prose prose-slate max-w-none">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
        // Custom styling for code blocks
        code({ node, className, children, ...props }) {
          const match = /language-(\w+)/.exec(className || '');
          // A fenced code block with no language tag (```` ``` ````, no
          // `bash`/etc after it) still produces a <pre><code> structure with
          // no `language-*` className - checking className alone misclassified
          // it as inline code, which skipped the overflow-x-auto wrapper and
          // caused real page-level horizontal overflow on mobile for any such
          // block. True inline code (single backtick) never contains a
          // newline, so that's the reliable signal instead.
          const isInline = !match && !String(children).includes('\n');

          if (isInline) {
            return (
              <code className="bg-foreground/10 text-primary px-1.5 py-0.5 rounded text-sm font-mono" {...props}>
                {children}
              </code>
            );
          }

          return (
            <pre className="bg-foreground text-white p-4 rounded-lg overflow-x-auto my-4">
              <code className="font-mono text-sm" {...props}>
                {children}
              </code>
            </pre>
          );
        },
        // Custom styling for headings
        h2({ children }) {
          const id = String(children).toLowerCase().replace(/[^a-z0-9]+/g, '-');
          return (
            <h2
              id={id}
              className="text-2xl font-display font-bold text-foreground mb-4 mt-8 pb-2 border-b border-foreground/10 scroll-mt-24"
            >
              {children}
            </h2>
          );
        },
        h3({ children }) {
          return (
            <h3 className="text-xl font-display font-semibold text-foreground mt-6 mb-3">
              {children}
            </h3>
          );
        },
        // Custom styling for paragraphs
        p({ children }) {
          return <p className="text-muted-foreground leading-relaxed my-4">{children}</p>;
        },
        // Custom styling for links
        a({ href, children }) {
          return (
            <a
              href={href}
              className="text-primary hover:text-primary/80 underline transition-colors"
              target={href?.startsWith('http') ? '_blank' : undefined}
              rel={href?.startsWith('http') ? 'noopener noreferrer' : undefined}
            >
              {children}
            </a>
          );
        },
        // Custom styling for lists
        ul({ children }) {
          return <ul className="list-disc list-inside space-y-2 text-muted-foreground my-4">{children}</ul>;
        },
        ol({ children }) {
          return <ol className="list-decimal list-inside space-y-2 text-muted-foreground my-4">{children}</ol>;
        },
        // Custom styling for tables
        table({ children }) {
          return (
            <div className="overflow-x-auto my-6">
              <table className="w-full border-collapse border border-foreground/10">
                {children}
              </table>
            </div>
          );
        },
        thead({ children }) {
          return <thead className="bg-background">{children}</thead>;
        },
        th({ children }) {
          return (
            <th className="border border-foreground/10 px-4 py-2 text-left font-semibold text-foreground">
              {children}
            </th>
          );
        },
        td({ children }) {
          return (
            <td className="border border-foreground/10 px-4 py-2 text-muted-foreground">
              {children}
            </td>
          );
        },
        // Custom styling for blockquotes
        blockquote({ children }) {
          return (
            <blockquote className="border-l-4 border-primary/30 pl-4 italic text-muted-foreground my-4">
              {children}
            </blockquote>
          );
        },
        // Custom styling for strong
        strong({ children }) {
          return <strong className="font-semibold text-foreground">{children}</strong>;
        },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
