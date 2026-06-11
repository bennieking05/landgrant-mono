import { useCallback, useRef, useState } from "react";

/**
 * Safe optimistic UI (UX-11).
 *
 * Applies an optimistic state update immediately, runs the async commit, and
 * automatically rolls back to the captured previous state if the commit throws.
 * Guarantees the UI never lies: a failed mutation reverts and surfaces an error.
 *
 * @example
 * const { run, pending } = useOptimisticAction<Task[]>();
 * run({
 *   current: tasks,
 *   optimistic: tasks.map(t => t.id === id ? { ...t, status: "completed" } : t),
 *   apply: setTasks,
 *   commit: () => completeTask(id),
 *   onError: (e) => toast.error(String(e)),
 * });
 */
export function useOptimisticAction<TState>() {
  const [pending, setPending] = useState(false);
  const inFlight = useRef(0);

  const run = useCallback(
    async (opts: {
      /** Snapshot to revert to on failure. */
      current: TState;
      /** Optimistic next state, applied immediately. */
      optimistic: TState;
      /** Setter that renders state (e.g. a useState setter). */
      apply: (next: TState) => void;
      /** The async mutation. Reject to trigger rollback. */
      commit: () => Promise<unknown>;
      /** Called after a successful commit (e.g. refetch authoritative data). */
      onSuccess?: () => void;
      /** Called with the error after rollback. */
      onError?: (error: unknown) => void;
    }) => {
      const { current, optimistic, apply, commit, onSuccess, onError } = opts;
      const id = ++inFlight.current;
      apply(optimistic);
      setPending(true);
      try {
        await commit();
        if (inFlight.current === id) onSuccess?.();
      } catch (error) {
        // Roll back to the snapshot; the optimistic state was a lie.
        apply(current);
        onError?.(error);
      } finally {
        if (inFlight.current === id) setPending(false);
      }
    },
    [],
  );

  return { run, pending };
}
