import { describe, it, expect } from "vitest";
import { SSEParser } from "./sse";

describe("SSEParser", () => {
  it("yields a single complete event", () => {
    const p = new SSEParser();
    const events = p.feed("event: chunk\ndata: hello\n\n");
    expect(events).toEqual([{ event: "chunk", data: "hello", id: undefined }]);
  });

  it("buffers until the terminating blank line", () => {
    const p = new SSEParser();
    // Feed the payload across three chunks; nothing should fire until the
    // final blank line arrives, matching the whatwg SSE contract.
    expect(p.feed("event: chunk\n")).toEqual([]);
    expect(p.feed("data: ")).toEqual([]);
    expect(p.feed("hello\n\n")).toEqual([
      { event: "chunk", data: "hello", id: undefined },
    ]);
  });

  it("handles CRLF separators", () => {
    const p = new SSEParser();
    const events = p.feed("event: a\r\ndata: 1\r\n\r\nevent: b\r\ndata: 2\r\n\r\n");
    expect(events).toHaveLength(2);
    expect(events[0].data).toBe("1");
    expect(events[1].data).toBe("2");
  });

  it("ignores comment lines starting with ':'", () => {
    const p = new SSEParser();
    const events = p.feed(": heartbeat\nevent: ping\ndata: ok\n\n");
    expect(events).toEqual([{ event: "ping", data: "ok", id: undefined }]);
  });

  it("concatenates multiple data lines with newlines", () => {
    const p = new SSEParser();
    const events = p.feed("data: line1\ndata: line2\n\n");
    expect(events[0].data).toBe("line1\nline2");
  });

  it("defaults event name to 'message' when omitted", () => {
    const p = new SSEParser();
    const events = p.feed("data: anonymous\n\n");
    expect(events[0].event).toBe("message");
  });

  it("exposes id when provided", () => {
    const p = new SSEParser();
    const events = p.feed("id: 42\ndata: x\n\n");
    expect(events[0].id).toBe("42");
  });

  it("flushes trailing buffered event on end()", () => {
    const p = new SSEParser();
    expect(p.feed("event: final\ndata: z")).toEqual([]);
    // No blank line ever arrives; end() should still surface the partial
    // event so callers that close the stream cleanly don't lose the tail.
    expect(p.end()).toEqual([{ event: "final", data: "z", id: undefined }]);
  });

  it("skips an empty block (only whitespace / no data)", () => {
    const p = new SSEParser();
    const events = p.feed("\n\nevent: real\ndata: payload\n\n");
    expect(events).toHaveLength(1);
    expect(events[0].data).toBe("payload");
  });
});
