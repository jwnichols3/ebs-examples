# CLAUDE.md

This repo's agent instructions live in **[AGENTS.md](./AGENTS.md)**. Read it - it is
canonical and this file only defers to it, so Claude, Codex, and any other agent work
from the same instructions.

The Slack routing is repeated below on purpose. Both files are auto-loaded, and a
routing decision made at the end of a run must not depend on following a link.

## Slack channels

Agent messages from this repo go to Slack, not to Rocket's DM.

- **Status** - `#rocket-a-ebs-projects` (`C0BR51EBJHW`)
- **Publications** - `#rocket-a-ebs-projects` (`C0BR51EBJHW`)

Post with `mcp__slack-mcp__post_message` using the **ID**, not the name. Open every
message with one line naming the project and the machine:

```
ebs-examples - <hostname -s>
```

The channel carries the project; it does not carry the machine, and Rocket runs this
repo from more than one box. Change a destination with `/setup-slack-routing`.
