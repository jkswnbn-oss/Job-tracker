# Job Tracker CLI

A command-line tool for tracking job applications through a search pipeline — companies, roles, stages, notes — stored in a local SQLite database.

I built this for two reasons: I'm running an active job search and wanted something faster than a spreadsheet, and I wanted to learn how to actually build a CLI using agentic coding tools instead of just reading about them.

## Commands

```
jobs add       # log a new application (company, role, stage, date, notes, URL)
jobs update    # move an application forward (e.g. to interview)
jobs list      # view active applications in a table
jobs show      # full detail on one application
jobs pipeline  # pipeline view by stage
jobs delete    # remove an entry
```

Built with Python, [Click](https://click.palletsprojects.com/) for the command interface, and [Rich](https://rich.readthedocs.io/) for table output. Data lives in a local SQLite database — nothing leaves your machine.

## How it was built

Entirely with Claude Code — from my phone. Coming from manually writing everything in school, the speed was the surprising part: the gap between "idea" and "working tool" has basically collapsed.

The honest version: my first attempt stalled because I bit off more than I could chew — the tool worked, but I couldn't explain every line of it, and a tool you can't explain isn't really yours. Coming back to it, I realized I was much further along than I thought. Now I'm working back through the codebase piece by piece until I can walk anyone through every decision in it.

## What's next

- `stats` — weekly rollup against my search quotas (applications and outreach touches per week)
- Stage-age warnings for applications sitting too long without a touch
- An LLM-generated pipeline digest via the Anthropic API

Suggestions welcome.