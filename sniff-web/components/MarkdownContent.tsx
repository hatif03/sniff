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
          const isInline = !match;

          if (isInline) {
            return (
              <code className="bg-primary/10 text-accent px-1.5 py-0.5 rounded text-sm font-mono" {...props}>
                {children}
              </code>
            );
          }

          return (
            <pre className="bg-primary text-white p-4 rounded-lg overflow-x-auto my-4">
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
              className="text-2xl font-display font-bold text-primary mb-4 mt-8 pb-2 border-b border-primary/10 scroll-mt-24"
            >
              {children}
            </h2>
          );
        },
        h3({ children }) {
          return (
            <h3 className="text-xl font-display font-semibold text-primary mt-6 mb-3">
              {children}
            </h3>
          );
        },
        // Custom styling for paragraphs
        p({ children }) {
          return <p className="text-muted leading-relaxed my-4">{children}</p>;
        },
        // Custom styling for links
        a({ href, children }) {
          return (
            <a
              href={href}
              className="text-accent hover:text-accent/80 underline transition-colors"
              target={href?.startsWith('http') ? '_blank' : undefined}
              rel={href?.startsWith('http') ? 'noopener noreferrer' : undefined}
            >
              {children}
            </a>
          );
        },
        // Custom styling for lists
        ul({ children }) {
          return <ul className="list-disc list-inside space-y-2 text-muted my-4">{children}</ul>;
        },
        ol({ children }) {
          return <ol className="list-decimal list-inside space-y-2 text-muted my-4">{children}</ol>;
        },
        // Custom styling for tables
        table({ children }) {
          return (
            <div className="overflow-x-auto my-6">
              <table className="w-full border-collapse border border-primary/10">
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
            <th className="border border-primary/10 px-4 py-2 text-left font-semibold text-primary">
              {children}
            </th>
          );
        },
        td({ children }) {
          return (
            <td className="border border-primary/10 px-4 py-2 text-muted">
              {children}
            </td>
          );
        },
        // Custom styling for blockquotes
        blockquote({ children }) {
          return (
            <blockquote className="border-l-4 border-accent/30 pl-4 italic text-muted my-4">
              {children}
            </blockquote>
          );
        },
        // Custom styling for strong
        strong({ children }) {
          return <strong className="font-semibold text-primary">{children}</strong>;
        },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
