"use client";

import type { Components } from "react-markdown";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const components: Components = {
  h2: ({ children }) => (
    <h2 className="mt-5 text-base font-semibold text-[var(--ink)] first:mt-0">{children}</h2>
  ),
  h3: ({ children }) => (
    <h3 className="mt-4 text-sm font-semibold text-[var(--ink)] first:mt-0">{children}</h3>
  ),
  h4: ({ children }) => (
    <h4 className="mt-3 text-sm font-medium text-[var(--ink)] first:mt-0">{children}</h4>
  ),
  p: ({ children }) => <p className="mt-2 text-sm leading-6 text-[var(--ink)] first:mt-0">{children}</p>,
  ul: ({ children }) => <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-[var(--ink)]">{children}</ul>,
  ol: ({ children }) => (
    <ol className="mt-2 list-decimal space-y-1 pl-5 text-sm leading-6 text-[var(--ink)]">{children}</ol>
  ),
  li: ({ children }) => <li className="leading-6">{children}</li>,
  strong: ({ children }) => <strong className="font-semibold text-[var(--ink)]">{children}</strong>,
  blockquote: ({ children }) => (
    <blockquote className="mt-2 border-l-2 border-[var(--line)] pl-3 text-sm text-[var(--ink)]/80">{children}</blockquote>
  ),
  table: ({ children }) => (
    <div className="mt-2 overflow-x-auto rounded-xl border border-[var(--line)]">
      <table className="w-full border-collapse text-sm">{children}</table>
    </div>
  ),
  thead: ({ children }) => <thead className="bg-[var(--cream)] text-left text-xs uppercase tracking-wide">{children}</thead>,
  th: ({ children }) => <th className="px-3 py-2 font-medium text-[var(--ink)]/70">{children}</th>,
  td: ({ children }) => <td className="border-t border-[var(--line)] px-3 py-2 text-[var(--ink)]">{children}</td>,
  a: ({ children, href }) => (
    <a href={href} className="text-[var(--brand)] underline" target="_blank" rel="noreferrer">
      {children}
    </a>
  ),
};

export function MarkdownView({ value }: { value: string }) {
  return <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>{value}</ReactMarkdown>;
}
