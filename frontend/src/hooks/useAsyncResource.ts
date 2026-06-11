import { useCallback, useEffect, useRef, useState } from "react";
import { isApiError } from "@/lib/api";

export type AsyncResourcePhase =
  | "idle"
  | "loading"
  | "success"
  | "empty"
  | "error"
  | "forbidden";

export type UseAsyncResourceOptions<T> = {
  /** Return loaded data */
  load: () => Promise<T>;
  /** When data counts as empty (show empty state, not error) */
  isEmpty: (data: T) => boolean;
  /** Fail load after this many ms (default 30_000). Uses Promise.race. */
  timeoutMs?: number;
  /** Run load on mount when true (default true) */
  loadOnMount?: boolean;
};

export type UseAsyncResourceResult<T> = {
  phase: AsyncResourcePhase;
  data: T | undefined;
  errorMessage: string | null;
  /** True when HTTP 403 or 401 */
  accessDenied: boolean;
  retry: () => void;
  /** Call when dependencies change (e.g. filter) */
  reload: () => void;
};

const DEFAULT_TIMEOUT_MS = 10_000;

class AsyncTimeoutError extends Error {
  constructor() {
    super("timeout");
    this.name = "AsyncTimeoutError";
  }
}

/**
 * Standard loading / empty / error / forbidden handling with optional timeout.
 * Use with {@link ApiError} from api.ts so 403 is not shown as "no data".
 */
export function useAsyncResource<T>(
  options: UseAsyncResourceOptions<T>,
): UseAsyncResourceResult<T> {
  const {
    load,
    isEmpty,
    timeoutMs = DEFAULT_TIMEOUT_MS,
    loadOnMount = true,
  } = options;

  const [phase, setPhase] = useState<AsyncResourcePhase>(
    loadOnMount ? "loading" : "idle",
  );
  const [data, setData] = useState<T | undefined>(undefined);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [accessDenied, setAccessDenied] = useState(false);
  const seq = useRef(0);

  const run = useCallback(async () => {
    const my = ++seq.current;
    setPhase("loading");
    setErrorMessage(null);
    setAccessDenied(false);

    const timedLoad = async (): Promise<T> => {
      if (timeoutMs <= 0) {
        return load();
      }
      return Promise.race([
        load(),
        new Promise<never>((_, reject) => {
          window.setTimeout(() => reject(new AsyncTimeoutError()), timeoutMs);
        }),
      ]);
    };

    try {
      const result = await timedLoad();
      if (seq.current !== my) return;
      if (isEmpty(result)) {
        setData(result);
        setPhase("empty");
      } else {
        setData(result);
        setPhase("success");
      }
    } catch (e: unknown) {
      if (seq.current !== my) return;
      if (e instanceof AsyncTimeoutError) {
        setErrorMessage(
          "This is taking longer than expected. Check your connection and try again.",
        );
        setPhase("error");
        return;
      }
      if (isApiError(e) && (e.status === 403 || e.status === 401)) {
        setAccessDenied(true);
        setErrorMessage(
          "You don't have access to this data. Ask your administrator if you need a different role.",
        );
        setPhase("forbidden");
        return;
      }
      const msg =
        e instanceof Error ? e.message : "Something went wrong. Please try again.";
      setErrorMessage(msg);
      setPhase("error");
    }
  }, [load, isEmpty, timeoutMs]);

  useEffect(() => {
    if (!loadOnMount) return;
    void run();
  }, [loadOnMount, run]);

  const retry = useCallback(() => {
    void run();
  }, [run]);

  return {
    phase,
    data,
    errorMessage,
    accessDenied,
    retry,
    reload: retry,
  };
}
