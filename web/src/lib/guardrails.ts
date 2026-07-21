import { toast } from "sonner";

import type { GuardrailFinding } from "@/lib/api";

/**
 * Surface guardrail findings at log time.
 *
 * A caution is advisory -- the save already succeeded, so this informs rather
 * than blocks. A cannot_evaluate finding is shown too, deliberately: silence
 * would read as "all clear" when the truth is "couldn't check". Both linger
 * (10s) because they carry numbers worth reading, not a transient confirmation.
 */
export function showGuardrailFindings(findings: GuardrailFinding[] | undefined): void {
  for (const finding of findings ?? []) {
    if (finding.severity === "caution") {
      toast.warning(finding.title, { description: finding.message, duration: 10000 });
    } else if (finding.severity === "cannot_evaluate") {
      toast.info(finding.title, { description: finding.message, duration: 10000 });
    }
  }
}
