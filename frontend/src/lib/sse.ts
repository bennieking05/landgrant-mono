/**
 * Tiny incremental Server-Sent Events parser.
 *
 * Phase 4.4: the copilot streaming panel used to split on ``\n`` at read
 * boundaries, which drops ``data:`` records whose payloads span multiple
 * chunks.  ``SSEParser`` buffers bytes and yields complete events only after
 * the terminating blank line, matching the SSE spec:
 * https://html.spec.whatwg.org/multipage/server-sent-events.html
 */

export type SSEEvent = {
  event: string;
  data: string;
  id?: string;
};

export class SSEParser {
  private buffer = "";
  private decoder = new TextDecoder();

  feed(chunk: Uint8Array | string): SSEEvent[] {
    const text =
      typeof chunk === "string" ? chunk : this.decoder.decode(chunk, { stream: true });
    this.buffer += text;
    return this.flushEvents();
  }

  /** Flush any trailing event that isn't terminated by ``\n\n``. */
  end(): SSEEvent[] {
    if (this.buffer.length === 0) return [];
    const trailing = this.buffer;
    this.buffer = "";
    const ev = this.parseBlock(trailing);
    return ev ? [ev] : [];
  }

  private flushEvents(): SSEEvent[] {
    const events: SSEEvent[] = [];
    let idx: number;

    // Per spec, events are separated by a blank line (\n\n or \r\n\r\n).
    while (
      (idx = Math.min(
        this.firstIndex("\n\n"),
        this.firstIndex("\r\n\r\n"),
      )) !== Number.POSITIVE_INFINITY
    ) {
      const raw = this.buffer.slice(0, idx);
      this.buffer = this.buffer.slice(
        idx + (this.buffer.startsWith("\r\n", idx) ? 4 : 2),
      );
      const parsed = this.parseBlock(raw);
      if (parsed) events.push(parsed);
    }
    return events;
  }

  private firstIndex(needle: string): number {
    const i = this.buffer.indexOf(needle);
    return i === -1 ? Number.POSITIVE_INFINITY : i;
  }

  private parseBlock(raw: string): SSEEvent | null {
    if (!raw.trim()) return null;
    let event = "message";
    let data = "";
    let id: string | undefined;

    for (const rawLine of raw.split(/\r?\n/)) {
      if (!rawLine || rawLine.startsWith(":")) continue; // comments
      const idx = rawLine.indexOf(":");
      const field = idx === -1 ? rawLine : rawLine.slice(0, idx);
      const value = idx === -1 ? "" : rawLine.slice(idx + 1).replace(/^ /, "");

      switch (field) {
        case "event":
          event = value;
          break;
        case "data":
          data = data ? `${data}\n${value}` : value;
          break;
        case "id":
          id = value;
          break;
        default:
          break;
      }
    }

    if (!data) return null;
    return { event, data, id };
  }
}

/** Convenience helper for async iteration over a streaming body. */
export async function* readSSEStream(
  reader: ReadableStreamDefaultReader<Uint8Array>,
): AsyncGenerator<SSEEvent> {
  const parser = new SSEParser();
  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      for (const ev of parser.end()) yield ev;
      return;
    }
    for (const ev of parser.feed(value)) yield ev;
  }
}
