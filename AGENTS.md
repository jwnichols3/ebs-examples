# ebs-examples - agent instructions

Canonical agent instructions for this repo. `CLAUDE.md` defers to this file so every
tool reads the same thing.

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
