import { clsx, type ClassValue } from "clsx";
import { extendTailwindMerge } from "tailwind-merge";

// The design system defines custom font-size tokens (text-display/h1/h2/h3/
// body/small/caption). Plain tailwind-merge doesn't know these are font sizes,
// so it misclassified e.g. `text-body` as a text *color* and stripped a
// genuine `text-white` that appeared earlier in the class list — silently
// turning primary buttons' labels dark. Registering the tokens in the
// font-size group fixes the conflict resolution.
const twMerge = extendTailwindMerge({
  extend: {
    classGroups: {
      "font-size": [{ text: ["display", "h1", "h2", "h3", "body", "small", "caption"] }],
    },
  },
});

/** Merge conditional class names with Tailwind conflict resolution. */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
