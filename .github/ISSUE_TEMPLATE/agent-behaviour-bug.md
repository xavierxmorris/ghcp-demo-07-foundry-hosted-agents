---
name: Agent behaviour bug
about: The agent said something wrong, fabricated, or unhelpful
title: '<agent>: <short description of the bad behaviour>'
labels: ['bug']
---

## What I asked

```
<the exact prompt>
```

## What it said

```
<the exact response>
```

## What it should have said

<!-- Be specific. "Better" is not actionable; "should have refused because the
corpus has nothing on processing fees" is. -->

## Trace ID

<!-- From the `azd ai agent invoke` output. Lets us pull the whole tool sequence
from Application Insights -- see docs/07-observability.md -->

```
Trace ID: <id>
```

## Which layer failed

<!-- Check what you know. If unsure, leave blank -- triage will work it out. -->

- [ ] The tool was never called → tool description problem
- [ ] The tool was called with wrong arguments → parameter description problem
- [ ] The tool returned wrong data → domain-logic bug (reproducible in `pytest`)
- [ ] The tool returned correct data but the answer was wrong → instructions problem

## Environment

- Agent + version: <!-- `azd ai agent show <agent> --output json` -->
- Local or deployed:
- `azd version`:

## Definition of done

- [ ] A failing unit test **or** eval case reproduces this
- [ ] The fix is in the correct layer
- [ ] The test/eval case now passes
