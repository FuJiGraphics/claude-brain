# registry - path prefixes and projects

If the working folder (or one of its parents) matches a prefix below, that is the project. The thalamus recalls memories only inside projects registered here.
No match means an unregistered folder, and nothing is recalled. The hippocampus does the registering: the nightly cycle hands it git folders you work in often, and /claude-brain-register asks for one right away.

| Path prefix | Project slug | Stack | Stack version | Note |
|---|---|---|---|---|

- At session start the thalamus shows the project's `projects/<slug>/INDEX.md`. Recall and search look at `projects/<slug>/`, `stacks/<stack>/` and `common/`, reading only the thin indexes and opening a memory file only when it matches.
- The note is shown at session start as the project gist (up to 500 characters). Keep it to one or two sentences: what the project is and where to look.
- The stack version filters lessons and step cards by version tag. When the project upgrades its engine, update only this column. If branches use different versions, list them per branch here.
- Projects without a stack (plain libraries and so on) put `-` in the stack column and skip the stack layer.
