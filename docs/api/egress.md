# EgressFilter API

::: rlm.security.egress.EgressFilter
    options:
      show_source: true
      members:
        - filter
        - check_entropy
        - check_context_echo
        - check_secrets
        - truncate_output

## Utility Functions

::: rlm.security.egress.calculate_shannon_entropy

::: rlm.security.egress.calculate_similarity

::: rlm.security.egress.detect_secrets

::: rlm.security.egress.sanitize_output
