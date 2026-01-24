// app/components/Section.tsx
import Container from "./Container";

export default function Section({
  eyebrow,
  title,
  children,
}: {
  eyebrow?: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="py-10 md:py-12 border-b border-zinc-900/80">
      <Container>
        {eyebrow && (
          <p className="text-xs font-semibold tracking-[0.2em] uppercase text-zinc-500 mb-3">
            {eyebrow}
          </p>
        )}
        <h2 className="text-2xl md:text-3xl font-semibold mb-4 text-zinc-50">
          {title}
        </h2>
        <div className="prose prose-invert prose-sm md:prose-base max-w-none prose-headings:text-zinc-50 prose-p:text-zinc-300/90 prose-li:text-zinc-300/90 prose-strong:text-zinc-50">
          {children}
        </div>
      </Container>
    </section>
  );
}
