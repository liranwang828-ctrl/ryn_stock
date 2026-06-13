# Output Packets

Output packets define how external tools, especially `stock_team`, hand results to `investing-os`.

They are not final knowledge. They are review envelopes.

## Packet Flow

```text
stock_team / ChatGPT / manual research
|
output packet
|
human review against WHY, constitution, framework, and discipline checks
|
wiki, journal, principle, thesis, or plan update
```

## Boundary

Packets may contain:

- facts
- evidence
- generated summaries
- metrics
- candidate actions
- open questions
- source references

Packets must not contain:

- autonomous trading permission
- hidden runtime state
- unreviewed rule changes
- broker credentials
- secrets
- irreversible instructions

## Packet Types

- `company-research-packet.md`
- `industry-research-packet.md`
- `pre-market-packet.md`
- `post-market-packet.md`
- `runtime-monitor-packet.md`
- `contextual-trade-evidence-packet.md`

## Status Values

Use one of:

- `draft`: not reviewed yet
- `reviewed`: checked by human or review agent
- `absorbed`: durable learning has been moved into wiki/templates/system files
- `rejected`: reviewed but not used

## Required Review Questions

Every packet must answer:

1. Does this support the WHY?
2. Is this fact, inference, or action suggestion?
3. What would make this wrong?
4. What should be updated, if anything?
5. What should remain temporary and not enter the wiki?
