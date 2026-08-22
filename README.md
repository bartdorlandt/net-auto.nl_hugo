# net-auto.nl

Hugo site for NLNAM, the NL Network Automation Meetup.

## Setup

```bash
task init          # hugo and the theme submodule
cp .envrc.example .envrc   # then put the real PRETIX_API_TOKEN in it
direnv allow
```

The event scripts in `scripts/` are [PEP 723](https://peps.python.org/pep-0723/)
single-file scripts: each declares its own dependencies inline and uv installs
them on first run, so there is no project, no lockfile and no virtualenv to
manage. They are executable, so `./scripts/list_events.py` works as well as
`task event:list`.

## Running the site

```bash
task serve         # http://localhost:1313/
task build:strict  # build and fail on any warning
```

## Creating a new event

Event pages are the single source of truth. There is no `events.yaml`: the front
matter of `content/events/<YYYYMMDD>_<Sponsor>/index.md` is what the pretix
script and the reminder generator read back.

The whole flow, in one command:

```bash
task event
```

Or step by step:

```bash
task event:page      # prompts for date, sponsor, website, address
task event:pretix DATE=20270210      # clone a pretix event, create vouchers, go live
task reminders DATE=20270210         # LinkedIn posts + posting schedule
```

Useful extras:

```bash
task event:list                      # every event with its number and pretix slug
task event:pretix:dry DATE=20270210  # show the pretix payload without sending it
task reminders                       # defaults to the next upcoming event
```

`task event:page` derives the meetup number (one past the highest in use), the
pretix slug, the directory name and the registration URL, so those cannot drift
apart. After it runs, edit the page to fill in the agenda and parking details.

The page template is `archetypes/event.md`, in the usual Hugo location. Edit it
to change the default agenda or the boilerplate. Note that `hugo new --kind
event` will not produce a usable page on its own -- it cannot know the sponsor,
the meetup number or the event date -- so the archetype is filled in by
`task event:page` rather than by Hugo.

### Front matter

| Key                            | Meaning                                                             |
| ------------------------------ | ------------------------------------------------------------------- |
| `host` / `hostURL`             | Sponsor name and website                                            |
| `eventNumber`                  | Meetup number, used in the title and the pretix event name          |
| `pretixSlug`                   | Ticket-shop slug. Not `slug`: Hugo would treat that as the page URL |
| `venue`                        | Full address; rendered as a Google Maps link                        |
| `doorsOpen` / `endsAt`         | Times shown in the header, and the pretix admission time            |
| `registrationClosesDaysBefore` | Days before the event that registration closes                      |
| `cfpClosesDaysBefore`          | Days before the event that the call for papers closes               |

Generated LinkedIn posts land in `reminders/`, which is gitignored.

### Scripts

| Script                           | Purpose                                                   |
| -------------------------------- | --------------------------------------------------------- |
| `scripts/new_event.py`           | Write a new event page with derived number, slug and URLs |
| `scripts/create_pretix_event.py` | Clone a pretix event, create vouchers, go live            |
| `scripts/reminders.py`           | LinkedIn posts and the posting schedule                   |
| `scripts/list_events.py`         | List events with number, pretix slug and host             |
| `scripts/events.py`              | Shared reader for the event pages; imported, not run      |
