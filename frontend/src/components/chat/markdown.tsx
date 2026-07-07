import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn } from "@/lib/utils";

/** Renders chat message content as formatted markdown (bold, lists, code,
 * tables, links) instead of raw text. Used for both finished messages and
 * the in-progress streaming turn — react-markdown tolerates a still-open
 * `**`/code fence mid-stream, so it's safe to feed it partial text too. */
export function Markdown({ content, className }: { content: string; className?: string }) {
  return (
    <div className={cn("space-y-2 text-sm leading-relaxed text-foreground [&>*:last-child]:mb-0", className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          p: ({ children }) => <p className="whitespace-pre-wrap">{children}</p>,
          ul: ({ children }) => <ul className="list-disc space-y-1 pl-5">{children}</ul>,
          ol: ({ children }) => <ol className="list-decimal space-y-1 pl-5">{children}</ol>,
          li: ({ children }) => <li>{children}</li>,
          a: ({ children, href }) => (
            <a
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary underline underline-offset-2 hover:opacity-80"
            >
              {children}
            </a>
          ),
          strong: ({ children }) => <strong className="font-semibold text-foreground">{children}</strong>,
          code: ({ children, className }) => {
            const isBlock = /language-/.test(className ?? "");
            if (isBlock) {
              return <code className="block overflow-x-auto text-xs">{children}</code>;
            }
            return <code className="rounded bg-muted px-1 py-0.5 text-xs">{children}</code>;
          },
          pre: ({ children }) => (
            <pre className="overflow-x-auto rounded-md bg-muted p-3">{children}</pre>
          ),
          blockquote: ({ children }) => (
            <blockquote className="border-l-2 border-border pl-3 text-muted-foreground">
              {children}
            </blockquote>
          ),
          h1: ({ children }) => <h1 className="text-base font-semibold text-foreground">{children}</h1>,
          h2: ({ children }) => <h2 className="text-sm font-semibold text-foreground">{children}</h2>,
          h3: ({ children }) => <h3 className="text-sm font-semibold text-foreground">{children}</h3>,
          table: ({ children }) => (
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-left text-xs">{children}</table>
            </div>
          ),
          th: ({ children }) => (
            <th className="border-b border-border px-2 py-1 font-medium text-muted-foreground">{children}</th>
          ),
          td: ({ children }) => <td className="border-b border-border px-2 py-1">{children}</td>,
          hr: () => <hr className="border-border" />,
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
