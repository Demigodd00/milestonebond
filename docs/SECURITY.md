# Security and reviewer limitations

MilestoneBond v0.1 is a StudioNet prototype with simulated GEN. It is not audited and must not be used with real-value assets.

Critical external trust remains with GitHub availability, repository control, workflow configuration, CI runner/dependency integrity, and the meaning of sponsor-authored criteria. A repository owner could weaken tests before the commitment; the contract freezes workflow content, not the quality of its external dependencies. GenLayer validators provide independent retrieval and semantic agreement, not proof that code will behave safely in deployment.

This release intentionally restricts patches to a single direct-child commit, 1–4 modified allowlisted existing files, 24 KB of complete source, same-repository PRs, and a successful pinned push workflow. Large changes, forks, merge commits, changed workflows, binary files and missing evidence are unsupported. Do not work around a rejection by claiming a simulated result is live.

Onchain state can credit a withdrawal before the protocol’s outbound transfer is observed. Confirm both the `withdraw` receipt and any triggered native transfer before reporting funds received. Contract-wallet recipient failure modes are outside the tested scope.

Do not put account keys, GitHub tokens, private issue text, or personal data in terms or source. GitHub source and issue bodies are public and may be copied into onchain evidence. Report security issues privately to the repository owner rather than publishing exploit details.
