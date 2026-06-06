# Templates declare `requires_john`; apply checks it warn-only

A template built against one John layout can silently misbehave on another, so `template.json`'s `requires_john` (`>=X.Y.Z` or exact) is checked at apply time against the installed version — but a mismatch only warns, never blocks. Considered hard-blocking and rejected: templates routinely outlive minor John bumps unharmed, and a hard gate would force pointless re-packaging; the warning puts the risk on record and leaves the call with the user.
